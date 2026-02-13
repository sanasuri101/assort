import os
import sys
import asyncio
import aiohttp
import logging
import weave
from typing import Optional, List

# Pipecat imports
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.frames.frames import Frame, TextFrame, EndFrame, LLMMessagesFrame, TranscriptionFrame, LLMFullResponseEndFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.processors.aggregators.llm_response import LLMUserContextAggregator, LLMAssistantContextAggregator
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.google import GoogleLLMService
from pipecat.transports.services.daily import DailyTransport, DailyParams, DailyTransportMessageFrame
from pipecat.vad.silero import SileroVADAnalyzer
from pipecat.vad.vad_analyzer import VADParams
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

# Redis imports
import redis.asyncio as redis

# Local imports
from app.config import settings
from app.voice.call_state import CallState, CallStateMachine
from app.voice.prompts import get_post_verification_prompt
from app.voice.prompt_manager import PromptManager
from app.voice.knowledge import KnowledgeBase, VALLEY_FAMILY_MEDICINE_FAQ
from app.voice.tools import TOOL_SCHEMAS, dispatch_tool
from app.services.ehr.factory import get_ehr_service
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class TranscriptLogger(FrameProcessor):
    """
    Logs transcriptions and text frames to Redis.
    Buffers assistant responses and logs complete sentences when LLM finishes.
    Matches wnbHack's bot.py pattern exactly.
    """

    def __init__(self, call_id: str, redis_service: RedisService, role: str = "user"):
        super().__init__()
        self.call_id = call_id
        self.redis_service = redis_service
        self.role = role  # "user" or "assistant"
        self.assistant_buffer = []  # Buffer for assistant words

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Log transcription frames (user speech)
        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip()
            if text:
                logger.info(f"[TRANSCRIPT] 👤 User: \"{text}\"")
                await self.redis_service.log_call_interaction(
                    self.call_id,
                    {"type": "user_speech", "text": text}
                )

        # Buffer text frames (assistant responses come word-by-word)
        elif isinstance(frame, TextFrame) and self.role == "assistant":
            text = frame.text
            if text:
                self.assistant_buffer.append(text)

        # When LLM finishes, log the complete response (wnbHack pattern)
        elif isinstance(frame, LLMFullResponseEndFrame) and self.role == "assistant":
            if self.assistant_buffer:
                complete_response = "".join(self.assistant_buffer).strip()
                if complete_response:
                    logger.info(f"[TRANSCRIPT] 🤖 Assistant: \"{complete_response}\"")
                    await self.redis_service.log_call_interaction(
                        self.call_id,
                        {"type": "assistant_speech", "text": complete_response}
                    )
                self.assistant_buffer = []  # Clear buffer

        # Pass frame through
        await self.push_frame(frame, direction)


async def run_agent(
    call_id: str,
    room_url: str,
    room_name: str
) -> None:
    """
    Run the Pipecat voice agent for a specific call.
    Matches the pattern from wnbHack's bot.py.
    """
    # Initialize Weave for real-time observability (wnbHack pattern extension)
    weave.init(f"assort-health-{settings.practice_name.lower().replace(' ', '-')}")
    
    logger.info(f"Starting agent for call {call_id} in room {room_name}")

    from app.services.redis_service import get_redis_service
    from app.services.daily_service import get_daily_service
    from app.voice.presence import PresenceHandler
    from app.voice.emergency import EmergencyDetector
    from app.voice.prompt_manager import PromptManager
    from app.services.ehr.factory import get_ehr_service
    import json

    redis_service = get_redis_service()
    daily_service = get_daily_service()
    ehr_service = get_ehr_service()
    prompt_manager = PromptManager()

    # Generate bot token
    bot_token = await daily_service.get_meeting_token(
        room_name=room_name,
        user_name="Assort Health AI",
        is_owner=True
    )

    # Initialize presence and state handlers
    presence_handler = PresenceHandler(
        call_id=call_id,
        redis_service=redis_service
    )
    call_state_machine = CallStateMachine(redis_service)

    try:
        # Configure Daily transport
        transport = DailyTransport(
            room_url=room_url,
            token=bot_token,
            bot_name="Assort Health AI",
            params=DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_enabled=True,
            )
        )

        # Configure STT, TTS, LLM (Healthcare Providers)
        stt = DeepgramSTTService(api_key=settings.deepgram_api_key)
        
        tts = CartesiaTTSService(
            api_key=settings.cartesia_api_key,
            voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22", # British Lady
        )

        llm = GoogleLLMService(
            api_key=settings.gemini_api_key,
            model=settings.voice_model,
        )

        # System prompt and conversation context
        system_instruction = prompt_manager.get_system_prompt()
        messages = [
            {"role": "system", "content": system_instruction}
        ]

        # Context and Aggregators (Pipecat 0.0.52 specific setup)
        context = OpenAILLMContext(messages, tools=TOOL_SCHEMAS)
        user_aggregator = LLMUserContextAggregator(context)
        assistant_aggregator = LLMAssistantContextAggregator(context)

        # Loggers (wnbHack pattern)
        user_transcript_logger = TranscriptLogger(call_id, redis_service, role="user")
        assistant_transcript_logger = TranscriptLogger(call_id, redis_service, role="assistant")

        # Emergency Detector
        emergency_detector = EmergencyDetector()

        # Tool handler (Healthcare specific)
        @weave.op()
        async def tools_handler(function_name, tool_call_id, args, llm, context, result_callback):
            logger.info(f"[Tool Call] {function_name}: {args}")
            
            # Execute tool
            result_json = await dispatch_tool(
                function_name, 
                args, 
                call_id, 
                call_state_machine, 
                ehr_service
            )
            
            # Identity Verification Gate
            if function_name == "verify_patient":
                try:
                    result_data = json.loads(result_json)
                    if result_data.get("verified"):
                        patient_name = result_data.get("patient_name", "Valued Patient")
                        new_prompt = get_post_verification_prompt(patient_name)
                        
                        # Update system prompt
                        sys_msg = {"role": "system", "content": new_prompt}
                        await task.queue_frames([LLMMessagesFrame([sys_msg])]) 
                        logger.info(f"Swapped system prompt for verified patient: {patient_name}")
                except Exception as e:
                    logger.error(f"Error checking verification result: {e}")

            await result_callback(result_json)

        # Register tools
        for tool in TOOL_SCHEMAS:
            llm.register_function(
                tool["function"]["name"],
                tools_handler,
                format=tool["function"]
            )

        # Build the pipeline (wnbHack recommended order)
        pipeline = Pipeline([
            transport.input(),              # Audio input from Daily
            stt,                            # Deepgram STT
            emergency_detector,             # Emergency Scanner
            user_transcript_logger,         # Log user speech
            user_aggregator,                # Aggregate user speech
            llm,                            # Gemini LLM
            assistant_transcript_logger,    # Log assistant response (buffered)
            tts,                            # Cartesia TTS
            transport.output(),             # Audio output to Daily
            assistant_aggregator,           # Aggregate assistant response
        ])

        # VAD is handled by transport params in this pipeline, or can be added as a processor
        # For simplicity and stability in 0.0.52, we rely on transport VAD if configured

        # Runner and Task
        runner = PipelineRunner()
        task = PipelineTask(
            pipeline, 
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True
            )
        )

        # Event handlers matching wnbHack
        @transport.event_handler("on_participant_joined")
        async def on_participant_joined(transport, participant):
            await presence_handler.on_participant_joined(participant)
            
            # Trigger greeting for human arrival
            if not participant.get("local", False):
                # wnbHack pattern: trigger greeting for human arrival
                logger.info(f"[Voice] Triggering greeting for human participant")
                messages.append({"role": "user", "content": "The patient has joined. Please greet them and ask how you can help."})
                await task.queue_frames([LLMMessagesFrame(messages)])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant):
            await presence_handler.on_participant_left(participant)

        @transport.event_handler("on_call_state_updated")
        async def on_call_state_updated(transport, state):
            if state == "left":
                await presence_handler.on_call_ended()

        logger.info(f"Starting pipeline for call {call_id}")
        await runner.run(task)

    except Exception as e:
        logger.error(f"Agent error for call {call_id}: {e}", exc_info=True)
        raise
    finally:
        await presence_handler.on_call_ended()
        logger.info(f"Agent exited for call {call_id}")


if __name__ == "__main__":
    # For standalone testing if needed
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--room-url", required=True)
    parser.add_argument("--room-name", required=True)
    parser.add_argument("--call-id", required=True)
    args = parser.parse_args()
    
    asyncio.run(run_agent(args.call_id, args.room_url, args.room_name))

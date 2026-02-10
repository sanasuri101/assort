import os
import sys
import asyncio
import aiohttp
import logging
from typing import Optional, List

# Pipecat imports
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.frames.frames import Frame, TextFrame, EndFrame, LLMMessagesFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.google import GoogleLLMService
from pipecat.transports.services.daily import DailyTransport, DailyParams, DailyTransportMessageFrame
from pipecat.vad.silero import SileroVADAnalyzer
from pipecat.processors.aggregators.google_llm_context import GoogleLLMContext

# Redis imports
import redis.asyncio as redis

# Local imports
from app.config import settings
from app.voice.call_state import CallState, CallStateMachine
from app.voice.prompts import PromptManager, get_post_verification_prompt
from app.voice.knowledge import KnowledgeBase, VALLEY_FAMILY_MEDICINE_FAQ
from app.voice.tools import TOOL_SCHEMAS, dispatch_tool
from app.services.ehr.factory import get_ehr_service

logger = logging.getLogger(__name__)

class RedisTranscriptLogger(FrameProcessor):
    def __init__(self, redis_url: str, call_id: str):
        super().__init__()
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.call_id = call_id
        self.transcript = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TextFrame):
            # Log transcript to Redis
            text = f"{direction.name}: {frame.text}"
            self.transcript.append({"role": direction.name, "content": frame.text})
            await self.redis.rpush(f"call:{self.call_id}:transcript", text)
        
        await self.push_frame(frame, direction)

    def get_transcript(self) -> List[dict]:
        return self.transcript

    async def cleanup(self):
        await self.redis.close()

class VoiceBot:
    def __init__(self, room_url: str, token: str, call_id: str, provider_id: str = "default"):
        self.room_url = room_url
        self.token = token
        self.call_id = call_id
        self.provider_id = provider_id
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def fetch_system_prompt(self) -> str:
        # Default prompt
        default_prompt = "You are a helpful healthcare assistant. You verify patient details and schedule appointments."
        
        # Try to get from Redis
        try:
            # For now, just use a simple key or default
            # stored_prompt = await self.redis.get(f"provider:{self.provider_id}:prompt")
            # if stored_prompt:
            #     return stored_prompt.decode("utf-8")
            pass
        except Exception as e:
            logger.error(f"Failed to fetch prompt from Redis: {e}")
            
        return default_prompt

    async def start(self):
        async with aiohttp.ClientSession() as session:
            # Initialize dependencies
            from app.voice.prompts import PRE_VERIFICATION_PROMPT, get_post_verification_prompt
            from app.voice.tools import TOOL_SCHEMAS, dispatch_tool
            from app.voice.call_state import CallStateMachine
            from app.services.ehr.mock import MockEHRAdapter
            import json

            # Initialize services
            # In a real app, these might be injected or singletons
            call_state = CallStateMachine(self.redis)
            ehr_service = get_ehr_service()

            # Initialize Knowledge Base Seeding (async)
            from app.voice.knowledge import KnowledgeBase, VALLEY_FAMILY_MEDICINE_FAQ
            async def seed_knowledge_base():
                kb = KnowledgeBase(settings.redis_url)
                try:
                    await kb.seed(VALLEY_FAMILY_MEDICINE_FAQ)
                    await kb.close()
                except Exception as e:
                    logger.error(f"Failed to seed KB: {e}")
            asyncio.create_task(seed_knowledge_base())
            
            # Initialize Prompt Manager
            from app.voice.prompt_manager import PromptManager
            prompt_manager = PromptManager()

            # Extract call ID and create initial state
            await call_state.create_call(self.call_id, self.provider_id)
            
            # Create transport
            transport = DailyTransport(
                self.room_url,
                self.token,
                "Assort Health AI",
                DailyParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                    camera_out_enabled=False,
                    vad_enabled=True,
                    vad_analyzer=SileroVADAnalyzer(),
                    vad_audio_passthrough=True,
                    transcription_enabled=False, # We use Deepgram
                )
            )

            stt = DeepgramSTTService(api_key=settings.deepgram_api_key)
            
            tts = CartesiaTTSService(
                api_key=settings.cartesia_api_key,
                voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22", # British Lady
            )

            # Use PromptManager to get system prompt
            system_instruction = prompt_manager.get_system_prompt()
            
            llm = GoogleLLMService(
                api_key=settings.gemini_api_key,
                model=settings.voice_model,
            )

            # Register tools define system messages
            messages = [
                {
                    "role": "system",
                    "content": system_instruction, # PRE_VERIFICATION prompt is inside PromptManager (assumed default)
                },
            ]
            
            # or just fire-and-forget.
            # actually, let's just do it here for now.
            try:
                await kb.seed(VALLEY_FAMILY_MEDICINE_FAQ)
                await kb.close()
            except Exception as e:
                logger.error(f"Failed to seed KB: {e}")

            # Register tools with LLM
            # ... (rest of code) ...
            # Note: in pipecat < 0.0.40, tools might be passed differently
            # but usually it's compatible with OpenAI format
            # llm.register_function(name, handler) is one way, but we want 
            # to handle dispatch ourselves or use the context. 
            
            # Defining the execution handler
            async def tools_handler(function_name, tool_call_id, args, llm, context, result_callback):
                logger.info(f"Tool call: {function_name} args={args}")
                
                # Execute tool
                result_json = await dispatch_tool(
                    function_name, 
                    args, 
                    self.call_id, 
                    call_state, 
                    ehr_service
                )
                
                # If verification succeeded, update system prompt
                if function_name == "verify_patient":
                    try:
                        result_data = json.loads(result_json)
                        if result_data.get("verified"):
                            patient_name = result_data.get("patient_name", "Valued Patient")
                            new_prompt = get_post_verification_prompt(patient_name)
                            
                            # Update system prompt in context
                            # We need to find the system message and update it
                            # GoogleLLMContext maintains messages list
                            sys_msg = {"role": "system", "content": new_prompt}
                            
                            # Updating context messages directly
                            # This is a bit internal-y but standard pattern in pipecat examples
                            # Context aggregator handles message history
                            await task.queue_frames([LLMMessagesFrame([sys_msg])]) 
                            logger.info(f"Swapped system prompt for verified patient: {patient_name}")
                    except Exception as e:
                        logger.error(f"Error checking verification result: {e}")

                # Send result back to LLM
                await result_callback(result_json)

            # Register functions with the LLM service
            # This registers schema AND the handler
            for tool in TOOL_SCHEMAS:
                llm.register_function(
                    tool["function"]["name"],
                    tools_handler,
                    format=tool["function"]
                )

            context = GoogleLLMContext(messages, tools=TOOL_SCHEMAS)
            context_aggregator = llm.create_context_aggregator(context)

            transcript_logger = RedisTranscriptLogger(settings.redis_url, self.call_id)

            from app.voice.emergency import EmergencyDetector
            emergency_detector = EmergencyDetector()
            
            pipeline = Pipeline([
                transport.input(),   # Transport user input
                stt,                 # STT
                emergency_detector,  # <--- Emergency Keyword Scanner
                transcript_logger,   # Log user text
                context_aggregator.user(), # User context
                llm,                 # LLM
                transcript_logger,   # Log bot text
                tts,                 # TTS
                transport.output(),  # Transport bot output
                context_aggregator.assistant(), # Assistant context
            ])

            task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

            @transport.event_handler("on_first_participant_joined")
            async def on_first_participant_joined(transport, participant):
                transport.capture_participant_transcription(participant["id"])
                # Kick off conversation
                # We already set the system prompt in 'messages' above
                await task.queue_frames([LLMMessagesFrame(messages)])

            @transport.event_handler("on_participant_left")
            async def on_participant_left(transport, participant, reason):
                logger.info(f"Participant left: {participant}")
                # Analyze outcome
                state = await call_state.get_state(call_id)
                call_info = await call_state.get_call_info(call_id)
                
                outcome = "abandoned"
                if call_info.get("scheduled") == "true":
                    outcome = "scheduled"
                    # Send SMS
                    patient_id = call_info.get("patient_id")
                    patient_phone = None
                    
                    if patient_id:
                        try:
                            # Fetch patient from EHR to get real phone number
                            patient = await ehr_service.lookup_patient_by_id(patient_id)
                            if patient and patient.telecom:
                                for telecom in patient.telecom:
                                    if telecom.system == "phone":
                                        patient_phone = telecom.value
                                        break
                        except Exception as e:
                            logger.error(f"Failed to fetch patient phone: {e}")

                    if patient_phone:
                        try:
                            from app.voice.sms import SMSService
                            sms = SMSService()
                            details = call_info.get("appointment_details", "an appointment")
                            await sms.send_confirmation(patient_phone, details)
                            logger.info(f"Sent confirmation SMS to {patient_phone}")
                        except Exception as e:
                            logger.error(f"Failed to send confirmation SMS: {e}")
                    else:
                        logger.warning(f"No phone number found for patient {patient_id}. Skipping SMS.")

                elif state == CallState.VERIFIED:
                    outcome = "answered"
                elif "emergency" in str(await transcript_logger.get_transcript()).lower(): 
                   # Crude check, better to have emergency detector set metadata
                   outcome = "emergency"
                
                # Store transcript for analysis
                full_transcript = transcript_logger.get_transcript()
                transcript_text = "\n".join([f"{entry['role']}: {entry['content']}" for entry in full_transcript])
                
                # We need a redis client here. Bot uses `call_state` which has redis, but it's encapsulated.
                # Let's instantiate a quick client or expose it from call_state.
                # Accessing settings.redis_url
                import redis.asyncio as redis
                r = redis.from_url(settings.redis_url, decode_responses=True)
                
                try:
                    await r.set(f"call:{self.call_id}:transcript", transcript_text, ex=86400) # 24h expiry
                    await r.xadd(settings.redis_stream_analysis, {"call_id": self.call_id})
                    logger.info("Queued call for analysis.")
                except Exception as e:
                    logger.error(f"Failed to queue analysis: {e}")
                finally:
                    await r.close()
                
                await task.cancel()
                await runner.stop()


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse
    import aiohttp
    
    parser = argparse.ArgumentParser(description="Start VoiceBot")
    parser.add_argument("-u", "--url", type=str, required=True, help="Daily room URL")
    parser.add_argument("-t", "--token", type=str, required=True, help="Daily room token")
    parser.add_argument("-p", "--provider", type=str, default="default", help="Provider ID")
    
    args = parser.parse_args()
    
    import uuid
    call_id = str(uuid.uuid4())
    bot = VoiceBot(args.url, args.token, call_id, args.provider)
    asyncio.run(bot.start())

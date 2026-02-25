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
from pipecat.frames.frames import (
    Frame, TextFrame, EndFrame, TranscriptionFrame,
    InterimTranscriptionFrame, LLMFullResponseEndFrame,
    UserStartedSpeakingFrame, UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.google import GoogleLLMService, GoogleLLMContext
from pipecat.transports.services.daily import DailyTransport, DailyParams, DailyTransportMessageFrame
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContextFrame

# Redis imports
import redis.asyncio as redis

# Local imports
from app.config import settings
from app.voice.call_state import CallState, CallStateMachine
from app.voice.prompts import get_post_verification_prompt
from app.voice.prompt_manager import PromptManager
from app.voice.knowledge import KnowledgeBase, VALLEY_FAMILY_MEDICINE_FAQ
from app.voice.tools import TOOL_SCHEMAS, dispatch_tool
from app.voice.thinking_phrases import get_thinking_phrase, clear_call_phrases
from app.voice.latency import LatencyTracker
from app.voice.kb_prefetch import KBPrefetcher
from app.services.ehr.factory import get_ehr_service
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class TranscriptLogger(FrameProcessor):
    """
    Logs assistant text frames to Redis.
    Buffers assistant responses and logs complete sentences when LLM finishes.
    Fire-and-forget Redis logging to avoid CancelledError blocking push_frame.
    """

    def __init__(self, call_id: str, redis_service: RedisService):
        super().__init__()
        self.call_id = call_id
        self.redis_service = redis_service
        self.assistant_buffer = []  # Buffer for assistant words

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Buffer text frames (assistant responses come word-by-word)
        if isinstance(frame, TextFrame):
            text = frame.text
            if text:
                self.assistant_buffer.append(text)

        # When LLM finishes, log the complete response
        elif isinstance(frame, LLMFullResponseEndFrame):
            if self.assistant_buffer:
                complete_response = "".join(self.assistant_buffer).strip()
                if complete_response:
                    logger.info(f"[TRANSCRIPT] Assistant: \"{complete_response}\"")
                    # Fire-and-forget — don't let Redis block frame flow
                    asyncio.create_task(self._log_safe(
                        {"type": "assistant_speech", "text": complete_response}
                    ))
                self.assistant_buffer = []  # Clear buffer

        # Pass frame through
        await self.push_frame(frame, direction)

    async def _log_safe(self, data: dict):
        try:
            await self.redis_service.log_call_interaction(self.call_id, data)
        except Exception as e:
            logger.warning(f"Redis log failed (non-fatal): {e}")


class UserTranscriptionLogger(FrameProcessor):
    """Log user transcriptions to Redis. Passes ALL frames through unchanged.

    Does NOT add to LLM context or trigger LLM calls — that's the
    user_aggregator's job. The aggregator waits for VAD end-of-speech
    before sending the complete utterance to the LLM, preventing:
      - Sentence-split fragments triggering separate LLM calls
      - Duplicate Deepgram finals cascading into TTS queue backup
      - Incomplete fragments confusing the LLM into greeting loops

    Redis logging is fire-and-forget.
    """

    DEDUP_WINDOW = 5.0

    def __init__(self, call_id: str, redis_service: RedisService):
        super().__init__()
        self._call_id = call_id
        self._redis_service = redis_service
        self._last_text: str = ""
        self._last_time: float = 0.0

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip() if hasattr(frame, "text") else ""
            if text:
                import time
                now = time.monotonic()

                # Dedup logging (don't log identical text within window)
                if text != self._last_text or (now - self._last_time) >= self.DEDUP_WINDOW:
                    self._last_text = text
                    self._last_time = now
                    logger.info(f"[TRANSCRIPT] User: \"{text}\"")
                    asyncio.create_task(self._log_safe(text))

        # Always pass ALL frames through — let aggregator handle context
        await self.push_frame(frame, direction)

    async def _log_safe(self, text: str):
        try:
            await self._redis_service.log_call_interaction(
                self._call_id,
                {"type": "user_speech", "text": text}
            )
        except Exception as e:
            logger.warning(f"Redis log failed (non-fatal): {e}")


class TranscriptionVADGuard(FrameProcessor):
    """Safety net: synthesizes VAD events when Deepgram transcribes speech
    that the local VAD misses.

    Problem: The aggregator only flushes transcriptions to the LLM when it
    receives UserStoppedSpeakingFrame from the VAD. If the local VAD doesn't
    detect speech (volume too low, noise conditions, etc.), transcriptions
    are silently dropped — the LLM never sees them.

    Solution: When a final TranscriptionFrame arrives without a preceding
    UserStartedSpeaking, this guard synthesizes the VAD events so the
    aggregator properly collects and flushes the text.

    Flow:
      1. TranscriptionFrame arrives, no active VAD session →
         push synthetic UserStartedSpeaking, then the TranscriptionFrame
      2. After DEBOUNCE_SECS of no new transcriptions →
         push synthetic UserStoppedSpeaking (triggers aggregator flush)
      3. If real VAD events arrive, cancel synthetic ones and defer to VAD
    """

    DEBOUNCE_SECS = 0.4  # Wait after last transcription before sending stop

    def __init__(self):
        super().__init__()
        self._vad_active = False
        self._synthetic_active = False
        self._debounce_task: Optional[asyncio.Task] = None

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStartedSpeakingFrame):
            self._vad_active = True
            # Real VAD took over — cancel any pending synthetic stop
            if self._synthetic_active:
                self._synthetic_active = False
                if self._debounce_task and not self._debounce_task.done():
                    self._debounce_task.cancel()
            await self.push_frame(frame, direction)

        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._vad_active = False
            # Real VAD fired stop — cancel synthetic
            if self._synthetic_active:
                self._synthetic_active = False
                if self._debounce_task and not self._debounce_task.done():
                    self._debounce_task.cancel()
            await self.push_frame(frame, direction)

        elif isinstance(frame, TranscriptionFrame):
            text = frame.text.strip() if hasattr(frame, "text") else ""
            if text and len(text) >= 2:
                if not self._vad_active and not self._synthetic_active:
                    # VAD missed this speech! Synthesize start event.
                    self._synthetic_active = True
                    logger.info(f"[VAD-GUARD] Synthesizing start for: \"{text[:60]}\"")
                    await self.push_frame(UserStartedSpeakingFrame(), direction)

                # Schedule/reschedule synthetic stop after debounce
                if self._synthetic_active:
                    if self._debounce_task and not self._debounce_task.done():
                        self._debounce_task.cancel()
                    self._debounce_task = asyncio.create_task(
                        self._delayed_stop(direction)
                    )

            # Always pass transcription through
            await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _delayed_stop(self, direction: FrameDirection):
        """After debounce period, synthesize UserStoppedSpeaking."""
        try:
            await asyncio.sleep(self.DEBOUNCE_SECS)
            if self._synthetic_active:
                self._synthetic_active = False
                self._vad_active = False
                logger.info("[VAD-GUARD] Synthesizing stop (debounce expired)")
                await self.push_frame(UserStoppedSpeakingFrame(), direction)
        except asyncio.CancelledError:
            pass  # New transcription arrived, debounce reset


def _convert_tools_to_google(openai_schemas: list) -> list:
    """Convert OpenAI-format tool schemas to Google protos.Tool objects.

    OpenAI uses lowercase type strings ("object", "string") and wraps each
    tool in {"type": "function", "function": {...}}.  Google's API expects
    protos.FunctionDeclaration with uppercase Type enums (OBJECT, STRING).
    """
    import google.generativeai as genai

    TYPE_MAP = {
        "string": genai.protos.Type.STRING,
        "number": genai.protos.Type.NUMBER,
        "integer": genai.protos.Type.INTEGER,
        "boolean": genai.protos.Type.BOOLEAN,
        "array": genai.protos.Type.ARRAY,
        "object": genai.protos.Type.OBJECT,
    }

    def _convert_schema(schema: dict) -> genai.protos.Schema:
        kwargs: dict = {}
        if "type" in schema:
            kwargs["type"] = TYPE_MAP[schema["type"]]
        if "description" in schema:
            kwargs["description"] = schema["description"]
        if "enum" in schema:
            kwargs["enum"] = schema["enum"]
        if "required" in schema:
            kwargs["required"] = schema["required"]
        if "properties" in schema:
            kwargs["properties"] = {
                k: _convert_schema(v) for k, v in schema["properties"].items()
            }
        if "items" in schema:
            kwargs["items"] = _convert_schema(schema["items"])
        return genai.protos.Schema(**kwargs)

    declarations = []
    for tool in openai_schemas:
        func = tool["function"]
        fd = genai.protos.FunctionDeclaration(
            name=func["name"],
            description=func["description"],
            parameters=_convert_schema(func.get("parameters", {})),
        )
        declarations.append(fd)

    return [genai.protos.Tool(function_declarations=declarations)]


async def run_agent(
    call_id: str,
    room_url: str,
    room_name: str
) -> None:
    """
    Run the Pipecat voice agent for a specific call.

    Latency-optimized pipeline:
      - KB pre-loaded at call start (warm connection, seeded)
      - Thinking phrases fill dead air during tool calls
      - KB prefetcher starts lookups on stabilized STT partials
      - Latency tracker measures TTFT/TTFA per turn
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

    # ── Context Pre-Loading ─────────────────────────────────────────
    # Create KB singleton ONCE at call start. Seed FAQ data.
    # The KB connection stays warm for the entire call duration.
    kb = KnowledgeBase(settings.redis_url)
    await kb.seed(VALLEY_FAMILY_MEDICINE_FAQ)
    logger.info(f"[PRELOAD] KB pre-loaded with {len(VALLEY_FAMILY_MEDICINE_FAQ)} FAQ items")

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

    # Declare variables used in finally block so cleanup works even if
    # DailyTransport init fails (e.g. virtual speaker device conflict).
    latency_tracker = None

    try:
        # Configure Daily transport
        transport = DailyTransport(
            room_url=room_url,
            token=bot_token,
            bot_name="Assort Health AI",
            params=DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                audio_out_is_live=True,
                vad_enabled=True,
                vad_audio_passthrough=True,
                vad_analyzer=SileroVADAnalyzer(
                    params=VADParams(
                        confidence=0.5,    # Lower threshold (was 0.7 default)
                        start_secs=0.15,   # Faster speech start detection
                        stop_secs=0.4,     # Faster end-of-speech (was 0.6)
                        min_volume=0.2,    # Much lower volume gate (was 0.6!)
                    )
                ),
            )
        )

        # Configure STT, TTS, LLM
        # endpointing=500 gives Deepgram a wider window to consolidate
        # speech into a single final, preventing duplicate transcriptions
        # that cascade into multiple LLM calls and TTS queue backup.
        from deepgram import LiveOptions
        stt = DeepgramSTTService(
            api_key=settings.deepgram_api_key,
            live_options=LiveOptions(
                endpointing=350,
                interim_results=True,
                smart_format=True,
            ),
        )

        tts = CartesiaTTSService(
            api_key=settings.cartesia_api_key,
            voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",  # British Lady
        )

        # System prompt passed via GoogleLLMService (not as a message —
        # Google's API uses system_instruction on the model, not in messages)
        system_instruction = prompt_manager.get_system_prompt()

        llm = GoogleLLMService(
            api_key=settings.gemini_api_key,
            model=settings.voice_model,
            system_instruction=system_instruction,
        )

        # Context and Aggregators — use GoogleLLMContext directly so that
        # Google-native aggregators add glm.Content objects without needing
        # the fragile OpenAI→Google upgrade/conversion path.
        # Tools must be google.ai.generativelanguage protos, not OpenAI dicts.
        google_tools = _convert_tools_to_google(TOOL_SCHEMAS)
        context = GoogleLLMContext(messages=[], tools=google_tools)
        context_aggregator = GoogleLLMService.create_context_aggregator(context)
        user_aggregator = context_aggregator.user()
        assistant_aggregator = context_aggregator.assistant()

        # Assistant transcript logger (user logging is handled by DirectTranscriptionHandler)
        assistant_transcript_logger = TranscriptLogger(call_id, redis_service)

        # Emergency Detector
        emergency_detector = EmergencyDetector()

        # ── Latency-Optimized Processors ────────────────────────────
        # Latency Tracker: measures TTFT, TTFA, tool duration per turn
        latency_tracker = LatencyTracker(
            call_id=call_id,
            redis_service=redis_service,
        )

        # KB Prefetcher: speculative lookups on stabilized STT partials
        kb_prefetcher = KBPrefetcher(kb=kb)

        # User transcription logger: logs to Redis, passes ALL frames
        # through to the user_aggregator which handles VAD-based turn
        # detection and sends complete utterances to the LLM.
        user_transcript_logger = UserTranscriptionLogger(
            call_id=call_id,
            redis_service=redis_service,
        )

        # VAD guard: synthesizes VAD events when Deepgram transcribes
        # speech the local VAD misses (e.g. quiet speakers, noise)
        vad_guard = TranscriptionVADGuard()

        # ── Tool Configuration ──────────────────────────────────────
        # EHR tools can be slow in production (1-8s). Thinking phrases
        # fill dead air during these calls. KB lookups are fast (~200ms)
        # so they DON'T get phrases (would add latency, not reduce it).
        SLOW_TOOLS = {
            "verify_patient", "get_availability", "book_appointment",
            "check_insurance", "list_providers",
        }
        TOOL_TIMEOUT_SECS = 8.0  # Hard timeout for any tool call

        @weave.op()
        async def tools_handler(function_name, tool_call_id, args, llm, context, result_callback):
            logger.info(f"[Tool Call] {function_name}: {args}")

            # ── Thinking phrase for slow tools ─────────────────
            # Play a context-aware filler while EHR tools execute.
            # KB lookups skip this — they're faster than TTS synthesis.
            if function_name in SLOW_TOOLS:
                phrase = get_thinking_phrase(function_name, call_id)
                await task.queue_frames([TTSSpeakFrame(text=phrase)])
                logger.info(f"[Thinking] Playing: \"{phrase}\"")

            # ── Latency Tracking ────────────────────────────────
            latency_tracker.mark_tool_start()

            # ── Execute Tool with timeout ───────────────────────
            try:
                result_json = await asyncio.wait_for(
                    dispatch_tool(
                        function_name,
                        args,
                        call_id,
                        call_state_machine,
                        ehr_service,
                        kb=kb,
                        prefetcher=kb_prefetcher,
                    ),
                    timeout=TOOL_TIMEOUT_SECS,
                )
            except asyncio.TimeoutError:
                logger.error(f"[Tool] {function_name} timed out after {TOOL_TIMEOUT_SECS}s")
                result_json = json.dumps({
                    "error": "timeout",
                    "message": "I'm sorry, that's taking longer than expected. Could you try again?",
                })

            latency_tracker.mark_tool_end()
            
            # Identity Verification Gate
            if function_name == "verify_patient":
                try:
                    result_data = json.loads(result_json)
                    if result_data.get("verified"):
                        patient_name = result_data.get("patient_name", "Valued Patient")
                        new_prompt = get_post_verification_prompt(patient_name)

                        # Update system instruction — GoogleLLMService detects the
                        # change on the next _process_context and recreates the client
                        context.system_message = new_prompt
                        logger.info(f"Updated system instruction for verified patient: {patient_name}")
                except Exception as e:
                    logger.error(f"Error checking verification result: {e}")

            await result_callback(result_json)

        # Register tools
        for tool in TOOL_SCHEMAS:
            llm.register_function(
                tool["function"]["name"],
                tools_handler,
            )

        # Build the pipeline — optimized for minimum LLM→TTS latency.
        #
        # Key design decisions (learned from RealtimeVoiceChat):
        #   1. LLM→TTS is DIRECT with zero intermediate processors
        #   2. User aggregator handles VAD-based turn detection —
        #      waits for complete utterance before sending to LLM
        #      (prevents sentence-split fragments from triggering
        #      separate LLM calls and TTS queue backup)
        #   3. No thinking phrases — KB lookups (300ms) complete
        #      faster than TTS can synthesize a filler phrase
        #   4. Latency/logging observers placed AFTER audio output
        #
        # Flow: Audio → STT → Log → Prefetch → Emergency →
        #       Aggregator(VAD) → LLM → TTS → Output →
        #       Tracker → Logger → AssistantAgg
        pipeline = Pipeline([
            transport.input(),              # Audio input from Daily
            stt,                            # Deepgram STT
            user_transcript_logger,         # Log user speech (pass-through)
            kb_prefetcher,                  # Speculative KB lookup on partials
            emergency_detector,             # Emergency Scanner
            vad_guard,                      # Synthesize VAD if local VAD misses speech
            user_aggregator,                # VAD-based turn detection → LLM
            llm,                            # Gemini LLM
            tts,                            # Cartesia TTS (DIRECT from LLM)
            transport.output(),             # Audio output to Daily
            latency_tracker,                # Observe after output
            assistant_transcript_logger,    # Log after output
            assistant_aggregator,           # Aggregate assistant response
        ])

        # Runner and Task
        runner = PipelineRunner()
        task = PipelineTask(
            pipeline, 
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True
            )
        )

        # ── TTS Pre-Warm ──────────────────────────────────────────
        # Cartesia WebSocket has a cold-start penalty (first TTFB can be
        # 3-6s vs ~0.7s warmed). We warm up by sending a tiny synthesis
        # request shortly after the pipeline starts (before any human joins).
        # This primes the WebSocket, loads the voice model on Cartesia's
        # side, and ensures the greeting response has warm TTS.
        from pipecat.frames.frames import TTSSpeakFrame

        async def _delayed_tts_warmup():
            """Wait for pipeline to initialize, then warm Cartesia."""
            await asyncio.sleep(0.5)  # Let pipeline start
            try:
                await task.queue_frames([TTSSpeakFrame(text="Warm")])
                logger.info("[TTS] Pre-warmed Cartesia connection")
            except Exception as e:
                logger.warning(f"[TTS] Warmup failed (non-fatal): {e}")

        # Event handlers
        @transport.event_handler("on_participant_joined")
        async def on_participant_joined(transport, participant):
            await presence_handler.on_participant_joined(participant)

            # Trigger greeting for human arrival (bot join doesn't have this flag)
            if not participant.get("info", {}).get("isLocal", participant.get("local", False)):
                logger.info(f"[Voice] Triggering greeting for human participant")
                context.add_messages([{"role": "user", "content": "The patient has joined. Please greet them and ask how you can help."}])
                await task.queue_frames([OpenAILLMContextFrame(context)])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            await presence_handler.on_participant_left(participant)

        @transport.event_handler("on_call_state_updated")
        async def on_call_state_updated(transport, state):
            if state == "left":
                await presence_handler.on_call_ended()

        logger.info(f"Starting pipeline for call {call_id}")
        # Launch TTS warmup as background task — runs after pipeline starts
        asyncio.create_task(_delayed_tts_warmup())
        await runner.run(task)

    except Exception as e:
        logger.error(f"Agent error for call {call_id}: {e}", exc_info=True)
        raise
    finally:
        # ── Cleanup ─────────────────────────────────────────────────
        # Log latency summary before shutdown (guard against early crash)
        if latency_tracker is not None:
            summary = latency_tracker.get_summary()
            logger.info(f"[CALL END] Latency summary for {call_id}: {summary}")

        # Clean up thinking phrase tracking
        clear_call_phrases(call_id)

        # Close KB connection
        await kb.close()

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

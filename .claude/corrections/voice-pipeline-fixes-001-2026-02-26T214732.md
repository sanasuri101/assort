# Drift Guard Correction - 2026-02-26T21:47:32Z

**Session:** voice-pipeline-fixes-001
**Score:** 3/100
**Status:** critical drift - zero implementation

**Problem:** The branch contains only correction metadata files. No actual voice pipeline implementation exists.

**Required Actions:**

1. Create `backend/app/voice/bot.py` - Implement the Pipecat pipeline with this structure:
   - Transport (Daily.co) → STT (Deepgram) → RedisTranscriptLogger (custom FrameProcessor) → LLM Context → OpenAI LLM → Logger → TTS (Cartesia) → Transport
   - Include Silero VAd integration and BackgroundTasks-based bot lifecycle management

2. Create `backend/app/voice/call_state.py` - Implement CallStateMachine using Redis hash for current state storage and Redis Streams for audit trail. States must include: INITIATED, RINGING, IN_PROGRESS, ON_HOLD, COMPLETED, FAILED.

3. Create `backend/app/routers/voice.py` - Implement Twilio webhook endpoint that generates TwiML to bridge calls via Daily.co SIP. Use FastAPI BackgroundTasks to spawn the bot process.

4. Create `backend/app/voice/__init__.py` - Package init file.

5. Create `tests/conftest.py` - Add module mocking for all pipecat, daily-python, silero, and torchaudio modules so tests pass on Windows/CI without native deps.

6. Add required dependencies to requirements: pipecat-ai, daily-python, deepgram-sdk, cartesia, silero-vad, torchaudio, aiohttp.

**PRD Reference:** .planning/phases/03-voice-pipeline/03-SUMMARY.gd

**Target:** 22 passing tests across voice pipeline components.

**Warning:** Stop creating correction files. The .claude/corrections/ directory already has 2 correction files - stop adding metadata and start building the pipeline.
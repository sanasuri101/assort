#Critical Correction: Voice Pipeline Fixes - Score 4/100

## Drift Analysis

This branch has catastrophically failed to implement any PRD requirements. All 17 commits consist exclusively of drift-guard correction metadata files under .claud/corrections/ and a trace log - no actual source code has been written.

## REQUIRED IMPLEMENTATION - Stop writing corrections, write code now

You must immediately implement the following PRD artifacts:

1. **backend/app/voice/bot.py** - Create VoiceBot class with full Pipecat pipeline:
   - Transport (Daily.co WebRTC) → STT (Deepgram) → RedisTranscriptLogger (custom FrameProcessor) → Context → LMM (OpenAI GPT-4o) → Logger → TTS (Cartesia) → Transport
   - Include Silero VAD for interruption handling

2. **backend/app/voice/call_state.py** - Implement CallStateMachine:
   - Redis hash for state storage + Redis Streams audit trail (call:{id}:events)
   - Valid transitions: RINGING→GREETING→OUTING↓VERIFIED→ESOLVING↓COMPLETED
   - TRANSFERRING↓RANSFERDED and ABANDONED branches

3. **backend/app/routers/voice.py** - Implement four endpoints:
   - POST /session
   - POST /agent/start
   - POST /incoming (Twilio TwiML/SIP bridge to Daily.co)
   - GET /status

4. **backend/app/main.py** - Register voice and EHR routers

5. **backend/tests/test_voice_api.py** - API tests with mocked Pipecat dependencies

6. **backend/tests/test_call_state.py** - Minimum 6 unit tests covering all state machine transitions

7. **backend/tests/conftest.py** - Add pipecat module mocking for Windows-incompatible native deps (daily-python, silero-vad, torchaudio)

8. **backend/app/services/__init__.py** and **backend/app/services/ehr/__init__.py** - Package init files

## Success Criteria

- All 22 tests must pass
- Pipecat pipeline must handle streaming, VAD, interruptions
- Redis call state machine must persist state and audit trail
- Twilio webhook must bridge to Daily.co via SIP

---
**NOTE:** This branch is 27 commits behind main. Consider rebasing before continuing implementation.
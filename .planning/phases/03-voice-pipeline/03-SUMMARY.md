---
phase: 03-voice-pipeline
plan: 03-04
name: Voice Pipeline
status: complete
completed: 2026-02-09
duration: ~45min
tasks_completed: 4
files_created: 6
tests_passed: 22

dependency-graph:
  provides:
    - backend/app/voice/bot.py
    - backend/app/voice/call_state.py
    - backend/app/routers/voice.py
  affects:
    - Phase 4 (Healthcare Call Flow) - depends on pipeline + state machine
    - Phase 5 (Learning Engine) - consumes transcripts from Redis streams

tech-stack:
  added:
    - pipecat-ai (Daily, Deepgram, Cartesia, OpenAI plugins)
    - daily-python (WebRTC transport)
    - deepgram-sdk (STT)
    - cartesia (TTS)
    - silero-vad + torchaudio (Voice Activity Detection)
    - aiohttp (async HTTP sessions)

patterns-established:
  - "Pipecat Pipeline: Transport → STT → Logger → Context → LLM → Logger → TTS → Transport"
  - "RedisTranscriptLogger as a custom FrameProcessor for HIPAA logging"
  - "CallStateMachine with Redis hash + Redis Streams audit trail"
  - "Twilio webhook → Daily.co SIP bridge via TwiML"
  - "BackgroundTasks for bot lifecycle (production: use Celery/RQ)"
  - "Module mocking in conftest.py for Windows-incompatible native deps"

key-decisions:
  - "Pipecat for pipeline orchestration — handles streaming, VAD, interruptions natively"
  - "Daily.co as WebRTC transport — supports SIP dial-in for Twilio bridging"
  - "Silero VAD for speech boundary detection — lightweight, no cloud dependency"
  - "Call state machine uses Redis hash (state) + Redis Streams (audit log)"
  - "Bot spawns via BackgroundTasks for MVP; production should use worker queue"
  - "daily-python incompatible on Windows — tests mock all pipecat modules"
---

# Phase 3: Voice Pipeline — Summary

## What Was Built

Full voice pipeline using Pipecat with Daily.co WebRTC transport, Deepgram STT, OpenAI GPT-4o LLM, and Cartesia TTS. Includes VAD-based interruption handling, Redis transcript logging, call state machine with HIPAA audit trail, and Twilio SIP webhook for PSTN inbound calls.

## Files Created / Modified

### Voice Engine
- `backend/app/voice/bot.py` — VoiceBot class with Pipecat pipeline, RedisTranscriptLogger
- `backend/app/voice/call_state.py` — Redis-backed CallStateMachine with valid transitions and audit trail

### API Layer
- `backend/app/routers/voice.py` — Endpoints: `/session`, `/agent/start`, `/incoming` (Twilio), `/status`
- `backend/app/main.py` — Updated: voice + EHR routers registered

### Tests
- `backend/tests/test_voice_api.py` — API tests with mocked Pipecat dependencies
- `backend/tests/test_call_state.py` — 6 unit tests for state machine transitions
- `backend/tests/conftest.py` — Updated: pipecat module mocking, EHR service init

### Packaging
- `backend/app/services/__init__.py` — Package init
- `backend/app/services/ehr/__init__.py` — Package init

## Call State Machine

```
RINGING → GREETING → ROUTING → VERIFIED → RESOLVING → COMPLETED
                                    ↓
                              TRANSFERRING → TRANSFERRED
                                    ↓
                               ABANDONED
```

All transitions logged to Redis Stream `call:{id}:events` for HIPAA compliance.

## Test Results

22 passed, 0 failed.

## Next Phase

**Phase 4: Healthcare Call Flow**
Identity verification gate, scheduling flow with EHR function calls, knowledge base via Redis vector search, emergency detection, and SMS confirmation.

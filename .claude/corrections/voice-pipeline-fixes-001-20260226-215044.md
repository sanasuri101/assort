# Drift Correction - Session voice-pipeline-fixes-001
**Generated:** 2026-02-26 21:50:44 UTC  
**Alignment Score:** 2/100  
**Drift Detected:** YES  
** Branch:** feat/voice-pipeline-fixes  
**Status:** CRITICAL - No implementation files exist

## Problem Summary
The branch contains zero implementation files. All 7 commits are drift-guard correction metadata files and a trace log — no actual source code was written for the Phase 3 Voice Pipeline.

## Required Action

### 1. Create Voice Bot Implementation
**File:** `backend/app/voice/bot.py`
- Implement `VoiceBot` class using Pipecat pipeline
- Pipeline order: Daily.co WebRTC Transport → Deepgram STT ↓ RedisTranscriptLogger ₘ OpenAI Context Aggregator ₘ OpenAI GPT-4o LLM ↓ RedisTranscriptLogger ₘ Cartesia TTS ↓ Transport
- Enable Silero VAD for speech boundary detection
- `RedisTranscriptLogger` must write transcripts to Redis Streams for HIPAA compliance

### 2. Create Call State Machine
**File:** `backend/app/voice/call_state.py`
- Implement CallStateMachine backed by Redis hash for current state
- Use Redis Stream `call:{id}:events` for audit trail
- Valid transitions:
  - RINGING→GREETING→ROUTING↓TERIFIED→ESOLVING↓COMPLETED
  - VERIFIED→TRANSFERRING→TRANSFERRED
  - RESOLVING↓ABANDONED

  - VERIFIED→ABANDONED

##3 3. Create Voice Router
**File:** `backend/app/routers/voice.py`
Implement four endpoints:
- POST `/session` - Create Daily.co room
- POST `/agent/start` - Spawn VoiceBot via BackgroundTasks
- POST `/incoming` - Twilio webhook returning TwiML for SIP bridge to Daily.co
- GET  `/status` - Return call state from Redis

### 4. Update Main App
**File:** `backend/app/main.py`
- Register the voice router
- Register the EHR router

##3 5. Create Tests
**File:** `backend/tests/test_voice_api.py`
- API tests with all pipecat/daily/deepgram/cartesia/silero modules mocked via conftest.py

**File:** `backend/tests/test_call_state.py`
- Minimum 6 unit tests covering valid state transitions and invalid transition rejection

**File:** `backend/tests/conftest.py`
- Mock all pipecat, daily-python, deepgram-sdk, cartesia, and silero/torchaudio modules
- Ensure tests pass on Windows and CI without native deps

### 6. Add Dependencies
**File:** `backend/app/services/redis.py`
- Add Redis client for state management and streams

**File:** `backend/requirements.txt`
- Add: pipecat-ai, daily-python, deepgram-sdk, cartesia, silero-vad, torchaudio, aiohttp

## Tech Stack Reminder
- Pipecat for pipeline orchestration
- Daily.co as WebRTC transport (supports SIP dial-in)
- Silero VAD for speech boundary detection
- Redis hash + Redis Streams for state and audit
- BackgroundTasks for MVP (use Celery/RQ in production)

## STOP WRITING CORRECTION FILES
Start writing actual implementation code. The drift-guard has already injected 6 corrections. No more metadata files.
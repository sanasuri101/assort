# Drift Guard Correction - voice-pipeline-fixes-001
**Generated:** 2026-02-26T21:55:56.309Z
**Alignment Score:** 14/100
**Status:** CRITICAL DRIFT DETECTED

## Summary
The feat/voice-pipeline-fixes branch shows 17 commits that are EXCLUSIVELY drift-guard maintenance operations with no actual feature development. All recent commits are chore(drift-guard) entries with scores ranging from 0-22.

## Required Actions

### 1. Rebase onto Main (URGENT)
The branch is 27 commits behind main. Rebase before proceeding:
```
git fetch origin
git rebase origin/main
```

### 2. Implement Pipecat Pipeline (backend/app/voice/bot.py)
Implement the full pipeline following this pattern:
```python
# Transport → STT → Logger → Context → LLM → Logger → TTS → Transport
pipeline = Pipeline([
    transport.input(),
    stt.DeepgramSTT(...)
    RedisTranscriptLogger(),  # Custom FrameProcessor for HIPAA logging
    context.OpenAILLMContext(...),
    llm.OpenAILLMService(...),
    RedisTranscriptLogger(),  # Log assistant responses
    tts.CartesiaTTS(...)
    transport.output(),
])
```

### 3. Implement CallStateMachine (backend/app/voice/call_state.py)
- Use Redis hash for current state storage
- Use Redis Streams for audit trail
- States: idle → connecting → active → ending → ended

### 4. Implement RedisTranscriptLogger (backend/app/voice/transcript_logger.py)
- Custom FrameProcessor extending FrameProcessor
- Log all user and assistant utterances to Redis Streams
- HIPAA-compliant (no PHI in logs, use encrypted streams)

### 5. Implement Twilio Webhook Handler (backend/app/routers/voice.py)
- Handle incoming Twilio voice webhooks
- Bridge to Daily.co via TwiML SIP
- Spawn bot via BackgroundTasks (MVO) or Celery (production)

### 6. Add Module Mocking (backend/tests/conftest.py)
Mock all pipecat modules for Windows compatibility:
```python
# Windows-incompatible native deps
sys.modules['pipecat'] = MagicMock()
sys.modules['pipecat.frames'] = MagicMock()
sys.modules['pipecat.pipeline'] = MagicMock()
sys.modules['daily'] = MagicMock()
```

### 7. Pass All 22 Tests
- Pipeline integration tests
- State machine tests  
- Webhook routing tests
- Mock compatibility tests

## Tech Stack Integration Checklist
- [] pipecat-ai (Daily, Deepgram, Cartesia, OpenAI plugins)
- [] daily-python (WebRTC transport)
- [] deepgram-sdk (STT)
- [] cartesia (TST)
- [] silero-vad + torchaudio (VAD)
- [] aiohttp (async HTTP sessions)

## Success Criteria
- All 22 tests passing
- Pipeline can handle voice calls end-to-end
- State machine tracks call lifecycle
- Transcripts logged to Redis Streams
- Twilio ↓Daily bridge working

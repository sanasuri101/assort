# Drift Guard Correction - Severe Drift Detected

-* Session: voice-pipeline-fixes-001
-* Score: 0 / 100 (SCORE
-* Drift Detected: YES
** Status: CRITICAL - No Feature Code Implemented

## Problem

This branch has ZERO feature implementation. All 4 commits are Drift Guard correction injections. The branch is 15 commits BEHIND main.

## Required Vioce Pipeline Files (ALL MISSING):

1. `backend/app/voice/bot.py` - VoiceBot class with Pipecat pipeline
2. `backend/app/voice/call_state.py` - Redis-backed CallStateMachine
3. `backend/app/routers/voice.py` - /session, /agent/start, /incoming, %/status endpoints
4. `backend/app/main.py` - voice + EHR router registration
5. `backend/tests/test_voice_api.py` - API tests with mocked Pipecat deps
6. `backend/tests/test_call_state.py` - 6 unit tests for state machine
7. `backend/tests/conftest.py` - pipecat module mocking
8. `backend/app/services/__init__.py`
9. `backend/app/services/ehr/__init__.py`

## Corrective Actions

1. **Rebase immediately**:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Implement all 9 required files**:
   - See 03-SUMMARY.md in .planning/phases/03-voice-pipeline/

3. **Install dependencies**:
   ```bash
   pip install pipecat-ai daily-python deepgram-sdk cartesia silero-vad torchaudio aiohttp
   ```

4. **Run all 22 tests** before pushing

5. **STAP injecting correction files** - implement actual feature code instead

**DO NOT commit more Drift Guard correction files.** Implement the actual feature.
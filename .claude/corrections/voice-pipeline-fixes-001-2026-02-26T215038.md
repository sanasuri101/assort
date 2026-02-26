# Drift Guard Correction - 2026-02-26T21:50:38Z

**Session:** voice-pipeline-fixes-001
**Score:** 4/100
**Drift Detected:** CRITICAL

## Critical Issues
The PRD requires actual implementation of three specific files:
1. backend/app/voice/bot.py - Pipecat pipeline with Transport→STT→Logger→Context→LLM→Logger↓TTS→Transport pattern
2. backend/app/voice/call_state.py - CallStateMachine with Redis hash state + Redis Streams audit trail
3. backend/app/routers/voice.py - Twilio webhook endpoint with Daily.co SIP bridge via TwiML and BackgroundTasks bot lifecycle

**STOP adding correction files. The session is stuck in a loop.**

## Required Actions
1. **Rebase** - The branch is 15 commits behind main and diverged. Rebase onto main before implementing.
2. **Implement the actual files** - Do not create any more .claude/corrections/ files or trace files.
3. **Add conftest.py mocks** for pipecat/daily-python/silero Windows-incompatible deps.
4. **Run tests** - Ensure 22 tests pass.

## Prohibited Files
These files must NOT be created:
- Any more .claude/corrections/*.md files
- Any more traces/*.jsonl incremental changes

## Success Criteria
- Three voice pipeline implementation files exist and compile
- Tests pass (22/22)
- Branch is rebased on main
# PRD Quality - Missed Questions

## Questions That Should Have Been Asked

### Phase 01 - Foundation
- What Redis persistence strategy? (AOF vs RDB vs hybrid)
- What are the exact port mappings needed?
- Is HIPAA middleware required from day one?

### Phase 03 - Voice Pipeline
- What VAD strategy? (WebRTC vs Silero)
- What are acceptable latency thresholds?
- How should thinking phrases work during tool calls?

## Patterns
- Infrastructure plans need explicit persistence/port config questions
- Voice/AI plans need latency budget questions upfront

*Last updated: 2026-02-26T21:20:00.300Z*

## Voice Pipeline Session (voice-pipeline-fixes-001) — 2024

### Questions That Would Have Prevented This Failure

#### Q1: Is the branch in a state where implementation can begin immediately?
**Should be asked:** Before any agent work starts
**Why it matters:** The branch was 22 commits behind main at session open. Starting implementation on a stale branch guarantees drift-guard misalignment from cycle 1. A simple `git status` + divergence check should gate session start.
**Required answer format:** Branch must be ≤N commits behind main (suggest N=5), or a rebase must be the first committed action.

#### Q2: Does at least one target implementation file exist, even as a stub?
**Should be asked:** During pre-flight / plan validation
**Why it matters:** The agent produced zero source files across 16 commits. With no anchor file to edit or extend, the agent had no concrete action to take and defaulted to meta-work. A stub (`touch backend/app/voice/bot.py` with a module docstring) would have given the agent a concrete first target.
**Required answer format:** List of stub files that exist OR explicit first action is "create stub files for all PRD targets."

#### Q3: What is the agent's literal first output file and path?
**Should be asked:** At plan parsing time, before session is marked active
**Why it matters:** Plans that describe architecture without specifying a first concrete file leave the agent in ambiguous start state. If the agent cannot name the first file it will write in the next 60 seconds, the plan is underspecified.
**Required answer format:** `First file: backend/app/voice/bot.py — create VoiceBot class skeleton with __init__ and connect() stubs.`

#### Q4: What is the maximum number of consecutive correction cycles before the session halts for human review?
**Should be asked:** During session configuration
**Why it matters:** No circuit breaker existed. 15 correction files were generated before manual abandonment. A pre-agreed threshold (e.g., 3 consecutive cycles with score <10) would have surfaced the failure much earlier.
**Required answer format:** Explicit integer threshold stored in session config.

#### Q5: Are all external dependencies available and verified before implementation starts?
**Should be asked:** Pre-flight
**Why it matters:** The Voice Pipeline required Pipecat, Daily.co, Redis, and Twilio integrations. If any of these were unavailable (wrong env, missing credentials, package not installed), the agent may have stalled on setup rather than implementation, contributing to the correction loop.
**Required answer format:** Checklist — Redis reachable? Daily.co API key set? Pipecat importable? Twilio credentials present?

#### Q6: Is the PRD phase summary the sole source of truth, or are there conflicting instructions in other planning files?
**Should be asked:** At session initialization
**Why it matters:** The session referenced `.planning/phases/03-voice-pipeline/03-SUMMARY.md` but the branch was also 22 commits behind main, suggesting main may have drifted from that summary. Conflicting specs produce low alignment scores regardless of agent behavior.
**Required answer format:** Confirm that PRD summary is consistent with current main branch state, or flag reconciliation needed before session starts.

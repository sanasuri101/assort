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

### Session Planning (NEW - voice-pipeline-fixes-001)
- What specific bug or regression prompted this fix branch?
- Is the target phase already complete on main?
- Does the branch need to rebase before starting work?
- How will we distinguish correction metadata from actual work?

### Patterns
- Infrastructure plans need explicit persistence/port config questions
- Voice/AI plans need latency budget questions upfront
- Fix branches need explicit bug definition and completion criteria
- Branches targeting completed phases need rebase verification

*Last updated: 2026-02-26T21:58:00.591Z*
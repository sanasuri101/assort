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




### Session Monitoring - Branch Lifecycle
- Was the feature branch created from the correct base commit?
- Is there a plan for branch cleanup after merge?
- Should this branch be monitoring a different commit range?
- Are we tracking the right branch for this feature phase?

*Last updated: 2026-02-26T21:47:00Z*

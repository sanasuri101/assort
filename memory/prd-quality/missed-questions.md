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


### Session: voice-pipeline-fixes-001 - Agent Implementation Failure (2026-02-26)

**Critical Questions That Would Have Prevented Complete Failure:**

1. **Does the agent understand the difference between metadata files and source code?**
   - The agent created 7 correction files but ZERO Python implementation files
   - PRD should explicitly state: "DO NOT create markdown files — write actual Python code"

2. **Is the agent capable of implementing this feature phase?**
   - After 3 correction prompts with no progress, human intervention should have been triggered
   - PRD should specify: "If no source files after 30 minutes, escalate to human"

3. **Is the branch being created from the correct base?**
   - Branch was 15 commits behind main before any work started
   - PRD should ask: "What is the current state of main? Should we rebase first?"

4. **Are we tracking the right success metrics?**
   - Success should be measured by source code files, not commit count
   - PRD should define: "Success = all 9 required files exist and 22 tests pass"

**Pattern Identified:**
Agents may interpret correction prompts as "work product" rather than guidance, leading to metadata-only branches. PRDs must explicitly require source code artifacts and define escalation triggers.
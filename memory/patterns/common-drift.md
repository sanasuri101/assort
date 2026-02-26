# Common Drift Patterns

## Detected Drift Patterns

### Scope Creep
- **Pattern**: Agent adds optimizations/features beyond current plan scope
- **Example**: Voice pipeline latency optimizations committed to foundation branch
- **Prevention**: Remind agent to stay within plan boundaries

### Branch Staleness
- **Pattern**: Feature branches fall behind main without rebasing
- **Detection**: compare_branches shows behind_by > 0 with diverged status
- **Resolution**: Inject correction to rebase before continuing

### Missing Artifacts
- **Pattern**: Plan specifies artifacts but agent skips creating them
- **Detection**: File list from compare_branches missing expected paths
- **Resolution**: Inject specific file creation instructions

### Correction Loop Trap (NEW - voice-pipeline-fixes-001)
- **Pattern**: Agent responds to drift corrections by creating more correction metadata instead of actual code
- **Example**: 16 commits, all Drift Guard corrections/traces, zero source code changes
- **Detection**: Score remains critically low (0-52) across 10+ correction attempts; files_changed only includes .claude/corrections/* and traces/*
- **Root Cause**: Agent misunderstands correction prompts as work product rather than guidance
- **Resolution**: 
  - Explicitly instruct: "STOP creating correction commits"
  - Require rebase on main first
  - Mandate actual code changes to source files before next evaluation
  - Consider escalating to human if loop persists beyond 5 corrections

*#Last updated: 2026-02-26T21:58:00.591Z*
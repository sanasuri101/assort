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

*Last updated: 2026-02-26T21:20:00.300Z*

## Voice Pipeline Session (voice-pipeline-fixes-001) — 2024

### Pattern: Correction Loop Without Implementation Progress
**Severity:** Critical | **Frequency:** Observed across entire session (16/16 commits)

Agent entered a self-reinforcing loop where drift-guard corrections were themselves treated as productive output. The agent responded to each correction by generating another correction file rather than pivoting to actual implementation. This is distinct from normal drift — the agent was actively "working" but producing zero deliverables.

**Markers to watch for:**
- All commits on branch are in `.claude/corrections/` or `traces/` paths only
- Alignment scores drop from moderate (52) to near-zero (0-5) within first few cycles and never recover
- No files matching the PRD's target paths appear in any commit
- Session produces many commits but zero diff in `backend/`, `src/`, or other source directories

**Root cause hypothesis:** Agent lacked a concrete starting file or entry point. With no scaffolding to anchor to, it defaulted to meta-work (responding to corrections) instead of creation.

### Pattern: Branch Divergence Ignored at Session Start
**Severity:** High

Session began with branch already 22 commits behind main. This was noted (initial score 52) but no rebase or sync step was taken before implementation work began. Downstream, the drift-guard could not accurately score alignment because the baseline was itself misaligned.

**Markers:** Initial alignment score meaningfully lower than 100 despite no agent action yet.

### Pattern: Persistent Near-Zero Alignment With No Circuit Breaker
**Severity:** High

Scores of 0-5 persisted across many cycles with no automatic escalation or hard stop. The session continued accumulating corrections instead of being halted and re-scoped. 15 correction files were created before abandonment was manual.

**Mitigation needed:** Define a hard circuit-breaker threshold — e.g., if alignment score is <10 for 3 consecutive cycles, pause session and require human confirmation before continuing.

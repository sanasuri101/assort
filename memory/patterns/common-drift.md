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

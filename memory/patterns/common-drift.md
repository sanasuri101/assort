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




### Branch Obsolescence
- **Pattern**: Feature branch becomes obsolete when work is merged to main via different branch
- **Detection**: Branch shows 10+ commits behind main with 0 relevant file changes
- **Example**: voice-pipeline-fixes-001 branch only contains drift-guard traces while Phase 3 work exists on main
- **Resolution**: Close obsolete branches rather than continuing to monitor them

*Last updated: 2026-02-26T21:47:00Z*

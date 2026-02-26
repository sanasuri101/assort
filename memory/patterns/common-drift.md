The page outlines three common drift patterns that can occur in project management. 

1. **Scope Creep**: Refers to the addition of optimizations or features beyond the agreed plan scope. An example includes latency optimizations in a voice pipeline. Prevention involves reminding agents to adhere to the original plan boundaries.

2. **Branch Staleness**: This occurs when feature branches become outdated compared to the main branch. Detection methods utilize a comparison that shows how far behind the branch is, requiring resolution through rebasing before further work.

3. **Missing Artifacts**: This pattern happens when specified artifacts are not created by agents as outlined in the plan. Detection involves checking the file list against expectations and resolution can involve providing specific instructions to ensure artifact creation.

*This information was last updated on February 26, 2026.*

### Metadata-Only Implementation
- **Pattern**: Agent creates only correction/tracing metadata files without actual implementation
- **Detection**: File list shows only .claude/corrections/ entries, no source code files
- **Example**: voice-pipeline-fixes-001 branch has 3 commits, all are drift-guard traces/corrections
- **Root Cause**: Agent misinterprets correction prompts as work product instead of guidance
- **Prevention**: PRD must explicitly state "DO NOT create markdown files — write actual Python code"
- **Resolution**: Close obsolete branches; require implementation files in alignment checks

*Detected: 2026-02-26T21:47:53Z*


## Session: voice-pipeline-fixes-001 (2026-02-26)

### Pattern: Complete Implementation Failure (Score: 0)

**Symptoms:**
- Branch contains ONLY Drift Guard correction files (7 total)
- ZERO actual feature implementation files
- Branch is 15 commits BEHIND main (severely stale)
- All commits are metadata-only, no source code

**Root Cause:**
Agent failed to implement any actual feature code despite receiving multiple correction prompts. The branch became a graveyard of correction files without any forward progress.

**Detection:**
- File list analysis shows only ".claude/corrections/" entries
- Compare vs main shows 0 source files added
- Commit messages all contain "drift-guard" and "correction"

**Resolution:**
1. Rebase branch onto main immediately
2. Implement ALL required files in a single focused session
3. Run all 22 tests before pushing
4. Stop accepting correction file commits as progress

**Prevention for Future Sessions:**
- Check for actual source code files within first 3 commits
- If only metadata files exist after 30 minutes, escalate to human
- Require at least one source file before accepting any commit
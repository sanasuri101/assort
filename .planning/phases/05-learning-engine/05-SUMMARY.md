# Phase 5 Summary: Learning Engine

**Goal**: Implement the "Learning Loop" to improve the voice bot over time through post-call analysis, pattern extraction, and automated evaluation.

## Accomplishments
- **Post-call Analysis Pipeline**: Implemented async analysis using Redis Streams (`call:analysis`) and `worker.py`. Uses `gpt-4o-mini` to extract outcome, sentiment, and missing info.
- **Pattern Extraction**: Automatically identifies missing information and generates "Knowledge Candidates" (Q&A pairs) for the knowledge base.
- **Strict PII Filtering**: Implemented `PIIFilter` to redact sensitive data (SSN, Phone, Email, etc.) from candidates before storage.
- **W&B Weave Integration**:
    - **Tracing**: All analysis and eval operations are traced via `@weave.op`.
    - **Evaluator**: Automated prompt scoring against a golden dataset.
    - **Prompt Optimizer**: Logic to generate and gate prompt revisions based on failed calls (avg_score >= 0.5 safety gate).
- **Prompt Management**: Created `PromptManager` for hierarchical prompt resolution (Provider -> Specialty -> Base) and updated `bot.py` to use it.

## Key Files
- `app/worker.py`: Analysis consumer.
- `app/learning/analysis.py`: `CallAnalyzer`, `PIIFilter`, `KnowledgeCandidate`.
- `app/learning/evals.py`: `Evaluator`, `PromptOptimizer`.
- `app/voice/prompt_manager.py`: Dynamic prompt resolution.
- `scripts/run_evals.py`: CLI for running evaluations.
- `tests/data/golden_conversations.json`: Test dataset.

## Verification
- **Unit Tests**:
    - `tests/learning/test_analysis.py`: Verified LLM extraction.
    - `tests/learning/test_worker.py`: Verified stream consumption and storage.
    - `tests/learning/test_candidates.py`: Verified PII redaction and candidate generation.
    - `tests/learning/test_evals.py`: Verified Evaluator scoring and Optimizer gating.
- **Manual Verification**:
    - `run_evals.py` script exists for manual invocation.

## Next Steps
- **Phase 6: Provider Dashboard**: Build the React frontend to visualize these insights and approve/reject knowledge candidates.

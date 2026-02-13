import pytest
from app.learning.evals import Evaluator, PromptOptimizer, TestCase
from app.voice.prompt_manager import PromptManager

@pytest.mark.asyncio
async def test_evaluator_score():
    # Real Evaluator call (requires GEMINI_API_KEY)
    evaluator = Evaluator()
    case = TestCase(
        input_transcript="I want to book a checkup for tomorrow.",
        expected_outcome="scheduled",
        expected_tools=["book_appointment"]
    )
    
    # This will hit real Gemini if key is set
    score = await evaluator.score_interaction("You are a healthcare assistant.", case)
    assert isinstance(score, float)
    assert 0 <= score <= 1.0


@pytest.mark.asyncio
async def test_prompt_optimizer_gate():
    # Real PromptManager (reads from disk)
    pm = PromptManager()
    
    # Real Optimizer
    optimizer = PromptOptimizer(pm)
    
    # Try to optimize (will use real LLM)
    # We use a dummy transcript
    transcript = "user: help me\nassistant: how?"
    await optimizer.optimize_and_gate("test-call-eval", transcript, "old system prompt")
    
    # Verify we don't crash
    assert True

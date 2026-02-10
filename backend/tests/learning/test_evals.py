import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.learning.evals import Evaluator, PromptOptimizer, TestCase
from app.voice.prompt_manager import PromptManager

@pytest.fixture
def mock_openai():
    with patch("app.learning.evals.AsyncOpenAI") as mock:
        yield mock

@pytest.fixture
def mock_weave():
    with patch("app.learning.evals.weave") as mock:
        yield mock

@pytest.mark.asyncio
async def test_evaluator_score(mock_openai, mock_weave):
    # Mock LLM response for scoring
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    # LLM says "Outcome: scheduled, Tools: book_appointment"
    mock_response.choices[0].message.content = "Outcome: scheduled, Tool: book_appointment"
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    evaluator = Evaluator()
    case = TestCase(
        input_transcript="Book me",
        expected_outcome="scheduled",
        expected_tools=["book_appointment"]
    )
    
    score = await evaluator.score_interaction("system prompt", case)
    assert score > 0.5

@pytest.mark.asyncio
async def test_prompt_optimizer_gate(mock_openai, mock_weave):
    # Mock PM
    pm = MagicMock(spec=PromptManager)
    
    # Mock Evaluator
    with patch("app.learning.evals.Evaluator") as MockEvaluator:
        mock_eval = MockEvaluator.return_value
        # Score > 0.5
        mock_eval.score_interaction = AsyncMock(return_value=0.8)
        
        # Mock Optimizer LLM generation
        mock_client = mock_openai.return_value
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Improved Prompt"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        optimizer = PromptOptimizer(pm)
        await optimizer.optimize_and_gate("call-1", "fail transcript", "old prompt")
        
        # Verify it tried to score
        mock_eval.score_interaction.assert_called()

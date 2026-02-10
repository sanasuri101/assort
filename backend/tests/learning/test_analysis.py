import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.learning.analysis import CallAnalyzer, CallAnalysis

@pytest.fixture
def mock_openai():
    with patch("app.learning.analysis.AsyncOpenAI") as mock:
        yield mock

@pytest.fixture
def mock_weave():
    with patch("app.learning.analysis.weave") as mock:
        yield mock

@pytest.mark.asyncio
async def test_analyze_transcript_success(mock_openai, mock_weave):
    # Setup mock response
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """
    {
        "summary": "Patient wanted to book appointment.",
        "outcome": "scheduled",
        "sentiment": "positive",
        "missing_info": [],
        "compliance_issues": []
    }
    """
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    analyzer = CallAnalyzer()
    result = await analyzer.analyze_transcript("call-123", "User: Hi\nAssistant: Hello")
    
    assert isinstance(result, CallAnalysis)
    assert result.call_id == "call-123"
    assert result.outcome == "scheduled"
    assert result.sentiment == "positive"
    
@pytest.mark.asyncio
async def test_analyze_transcript_failure(mock_openai, mock_weave):
    # Simulate API error
    mock_client = mock_openai.return_value
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
    
    analyzer = CallAnalyzer()
    result = await analyzer.analyze_transcript("call-error", "transcript")
    
    assert result.outcome == "unknown"
    assert result.summary == "Analysis failed"

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.learning.analysis import CallAnalyzer, CallAnalysis, KnowledgeCandidate, PIIFilter

@pytest.fixture
def mock_openai():
    with patch("app.learning.analysis.AsyncOpenAI") as mock:
        yield mock

@pytest.fixture
def mock_weave():
    with patch("app.learning.analysis.weave") as mock:
        yield mock

def test_pii_filter():
    text = "My SSN is 123-45-6789 and my phone is 555-123-4567."
    redacted = PIIFilter.redact(text)
    assert "[SSN]" in redacted
    assert "123-45-6789" not in redacted
    assert "[PHONE]" in redacted
    assert "555-123-4567" not in redacted

def test_candidate_pii_validation():
    # Model validation should redact PII automatically
    cand = KnowledgeCandidate(
        question="My email is test@example.com",
        answer="Sure",
        confidence=0.9,
        source_call_id="call-1"
    )
    assert "[EMAIL]" in cand.question
    assert "test@example.com" not in cand.question

@pytest.mark.asyncio
async def test_extract_candidates(mock_openai, mock_weave):
    # Mock LLM response with candidates
    mock_client = mock_openai.return_value
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """
    {
        "summary": "User asked about wifi.",
        "outcome": "answered",
        "sentiment": "neutral",
        "missing_info": ["Do you have wifi?"],
        "compliance_issues": [],
        "knowledge_candidates": [
            {
                "question": "Do you have wifi?",
                "answer": "Yes, network is Guest.",
                "confidence": 0.95
            }
        ]
    }
    """
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    analyzer = CallAnalyzer()
    result = await analyzer.analyze_transcript("call-1", "user: wifi?")
    
    assert len(result.knowledge_candidates) == 1
    cand = result.knowledge_candidates[0]
    assert cand.question == "Do you have wifi?"
    assert cand.source_call_id == "call-1" # Injected helper

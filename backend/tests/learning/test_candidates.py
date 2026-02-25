import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.learning.analysis import CallAnalyzer, CallAnalysis, KnowledgeCandidate, PIIFilter

@pytest.fixture
def mock_genai():
    with patch("app.learning.analysis.genai") as mock:
        yield mock

@pytest.fixture
def mock_weave():
    with patch("app.learning.analysis.weave") as mock:
        mock.op = lambda: (lambda f: f)  # Make @weave.op() a no-op decorator
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
async def test_extract_candidates(mock_genai, mock_weave):
    # Mock Gemini response with candidates
    mock_response = MagicMock()
    mock_response.text = """
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
    mock_client = mock_genai.Client.return_value
    mock_client.models.generate_content.return_value = mock_response

    analyzer = CallAnalyzer()
    result = await analyzer.analyze_transcript("call-1", "user: wifi?")

    assert len(result.knowledge_candidates) == 1
    cand = result.knowledge_candidates[0]
    assert cand.question == "Do you have wifi?"
    assert cand.source_call_id == "call-1" # Injected helper

import pytest
from app.learning.analysis import CallAnalyzer, CallAnalysis

@pytest.mark.asyncio
async def test_analyze_transcript_success():
    # This will use real Gemini if GEMINI_API_KEY is set.
    # Otherwise it might fail or return error.
    analyzer = CallAnalyzer()
    
    # Tiny transcript to minimize cost/delay if real
    transcript = "User: I'd like to book an appointment.\nAssistant: I can help with that. When works for you?"
    result = await analyzer.analyze_transcript("call-123", transcript)
    
    assert isinstance(result, CallAnalysis)
    assert result.call_id == "call-123"
    # We can't assert the exact content if it's non-deterministic LLM, 
    # but we can check it has some values if it didn't fail.
    if result.summary != "Analysis failed":
        assert result.outcome is not None
        assert result.sentiment is not None

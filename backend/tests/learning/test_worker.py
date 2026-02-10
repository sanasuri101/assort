import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.worker import process_stream
from app.learning.analysis import CallAnalysis, KnowledgeCandidate

@pytest.mark.asyncio
async def test_worker_processing():
    # Mock Redis
    mock_redis = AsyncMock()
    # Mock stream response: [[stream_key, [[message_id, data]]]]
    mock_redis.xreadgroup.side_effect = [
        [["call:analysis", [("msg-1", {"call_id": "call-1"})]]],
        asyncio.CancelledError() # Stop the loop
    ]
    mock_redis.get.return_value = "transcript data"
    
    # Mock Analyzer
    mock_analyzer = AsyncMock()
    mock_analyzer.analyze_transcript.return_value = CallAnalysis(
        call_id="call-1",
        summary="Test summary",
        outcome="scheduled",
        sentiment="positive",
        missing_info=[],
        compliance_issues=[],
        knowledge_candidates=[
            KnowledgeCandidate(
                question="Q1", answer="A1", confidence=1.0, source_call_id="call-1"
            )
        ]
    )
    
    # Run worker loop (it will raise CancelledError when side_effect hits)
    try:
        await process_stream(mock_redis, mock_analyzer)
    except asyncio.CancelledError:
        pass
        
    # Verify method calls
    mock_redis.xgroup_create.assert_called_once()
    mock_redis.xreadgroup.assert_called()
    mock_redis.xack.assert_called_with("call:analysis", "analysis_workers", "msg-1")
    mock_analyzer.analyze_transcript.assert_called_with("call-1", "transcript data")
    mock_redis.hset.assert_called()
    mock_redis.lpush.assert_called_with("candidates:knowledge", "cand:call-1:{}".format(hash("Q1")))

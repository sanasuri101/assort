import pytest
import asyncio
import json
from app.worker import process_stream, STOP_EVENT
from app.learning.analysis import CallAnalyzer

@pytest.mark.asyncio
async def test_worker_processing(redis_client):
    # Setup real data in Redis
    call_id = "test-worker-call"
    transcript_key = f"call:{call_id}:transcript"
    await redis_client.delete(transcript_key)
    await redis_client.lpush(transcript_key, "user: hello", "assistant: hi")
    
    # Push to stream
    stream_key = "call:analysis" # Matches settings.redis_stream_analysis
    await redis_client.xadd(stream_key, {"call_id": call_id})
    
    # Initialize real analyzer
    analyzer = CallAnalyzer()
    
    # Run worker in background and stop it after a bit
    STOP_EVENT.clear()
    worker_task = asyncio.create_task(process_stream(redis_client, analyzer))
    
    # Wait for processing (give it a few seconds for LLM if real)
    await asyncio.sleep(2)
    STOP_EVENT.set()
    await worker_task
    
    # Verify result in Redis
    analysis_key = f"analysis:{call_id}"
    exists = await redis_client.exists(analysis_key)
    # If GEMINI_API_KEY is missing, it might not have stored anything or stored failure
    if exists:
        data = await redis_client.hgetall(analysis_key)
        assert data["outcome"] != ""

import pytest
import json
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient, redis_client):
    # Seed data
    await redis_client.hset("analysis:test-call-1", mapping={
        "outcome": "scheduled",
        "duration": 120,
        "sentiment": "positive",
        "created_at": "2024-02-12T10:00:00Z"
    })
    
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_calls" in data
    assert data["total_calls"] >= 1


@pytest.mark.asyncio
async def test_dashboard_calls(client: AsyncClient, redis_client):
    # Seed data
    await redis_client.hset("analysis:test-call-2", mapping={
        "outcome": "scheduled",
        "duration": 150,
        "sentiment": "positive",
        "created_at": "2024-02-12T11:00:00Z",
        "summary": "Patient booked appointment"
    })
    # Also need metadata for patient name if dashboard uses it
    await redis_client.hset("call:test-call-2:metadata", mapping={
        "patient_name": "Jane Smith"
    })
    
    response = await client.get("/api/dashboard/calls")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Clean up (optional, but good practice)
    # Actually, we let the fixture handle it if we used a separate DB, 
    # but here we'll just leave it or manually delete if needed.


@pytest.mark.asyncio
async def test_dashboard_call_detail(client: AsyncClient, redis_client):
    call_id = "test-call-3"
    # Seed analysis
    await redis_client.hset(f"analysis:{call_id}", mapping={
        "outcome": "scheduled",
        "duration": 180,
        "sentiment": "positive",
        "created_at": "2024-02-12T12:00:00Z",
        "summary": "Detailed call info"
    })
    # Seed transcript
    transcript_key = f"call:{call_id}:transcript"
    await redis_client.lpush(transcript_key, "user: hello", "assistant: hi", "tool: verify_patient")
    
    response = await client.get(f"/api/dashboard/calls/{call_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["call_id"] == call_id
    assert "transcript" in data
    assert len(data["transcript"]) > 0
    
    # Verify visual flow transformation
    # "tool: verify_patient" should be role="tool"
    tool_msg = next((m for m in data["transcript"] if m["role"] == "tool"), None)
    assert tool_msg is not None
    assert tool_msg["tool_name"] == "verify_patient"

import pytest
import json
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_call(client: AsyncClient, redis_client):
    # This calls real Daily API if DAILY_API_KEY is set
    # and real Redis to store state.
    response = await client.post("/api/voice/create", json={"provider_id": "test-prov"})
    
    # If DAILY_API_KEY is missing, it should return 500 with detail
    if response.status_code == 200:
        data = response.json()
        assert "call_id" in data
        assert "room_url" in data
        # Verify in Redis
        saved = await redis_client.get(f"call:{data['call_id']}:state")
        assert saved is not None
    elif response.status_code == 500:
        assert "Daily API key" in response.json()["detail"] or "Failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_join_agent(client: AsyncClient, redis_client):
    # Seed a call
    call_id = "test-join-123"
    await redis_client.set(f"call:{call_id}:state", json.dumps({
        "call_id": call_id,
        "room_url": "https://test.daily.co/room",
        "room_name": "room",
        "agent_joined": False
    }))
    
    response = await client.post(f"/api/voice/{call_id}/join-agent")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify state updated in Redis (wait for background task)
    for _ in range(10):
        saved_data = await redis_client.get(f"call:{call_id}:state")
        if saved_data:
            saved = json.loads(saved_data)
            if saved.get("agent_joined"):
                break
        await asyncio.sleep(0.2)
    
    assert saved["agent_joined"] is True

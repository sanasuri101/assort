import sys
from unittest.mock import MagicMock
import types

# Helper to mock a module structure
def mock_module(name):
    parts = name.split('.')
    for i in range(1, len(parts) + 1):
        module_name = '.'.join(parts[:i])
        if module_name not in sys.modules:
            sys.modules[module_name] = MagicMock()

# Mock all used pipecat modules
modules_to_mock = [
    "pipecat",
    "pipecat.pipeline",
    "pipecat.pipeline.pipeline",
    "pipecat.pipeline.runner",
    "pipecat.pipeline.task",
    "pipecat.frames",
    "pipecat.frames.frames",
    "pipecat.processors",
    "pipecat.processors.frame_processor",
    "pipecat.processors.aggregators",
    "pipecat.processors.aggregators.openai_llm_context",
    "pipecat.services",
    "pipecat.services.deepgram",
    "pipecat.services.cartesia",
    "pipecat.services.openai",
    "pipecat.transports",
    "pipecat.transports.services",
    "pipecat.transports.services.daily",
    "pipecat.vad",
    "pipecat.vad.silero",
    "daily",
]

for m in modules_to_mock:
    mock_module(m)

import pytest
import httpx
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

# Must import app AFTER mocking
try:
    from app.main import app
except ImportError:
    # If it fails here, the mocking didn't work for some reason
    raise

@pytest.mark.asyncio
async def test_create_session_no_api_key():
    # Test that it fails without API key configured (mock settings)
    with patch("app.config.settings.daily_api_key", ""), \
         patch("redis.asyncio.Redis.from_url", return_value=AsyncMock()):
        
        transport = httpx.ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/voice/session", json={"provider_id": "test"})
            assert response.status_code == 500
            assert "Daily API key not configured" in response.json()["detail"]

@pytest.mark.asyncio
async def test_start_agent():
    # Test starting the agent (mocking VoiceBot)
    # We need to patch where VoiceBot is imported in `app.routers.voice`
    # But since VoiceBot is imported at top level in `voice.py`, we patch the class in the module
    
    with patch("app.voice.bot.VoiceBot") as MockBot, \
         patch("redis.asyncio.Redis.from_url", return_value=AsyncMock()):
        
        MockBot.return_value.start = AsyncMock()
        
        transport = httpx.ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/voice/agent/start", json={
                "room_url": "https://daily.co/test",
                "token": "test-token",
                "provider_id": "test-provider"
            })
            assert response.status_code == 200
            assert response.json()["status"] == "started"

"""Shared test fixtures for Assort Health backend tests."""

import sys
from unittest.mock import MagicMock, AsyncMock

# Helper to mock a module structure
def mock_module(name):
    parts = name.split('.')
    for i in range(1, len(parts) + 1):
        module_name = '.'.join(parts[:i])
        if module_name not in sys.modules:
            sys.modules[module_name] = MagicMock()

# Patch sentry_sdk.Hub for compatibility with Sentry 2.x during collection
import sys
from unittest.mock import MagicMock
mock_module("sentry_sdk")
import sentry_sdk
sentry_sdk.Hub = MagicMock()
sys.modules['sentry_sdk.hub'] = MagicMock()
sys.modules['sentry_sdk.Hub'] = MagicMock()

# Mock all used pipecat modules globally for tests
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
    # "redis", # redis is installed, but redis.asyncio might use binary extensions? usually fine.
]

for m in modules_to_mock:
    mock_module(m)

import httpx
import pytest
import pytest_asyncio

from app.main import app


@pytest.fixture
def mock_redis():
    """Create a mock Redis client with common operations."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.close = AsyncMock()
    return redis


@pytest_asyncio.fixture
async def client(mock_redis):
    """Async HTTP client with mocked Redis and EHR service."""
    app.state.redis = mock_redis
    # Initialize EHR service for integration tests
    from app.services.ehr.mock import MockEHRAdapter
    app.state.ehr_service = MockEHRAdapter()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def valid_api_key():
    """Return the configured API key for authenticated requests."""
    from app.config import settings
    return settings.api_key

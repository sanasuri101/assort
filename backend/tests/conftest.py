"""Shared test fixtures for Assort Health backend tests."""

from unittest.mock import AsyncMock

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
    """Async HTTP client with mocked Redis."""
    app.state.redis = mock_redis
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

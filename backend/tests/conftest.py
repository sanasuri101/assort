"""Shared test fixtures for Assort Health backend tests."""

# Sentry and Pipecat mocks removed. Tests will use real libraries if installed.

import httpx
import pytest
import pytest_asyncio

from app.main import app


@pytest_asyncio.fixture
async def redis_client():
    """Fixture for real Redis client connected to test database."""
    from app.config import settings
    from redis.asyncio import Redis
    
    # Use a specific database for testing if possible, or just the default
    # But for simplicity, we'll use the configured URL
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    await client.ping()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def redis_service(redis_client):
    """Fixture for real RedisService, ensuring it's used as a singleton."""
    from app.services.redis_service import RedisService, get_redis_service
    import app.services.redis_service as rs
    
    service = RedisService()
    service.client = redis_client
    # Overwrite the singleton for app code
    rs._redis_service = service
    return service


@pytest_asyncio.fixture
async def client(redis_client, redis_service):
    """Async HTTP client with real Redis and EHR service."""
    app.state.redis = redis_client
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

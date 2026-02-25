"""Shared test fixtures for Assort Health backend tests."""

# Sentry and Pipecat mocks removed. Tests will use real libraries if installed.

import os

# Disable wandb/weave telemetry in tests — its background asyncio thread
# causes event loop interference with module-scoped async fixtures.
os.environ.setdefault("WANDB_MODE", "disabled")
os.environ.setdefault("WANDB_DISABLED", "true")

# Patch weave.op to a no-op BEFORE app imports apply decorators.
# weave.op() wraps async functions with tracing that spawns background
# threads, which accumulate across tests and poison the event loop.
import weave  # noqa: E402

def _noop_weave_op(*args, **kwargs):
    """No-op weave.op() — returns the function unchanged."""
    if args and callable(args[0]):
        return args[0]  # @weave.op without parens
    def decorator(fn):
        return fn
    return decorator

weave.op = _noop_weave_op


class _WeaveObjectStub:
    """Lightweight stand-in for weave.Object that supports keyword init."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


weave.Object = _WeaveObjectStub

# Patch Pipecat FrameProcessor.__init__ to a no-op. Both KBPrefetcher and
# LatencyTracker extend FrameProcessor, which spawns background async tasks
# that accumulate across tests and deadlock the event loop.
import pipecat.processors.frame_processor as _fp  # noqa: E402


def _noop_fp_init(self, *args, **kwargs):
    """Minimal FrameProcessor init — just set attrs tests rely on."""
    self.name = getattr(self, "name", self.__class__.__name__)


_fp.FrameProcessor.__init__ = _noop_fp_init

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.main import app  # noqa: E402


def pytest_collection_modifyitems(items):
    """Reorder tests to avoid event loop pollution deadlocks.

    Order: knowledge → middleware → everything else → latency

    - test_knowledge runs first: module-scoped async fixture deadlocks
      if other tests have left orphaned async tasks.
    - test_middleware runs second: BaseHTTPMiddleware's call_next creates
      async tasks that deadlock when orphaned background tasks exist.
    - test_latency runs last: LatencyTracker (Pipecat FrameProcessor)
      spawns background async tasks that poison the event loop.
    """
    knowledge = []
    middleware = []
    latency = []
    rest = []
    for item in items:
        if "test_knowledge" in item.nodeid:
            knowledge.append(item)
        elif "test_middleware" in item.nodeid:
            middleware.append(item)
        elif "test_latency" in item.nodeid:
            latency.append(item)
        else:
            rest.append(item)
    items[:] = knowledge + middleware + rest + latency


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
    from app.services.redis_service import RedisService
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

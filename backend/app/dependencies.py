"""FastAPI dependency injection providers."""

from fastapi import Request
from redis.asyncio import Redis


async def get_redis(request: Request) -> Redis:
    """Get Redis client from application state.

    Usage:
        @app.get("/example")
        async def example(redis: Redis = Depends(get_redis)):
            await redis.get("key")
    """
    return request.app.state.redis


def get_ehr_service(request: Request):
    """Get EHR Service singleton from application state."""
    return request.app.state.ehr_service

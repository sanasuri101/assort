"""Health check endpoints.

Provides basic and detailed health checks for service monitoring.
"""

import time

from fastapi import APIRouter, Request


router = APIRouter(tags=["health"])


@router.get("")
async def health(request: Request):
    """Basic health check with Redis status."""
    try:
        await request.app.state.redis.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "disconnected"

    return {
        "status": "ok",
        "redis": redis_status,
        "version": "0.1.0",
    }


@router.get("/detailed")
async def health_detailed(request: Request):
    """Detailed health check with per-service status and latency."""
    services = {
        "api": {"status": "running"},
    }

    # Check Redis
    try:
        start = time.time()
        await request.app.state.redis.ping()
        latency_ms = round((time.time() - start) * 1000, 2)
        services["redis"] = {"status": "connected", "latency_ms": latency_ms}
        overall_status = "ok"
    except Exception:
        services["redis"] = {"status": "disconnected"}
        overall_status = "degraded"

    return {
        "status": overall_status,
        "version": "0.1.0",
        "services": services,
    }

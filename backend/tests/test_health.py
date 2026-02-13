"""Tests for health check endpoints."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_endpoint(client):
    """GET /health returns 200 with status ok and Redis status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["redis"] == "connected"
    assert data["version"] == "0.1.0"


async def test_health_detailed_redis_connected(client):
    """GET /health/detailed returns services with Redis connected."""
    response = await client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["services"]["redis"]["status"] == "connected"
    assert "latency_ms" in data["services"]["redis"]
    assert data["services"]["api"]["status"] == "running"

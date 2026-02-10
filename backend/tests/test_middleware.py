"""Tests for HIPAA audit and auth middleware."""

import json
import logging
from unittest.mock import AsyncMock

import pytest

from app.middleware.auth import verify_api_key


pytestmark = pytest.mark.asyncio


async def test_hipaa_audit_logs_phi_access(client, caplog):
    """HIPAA middleware logs access to PHI endpoint paths."""
    with caplog.at_level(logging.INFO, logger="hipaa.audit"):
        response = await client.get("/api/patients/123")

    # PHI path should trigger audit log
    audit_logs = [r for r in caplog.records if r.name == "hipaa.audit"]
    assert len(audit_logs) >= 1

    # Parse the structured JSON log entry
    entry = json.loads(audit_logs[0].message)
    assert entry["event"] == "phi_access"
    assert entry["method"] == "GET"
    assert "/api/patients" in entry["path"]
    assert "timestamp" in entry
    assert "duration_ms" in entry
    assert "caller_ip" in entry


async def test_hipaa_audit_skips_non_phi_paths(client, caplog):
    """HIPAA middleware does NOT log access to non-PHI paths."""
    with caplog.at_level(logging.INFO, logger="hipaa.audit"):
        await client.get("/health")

    audit_logs = [r for r in caplog.records if r.name == "hipaa.audit"]
    assert len(audit_logs) == 0


async def test_auth_rejects_no_key(client):
    """Protected endpoint returns 401 without API key."""
    response = await client.get("/api/protected")
    assert response.status_code == 401


async def test_auth_rejects_invalid_key(client):
    """Protected endpoint returns 401 with wrong API key."""
    response = await client.get(
        "/api/protected",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


async def test_auth_accepts_valid_key(client, valid_api_key):
    """Protected endpoint returns 200 with correct API key."""
    response = await client.get(
        "/api/protected",
        headers={"X-API-Key": valid_api_key},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "authenticated"

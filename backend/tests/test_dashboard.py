import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.dashboard import router
# Avoid importing app.main to skip voice dependencies

app = FastAPI()
app.include_router(router, prefix="/api/dashboard")

client = TestClient(app)

def test_dashboard_stats():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_calls" in data
    assert "avg_duration_sec" in data

def test_dashboard_calls():
    response = client.get("/api/dashboard/calls")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert "call_id" in data[0]

def test_dashboard_call_detail():
    response = client.get("/api/dashboard/calls/call-123")
    assert response.status_code == 200
    data = response.json()
    assert data["call_id"] == "call-123"
    assert "transcript" in data
    assert len(data["transcript"]) > 0
    # Check visual flow data
    assert data["transcript"][3]["role"] == "tool"
    assert data["transcript"][3]["tool_name"] == "verify_patient"

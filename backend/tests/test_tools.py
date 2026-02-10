"""
Test EHR tool wrappers — verify gating, verification flow, and tool dispatch.
"""

import pytest
import json

import fakeredis.aioredis

from app.services.ehr.mock import MockEHRAdapter
from app.voice.call_state import CallStateMachine, CallState
from app.voice.tools import (
    dispatch_tool,
    execute_verify_patient,
    execute_get_availability,
    execute_book_appointment,
    execute_check_insurance,
)


@pytest.fixture
def ehr_service():
    return MockEHRAdapter()


@pytest.fixture
async def redis_client():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.close()


@pytest.fixture
def call_state(redis_client):
    return CallStateMachine(redis_client)


@pytest.fixture
def known_patient(ehr_service):
    """Get a patient from the mock EHR for testing."""
    patient = list(ehr_service.patients.values())[0]
    return patient


# ---- verify_patient tests ----


@pytest.mark.asyncio
async def test_verify_patient_match(call_state, ehr_service, known_patient):
    """verify_patient with matching name + DOB should succeed and set VERIFIED."""
    call_id = "test-call-001"
    await call_state.create_call(call_id)
    await call_state.transition(call_id, CallState.GREETING)
    await call_state.transition(call_id, CallState.ROUTING)

    name = known_patient.name[0].full_name
    dob = known_patient.birthDate.isoformat()

    result = json.loads(await execute_verify_patient(
        call_id, call_state, ehr_service, name=name, date_of_birth=dob,
    ))

    assert result["verified"] is True
    assert result["patient_id"] == known_patient.id
    assert await call_state.get_state(call_id) == CallState.VERIFIED


@pytest.mark.asyncio
async def test_verify_patient_no_match(call_state, ehr_service):
    """verify_patient with wrong info should fail and leave state unchanged."""
    call_id = "test-call-002"
    await call_state.create_call(call_id)
    await call_state.transition(call_id, CallState.GREETING)
    await call_state.transition(call_id, CallState.ROUTING)

    result = json.loads(await execute_verify_patient(
        call_id, call_state, ehr_service,
        name="Nobody Real", date_of_birth="1900-01-01",
    ))

    assert result["verified"] is False
    assert await call_state.get_state(call_id) == CallState.ROUTING


# ---- Gated tools before verification ----


@pytest.mark.asyncio
async def test_gated_tools_before_verification(call_state, ehr_service):
    """Gated tools should return identity_not_verified error before VERIFIED state."""
    call_id = "test-call-003"
    await call_state.create_call(call_id)
    await call_state.transition(call_id, CallState.GREETING)
    await call_state.transition(call_id, CallState.ROUTING)

    # get_availability — gated
    result = json.loads(await execute_get_availability(
        call_id, call_state, ehr_service,
        provider_id="any", start_date="2025-01-01", end_date="2025-01-05",
    ))
    assert result["error"] == "identity_not_verified"

    # book_appointment — gated
    result = json.loads(await execute_book_appointment(
        call_id, call_state, ehr_service,
        slot_id="any", visit_type="routine",
    ))
    assert result["error"] == "identity_not_verified"

    # check_insurance — gated
    result = json.loads(await execute_check_insurance(
        call_id, call_state, ehr_service,
        plan_id="any",
    ))
    assert result["error"] == "identity_not_verified"


# ---- Gated tools after verification ----


@pytest.mark.asyncio
async def test_gated_tools_after_verification(call_state, ehr_service, known_patient):
    """After verification, gated tools should execute successfully."""
    call_id = "test-call-004"
    await call_state.create_call(call_id)
    await call_state.transition(call_id, CallState.GREETING)
    await call_state.transition(call_id, CallState.ROUTING)

    # Verify first
    name = known_patient.name[0].full_name
    dob = known_patient.birthDate.isoformat()
    await execute_verify_patient(
        call_id, call_state, ehr_service, name=name, date_of_birth=dob,
    )
    assert await call_state.get_state(call_id) == CallState.VERIFIED

    # get_availability should work now (returns empty for random provider)
    result = json.loads(await execute_get_availability(
        call_id, call_state, ehr_service,
        provider_id="nonexistent", start_date="2025-01-01", end_date="2025-01-05",
    ))
    assert "error" not in result
    assert "slots" in result


# ---- dispatch_tool ----


@pytest.mark.asyncio
async def test_dispatch_unknown_tool(call_state, ehr_service):
    """Dispatching unknown tool returns error."""
    result = json.loads(await dispatch_tool(
        "nonexistent_tool", {}, "call-x", call_state, ehr_service,
    ))
    assert result["error"] == "unknown_tool"


@pytest.mark.asyncio
async def test_dispatch_verify_patient(call_state, ehr_service, known_patient):
    """dispatch_tool routes verify_patient correctly."""
    call_id = "test-call-005"
    await call_state.create_call(call_id)
    await call_state.transition(call_id, CallState.GREETING)
    await call_state.transition(call_id, CallState.ROUTING)

    name = known_patient.name[0].full_name
    dob = known_patient.birthDate.isoformat()

    result = json.loads(await dispatch_tool(
        "verify_patient",
        {"name": name, "date_of_birth": dob},
        call_id, call_state, ehr_service,
    ))
    assert result["verified"] is True

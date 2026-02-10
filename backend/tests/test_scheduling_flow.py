"""
Test the full scheduling flow with mocked EHR and gated tools.
"""

import pytest
import json
from datetime import date, datetime, timedelta

import fakeredis.aioredis

from app.services.ehr.mock import MockEHRAdapter
from app.voice.call_state import CallStateMachine, CallState
from app.voice.tools import (
    execute_verify_patient,
    execute_list_providers,
    execute_get_availability,
    execute_book_appointment,
)


@pytest.fixture
async def redis_client():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.close()


@pytest.fixture
def call_state(redis_client):
    return CallStateMachine(redis_client)


@pytest.fixture
def ehr_service():
    return MockEHRAdapter()


@pytest.fixture
def known_patient(ehr_service):
    return list(ehr_service.patients.values())[0]


@pytest.fixture
def known_provider(ehr_service):
    return list(ehr_service.practitioners.values())[0]


@pytest.mark.asyncio
async def test_scheduling_flow_happy_path(call_state, ehr_service, known_patient, known_provider):
    """
    Full flow:
    1. Verify patient -> match
    2. List providers -> returns list
    3. Get availability -> returns slots
    4. Book appointment -> success
    """
    call_id = "call-sched-001"
    await call_state.create_call(call_id)
    await call_state.transition(call_id, CallState.GREETING)
    await call_state.transition(call_id, CallState.ROUTING)

    # 1. Verify
    name = known_patient.name[0].full_name
    dob = known_patient.birthDate.isoformat()
    await execute_verify_patient(call_id, call_state, ehr_service, name=name, date_of_birth=dob)
    assert await call_state.get_state(call_id) == CallState.VERIFIED

    # 2. List Providers
    res_json = await execute_list_providers(call_id, call_state, ehr_service)
    res = json.loads(res_json)
    assert "providers" in res
    assert len(res["providers"]) > 0
    provider_id = res["providers"][0]["id"]

    # 3. Get Availability
    # Find a date range with slots (MockEHR seeds next 30 days)
    start_date = date.today().isoformat()
    end_date = (date.today() + timedelta(days=5)).isoformat()
    
    res_json = await execute_get_availability(
        call_id, call_state, ehr_service,
        provider_id=provider_id, start_date=start_date, end_date=end_date
    )
    res = json.loads(res_json)
    assert "slots" in res
    assert len(res["slots"]) > 0
    slot_id = res["slots"][0]["slot_id"]

    # 4. Book Appointment
    res_json = await execute_book_appointment(
        call_id, call_state, ehr_service,
        slot_id=slot_id, visit_type="checkup"
    )
    res = json.loads(res_json)
    assert "appointment_id" in res
    assert res["status"] == "booked"
    
    # Check state transition (should go to RESOLVING)
    assert await call_state.get_state(call_id) == CallState.RESOLVING


@pytest.mark.asyncio
async def test_scheduling_gated_before_verify(call_state, ehr_service):
    """Tools should be blocked if not verified."""
    call_id = "call-sched-002"
    await call_state.create_call(call_id)
    # State is GREETING/ROUTING, not VERIFIED

    # Try list_providers
    res = json.loads(await execute_list_providers(call_id, call_state, ehr_service))
    assert res["error"] == "identity_not_verified"
    
    # Try book_appointment
    res = json.loads(await execute_book_appointment(
        call_id, call_state, ehr_service,
        slot_id="any", visit_type="routine"
    ))
    assert res["error"] == "identity_not_verified"

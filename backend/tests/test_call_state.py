import pytest
from app.voice.call_state import CallStateMachine, CallState

@pytest.fixture
def csm(redis_service):
    return CallStateMachine(redis_service)


@pytest.mark.asyncio
async def test_create_call(csm, redis_service):
    call_id = "call-123"
    state = await csm.create_call(call_id, "prov-1")
    assert state == CallState.RINGING
    
    # Verify in real Redis
    saved = await redis_service.get_call_state(call_id)
    assert saved["state"] == CallState.RINGING.value
    assert saved["provider_id"] == "prov-1"


@pytest.mark.asyncio
async def test_valid_transition(csm):
    call_id = "call-trans"
    await csm.create_call(call_id)
    new_state = await csm.transition(call_id, CallState.GREETING)
    assert new_state == CallState.GREETING
    assert await csm.get_state(call_id) == CallState.GREETING


@pytest.mark.asyncio
async def test_transition_not_found(csm):
    with pytest.raises(ValueError, match="not found"):
        await csm.transition("call-999", CallState.GREETING)


@pytest.mark.asyncio
async def test_full_happy_path(csm):
    """Test the full call lifecycle: RINGING → GREETING → ROUTING → VERIFIED → RESOLVING → COMPLETED."""
    call_id = "call-happy"
    await csm.create_call(call_id)

    transitions = [
        CallState.GREETING,
        CallState.ROUTING,
        CallState.VERIFIED,
        CallState.RESOLVING,
        CallState.COMPLETED,
    ]
    for target in transitions:
        result = await csm.transition(call_id, target)
        assert result == target
        assert await csm.get_state(call_id) == target


@pytest.mark.asyncio
async def test_abandoned_from_any_active_state(csm):
    """ABANDONED should be reachable from any non-terminal state."""
    active_states = [
        CallState.GREETING,
        CallState.ROUTING,
        CallState.VERIFIED,
        CallState.RESOLVING,
        CallState.TRANSFERRING,
    ]
    for state in active_states:
        call_id = f"call-abn-{state.value}"
        await csm.create_call(call_id)
        if state != CallState.RINGING:
            await csm.transition(call_id, state)
            
        result = await csm.transition(call_id, CallState.ABANDONED)
        assert result == CallState.ABANDONED
        assert await csm.get_state(call_id) == CallState.ABANDONED

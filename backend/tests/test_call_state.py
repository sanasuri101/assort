import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.voice.call_state import CallStateMachine, CallState


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.hset = AsyncMock()
    r.hget = AsyncMock()
    r.hgetall = AsyncMock(return_value={})
    r.xadd = AsyncMock()
    return r


@pytest.fixture
def csm(mock_redis):
    return CallStateMachine(mock_redis)


@pytest.mark.asyncio
async def test_create_call(csm, mock_redis):
    state = await csm.create_call("call-123", "prov-1")
    assert state == CallState.RINGING
    mock_redis.hset.assert_called()
    mock_redis.xadd.assert_called()


@pytest.mark.asyncio
async def test_valid_transition(csm, mock_redis):
    mock_redis.hget.return_value = CallState.RINGING.value
    new_state = await csm.transition("call-123", CallState.GREETING)
    assert new_state == CallState.GREETING


@pytest.mark.asyncio
async def test_invalid_transition(csm, mock_redis):
    mock_redis.hget.return_value = CallState.RINGING.value
    with pytest.raises(ValueError, match="Invalid transition"):
        await csm.transition("call-123", CallState.COMPLETED)


@pytest.mark.asyncio
async def test_transition_not_found(csm, mock_redis):
    mock_redis.hget.return_value = None
    with pytest.raises(ValueError, match="not found"):
        await csm.transition("call-999", CallState.GREETING)


@pytest.mark.asyncio
async def test_full_happy_path(csm, mock_redis):
    """Test the full call lifecycle: RINGING → GREETING → ROUTING → VERIFIED → RESOLVING → COMPLETED."""
    # Create
    await csm.create_call("call-happy")

    transitions = [
        (CallState.RINGING, CallState.GREETING),
        (CallState.GREETING, CallState.ROUTING),
        (CallState.ROUTING, CallState.VERIFIED),
        (CallState.VERIFIED, CallState.RESOLVING),
        (CallState.RESOLVING, CallState.COMPLETED),
    ]
    for current, target in transitions:
        mock_redis.hget.return_value = current.value
        result = await csm.transition("call-happy", target)
        assert result == target


@pytest.mark.asyncio
async def test_abandoned_from_any_active_state(csm, mock_redis):
    """ABANDONED should be reachable from any non-terminal state."""
    active_states = [
        CallState.RINGING,
        CallState.GREETING,
        CallState.ROUTING,
        CallState.VERIFIED,
        CallState.RESOLVING,
        CallState.TRANSFERRING,
    ]
    for state in active_states:
        mock_redis.hget.return_value = state.value
        result = await csm.transition("call-abn", CallState.ABANDONED)
        assert result == CallState.ABANDONED

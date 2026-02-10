"""
Call State Machine — Redis-backed state tracking for voice calls.

States:
  RINGING → GREETING → ROUTING → VERIFIED → RESOLVING → COMPLETED
                                      ↓
                                TRANSFERRING → TRANSFERRED
                                      ↓
                                 ABANDONED
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CallState(str, Enum):
    RINGING = "ringing"
    GREETING = "greeting"
    ROUTING = "routing"
    VERIFIED = "verified"
    RESOLVING = "resolving"
    COMPLETED = "completed"
    TRANSFERRING = "transferring"
    TRANSFERRED = "transferred"
    ABANDONED = "abandoned"


# Valid state transitions
VALID_TRANSITIONS = {
    CallState.RINGING: {CallState.GREETING, CallState.ABANDONED},
    CallState.GREETING: {CallState.ROUTING, CallState.ABANDONED},
    CallState.ROUTING: {CallState.VERIFIED, CallState.TRANSFERRING, CallState.ABANDONED},
    CallState.VERIFIED: {CallState.RESOLVING, CallState.TRANSFERRING, CallState.ABANDONED},
    CallState.RESOLVING: {CallState.COMPLETED, CallState.TRANSFERRING, CallState.ABANDONED},
    CallState.TRANSFERRING: {CallState.TRANSFERRED, CallState.ABANDONED},
    CallState.TRANSFERRED: set(),
    CallState.COMPLETED: set(),
    CallState.ABANDONED: set(),
}


class CallStateMachine:
    """Redis-backed call state machine with HIPAA audit trail."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def create_call(self, call_id: str, provider_id: str = "default") -> CallState:
        """Initialize a new call in RINGING state."""
        now = datetime.now(timezone.utc).isoformat()
        await self.redis.hset(f"call:{call_id}", mapping={
            "state": CallState.RINGING.value,
            "provider_id": provider_id,
            "created_at": now,
            "updated_at": now,
        })
        await self._log_transition(call_id, None, CallState.RINGING)
        return CallState.RINGING

    async def transition(self, call_id: str, new_state: CallState) -> CallState:
        """Transition a call to a new state. Raises ValueError on invalid transition."""
        current = await self.get_state(call_id)
        if current is None:
            raise ValueError(f"Call {call_id} not found")

        if new_state not in VALID_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"Invalid transition: {current.value} → {new_state.value}"
            )

        now = datetime.now(timezone.utc).isoformat()
        await self.redis.hset(f"call:{call_id}", mapping={
            "state": new_state.value,
            "updated_at": now,
        })
        await self._log_transition(call_id, current, new_state)
        return new_state

    async def get_state(self, call_id: str) -> Optional[CallState]:
        """Get current state of a call."""
        state_val = await self.redis.hget(f"call:{call_id}", "state")
        if state_val is None:
            return None
        return CallState(state_val)

    async def set_metadata(self, call_id: str, key: str, value: str):
        """Set additional metadata on a call."""
        await self.redis.hset(f"call:{call_id}", key, value)

    async def get_call_info(self, call_id: str) -> Optional[dict]:
        """Get all call info as a dict."""
        data = await self.redis.hgetall(f"call:{call_id}")
        return data if data else None

    async def is_verified(self, call_id: str) -> bool:
        """Check if a call has been identity-verified."""
        state = await self.get_state(call_id)
        return state == CallState.VERIFIED

    async def _log_transition(
        self, call_id: str, from_state: Optional[CallState], to_state: CallState
    ):
        """Log state transition to Redis stream for HIPAA audit."""
        now = datetime.now(timezone.utc).isoformat()
        from_val = from_state.value if from_state else "none"
        await self.redis.xadd(f"call:{call_id}:events", {
            "type": "state_transition",
            "from": from_val,
            "to": to_state.value,
            "timestamp": now,
        })
        logger.info("Call %s: %s → %s", call_id, from_val, to_state.value)

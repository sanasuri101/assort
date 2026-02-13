from __future__ import annotations
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
from typing import Optional, Any

from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class CallState(Enum):
    """Voice call states matching wnbHack logic."""
    RINGING = "ringing"
    GREETING = "greeting"
    ROUTING = "routing"
    VERIFIED = "verified"
    RESOLVING = "resolving"
    COMPLETED = "completed"
    TRANSFERRING = "transferring"
    TRANSFERRED = "transferred"
    ABANDONED = "abandoned"

VALID_TRANSITIONS = {
    CallState.RINGING: {CallState.GREETING, CallState.ABANDONED},
    CallState.GREETING: {CallState.ROUTING, CallState.ABANDONED},
    CallState.ROUTING: {CallState.VERIFIED, CallState.TRANSFERRING, CallState.ABANDONED},
    CallState.VERIFIED: {CallState.RESOLVING, CallState.TRANSFERRING, CallState.ABANDONED},
    CallState.RESOLVING: {CallState.COMPLETED, CallState.ABANDONED},
    CallState.TRANSFERRING: {CallState.TRANSFERRED, CallState.ABANDONED},
}

class CallStateMachine:
    """Redis-backed call state machine with HIPAA audit trail."""

    def __init__(self, redis_service: RedisService):
        self.service = redis_service

    async def create_call(self, call_id: str, provider_id: str = "default") -> 'CallState':
        """Initialize a new call in RINGING state."""
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "status": "pending", # wnbHack compatibility
            "state": CallState.RINGING.value,
            "provider_id": provider_id,
            "created_at": now,
            "updated_at": now,
            "participants": [],
            "agent_joined": False
        }
        await self.service.set_call_state(call_id, state)
        await self._log_transition(call_id, None, CallState.RINGING)
        return CallState.RINGING

    async def transition(self, call_id: str, new_state: CallState) -> CallState:
        """Transition a call to a new state."""
        state = await self.service.get_call_state(call_id)
        if state is None:
            raise ValueError(f"Call {call_id} not found")

        current_val = state.get("state")
        current = CallState(current_val) if current_val else None

        # Basic validation
        if current and new_state not in VALID_TRANSITIONS.get(current, set()):
             logger.warning(f"Unexpected transition: {current.value} → {new_state.value}")
             # We still allow it for flexibility in voice flows, but log it

        state["state"] = new_state.value
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Sync with wnbHack 'status' field
        if new_state == CallState.COMPLETED:
            state["status"] = "completed"

        await self.service.set_call_state(call_id, state)
        await self._log_transition(call_id, current, new_state)
        return new_state

    async def get_state(self, call_id: str) -> Optional[CallState]:
        """Get current state of a call."""
        state = await self.service.get_call_state(call_id)
        if not state or "state" not in state:
            return None
        return CallState(state["state"])

    async def set_metadata(self, call_id: str, key: str, value: Any):
        """Set additional metadata on a call."""
        state = await self.service.get_call_state(call_id)
        if state:
            state[key] = value
            await self.service.set_call_state(call_id, state)

    async def get_call_info(self, call_id: str) -> Optional[dict]:
        """Get all call info as a dict."""
        return await self.service.get_call_state(call_id)

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
        
        # Use RedisService client directly for streams
        await self.service.client.xadd(f"call:{call_id}:events", {
            "type": "state_transition",
            "from": from_val,
            "to": to_state.value,
            "timestamp": now,
        })
        logger.info("Call %s: %s → %s", call_id, from_val, to_state.value)

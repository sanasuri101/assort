import logging
from typing import Any, List, Optional
import json

from app.services.redis_service import RedisService
from app.config import settings

logger = logging.getLogger(__name__)

class PresenceHandler:
    """
    Handler for Daily participant events and call lifecycle management.
    Updates Redis state when participants join or leave, and handles call completion.
    """

    def __init__(self, call_id: str, redis_service: RedisService):
        self.call_id = call_id
        self.redis_service = redis_service
        logger.info(f"PresenceHandler initialized for call {call_id}")

    async def on_participant_joined(self, participant: dict) -> None:
        """Handle participant joined event."""
        participant_id = participant.get("id", "unknown")
        # Daily transport participant info structure
        is_local = participant.get("local", False)

        logger.info(
            f"Participant joined call {self.call_id}: "
            f"id={participant_id}, is_local={is_local}"
        )

        if is_local:
            return

        # Update call state in Redis
        state = await self.redis_service.get_call_state(self.call_id)
        if state:
            participants = state.get("participants", [])
            if participant_id not in participants:
                participants.append(participant_id)
                state["participants"] = participants

            if state.get("status") == "pending":
                state["status"] = "active"
                logger.info(f"Call {self.call_id} status updated to 'active'")

            await self.redis_service.set_call_state(self.call_id, state)

    async def on_participant_left(self, participant: dict) -> None:
        """Handle participant left event."""
        participant_id = participant.get("id", "unknown")
        is_local = participant.get("local", False)

        logger.info(f"Participant left call {self.call_id}: id={participant_id}")

        if is_local:
            return

        state = await self.redis_service.get_call_state(self.call_id)
        if state:
            participants = state.get("participants", [])
            if participant_id in participants:
                participants.remove(participant_id)
                state["participants"] = participants

            if len(participants) == 0 and state.get("status") == "active":
                state["status"] = "waiting"
                logger.info(f"Call {self.call_id} status updated to 'waiting' (no participants)")

            await self.redis_service.set_call_state(self.call_id, state)

    async def on_call_ended(self) -> None:
        """Handle call ended event (e.g., bot left or room expired)."""
        logger.info(f"Call {self.call_id} ended")

        state = await self.redis_service.get_call_state(self.call_id)
        if state and state.get("status") != "completed":
            state["status"] = "completed"
            state["ended_at"] = json.dumps(True) # Just a marker
            await self.redis_service.set_call_state(self.call_id, state)
            logger.info(f"Call {self.call_id} status updated to 'completed'")

            # Trigger post-call analysis/learning
            await self._process_call_for_analysis(state)

    async def _process_call_for_analysis(self, state: dict) -> None:
        """
        Process the completed call: build transcript from Redis interactions
        and trigger the analysis pipeline.
        """
        try:
            # Get all interactions (transcript) for this call
            interactions = await self.redis_service.get_call_interactions(self.call_id)

            if not interactions:
                logger.info(f"No interactions found for call {self.call_id}, skipping analysis")
                return

            # Build transcript from interactions (wnbHack pattern)
            transcript_parts = []
            for interaction in interactions:
                role = interaction.get("role", "") or interaction.get("type", "").split("_")[0]
                text = interaction.get("text", "")

                if "user" in role:
                    transcript_parts.append(f"Customer: {text}")
                elif "assistant" in role or "agent" in role:
                    transcript_parts.append(f"Agent: {text}")

            if not transcript_parts:
                logger.info(f"No speech interactions for call {self.call_id}, skipping analysis")
                return

            full_transcript = "\n".join(transcript_parts)
            logger.info(f"Built transcript for call {self.call_id}: {len(full_transcript)} chars")

            # Store full transcript in Redis for the dashboard
            await self.redis_service.client.set(
                f"call:{self.call_id}:transcript", 
                full_transcript, 
                ex=86400  # 24h expiry
            )

            # Trigger the analysis worker via Redis Streams
            await self.redis_service.client.xadd(
                settings.redis_stream_analysis, 
                {"call_id": self.call_id}
            )
            logger.info(f"Queued call {self.call_id} for analysis")

        except Exception as e:
            logger.error(f"Error processing call for analysis: {e}", exc_info=True)

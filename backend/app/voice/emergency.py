"""
Emergency detection middleware for the voice pipeline.
Scans transcription frames for keywords and triggers emergency flow.
"""

import logging
from typing import Set

from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, TranscriptionFrame, LLMMessagesFrame
from app.voice.call_state import CallState

logger = logging.getLogger(__name__)


EMERGENCY_KEYWORDS: Set[str] = {
    "chest pain",
    "can't breathe",
    "heart attack",
    "stroke",
    "bleeding",
    "unconscious",
    "suicide",
    "overdose",
    "911",
    "difficulty breathing",
    "allergic reaction",
    "passing out",
    "killing myself",
    "want to die",
    "self-harm",
}


EMERGENCY_OVERRIDE_MESSAGE = (
    "EMERGENCY DETECTED. The caller may be experiencing a medical emergency. "
    "Immediately tell them: 'This sounds like it could be a medical emergency. "
    "Please hang up and call 911 immediately, or go to your nearest emergency room. "
    "If you need me to stay on the line while you call, I can do that.' "
    "Do NOT attempt to schedule or verify identity."
)


class EmergencyDetector(FrameProcessor):
    def __init__(self):
        super().__init__()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # only check user speech
        if isinstance(frame, TranscriptionFrame) and frame.user_id != "assistant":
            text = frame.text.lower()
            
            # Simple keyword matching
            if any(keyword in text for keyword in EMERGENCY_KEYWORDS):
                logger.warning(f"EMERGENCY DETECTED: {text}")
                
                # Inject system override message to force LLM into emergency mode
                # This doesn't stop the pipeline but steers the LLM response
                sys_msg = {"role": "system", "content": EMERGENCY_OVERRIDE_MESSAGE}
                await self.push_frame(LLMMessagesFrame([sys_msg]), direction)
                
                # We could also potentially trigger a state change here via callback
                # if we injected call_state manager, but for now we rely on LLM steering
        
        await self.push_frame(frame, direction)

"""
Test EmergencyDetector middleware.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import importlib
from pipecat.processors.frame_processor import FrameDirection
# We need to do this BEFORE importing EmergencyDetector
# But since we are in a test function, we might need to patch sys.modules or something?
# Actually, let's just define the stub and use patch('app.voice.emergency.FrameProcessor', StubFrameProcessor)
# But EmergencyDetector class definition runs at import time.
# So we need to reload the module.

class StubFrameProcessor:
    def __init__(self): pass
    async def process_frame(self, frame, direction): pass
    async def push_frame(self, frame, direction): pass

class StubFrame:
    def __init__(self): pass

class StubTranscriptionFrame(StubFrame):
    def __init__(self, text, user_id, timestamp):
        self.text = text
        self.user_id = user_id

class StubLLMMessagesFrame(StubFrame):
    def __init__(self, messages):
        self.messages = messages

@pytest.fixture
def detector_cls():
    """Return EmergencyDetector class that inherits from StubFrameProcessor."""
    # Create fake modules
    fake_proc_module = MagicMock()
    fake_proc_module.FrameProcessor = StubFrameProcessor
    fake_proc_module.FrameDirection = FrameDirection
    
    fake_frames_module = MagicMock()
    fake_frames_module.Frame = StubFrame
    fake_frames_module.TranscriptionFrame = StubTranscriptionFrame
    fake_frames_module.LLMMessagesFrame = StubLLMMessagesFrame

    with patch.dict(sys.modules, {
        "pipecat.processors.frame_processor": fake_proc_module,
        "pipecat.frames.frames": fake_frames_module
    }):
        import app.voice.emergency
        importlib.reload(app.voice.emergency)
        return app.voice.emergency.EmergencyDetector

@pytest.mark.asyncio
async def test_emergency_detector_triggers(detector_cls):
    """Test that emergency keywords trigger the override message."""
    detector = detector_cls()
    
    # Mock push_frame to capture output
    detector.push_frame = AsyncMock()
    
    # Create a frame with a keyword
    text = "I think I'm having a heart attack"
    
    # Use our stub class
    frame = StubTranscriptionFrame(text, "user", "iso")
    
    await detector.process_frame(frame, FrameDirection.DOWNSTREAM)
    
    # Should have pushed 2 frames: 
    # 1. The override message (LLMMessagesFrame)
    # 2. The original frame
    
    assert detector.push_frame.call_count == 2 
    # Check injection
    args, _ = detector.push_frame.call_args_list[0]
    injected = args[0]
    assert isinstance(injected, StubLLMMessagesFrame)
    assert "EMERGENCY DETECTED" in injected.messages[0]["content"]


@pytest.mark.asyncio
async def test_emergency_detector_passthrough(detector_cls):
    """Test that non-emergency text passes through without injection."""
    detector = detector_cls()
    detector.push_frame = AsyncMock()
    
    text = "I would like to book an appointment"
    frame = StubTranscriptionFrame(text, "user", "iso")
    
    await detector.process_frame(frame, FrameDirection.DOWNSTREAM)
    
    # Should push only original frame
    assert detector.push_frame.call_count == 1
    assert detector.push_frame.call_args[0][0] == frame

"""Tests for the LatencyTracker module."""

import pytest
import time
from app.voice.latency import LatencyTracker, TurnMetrics


class TestTurnMetrics:
    """Tests for the TurnMetrics dataclass calculations."""

    def test_ttft_calculation(self):
        m = TurnMetrics(
            turn_id=1,
            user_speech_end=100.0,
            first_llm_token=100.35,
        )
        assert abs(m.ttft_ms - 350.0) < 1.0

    def test_ttfa_calculation(self):
        m = TurnMetrics(
            turn_id=1,
            user_speech_end=100.0,
            first_audio_out=100.5,
        )
        assert abs(m.ttfa_ms - 500.0) < 1.0

    def test_tool_duration_calculation(self):
        m = TurnMetrics(
            turn_id=1,
            tool_call_start=100.0,
            tool_call_end=100.2,
        )
        assert abs(m.tool_duration_ms - 200.0) < 1.0

    def test_total_turn_calculation(self):
        m = TurnMetrics(
            turn_id=1,
            user_speech_end=100.0,
            llm_complete=101.5,
        )
        assert abs(m.total_turn_ms - 1500.0) < 1.0

    def test_zero_when_timestamps_missing(self):
        m = TurnMetrics(turn_id=1)
        assert m.ttft_ms == 0.0
        assert m.ttfa_ms == 0.0
        assert m.tool_duration_ms == 0.0
        assert m.total_turn_ms == 0.0


class TestLatencyTracker:
    """Tests for the LatencyTracker FrameProcessor."""

    def test_initial_state(self):
        tracker = LatencyTracker(call_id="test-001")
        assert tracker._turn_count == 0
        assert len(tracker._completed_turns) == 0

    def test_mark_tool_timing(self):
        tracker = LatencyTracker(call_id="test-001")
        tracker._current_turn.user_speech_end = time.monotonic()

        tracker.mark_tool_start()
        time.sleep(0.05)  # 50ms tool call (enough for Windows timer resolution)
        tracker.mark_tool_end()

        assert tracker._current_turn.tool_duration_ms >= 0

    def test_summary_empty(self):
        tracker = LatencyTracker(call_id="test-001")
        summary = tracker.get_summary()
        assert summary["turns"] == 0

    def test_summary_with_turns(self):
        tracker = LatencyTracker(call_id="test-001")

        # Simulate 3 completed turns
        for i in range(3):
            t = TurnMetrics(
                turn_id=i + 1,
                user_speech_end=100.0,
                first_llm_token=100.3,
                first_audio_out=100.5,
                llm_complete=101.0,
            )
            tracker._completed_turns.append(t)

        summary = tracker.get_summary()
        assert summary["turns"] == 3
        assert summary["ttft"]["p50"] > 0
        assert summary["ttfa"]["p50"] > 0

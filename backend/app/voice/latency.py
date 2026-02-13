"""
Latency Tracker — per-turn TTFA instrumentation for the voice pipeline.

Measures the metrics that matter for voice UX:
  - TTFT: Time to First Token (end of user speech → first LLM token)
  - TTFA: Time to First Audio (end of user speech → first TTS audio chunk)
  - Tool call duration
  - Full turn duration

Stores per-turn metrics in Redis for p50/p95/p99 analysis.
Logs a summary at call end.

Pipeline placement:
    STT → ... → [LatencyTracker] → LLM → TTS → [LatencyTracker] → Output
"""

import time
import logging
import json
import asyncio
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict

from pipecat.frames.frames import (
    Frame,
    TextFrame,
    TranscriptionFrame,
    LLMFullResponseEndFrame,
    AudioRawFrame,
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

logger = logging.getLogger(__name__)


@dataclass
class TurnMetrics:
    """Metrics for a single conversational turn."""
    turn_id: int = 0
    user_speech_end: float = 0.0
    first_llm_token: float = 0.0
    first_audio_out: float = 0.0
    llm_complete: float = 0.0
    tool_call_start: float = 0.0
    tool_call_end: float = 0.0

    @property
    def ttft_ms(self) -> float:
        """Time to First Token (ms)."""
        if self.user_speech_end and self.first_llm_token:
            return (self.first_llm_token - self.user_speech_end) * 1000
        return 0.0

    @property
    def ttfa_ms(self) -> float:
        """Time to First Audio (ms) — the metric users feel."""
        if self.user_speech_end and self.first_audio_out:
            return (self.first_audio_out - self.user_speech_end) * 1000
        return 0.0

    @property
    def tool_duration_ms(self) -> float:
        """Tool call duration (ms)."""
        if self.tool_call_start and self.tool_call_end:
            return (self.tool_call_end - self.tool_call_start) * 1000
        return 0.0

    @property
    def total_turn_ms(self) -> float:
        """Full turn duration (ms)."""
        if self.user_speech_end and self.llm_complete:
            return (self.llm_complete - self.user_speech_end) * 1000
        return 0.0


class LatencyTracker(FrameProcessor):
    """Pipecat FrameProcessor that instruments per-turn latency.

    Place in the pipeline after STT (to capture user speech end)
    and after TTS (to capture first audio). Or use a single instance
    that observes all frame types passing through.
    """

    def __init__(self, call_id: str, redis_service=None):
        super().__init__()
        self.call_id = call_id
        self.redis_service = redis_service
        self._current_turn = TurnMetrics()
        self._turn_count = 0
        self._completed_turns: List[TurnMetrics] = []
        self._awaiting_first_token = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        now = time.monotonic()

        # ── User speech end (start of agent turn) ───────────────
        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip() if hasattr(frame, "text") else ""
            if text:
                # Each new user utterance starts a new turn
                self._turn_count += 1
                self._current_turn = TurnMetrics(turn_id=self._turn_count)
                self._current_turn.user_speech_end = now
                self._awaiting_first_token = True

        # ── First LLM token ─────────────────────────────────────
        elif isinstance(frame, TextFrame) and self._awaiting_first_token:
            if self._current_turn.user_speech_end > 0:
                self._current_turn.first_llm_token = now
                self._awaiting_first_token = False
                ttft = self._current_turn.ttft_ms
                logger.info(
                    f"[LATENCY] Turn {self._turn_count} TTFT: {ttft:.0f}ms"
                )

        # ── First audio output ──────────────────────────────────
        elif isinstance(frame, AudioRawFrame):
            if (
                self._current_turn.user_speech_end > 0
                and self._current_turn.first_audio_out == 0
            ):
                self._current_turn.first_audio_out = now
                ttfa = self._current_turn.ttfa_ms
                logger.info(
                    f"[LATENCY] Turn {self._turn_count} TTFA: {ttfa:.0f}ms"
                )

        # ── LLM response complete ──────────────────────────────
        elif isinstance(frame, LLMFullResponseEndFrame):
            if self._current_turn.user_speech_end > 0:
                self._current_turn.llm_complete = now
                total = self._current_turn.total_turn_ms
                logger.info(
                    f"[LATENCY] Turn {self._turn_count} total: {total:.0f}ms"
                )
                self._completed_turns.append(self._current_turn)

                # Store in Redis if available
                if self.redis_service:
                    await self._store_turn_metrics(self._current_turn)

        # Always pass frame through
        await self.push_frame(frame, direction)

    def mark_tool_start(self):
        """Call this before executing a tool."""
        self._current_turn.tool_call_start = time.monotonic()

    def mark_tool_end(self):
        """Call this after a tool completes."""
        self._current_turn.tool_call_end = time.monotonic()
        dur = self._current_turn.tool_duration_ms
        logger.info(
            f"[LATENCY] Turn {self._turn_count} tool call: {dur:.0f}ms"
        )

    async def _store_turn_metrics(self, turn: TurnMetrics):
        """Store per-turn metrics in Redis for later analysis."""
        try:
            metrics = {
                "turn_id": str(turn.turn_id),
                "ttft_ms": f"{turn.ttft_ms:.1f}",
                "ttfa_ms": f"{turn.ttfa_ms:.1f}",
                "tool_ms": f"{turn.tool_duration_ms:.1f}",
                "total_ms": f"{turn.total_turn_ms:.1f}",
            }
            await self.redis_service.client.xadd(
                f"call:{self.call_id}:latency", metrics
            )
        except Exception as e:
            logger.warning(f"Failed to store latency metrics: {e}")

    def get_summary(self) -> Dict:
        """Get p50/p95/p99 summary for the call."""
        if not self._completed_turns:
            return {"turns": 0}

        ttfts = [t.ttft_ms for t in self._completed_turns if t.ttft_ms > 0]
        ttfas = [t.ttfa_ms for t in self._completed_turns if t.ttfa_ms > 0]
        tools = [t.tool_duration_ms for t in self._completed_turns if t.tool_duration_ms > 0]

        def percentiles(values):
            if not values:
                return {"p50": 0, "p95": 0, "p99": 0}
            s = sorted(values)
            n = len(s)
            return {
                "p50": s[n // 2],
                "p95": s[int(n * 0.95)] if n >= 20 else s[-1],
                "p99": s[int(n * 0.99)] if n >= 100 else s[-1],
            }

        summary = {
            "turns": len(self._completed_turns),
            "ttft": percentiles(ttfts),
            "ttfa": percentiles(ttfas),
            "tool_calls": percentiles(tools),
        }

        logger.info(
            f"[LATENCY SUMMARY] Call {self.call_id}: "
            f"{summary['turns']} turns, "
            f"TTFT p50={summary['ttft']['p50']:.0f}ms, "
            f"TTFA p50={summary['ttfa']['p50']:.0f}ms"
        )
        return summary

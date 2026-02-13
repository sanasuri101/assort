"""
KB Prefetcher — speculative knowledge base lookups on STT partials.

Listens to interim STT transcription frames and starts a KB lookup
in the background once the partial stabilizes. When the LLM eventually
triggers a `search_knowledge_base` tool call, the result may already
be cached — eliminating the ~400ms embedding + search latency.

Pipeline placement: after STT, before user aggregator.

    STT → KBPrefetcher → TranscriptLogger → UserAggregator → LLM

Key behaviors:
  - Debounce: waits 300ms of stable text before triggering a lookup
  - Cancellation: abandons in-flight lookups if the user changes direction
  - Cache: stores results for retrieval by the tool handler
  - Minimum length: ignores very short partials (< 5 words)
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List

from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

from app.voice.knowledge import KnowledgeBase

logger = logging.getLogger(__name__)

# Minimum word count to trigger a prefetch
MIN_WORDS_FOR_PREFETCH = 4
# Debounce: only prefetch after text stabilizes for this duration
DEBOUNCE_SECONDS = 0.3
# Cache TTL: how long to keep prefetched results
CACHE_TTL_SECONDS = 10.0


class KBPrefetcher(FrameProcessor):
    """Speculatively prefetches KB results during STT streaming.

    When the user's partial transcript stabilizes (same text for 300ms),
    starts a background KB lookup and caches the result.

    The tool handler can call `get_cached_result(query)` to retrieve
    a pre-computed result instead of running a fresh KB lookup.
    """

    def __init__(self, kb: KnowledgeBase):
        super().__init__()
        self.kb = kb
        self._last_partial: str = ""
        self._debounce_task: Optional[asyncio.Task] = None
        self._inflight_task: Optional[asyncio.Task] = None
        self._cache: Dict[str, Dict[str, Any]] = {}
        # {query_text: {"results": [...], "timestamp": float}}

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip() if hasattr(frame, "text") else ""
            if text and len(text.split()) >= MIN_WORDS_FOR_PREFETCH:
                await self._on_partial(text)

        # Always pass frame through
        await self.push_frame(frame, direction)

    async def _on_partial(self, text: str):
        """Handle a new STT partial — debounce and prefetch."""
        self._last_partial = text

        # Cancel any pending debounce
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        # Start new debounce timer
        self._debounce_task = asyncio.create_task(self._debounced_prefetch(text))

    async def _debounced_prefetch(self, text: str):
        """Wait for stability, then trigger KB lookup."""
        try:
            await asyncio.sleep(DEBOUNCE_SECONDS)
        except asyncio.CancelledError:
            return  # User is still speaking / text changed

        # After debounce, check text hasn't changed
        if text != self._last_partial:
            return

        # Cancel any in-flight prefetch
        if self._inflight_task and not self._inflight_task.done():
            self._inflight_task.cancel()
            logger.debug(f"[PREFETCH] Cancelled stale prefetch")

        # Skip if we already have a cached result for similar text
        if self._has_cached(text):
            logger.debug(f"[PREFETCH] Cache hit for: '{text[:50]}'")
            return

        # Launch background KB lookup
        self._inflight_task = asyncio.create_task(self._do_prefetch(text))

    async def _do_prefetch(self, query: str):
        """Execute the KB lookup in the background."""
        try:
            start = time.monotonic()
            results = await self.kb.query(query, top_k=3)
            elapsed = (time.monotonic() - start) * 1000

            self._cache[query.lower().strip()] = {
                "results": results,
                "timestamp": time.monotonic(),
            }

            if results:
                logger.info(
                    f"[PREFETCH] Cached {len(results)} results for "
                    f"'{query[:50]}' in {elapsed:.0f}ms"
                )
            else:
                logger.debug(f"[PREFETCH] No results for: '{query[:50]}'")

        except asyncio.CancelledError:
            logger.debug(f"[PREFETCH] Cancelled lookup for: '{query[:30]}'")
        except Exception as e:
            logger.warning(f"[PREFETCH] KB lookup failed: {e}")

    def _has_cached(self, query: str) -> bool:
        """Check if we have a recent cached result for this query."""
        key = query.lower().strip()
        entry = self._cache.get(key)
        if not entry:
            return False
        age = time.monotonic() - entry["timestamp"]
        return age < CACHE_TTL_SECONDS

    def get_cached_result(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve a prefetched result if available and fresh.

        Called by the tool handler to skip the full KB lookup.

        Returns:
            List of result dicts if cache hit, None if cache miss.
        """
        key = query.lower().strip()
        entry = self._cache.get(key)

        if entry:
            age = time.monotonic() - entry["timestamp"]
            if age < CACHE_TTL_SECONDS:
                logger.info(
                    f"[PREFETCH] Tool using cached result "
                    f"({age:.1f}s old, {len(entry['results'])} results)"
                )
                return entry["results"]
            else:
                # Stale — remove it
                del self._cache[key]

        # Also check for partial matches (the tool query may differ slightly)
        for cached_key, cached_entry in list(self._cache.items()):
            age = time.monotonic() - cached_entry["timestamp"]
            if age >= CACHE_TTL_SECONDS:
                del self._cache[cached_key]
                continue
            # Simple containment check for partial matches
            if key in cached_key or cached_key in key:
                logger.info(
                    f"[PREFETCH] Fuzzy cache hit: tool='{key[:30]}' "
                    f"cached='{cached_key[:30]}'"
                )
                return cached_entry["results"]

        return None

    def clear_cache(self):
        """Clear all cached prefetch results."""
        self._cache.clear()

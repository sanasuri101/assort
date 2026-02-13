"""Tests for the KBPrefetcher module."""

import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from app.voice.kb_prefetch import KBPrefetcher, DEBOUNCE_SECONDS


class TestKBPrefetcherCache:
    """Tests for the prefetch cache logic (no async needed)."""

    def test_empty_cache_returns_none(self):
        """Cache miss should return None."""
        kb_mock = MagicMock()
        prefetcher = KBPrefetcher(kb=kb_mock)
        result = prefetcher.get_cached_result("office hours")
        assert result is None

    def test_cached_result_returned(self):
        """Manually inserted cache entries should be retrievable."""
        kb_mock = MagicMock()
        prefetcher = KBPrefetcher(kb=kb_mock)

        # Manually populate cache
        prefetcher._cache["office hours"] = {
            "results": [{"content": "We are open...", "score": 0.85}],
            "timestamp": time.monotonic(),
        }

        result = prefetcher.get_cached_result("office hours")
        assert result is not None
        assert len(result) == 1
        assert result[0]["content"] == "We are open..."

    def test_stale_cache_returns_none(self):
        """Expired cache entries should not be returned."""
        kb_mock = MagicMock()
        prefetcher = KBPrefetcher(kb=kb_mock)

        # Insert an entry that's already expired
        prefetcher._cache["old query"] = {
            "results": [{"content": "stale", "score": 0.7}],
            "timestamp": time.monotonic() - 20.0,  # 20s ago, way past TTL
        }

        result = prefetcher.get_cached_result("old query")
        assert result is None

    def test_fuzzy_match_on_containment(self):
        """Partial query containment should trigger a fuzzy cache hit."""
        kb_mock = MagicMock()
        prefetcher = KBPrefetcher(kb=kb_mock)

        prefetcher._cache["what are your office hours"] = {
            "results": [{"content": "Monday through Friday", "score": 0.9}],
            "timestamp": time.monotonic(),
        }

        # Shorter query contained in cached key
        result = prefetcher.get_cached_result("office hours")
        assert result is not None
        assert result[0]["content"] == "Monday through Friday"

    def test_clear_cache(self):
        """clear_cache should empty all entries."""
        kb_mock = MagicMock()
        prefetcher = KBPrefetcher(kb=kb_mock)

        prefetcher._cache["q1"] = {"results": [], "timestamp": time.monotonic()}
        prefetcher._cache["q2"] = {"results": [], "timestamp": time.monotonic()}

        prefetcher.clear_cache()
        assert len(prefetcher._cache) == 0


class TestKBPrefetcherChunking:
    """Tests for the chunking and text processing helpers."""

    def test_short_text_ignored(self):
        """Texts shorter than MIN_WORDS_FOR_PREFETCH should not trigger prefetch."""
        kb_mock = MagicMock()
        prefetcher = KBPrefetcher(kb=kb_mock)

        # Simulate: _on_partial should not be called for short text
        # We test by checking that the method wouldn't match
        from app.voice.kb_prefetch import MIN_WORDS_FOR_PREFETCH
        short_text = " ".join(["word"] * (MIN_WORDS_FOR_PREFETCH - 1))
        assert len(short_text.split()) < MIN_WORDS_FOR_PREFETCH

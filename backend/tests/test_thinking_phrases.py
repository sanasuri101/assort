"""Tests for thinking_phrases module."""

import pytest
from app.voice.thinking_phrases import (
    get_thinking_phrase,
    clear_call_phrases,
    TOOL_PHRASES,
    DEFAULT_PHRASES,
)


class TestGetThinkingPhrase:
    """Tests for get_thinking_phrase function."""

    def test_returns_phrase_for_known_tool(self):
        """Each known tool type should return a phrase from its pool."""
        for tool_name in TOOL_PHRASES:
            phrase = get_thinking_phrase(tool_name)
            assert phrase in TOOL_PHRASES[tool_name], \
                f"Phrase '{phrase}' not in pool for '{tool_name}'"

    def test_returns_default_for_unknown_tool(self):
        """Unknown tool types should fall back to the default pool."""
        phrase = get_thinking_phrase("unknown_tool_xyz")
        assert phrase in DEFAULT_PHRASES

    def test_phrases_are_nonempty_strings(self):
        """All phrases should be non-empty strings."""
        for tool_name, phrases in TOOL_PHRASES.items():
            for p in phrases:
                assert isinstance(p, str)
                assert len(p) > 0

    def test_per_call_dedup_avoids_repetition(self):
        """Phrases should not repeat within a call (up to pool exhaustion)."""
        call_id = "test-dedup-001"
        clear_call_phrases(call_id)

        # Get all phrases for verify_patient (5 in pool)
        pool_size = len(TOOL_PHRASES["verify_patient"])
        seen = set()
        for _ in range(pool_size):
            phrase = get_thinking_phrase("verify_patient", call_id=call_id)
            seen.add(phrase)

        # Should have gotten at least min(pool_size, 4) unique phrases
        # (tracker keeps last 3, so 4th may be the 1st again)
        assert len(seen) >= min(pool_size, 3)

        clear_call_phrases(call_id)

    def test_clear_call_phrases(self):
        """Cleanup should remove tracking for a specific call."""
        call_id = "test-clear-001"
        get_thinking_phrase("verify_patient", call_id=call_id)
        get_thinking_phrase("verify_patient", call_id=call_id)
        clear_call_phrases(call_id)

        # After clearing, should be able to get any phrase again
        phrase = get_thinking_phrase("verify_patient", call_id=call_id)
        assert phrase in TOOL_PHRASES["verify_patient"]

    def test_different_calls_have_independent_tracking(self):
        """Each call_id should have its own phrase history."""
        call_a = "test-call-a"
        call_b = "test-call-b"
        clear_call_phrases(call_a)
        clear_call_phrases(call_b)

        phrase_a = get_thinking_phrase("verify_patient", call_id=call_a)
        phrase_b = get_thinking_phrase("verify_patient", call_id=call_b)

        # Both should be valid phrases (may or may not be the same)
        assert phrase_a in TOOL_PHRASES["verify_patient"]
        assert phrase_b in TOOL_PHRASES["verify_patient"]

        clear_call_phrases(call_a)
        clear_call_phrases(call_b)

    def test_all_tool_types_have_sufficient_variety(self):
        """Each tool type should have at least 3 phrases to avoid repetition."""
        for tool_name, phrases in TOOL_PHRASES.items():
            assert len(phrases) >= 3, \
                f"Tool '{tool_name}' has only {len(phrases)} phrases, need >=3"

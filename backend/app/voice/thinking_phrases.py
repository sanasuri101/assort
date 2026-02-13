"""
Thinking Phrases — context-aware filler utterances during tool calls.

Reduces perceived latency by filling dead air while tool calls execute.
Phrases are selected randomly per tool type to avoid repetition.

Usage:
    phrase = get_thinking_phrase("verify_patient")
    # → "Let me pull up your records..."
"""

import random
from typing import Optional

# ── Phrase Pools ────────────────────────────────────────────────────────
# Grouped by tool type for context-appropriate responses.
# Each pool has enough variety to avoid repetition across a single call.

TOOL_PHRASES = {
    "verify_patient": [
        "Let me pull up your records real quick.",
        "One moment while I look you up in our system.",
        "Let me verify that for you.",
        "Sure, let me check on that right now.",
        "Pulling up your information now.",
    ],
    "search_knowledge_base": [
        "Let me check on that for you.",
        "One moment, I'm looking that up.",
        "Great question, let me find that information.",
        "Sure, give me just a second.",
        "Let me look into that.",
    ],
    "get_availability": [
        "Let me check what we have available.",
        "One moment while I look at the schedule.",
        "Let me see what times are open.",
        "Sure, pulling up the calendar now.",
        "Let me check our availability for you.",
    ],
    "book_appointment": [
        "Let me get that booked for you.",
        "One moment while I confirm that slot.",
        "Sure, I'm scheduling that right now.",
        "Let me lock that in for you.",
        "Getting that appointment set up now.",
    ],
    "check_insurance": [
        "Let me verify your coverage.",
        "One moment while I check your plan.",
        "Let me look into your insurance details.",
        "Sure, checking on that now.",
        "Pulling up your insurance information.",
    ],
    "list_providers": [
        "Let me see who's available.",
        "One moment while I check our providers.",
        "Let me pull up our provider list.",
        "Sure, looking that up now.",
        "Let me find our available providers.",
    ],
}

# Fallback phrases for any tool type not explicitly mapped
DEFAULT_PHRASES = [
    "One moment please.",
    "Let me look into that.",
    "Sure, give me just a second.",
    "Working on that for you.",
    "Let me check on that.",
]

# Track recently used phrases per call to avoid repetition
_recent_phrases: dict[str, list[str]] = {}


def get_thinking_phrase(
    tool_name: str,
    call_id: Optional[str] = None,
) -> str:
    """Select a context-aware thinking phrase for a tool call.

    Avoids repeating the same phrase within a call by tracking recently used.
    Falls back to a default pool for unknown tool types.

    Args:
        tool_name: The function_name of the tool being called
        call_id: Optional call ID for per-call dedup

    Returns:
        A natural-sounding filler phrase
    """
    pool = TOOL_PHRASES.get(tool_name, DEFAULT_PHRASES)

    # Per-call dedup: avoid repeating phrases within the same call
    if call_id:
        recent_key = f"{call_id}:{tool_name}"
        recent = _recent_phrases.get(recent_key, [])

        # Filter out recently used phrases
        available = [p for p in pool if p not in recent]
        if not available:
            # All used — reset and start over
            available = pool
            recent = []

        phrase = random.choice(available)
        recent.append(phrase)
        _recent_phrases[recent_key] = recent[-3:]  # Keep last 3
    else:
        phrase = random.choice(pool)

    return phrase


def clear_call_phrases(call_id: str):
    """Clean up phrase tracking for a completed call."""
    keys_to_remove = [k for k in _recent_phrases if k.startswith(f"{call_id}:")]
    for k in keys_to_remove:
        del _recent_phrases[k]

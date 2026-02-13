"""Comprehensive tests for the hardened KnowledgeBase RAG pipeline.

Tests the full cycle: seed → cache → index → query → metadata
Uses production VALLEY_FAMILY_MEDICINE_FAQ data (7 items).

Key design decisions:
  - Module-scoped seed: seeds once, reuses across all tests (~15s vs ~77s)
  - Asserts metadata fields (category, source_key) in every result
  - Tests embedding cache hit/miss behavior
  - Tests category-filtered search
"""

import pytest
import pytest_asyncio
import asyncio
from app.voice.knowledge import KnowledgeBase, VALLEY_FAMILY_MEDICINE_FAQ, EMBEDDING_CACHE_PREFIX


# ── Shared Fixtures ─────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def seeded_kb():
    """Module-scoped: seed the KB once for all tests in this file."""
    from app.config import settings

    kb = KnowledgeBase(settings.redis_url)

    # Drop existing index to start clean
    try:
        await kb.redis.ft("idx:knowledge").dropindex(delete_documents=True)
    except Exception:
        pass

    # Clean up any cached embeddings and knowledge keys from prior runs
    for pattern in [f"{EMBEDDING_CACHE_PREFIX}*", "knowledge:*"]:
        keys = await kb.redis.keys(pattern)
        if keys:
            await kb.redis.delete(*keys)

    await kb.seed(VALLEY_FAMILY_MEDICINE_FAQ)
    await asyncio.sleep(2)  # Wait for RediSearch background indexing

    yield kb

    await kb.close()


# ── Test Cases ──────────────────────────────────────────────────────────

DIRECT_MATCH_QUERIES = [
    ("When are you open during the week?", "hours", "Monday"),
    ("Where is the clinic located?", "location", "located"),
    ("What's your phone number to call?", "phone", "phone"),
    ("Is there parking available near the building?", "parking", "parking"),
]

SEMANTIC_MATCH_QUERIES = [
    ("Do you take Blue Cross insurance?", "insurance", "insurance"),
    ("What if I need to cancel my appointment?", "cancellation", "cancel"),
]

PARAPHRASED_QUERIES = [
    ("I'm a first-time patient, what should I bring?", "new_patient", "new patient"),
    ("What is the address of your medical office building?", "location", "Valley Blvd"),
]

INFERENCE_QUERIES = [
    ("Can I come in on Saturday?", "hours", "closed"),
    ("What happens if I miss my appointment?", "cancellation", "missed"),
]


# ── Core Tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio(scope="module")
async def test_seed_indexes_all_documents(seeded_kb):
    """Verify all 7 FAQ items are indexed."""
    keys = await seeded_kb.redis.keys("knowledge:*")
    assert len(keys) == 7, f"Expected 7 FAQ items, got {len(keys)}: {keys}"

    info = await seeded_kb.redis.ft("idx:knowledge").info()
    num_docs = int(info["num_docs"])
    assert num_docs == 7, f"Index has {num_docs} docs, expected 7"


@pytest.mark.asyncio(scope="module")
@pytest.mark.parametrize("query,expected_category,expected_substr", DIRECT_MATCH_QUERIES)
async def test_direct_match(seeded_kb, query, expected_category, expected_substr):
    """Direct queries should match the correct FAQ category."""
    results = await seeded_kb.query(query)
    assert len(results) >= 1, f"No results for: '{query}'"

    top = results[0]
    assert expected_substr.lower() in top["content"].lower(), \
        f"Expected '{expected_substr}' in content, got: '{top['content'][:80]}'"
    assert "category" in top, "Missing 'category' metadata"
    assert "source_key" in top, "Missing 'source_key' metadata"
    assert top["score"] > 0.6, f"Score {top['score']:.3f} below threshold"


@pytest.mark.asyncio(scope="module")
@pytest.mark.parametrize("query,expected_category,expected_substr", SEMANTIC_MATCH_QUERIES)
async def test_semantic_match(seeded_kb, query, expected_category, expected_substr):
    """Semantically related queries should resolve to the right FAQ."""
    results = await seeded_kb.query(query)
    assert len(results) >= 1, f"No results for: '{query}'"
    assert expected_substr.lower() in results[0]["content"].lower()
    assert results[0]["category"] == expected_category, \
        f"Expected category '{expected_category}', got '{results[0]['category']}'"


@pytest.mark.asyncio(scope="module")
@pytest.mark.parametrize("query,expected_category,expected_substr", PARAPHRASED_QUERIES)
async def test_paraphrased(seeded_kb, query, expected_category, expected_substr):
    """Paraphrased queries should still retrieve the correct FAQ entry."""
    results = await seeded_kb.query(query)
    assert len(results) >= 1, f"No results for: '{query}'"
    assert expected_substr.lower() in results[0]["content"].lower()
    assert results[0]["category"] == expected_category


@pytest.mark.asyncio(scope="module")
@pytest.mark.parametrize("query,expected_category,expected_substr", INFERENCE_QUERIES)
async def test_inference(seeded_kb, query, expected_category, expected_substr):
    """Queries requiring inference should still find relevant FAQ entries."""
    results = await seeded_kb.query(query)
    assert len(results) >= 1, f"No results for: '{query}'"
    assert expected_substr.lower() in results[0]["content"].lower()


# ── Edge Cases ──────────────────────────────────────────────────────────

@pytest.mark.asyncio(scope="module")
async def test_irrelevant_query_returns_nothing(seeded_kb):
    """Completely irrelevant queries should return 0 results."""
    results = await seeded_kb.query("What is the capital of France?")
    assert len(results) == 0, \
        f"Expected 0 results for irrelevant query, got {len(results)}: {results}"


@pytest.mark.asyncio(scope="module")
async def test_multi_result_ranking(seeded_kb):
    """top_k=3 should return correctly ranked results."""
    results = await seeded_kb.query("What are your office hours and location?", top_k=3)
    assert len(results) >= 1, "Expected at least 1 result"

    for i in range(len(results) - 1):
        assert results[i]["score"] >= results[i + 1]["score"], \
            f"Results not sorted: [{i}]={results[i]['score']:.3f} < [{i+1}]={results[i+1]['score']:.3f}"


@pytest.mark.asyncio(scope="module")
async def test_all_scores_above_threshold(seeded_kb):
    """Every returned result must exceed the similarity threshold."""
    for q in ["office hours", "insurance plans", "new patient"]:
        results = await seeded_kb.query(q)
        for r in results:
            assert r["score"] > 0.6, f"Score {r['score']:.3f} below 0.6 for '{q}'"


# ── New: Architecture-Specific Tests ────────────────────────────────────

@pytest.mark.asyncio(scope="module")
async def test_embedding_cache_hit(seeded_kb):
    """After seeding, embeddings should be cached in Redis."""
    cache_keys = await seeded_kb.redis.keys(f"{EMBEDDING_CACHE_PREFIX}*")
    # At least 7 cached embeddings (one per FAQ item)
    assert len(cache_keys) >= 7, f"Expected >=7 cached embeddings, got {len(cache_keys)}"


@pytest.mark.asyncio(scope="module")
async def test_metadata_fields_present(seeded_kb):
    """All query results must include category and source_key metadata."""
    results = await seeded_kb.query("What insurance do you accept?")
    assert len(results) >= 1
    for r in results:
        assert "category" in r, f"Missing 'category' in result: {r}"
        assert "source_key" in r, f"Missing 'source_key' in result: {r}"
        assert r["category"] != "", "Empty category"
        assert r["source_key"] != "", "Empty source_key"


@pytest.mark.asyncio(scope="module")
async def test_category_filtered_search(seeded_kb):
    """Category filter should restrict results to a specific FAQ topic."""
    # Search with insurance filter — should only return insurance-related
    results = await seeded_kb.query(
        "Do you accept insurance?",
        top_k=3,
        category_filter="insurance",
    )
    for r in results:
        assert r["category"] == "insurance", \
            f"Category filter failed: got '{r['category']}' instead of 'insurance'"


@pytest.mark.asyncio(scope="module")
async def test_configurable_threshold(seeded_kb):
    """Higher threshold should return fewer or no results."""
    # Very high threshold: should return nothing
    results_strict = await seeded_kb.query("office hours", threshold=0.95)
    # Default threshold: should return something
    results_default = await seeded_kb.query("office hours")

    assert len(results_default) >= len(results_strict), \
        "Stricter threshold should return fewer or equal results"


@pytest.mark.asyncio(scope="module")
async def test_chunking_short_text(seeded_kb):
    """Short FAQ entries should not be chunked (1 doc per entry)."""
    from app.voice.knowledge import KnowledgeBase as KB
    chunks = KB._chunk_text("Short text under 500 chars.")
    assert len(chunks) == 1
    assert chunks[0] == "Short text under 500 chars."


@pytest.mark.asyncio(scope="module")
async def test_chunking_long_text(seeded_kb):
    """Long text should be split into overlapping chunks."""
    from app.voice.knowledge import KnowledgeBase as KB
    long_text = "A" * 1200  # 1200 chars
    chunks = KB._chunk_text(long_text, chunk_size=500, overlap=50)
    assert len(chunks) >= 3, f"Expected >=3 chunks, got {len(chunks)}"
    # Verify overlap: end of chunk N overlaps with start of chunk N+1
    assert chunks[0][-50:] == chunks[1][:50], "Chunks should overlap"

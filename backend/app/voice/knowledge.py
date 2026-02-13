"""
Knowledge base powered by Redis Vector Search.
Stores and retrieves practice FAQs with embedding caching,
metadata-enriched retrieval, and configurable thresholds.

Architecture:
  - Embeddings are cached in Redis with content-hash keys (no re-embedding static data)
  - Gemini SDK calls are offloaded via asyncio.to_thread (non-blocking)
  - Documents are chunked for longer content with configurable overlap
  - Query results include metadata (category, source_key) for tracing
  - Similarity threshold is configurable per query
"""

import logging
import hashlib
import asyncio
from typing import List, Dict, Any, Optional

import redis.asyncio as aioredis
from google import genai
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Gemini embedding-001 returns 3072 dimensions
EMBEDDING_DIM = 3072
INDEX_NAME = "idx:knowledge"
EMBEDDING_CACHE_PREFIX = "emb_cache:"

# Chunking defaults
DEFAULT_CHUNK_SIZE = 500       # characters
DEFAULT_CHUNK_OVERLAP = 50     # characters
DEFAULT_SIMILARITY_THRESHOLD = 0.6


class KnowledgeBase:
    """Production-quality RAG knowledge base backed by RediSearch.

    Features:
      - Embedding cache: static content is embedded once
      - Non-blocking: Gemini calls run in a thread pool
      - Metadata: results include category and source key
      - Chunking: long documents are split for better retrieval
      - Configurable threshold: per-query similarity cutoff
    """

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.genai_client = genai.Client(api_key=settings.gemini_api_key)

    # ── Embedding Layer ─────────────────────────────────────────────────

    def _content_hash(self, text: str) -> str:
        """Deterministic hash for embedding cache key."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _embed_sync(self, text: str) -> List[float]:
        """Synchronous Gemini embedding call (runs in thread pool)."""
        result = self.genai_client.models.embed_content(
            model=settings.embedding_model,
            contents=text,
        )
        return result.embeddings[0].values

    async def _get_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """Get embedding with content-hash cache.

        Cache flow:
          1. Hash the text content
          2. Check Redis for cached embedding bytes
          3. On miss: call Gemini (via thread pool), cache the result
        """
        cache_key = f"{EMBEDDING_CACHE_PREFIX}{self._content_hash(text)}"

        # Check cache
        if use_cache:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    return np.frombuffer(cached, dtype=np.float32).tolist()
            except Exception:
                pass  # Cache miss or error, proceed to embed

        # Embed in thread pool to avoid blocking the event loop
        try:
            values = await asyncio.to_thread(self._embed_sync, text)
        except Exception as e:
            logger.error(f"Embedding failed for text '{text[:50]}...': {e}")
            return []

        # Cache the result (no expiry — FAQ content is static)
        try:
            emb_bytes = np.array(values, dtype=np.float32).tobytes()
            await self.redis.set(cache_key, emb_bytes)
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")

        return values

    # ── Chunking Layer ──────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> List[str]:
        """Split text into overlapping chunks.

        Short texts (< chunk_size) are returned as-is.
        Longer texts are split at chunk_size boundaries with overlap.
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks

    # ── Index Management ────────────────────────────────────────────────

    async def _ensure_index(self):
        """Create RediSearch vector index if it does not exist."""
        try:
            await self.redis.ft(INDEX_NAME).info()
            return  # Index exists
        except Exception:
            pass  # Needs creation

        from redis.commands.search.field import TextField, TagField, VectorField
        from redis.commands.search.indexDefinition import IndexDefinition, IndexType

        schema = (
            TextField("content"),
            TagField("category"),
            TagField("source_key"),
            VectorField("embedding", "HNSW", {
                "TYPE": "FLOAT32",
                "DIM": EMBEDDING_DIM,
                "DISTANCE_METRIC": "COSINE",
            }),
        )

        await self.redis.ft(INDEX_NAME).create_index(
            fields=schema,
            definition=IndexDefinition(
                prefix=["knowledge:"],
                index_type=IndexType.HASH,
            ),
        )
        logger.info(f"Created RediSearch index: {INDEX_NAME}")

    # ── Seed ────────────────────────────────────────────────────────────

    async def seed(self, practice_data: Dict[str, str]):
        """Embed and store FAQ data in Redis with metadata.

        Each entry is stored as a Redis Hash:
          knowledge:{key}[:{chunk_idx}] -> {
              content: str,
              category: str,       # the FAQ key (hours, insurance, etc.)
              source_key: str,     # original key for tracing
              embedding: bytes,    # FLOAT32 vector
          }

        Embeddings are cached — re-seeding with identical content
        skips the Gemini API call entirely.
        """
        await self._ensure_index()
        logger.info("Seeding knowledge base...")

        count = 0
        for key, content in practice_data.items():
            chunks = self._chunk_text(content)
            for i, chunk in enumerate(chunks):
                embedding = await self._get_embedding(chunk)
                if not embedding:
                    logger.warning(f"Skipping {key} chunk {i}: embedding failed")
                    continue

                emb_bytes = np.array(embedding, dtype=np.float32).tobytes()
                doc_key = f"knowledge:{key}" if len(chunks) == 1 else f"knowledge:{key}:{i}"

                await self.redis.hset(doc_key, mapping={
                    "content": chunk,
                    "category": key,
                    "source_key": key,
                    "embedding": emb_bytes,
                })
                count += 1

        logger.info(f"Seeded {count} documents from {len(practice_data)} FAQ entries.")

    # ── Query ───────────────────────────────────────────────────────────

    async def query(
        self,
        question: str,
        top_k: int = 1,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        category_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find most relevant FAQ answers using vector similarity search.

        Args:
            question: Natural-language query
            top_k: Maximum number of results
            threshold: Minimum cosine similarity (0.0–1.0)
            category_filter: Optional tag filter (e.g. "insurance")

        Returns:
            List of dicts with keys: content, score, category, source_key
        """
        query_emb = await self._get_embedding(question, use_cache=False)
        if not query_emb:
            return []

        q_vec = np.array(query_emb, dtype=np.float32).tobytes()

        from redis.commands.search.query import Query

        # Build FT.SEARCH query with optional category filter
        if category_filter:
            filter_expr = f"@category:{{{category_filter}}}"
            q_str = f"({filter_expr})=>[KNN {top_k} @embedding $vec AS score]"
        else:
            q_str = f"*=>[KNN {top_k} @embedding $vec AS score]"

        q = (
            Query(q_str)
            .sort_by("score")
            .return_fields("content", "score", "category", "source_key")
            .paging(0, top_k)
            .dialect(2)
        )

        try:
            res = await self.redis.ft(INDEX_NAME).search(q, query_params={"vec": q_vec})

            results = []
            for doc in res.docs:
                distance = float(doc.score)
                similarity = 1 - distance

                if similarity > threshold:
                    results.append({
                        "content": doc.content,
                        "score": similarity,
                        "category": doc.category,
                        "source_key": doc.source_key,
                    })

            return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def close(self):
        """Close the Redis connection."""
        await self.redis.aclose()


# ── Seed Data ───────────────────────────────────────────────────────────

VALLEY_FAMILY_MEDICINE_FAQ = {
    "hours": "We are open Monday through Friday from 8:00 AM to 5:00 PM. We are closed on weekends.",
    "location": "We are located at 123 Valley Blvd, Suite 200, within the Medical Arts Building.",
    "phone": "Our phone number is (555) 867-5309.",
    "insurance": "We accept most major insurance plans including Aetna, Blue Cross, United Healthcare, Cigna, and Medicare.",
    "new_patient": "New patients should arrive 15 minutes early and bring their photo ID and insurance card.",
    "cancellation": "We require 24 hours notice for cancellations to avoid a missed appointment fee.",
    "parking": "Free parking is available in the garage behind the building.",
}

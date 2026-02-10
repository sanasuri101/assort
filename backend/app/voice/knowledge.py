"""
Knowledge base powered by Redis Vector Search.
Stores and retrieves office FAQs.
"""

import logging
import json
import asyncio
from typing import List, Dict, Any

import redis.asyncio as redis
from google import genai
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Dimension for models/embedding-001
EMBEDDING_DIM = 768
INDEX_NAME = "idx:knowledge"


class KnowledgeBase:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.genai = genai.Client(api_key=settings.gemini_api_key)

    async def _get_embedding(self, text: str) -> List[float]:
        try:
            # google-genai embed_content is synchronous in the current SDK version (v0.x)
            # or we check if there's an async client. 
            # Actually, the user's snippet used genai.Client(api_key=...).
            # I'll use to_thread to keep it non-blocking if needed, but let's follow the user's snippet.
            result = self.genai.models.embed_content(
                model=settings.embedding_model,
                contents=text
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []

    async def _create_index(self):
        """Create RediSearch vector index if not exists."""
        try:
            from redis.commands.search.field import TextField, VectorField
            from redis.commands.search.index_definition import IndexDefinition, IndexType
            
            # Check if index exists
            try:
                await self.redis.ft(INDEX_NAME).info()
                return
            except:
                pass
            
            schema = (
                TextField("content"),
                VectorField("embedding", "HNSW", {
                    "TYPE": "FLOAT32",
                    "DIM": EMBEDDING_DIM,
                    "DISTANCE_METRIC": "COSINE"
                })
            )
            
            await self.redis.ft(INDEX_NAME).create_index(
                fields=schema,
                definition=IndexDefinition(prefix=["knowledge:"], index_type=IndexType.HASH)
            )
            logger.info(f"Created RediSearch index: {INDEX_NAME}")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")

    async def seed(self, practice_data: Dict[str, str]):
        """Embed and store FAQ data in Redis with Vector Search."""
        await self._create_index()
        
        logger.info("Seeding knowledge base...")
        
        for key, content in practice_data.items():
            embedding = await self._get_embedding(content)
            if not embedding:
                continue
                
            emb_bytes = np.array(embedding, dtype=np.float32).tobytes()
            
            await self.redis.hset(f"knowledge:{key}", mapping={
                "content": content,
                "embedding": emb_bytes
            })
        
        logger.info(f"Seeded {len(practice_data)} items.")

    async def query(self, question: str, top_k: int = 1) -> List[Dict[str, Any]]:
        """Find most relevant FAQ answer using FT.SEARCH."""
        query_emb = await self._get_embedding(question)
        if not query_emb:
            return []
            
        q_vec = np.array(query_emb, dtype=np.float32).tobytes()
        
        # FT.SEARCH query
        # Dialect 2 is required for vector search
        from redis.commands.search.query import Query
        
        q = Query(f"*=>[KNN {top_k} @embedding $vec AS score]") \
            .sort_by("score") \
            .return_fields("content", "score") \
            .paging(0, top_k) \
            .dialect(2)
            
        try:
            res = await self.redis.ft(INDEX_NAME).search(q, query_params={"vec": q_vec})
            
            results = []
            for doc in res.docs:
                # Score in KNN is distance, so lower is better (0 = perfect match)
                # We canonicalize it to similarity if needed, but here we just check threshold
                distance = float(doc.score)
                # For COSINE distance, similarity = 1 - distance
                similarity = 1 - distance
                
                if similarity > 0.6: # Higher threshold for vector search
                    results.append({
                        "content": doc.content,
                        "score": similarity
                    })
            
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def close(self):
        await self.redis.close()


# Seed data
VALLEY_FAMILY_MEDICINE_FAQ = {
    "hours": "We are open Monday through Friday from 8:00 AM to 5:00 PM. We are closed on weekends.",
    "location": "We are located at 123 Valley Blvd, Suite 200, within the Medical Arts Building.",
    "phone": "Our phone number is (555) 867-5309.",
    "insurance": "We accept most major insurance plans including Aetna, Blue Cross, United Healthcare, Cigna, and Medicare.",
    "new_patient": "New patients should arrive 15 minutes early and bring their photo ID and insurance card.",
    "cancellation": "We require 24 hours notice for cancellations to avoid a missed appointment fee.",
    "parking": "Free parking is available in the garage behind the building."
}

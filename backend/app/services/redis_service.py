import json
import logging
from datetime import datetime
from typing import Optional, Any, List

import redis.asyncio as redis
import numpy as np
import struct

from app.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    """
    Service for Redis operations, including call state management,
    interaction logging, and vector search.
    """

    def __init__(self):
        self.redis_url = settings.redis_url
        self.client: Optional[redis.Redis] = None
        logger.info(f"RedisService initialized with URL: {self.redis_url}")

    async def connect(self):
        if self.client is None:
            self.client = redis.from_url(
                self.redis_url, 
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Redis connected")

    async def close(self):
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Redis disconnected")

    def _is_connected(self) -> bool:
        return self.client is not None

    # ==================== Call State Management ====================

    async def set_call_state(self, call_id: str, state: dict):
        """Store or update the complete state of a call."""
        key = f"call:{call_id}:state"
        if not self._is_connected():
            await self.connect()
        
        await self.client.set(key, json.dumps(state))
        logger.debug(f"[Redis] Set state for call {call_id}")

    async def get_call_state(self, call_id: str) -> Optional[dict]:
        """Retrieve the current state of a call."""
        key = f"call:{call_id}:state"
        if not self._is_connected():
            await self.connect()
            
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    # ==================== Interaction Logging ====================

    async def log_call_interaction(self, call_id: str, interaction: dict):
        """
        Log an interaction (user or assistant speech) to a Redis list.
        Matches wnbHack patterns.
        """
        if not self._is_connected():
            await self.connect()

        key = f"call:{call_id}:interactions"
        interaction["timestamp"] = datetime.utcnow().isoformat()

        await self.client.rpush(key, json.dumps(interaction))
        logger.debug(f"[Redis] Logged interaction for call {call_id}: {interaction.get('type')}")

    async def get_call_interactions(self, call_id: str) -> List[dict]:
        """Get all logged interactions for a call."""
        if not self._is_connected():
            await self.connect()

        key = f"call:{call_id}:interactions"
        data = await self.client.lrange(key, 0, -1)
        return [json.loads(item) for item in data]

    # ==================== Vector Search ====================

    async def vector_search(
        self,
        query_embedding: List[float],
        k: int = 5
    ) -> List[dict]:
        """
        Perform vector similarity search on Redis knowledge base.
        """
        logger.info(f"[Redis] Vector search with k={k}")
        
        if not self._is_connected():
            await self.connect()

        try:
            # Get all knowledge base keys
            cursor = 0
            all_keys = []
            while True:
                # wnbHack uses skill:*, Assort Health uses kb:*
                cursor, keys = await self.client.scan(cursor, match="kb:*", count=100)
                all_keys.extend(keys)
                if cursor == 0:
                    break

            if not all_keys:
                logger.info("[Redis] No knowledge base keys found")
                return []

            logger.info(f"[Redis] Found {len(all_keys)} knowledge base keys")

            # Convert query embedding to numpy for cosine similarity
            query_vec = np.array(query_embedding)
            query_norm = np.linalg.norm(query_vec)
            if query_norm == 0:
                return []

            results = []
            for key in all_keys:
                try:
                    # Get the hash data
                    data = await self.client.hgetall(key)
                    if not data:
                        continue

                    # Extract vector bytes and convert to floats (wnbHack pattern)
                    vector_bytes = data.get("vector")
                    if not vector_bytes:
                        continue

                    # Handle bytes vs string (decoding for decode_responses=True)
                    if isinstance(vector_bytes, str):
                        # If it looks like JSON, parse it, else treat as latin-1 bytes
                        if vector_bytes.startswith("["):
                            stored_vec = np.array(json.loads(vector_bytes))
                        else:
                            vector_bytes_raw = vector_bytes.encode('latin-1')
                            num_floats = len(vector_bytes_raw) // 4
                            stored_vec = np.array(struct.unpack(f'{num_floats}f', vector_bytes_raw))
                    else:
                        num_floats = len(vector_bytes) // 4
                        stored_vec = np.array(struct.unpack(f'{num_floats}f', vector_bytes))

                    # Compute cosine similarity
                    stored_norm = np.linalg.norm(stored_vec)
                    if stored_norm == 0:
                        continue

                    similarity = np.dot(query_vec, stored_vec) / (query_norm * stored_norm)

                    # Get content
                    content = data.get("content") or ""
                    
                    results.append({
                        "content": content,
                        "metadata": {"source": "knowledge_base", "key": key},
                        "score": float(similarity)
                    })
                    
                except Exception as e:
                    logger.debug(f"[Redis] Error processing key {key}: {e}")
                    continue

            # Sort by similarity score and return top k
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:k]

        except Exception as e:
            logger.error(f"[Redis] Vector search failed: {e}")
            return []

_redis_service: Optional[RedisService] = None

def get_redis_service() -> RedisService:
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
    return _redis_service

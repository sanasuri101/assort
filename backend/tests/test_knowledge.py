"""
Test KnowledgeBase embedding and querying.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import numpy as np
import fakeredis.aioredis

from app.voice.knowledge import KnowledgeBase


@pytest.fixture
async def redis_client():
    r = fakeredis.aioredis.FakeRedis(decode_responses=False) # Bytes needed for embeddings
    yield r
    await r.close()


@pytest.fixture
def mock_openai():
    with patch("app.voice.knowledge.AsyncOpenAI") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


@pytest.mark.asyncio
async def test_knowledge_base_seed_and_query(redis_client, mock_openai):
    # Mock embedding response
    # 3 items: query, doc1, doc2
    # simple deterministic embeddings
    
    embeddings_map = {
        "hours": [1.0, 0.0, 0.0],
        "location": [0.0, 1.0, 0.0],
        "insurance": [0.0, 0.0, 1.0]
    }
    
    async def create_embedding(input, **kwargs):
        data = MagicMock()
        vec = embeddings_map.get(input, [0.1, 0.1, 0.1])
        # Pad to 1536
        vec = vec + [0.0] * (1536 - len(vec))
        data.data = [MagicMock(embedding=vec)]
        return data

    mock_openai.embeddings.create = AsyncMock(side_effect=create_embedding)

    # Initialize KB with injected redis
    with patch("redis.asyncio.from_url", return_value=redis_client):
        kb = KnowledgeBase("redis://test")
        # Overwrite openai client with our mock
        kb.openai = mock_openai
        
        # Seed
        data = {
            "hours": "hours",  # content matches key for mapping
            "location": "location"
        }
        await kb.seed(data)
        
        # Verify redis has data
        assert len(await redis_client.keys("knowledge:*")) == 2
        
        # Query matching "hours"
        results = await kb.query("hours")
        assert len(results) >= 1
        assert results[0]["content"] == "hours"
        assert results[0]["score"] > 0.99 # Should be 1.0
        
        # Query matching "location"
        results = await kb.query("location")
        assert len(results) >= 1
        assert results[0]["content"] == "location"

        await kb.close()

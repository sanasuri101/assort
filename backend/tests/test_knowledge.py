import pytest
import asyncio
from app.voice.knowledge import KnowledgeBase

@pytest.mark.asyncio
async def test_knowledge_base_seed_and_query(redis_client):
    # Initialize KB with real redis
    # We use the same redis_client fixture
    kb = KnowledgeBase("redis://localhost:6379") # Or settings.redis_url
    # Ensure it uses the test client instance to share connection if needed
    kb.redis = redis_client
    
    # Seed
    data = {
        "hours": "Our office hours are 24/7 for testing.",
        "location": "Our office is in the cloud."
    }
    await kb.seed(data)
    
    # Verify redis has data
    keys = await redis_client.keys("knowledge:*")
    assert len(keys) >= 2, f"Expected keys to be seeded, got {keys}"
    
    # Wait a bit for indexing
    await asyncio.sleep(2)
    
    # Query matching "hours"
    # We use a retry since indexing is async
    results = []
    for i in range(5):
        results = await kb.query("What are your hours?")
        if results:
            break
        print(f"Retry {i+1}: No results yet...")
        await asyncio.sleep(1)
        
    if not results:
        # Check if embeddings are failing
        emb = await kb._get_embedding("test")
        print(f"Test embedding length: {len(emb)}")
        # Check FT.INFO
        try:
            info = await kb.redis.ft("idx:knowledge").info()
            print(f"FT.INFO: num_docs={info['num_docs']}, percent_indexed={info['percent_indexed']}")
        except Exception as e:
            print(f"FT.INFO failed: {e}")
        
    assert len(results) >= 1, f"No results found for 'What are your hours?'. Index keys: {keys}"
    assert "hours" in results[0]["content"]
    
    await kb.close()
    # Explicitly stop the client to avoid background task issues in tests
    await kb.redis.close()

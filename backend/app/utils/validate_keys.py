import asyncio
import logging
import sys
import httpx
from google import genai
from redis.asyncio import Redis
from app.config import settings

logger = logging.getLogger("validate_keys")

async def validate_gemini():
    if not settings.gemini_api_key:
        print("⚠️ Gemini API key not set")
        return False, "Not set"
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        # Try a very standard model name
        model_name = settings.embedding_model
        client.models.embed_content(model=model_name, contents="test")
        print("✅ Gemini API key valid")
        return True, None
    except Exception as e:
        print(f"❌ Gemini validation failed with model '{settings.embedding_model}': {e}")
        try:
            # Try to list models to suggest a fix
            client = genai.Client(api_key=settings.gemini_api_key)
            models = [m.name for m in client.models.list()]
            emb_models = [m for m in models if "embedding" in m]
            print(f"   Available embedding models: {emb_models[:3]}...")
        except:
            pass
        return False, str(e)

async def validate_deepgram():
    if not settings.deepgram_api_key:
        print("⚠️ Deepgram API key not set")
        return False, "Not set"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.deepgram.com/v1/projects",
                headers={"Authorization": f"Token {settings.deepgram_api_key}"}
            )
            if resp.status_code == 200:
                print("✅ Deepgram API key valid")
                return True, None
            else:
                print(f"❌ Deepgram API key invalid ({resp.status_code} {resp.reason_phrase})")
                return False, f"{resp.status_code} {resp.reason_phrase}"
    except Exception as e:
        print(f"❌ Deepgram validation failed ({e})")
        return False, str(e)

async def validate_cartesia():
    if not settings.cartesia_api_key:
        print("⚠️ Cartesia API key not set")
        return False, "Not set"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.cartesia.ai/voices",
                headers={
                    "X-API-Key": settings.cartesia_api_key,
                    "Cartesia-Version": "2024-06-10"
                }
            )
            if resp.status_code == 200:
                print("✅ Cartesia API key valid")
                return True, None
            else:
                print(f"❌ Cartesia API key invalid ({resp.status_code} {resp.reason_phrase})")
                return False, f"{resp.status_code} {resp.reason_phrase}"
    except Exception as e:
        print(f"❌ Cartesia validation failed ({e})")
        return False, str(e)

async def validate_daily():
    if not settings.daily_api_key:
        print("⚠️ Daily API key not set")
        return False, "Not set"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.daily.co/v1/rooms",
                headers={"Authorization": f"Bearer {settings.daily_api_key}"}
            )
            if resp.status_code == 200:
                print("✅ Daily API key valid")
                return True, None
            else:
                print(f"❌ Daily API key invalid ({resp.status_code} {resp.reason_phrase})")
                return False, f"{resp.status_code} {resp.reason_phrase}"
    except Exception as e:
        print(f"❌ Daily validation failed ({e})")
        return False, str(e)

async def validate_redis():
    try:
        import time
        from redis import Redis as SyncRedis
        start = time.perf_counter()
        
        # Use sync client for validation check - more robust on Windows for pings
        r = SyncRedis.from_url(settings.redis_url, socket_timeout=5)
        r.ping()
        
        latency = (time.perf_counter() - start) * 1000
        r.close()
        print(f"✅ Redis connected (latency: {latency:.2f}ms)")
        return True, None
    except Exception as e:
        print(f"❌ Redis connection failed ({e})")
        return False, str(e)

async def validate_wandb():
    if not settings.wandb_api_key:
        print("⚠️ W&B API key not set (learning engine disabled)")
        return True, None # Optional
    # For speed, we just check if it's set
    print("✅ W&B API key set")
    return True, None

async def validate_all_keys():
    print("\n--- Starting API Key Validation ---")
    results = await asyncio.gather(
        validate_gemini(),
        validate_deepgram(),
        validate_cartesia(),
        validate_daily(),
        validate_redis(),
        validate_wandb()
    )
    
    # Required keys are the first 5
    required_results = results[:5]
    if all(r[0] for r in required_results):
        print("--- All required keys valid ---\n")
        return True
    else:
        print("--- ❌ CRITICAL: Missing or invalid required API keys ---\n")
        return False

if __name__ == "__main__":
    if asyncio.run(validate_all_keys()):
        sys.exit(0)
    else:
        sys.exit(1)

"""Assort Health API — main application entry point.

Creates FastAPI app with:
- Redis connection lifecycle (connect on startup, close on shutdown)
- HIPAA audit logging middleware
- CORS middleware (dev: allow all origins)
- Health check endpoint
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings
from app.middleware.auth import verify_api_key
from app.middleware.hipaa_audit import HIPAAAuditMiddleware
from app.routers.health import router as health_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("assort_health")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — Redis connection."""
    # Startup
    app.state.redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    try:
        await app.state.redis.ping()
        logger.info("Redis connected at %s", settings.redis_url)
    except Exception as e:
        logger.warning("Redis connection failed: %s (app will start anyway)", e)

    yield

    # Shutdown
    await app.state.redis.close()
    logger.info("Redis disconnected")


app = FastAPI(
    title="Assort Health API",
    version="0.1.0",
    description="AI Patient Experience Platform",
    lifespan=lifespan,
)

# Middleware (LIFO order — last added runs first on request)
# Add CORS first so it runs last (after HIPAA audit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HIPAA audit runs first on requests (added after CORS)
app.add_middleware(HIPAAAuditMiddleware)


# Include routers
app.include_router(health_router)


@app.get("/api/protected")
async def protected(api_key: str = Security(verify_api_key)):
    """Test endpoint requiring API key authentication."""
    return {"message": "authenticated"}


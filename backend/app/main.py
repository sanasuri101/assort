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
from app.routers.voice import router as voice_router
from app.routers.health import router as health_router
from app.routers.ehr import router as ehr_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("assort_health")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — Key validation & Redis connection."""
    # Startup
    from app.utils.validate_keys import validate_all_keys
    if not await validate_all_keys():
        logger.critical("Startup failed due to invalid or missing configuration.")
        raise RuntimeError("Configuration validation failed")

    app.state.redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    try:
        await app.state.redis.ping()
        logger.info("Redis connected at %s", settings.redis_url)
    except Exception as e:
        logger.warning("Redis connection failed: %s (app will start anyway)", e)

    # Initialize EHR Service (using factory)
    from app.services.ehr.factory import get_ehr_service
    app.state.ehr_service = get_ehr_service()
    logger.info("EHR Service initialized via factory")
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
    allow_origins=["http://localhost:5173", "http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HIPAA audit runs first on requests (added after CORS)
app.add_middleware(HIPAAAuditMiddleware)


# Routes
# Routes
from app.routers import health, ehr, voice
from app.api import dashboard

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(ehr.router, prefix="/api/ehr", tags=["EHR"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])


@app.get("/api/protected")
async def protected(api_key: str = Security(verify_api_key)):
    """Test endpoint requiring API key authentication."""
    return {"message": "authenticated"}


# Phase 1: Foundation - Research

**Researched:** 2026-02-09
**Domain:** Infrastructure, Python Backend, Redis, Docker, HIPAA Middleware
**Confidence:** HIGH

## Summary

Phase 1 builds the foundational infrastructure: Docker Compose to start all services, Redis 7+ with vector search and persistence, FastAPI skeleton with HIPAA audit middleware, and environment-based configuration. This is a standard infrastructure phase with well-established patterns.

**Primary recommendation:** Use Docker Compose with `redis/redis-stack` image (includes RediSearch, RedisJSON modules), FastAPI with middleware pattern for HIPAA audit logging, and pydantic-settings for environment configuration.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ | REST API framework | Async-native, Pydantic v2 validation, OpenAPI docs |
| uvicorn | 0.30+ | ASGI server | Standard FastAPI runner |
| pydantic | 2.x | Data validation | Type-safe models, settings management |
| pydantic-settings | 2.x | Env configuration | `.env` file loading, type coercion, validation |
| redis[hiredis] | 5.x | Redis client | Async support via `redis.asyncio`, hiredis for speed |
| python-dotenv | 1.x | Env file loading | `.env` support in development |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.27+ | HTTP client | Testing FastAPI with async client |
| pytest | 8.x | Testing | Unit and integration tests |
| pytest-asyncio | 0.24+ | Async testing | Testing async endpoints |

### Docker Images
| Image | Tag | Purpose |
|-------|-----|---------|
| redis/redis-stack | 7.4-latest | Redis with RediSearch + RedisJSON modules |
| python | 3.11-slim | FastAPI base image |
| node | 20-slim | Frontend dev server |

**Installation:**
```bash
pip install fastapi uvicorn pydantic pydantic-settings "redis[hiredis]" python-dotenv httpx pytest pytest-asyncio
```

## Architecture Patterns

### Recommended Project Structure
```
assort-health/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app creation + middleware
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── dependencies.py      # Dependency injection (Redis, etc.)
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── hipaa_audit.py   # HIPAA audit logging middleware
│   │   │   └── auth.py          # API key authentication
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── health.py        # Health check endpoints
│   │   └── models/
│   │       └── __init__.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       ├── __init__.py
│       └── test_health.py
├── frontend/
│   ├── package.json             # Placeholder for Phase 6
│   ├── index.html
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── .env                         # Gitignored
```

### Pattern 1: HIPAA Audit Middleware
**What:** FastAPI middleware that logs every request with PHI access metadata
**When to use:** Every API endpoint that touches patient data

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import json, time, logging

logger = logging.getLogger("hipaa.audit")

class HIPAAAuditMiddleware(BaseHTTPMiddleware):
    PHI_PATHS = ["/api/patients", "/api/appointments", "/api/ehr"]

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        if any(request.url.path.startswith(p) for p in self.PHI_PATHS):
            logger.info(json.dumps({
                "event": "phi_access",
                "timestamp": time.time(),
                "method": request.method,
                "path": request.url.path,
                "caller_ip": request.client.host,
                "api_key": request.headers.get("X-API-Key", "none"),
                "status": response.status_code,
                "duration_ms": (time.time() - start) * 1000,
            }))
        return response
```

### Pattern 2: API Key Authentication
**What:** Simple API key validation via dependency injection
**When to use:** All provider dashboard endpoints

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
```

### Pattern 3: Redis Connection with Lifecycle
**What:** Async Redis client with FastAPI lifespan context
**When to use:** Application startup/shutdown

```python
from contextlib import asynccontextmanager
from redis.asyncio import Redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await app.state.redis.ping()
    yield
    await app.state.redis.close()
```

### Anti-Patterns to Avoid
- **Global Redis connections:** Use FastAPI lifespan, not module-level connections that leak
- **Sync Redis in async context:** Always use `redis.asyncio`, never blocking `redis.Redis`
- **Hardcoded config:** All settings via environment variables, never in source code
- **HIPAA logging in individual routes:** Use middleware, not per-route audit calls

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Environment config | Custom env parser | pydantic-settings | Type validation, .env support, nested configs |
| API key auth | Custom header parsing | FastAPI Security(APIKeyHeader) | OpenAPI docs, proper 401 handling |
| Redis connection management | Manual connect/disconnect | FastAPI lifespan + redis.asyncio | Proper lifecycle, no leaked connections |
| Docker orchestration | Shell scripts to start services | Docker Compose | Health checks, dependency ordering, restart policies |

## Common Pitfalls

### Pitfall 1: Redis Vector Search Module Not Loaded
**What goes wrong:** `redis-stack` image has modules, but vanilla `redis` image doesn't
**Why it happens:** Using `redis:7` instead of `redis/redis-stack:7.4`
**How to avoid:** Use `redis/redis-stack` image explicitly in docker-compose.yml
**Warning signs:** `UNKNOWN command FT.CREATE` errors

### Pitfall 2: FastAPI Middleware Order
**What goes wrong:** Auth middleware runs after HIPAA logging, so audit logs miss caller identity
**Why it happens:** Middleware execution order is LIFO (last added runs first)
**How to avoid:** Add HIPAA audit middleware AFTER auth middleware in `main.py`
**Warning signs:** Audit logs show "none" for api_key

### Pitfall 3: Docker Compose Health Check Missing
**What goes wrong:** FastAPI starts before Redis is ready, connection errors on startup
**Why it happens:** `depends_on` without `condition: service_healthy`
**How to avoid:** Add health check to Redis service, use `depends_on: condition: service_healthy`

## Sources

### Primary (HIGH confidence)
- FastAPI official docs — middleware, dependency injection, lifespan events
- Redis Stack documentation — module loading, vector search setup
- Docker Compose documentation — health checks, depends_on conditions

### Secondary (MEDIUM confidence)
- pydantic-settings documentation — BaseSettings, environment variable parsing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — well-established Python backend stack
- Architecture: HIGH — standard FastAPI patterns
- Pitfalls: HIGH — common Docker + Redis gotchas well-documented

**Research date:** 2026-02-09
**Valid until:** 2026-03-09 (stable domain)

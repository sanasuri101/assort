"""API key authentication middleware.

Provides a FastAPI dependency for validating X-API-Key headers
against the configured API key in settings.
"""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """Validate API key from X-API-Key header.

    Usage:
        @app.get("/protected")
        async def protected(key: str = Depends(verify_api_key)):
            return {"message": "authenticated"}

    Raises:
        HTTPException: 401 if key is missing or invalid.
    """
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
    return api_key

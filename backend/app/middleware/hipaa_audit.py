"""HIPAA audit logging middleware.

Logs every request to PHI-related endpoints with structured JSON including
timestamp, caller identity, resource accessed, HTTP method, and response status.
"""

import json
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger("hipaa.audit")

# Paths that access Protected Health Information
PHI_PATHS = [
    "/api/patients",
    "/api/appointments",
    "/api/ehr",
    "/api/calls",
]


class HIPAAAuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs access to PHI endpoints for HIPAA compliance.

    Every request matching a PHI path prefix is logged with:
    - event: "phi_access"
    - timestamp: Unix timestamp
    - method: HTTP method
    - path: Request path
    - caller_ip: Client IP address
    - api_key: API key from X-API-Key header (or "anonymous")
    - status_code: Response status code
    - duration_ms: Request duration in milliseconds
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Only log requests to PHI-related paths
        if any(request.url.path.startswith(prefix) for prefix in PHI_PATHS):
            audit_entry = {
                "event": "phi_access",
                "timestamp": time.time(),
                "method": request.method,
                "path": str(request.url.path),
                "caller_ip": request.client.host if request.client else "unknown",
                "api_key": request.headers.get("X-API-Key", "anonymous"),
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
            logger.info(json.dumps(audit_entry))

        return response

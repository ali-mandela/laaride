"""Request/response logging middleware — logs method, path, duration, status for every request."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import get_logger
from app.middleware import get_request_id

logger = get_logger("laaride.http")

# Paths to skip logging
SKIP_PATHS = {"/", "/health", "/api/v1/", "/api/v1/health"}

SLOW_REQUEST_THRESHOLD_MS = 1000


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip noisy endpoints
        if path in SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log_data = {
            "event": "request",
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "request_id": get_request_id(),
        }

        if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning("slow_request", **log_data)
        elif response.status_code >= 500:
            logger.error("server_error", **log_data)
        elif response.status_code >= 400:
            logger.warning("client_error", **log_data)
        else:
            logger.info("request_completed", **log_data)

        return response

import time

from fastapi import APIRouter, Depends
from typing import Any

from app.core.config import settings
from app.core.database import get_database

router = APIRouter(tags=["System"])


@router.get("/", summary="Service info")
async def info():
    return {
        "service": "LaaRide API",
        "version": settings.VERSION,
        "status": "running",
    }


@router.get("/health", summary="Health check")
async def health(db: Any = Depends(get_database)):
    """Enhanced health check with database connectivity test."""
    checks = {}
    overall = "ok"

    # Database check
    try:
        start = time.perf_counter()
        await db.command("ping")
        response_time_ms = round((time.perf_counter() - start) * 1000, 2)
        checks["database"] = "ok"
        checks["response_time_ms"] = response_time_ms
    except Exception:
        checks["database"] = "error"
        checks["response_time_ms"] = None
        overall = "degraded"

    from datetime import datetime, timezone

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "checks": checks,
    }

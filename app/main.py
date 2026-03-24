import os
import uuid
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import (
    db_instance,
    USERS_COLLECTION,
    OTP_COLLECTION,
    DRIVERS_COLLECTION,
    VEHICLES_COLLECTION,
    ROUTES_COLLECTION,
    BOOKINGS_COLLECTION,
    NOTIFICATIONS_COLLECTION,
    PAYMENTS_COLLECTION,
)
from app.core.exceptions import LaaRideException
from app.core.firebase import setup_firebase
from app.core.logging import setup_logging, get_logger
from app.middleware import RequestIDMiddleware, get_request_id
from app.middleware.logging import LoggingMiddleware
from app.routes.v1 import v1_router
from app.routes.v1.default import router as default_router

logger = get_logger("laaride.main")


# ── Rate Limiter ───────────────────────────────────────────────────────────

def _get_limiter_key(request: Request) -> str:
    return get_remote_address(request)


def _build_limiter() -> Limiter:
    """Build rate limiter — tries Redis (Upstash), falls back to in-memory."""
    if settings.REDIS_URL and settings.RATE_LIMIT_ENABLED:
        try:
            return Limiter(
                key_func=_get_limiter_key,
                default_limits=["30/minute"],
                enabled=True,
                storage_uri=settings.REDIS_URL,
            )
        except Exception as e:
            logger.warning(
                "Redis unavailable for rate limiting, falling back to memory",
                error=str(e),
            )
    return Limiter(
        key_func=_get_limiter_key,
        default_limits=["30/minute"],
        enabled=settings.RATE_LIMIT_ENABLED,
        storage_uri="memory://",
    )


limiter = _build_limiter()


# ── Upload dirs ────────────────────────────────────────────────────────────

os.makedirs(os.path.join("uploads", "profiles"), exist_ok=True)
os.makedirs(os.path.join("uploads", "routes"), exist_ok=True)


# ── Lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging
    setup_logging()
    logger.info("starting_up", version=settings.VERSION, env="dev" if settings.IS_DEVELOPMENT else "prod")

    # Startup: MongoDB
    db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db_instance.db = db_instance.client[settings.DATABASE_NAME]

    # Create indexes
    await db_instance.db[USERS_COLLECTION].create_index("phone", unique=True)
    await db_instance.db[OTP_COLLECTION].create_index([("phone", 1), ("expires_at", 1)])
    await db_instance.db[OTP_COLLECTION].create_index("expires_at", expireAfterSeconds=0)
    await db_instance.db[DRIVERS_COLLECTION].create_index("user_id", unique=True)
    await db_instance.db[VEHICLES_COLLECTION].create_index("registration_number", unique=True)
    await db_instance.db[VEHICLES_COLLECTION].create_index("driver_id")
    await db_instance.db[ROUTES_COLLECTION].create_index("slug", unique=True)
    await db_instance.db[ROUTES_COLLECTION].create_index("is_active")
    await db_instance.db[ROUTES_COLLECTION].create_index(
        [("name", "text"), ("origin.name", "text"), ("destination.name", "text")]
    )
    await db_instance.db[BOOKINGS_COLLECTION].create_index("passenger_id")
    await db_instance.db[BOOKINGS_COLLECTION].create_index("driver_id")
    await db_instance.db[BOOKINGS_COLLECTION].create_index("route_id")
    await db_instance.db[BOOKINGS_COLLECTION].create_index(
        [("vehicle_id", 1), ("route_id", 1), ("trip_date", 1), ("status", 1)]
    )
    await db_instance.db[BOOKINGS_COLLECTION].create_index("status")
    await db_instance.db[BOOKINGS_COLLECTION].create_index("scheduled_at")
    await db_instance.db[NOTIFICATIONS_COLLECTION].create_index("user_id")
    await db_instance.db[NOTIFICATIONS_COLLECTION].create_index("is_read")
    await db_instance.db[NOTIFICATIONS_COLLECTION].create_index("created_at")
    await db_instance.db[USERS_COLLECTION].create_index("fcm_tokens")
    # Search indexes
    await db_instance.db[ROUTES_COLLECTION].create_index([("origin.name", 1), ("is_active", 1)])
    await db_instance.db[ROUTES_COLLECTION].create_index([("destination.name", 1), ("is_active", 1)])
    await db_instance.db[DRIVERS_COLLECTION].create_index([("status", 1), ("availability", 1)])
    await db_instance.db[VEHICLES_COLLECTION].create_index([("driver_id", 1), ("is_active", 1)])
    # Payment indexes
    await db_instance.db[PAYMENTS_COLLECTION].create_index("razorpay_order_id", unique=True, sparse=True)
    await db_instance.db[PAYMENTS_COLLECTION].create_index("booking_id")
    await db_instance.db[PAYMENTS_COLLECTION].create_index("passenger_id")
    await db_instance.db[PAYMENTS_COLLECTION].create_index("payment_status")
    # Reviews, earnings, disputes indexes
    await db_instance.db["reviews"].create_index("booking_id", unique=True)
    await db_instance.db["reviews"].create_index("driver_id")
    await db_instance.db["reviews"].create_index([("driver_id", 1), ("is_visible", 1)])
    await db_instance.db["earnings"].create_index("driver_id")
    await db_instance.db["earnings"].create_index([("driver_id", 1), ("trip_date", -1)])
    await db_instance.db["earnings"].create_index([("driver_id", 1), ("status", 1)])
    await db_instance.db["disputes"].create_index([("booking_id", 1), ("status", 1)])
    await db_instance.db["disputes"].create_index("raised_by")
    await db_instance.db["disputes"].create_index("status")
    await db_instance.db["dispute_messages"].create_index("dispute_id")

    logger.info("indexes_created")

    # Initialise Firebase (graceful — no-op if credentials absent)
    setup_firebase(settings.FIREBASE_PROJECT_ID, settings.FIREBASE_SERVICE_ACCOUNT_KEY)

    yield

    db_instance.client.close()
    logger.info("shutdown_complete")


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A scalable transport infrastructure for Ladakh",
    lifespan=lifespan,
)

# Rate limiter state
app.state.limiter = limiter


# ── Exception Handlers ─────────────────────────────────────────────────────

@app.exception_handler(LaaRideException)
async def laaride_exception_handler(request: Request, exc: LaaRideException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": get_request_id(),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        })
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors},
                "request_id": get_request_id(),
            }
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down.",
                "details": None,
                "request_id": get_request_id(),
            }
        },
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found",
                "details": None,
                "request_id": get_request_id(),
            }
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        traceback=traceback.format_exc(),
        request_id=get_request_id(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": None,
                "request_id": get_request_id(),
            }
        },
    )


# ── Middleware Stack (order matters — outermost first) ─────────────────────

# 1. Request ID (outermost — runs first, adds ID for all downstream)
app.add_middleware(RequestIDMiddleware)

# 2. Security headers
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Logging middleware
app.add_middleware(LoggingMiddleware)


# ── Static files & routes ──────────────────────────────────────────────────

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.include_router(default_router) # Root level info and health
app.include_router(v1_router)

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.core.database import db_instance, USERS_COLLECTION, OTP_COLLECTION, DRIVERS_COLLECTION, VEHICLES_COLLECTION, ROUTES_COLLECTION, BOOKINGS_COLLECTION, NOTIFICATIONS_COLLECTION
from app.routes.v1 import v1_router


# Ensure upload directories exist before StaticFiles validates them
os.makedirs(os.path.join("uploads", "profiles"), exist_ok=True)
os.makedirs(os.path.join("uploads", "routes"), exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB client and database
    db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db_instance.db = db_instance.client[settings.DATABASE_NAME]

    # Create indexes
    # User phone must be unique
    await db_instance.db[USERS_COLLECTION].create_index("phone", unique=True)
    # OTP lookup index
    await db_instance.db[OTP_COLLECTION].create_index([("phone", 1), ("expires_at", 1)])
    # TTL index to auto-delete expired OTPs
    await db_instance.db[OTP_COLLECTION].create_index("expires_at", expireAfterSeconds=0)
    # Driver: unique user_id
    await db_instance.db[DRIVERS_COLLECTION].create_index("user_id", unique=True)
    # Vehicle: unique registration_number
    await db_instance.db[VEHICLES_COLLECTION].create_index("registration_number", unique=True)
    # Vehicle: index on driver_id for lookup
    await db_instance.db[VEHICLES_COLLECTION].create_index("driver_id")
    # Route: unique slug
    await db_instance.db[ROUTES_COLLECTION].create_index("slug", unique=True)
    # Route: index on is_active for filtering
    await db_instance.db[ROUTES_COLLECTION].create_index("is_active")
    # Route: text index for search
    await db_instance.db[ROUTES_COLLECTION].create_index(
        [("name", "text"), ("origin.name", "text"), ("destination.name", "text")]
    )
    # Booking indexes
    await db_instance.db[BOOKINGS_COLLECTION].create_index("passenger_id")
    await db_instance.db[BOOKINGS_COLLECTION].create_index("driver_id")
    await db_instance.db[BOOKINGS_COLLECTION].create_index("route_id")
    await db_instance.db[BOOKINGS_COLLECTION].create_index(
        [("vehicle_id", 1), ("route_id", 1), ("trip_date", 1), ("status", 1)]
    )
    await db_instance.db[BOOKINGS_COLLECTION].create_index("status")
    await db_instance.db[BOOKINGS_COLLECTION].create_index("scheduled_at")
    # Notification indexes
    await db_instance.db[NOTIFICATIONS_COLLECTION].create_index("user_id")
    await db_instance.db[NOTIFICATIONS_COLLECTION].create_index("is_read")
    await db_instance.db[NOTIFICATIONS_COLLECTION].create_index("created_at")
    # User fcm_tokens index
    await db_instance.db[USERS_COLLECTION].create_index("fcm_tokens")

    yield

    # Shutdown: Close MongoDB client
    db_instance.client.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A scalable transport infrastructure for Ladakh",
    lifespan=lifespan,
)

# Serve uploaded files (profile photos, etc.)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(v1_router)

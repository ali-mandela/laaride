import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.core.database import db_instance, USERS_COLLECTION, OTP_COLLECTION
from app.routes.v1 import v1_router


# Ensure upload directories exist before StaticFiles validates them
os.makedirs(os.path.join("uploads", "profiles"), exist_ok=True)


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

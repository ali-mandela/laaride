"""Shared pytest fixtures for LaaRide test suite."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.core.config import settings
from app.core.security import hash_otp

TEST_DB_NAME = "laaride_test"


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db():
    """Provide a fresh test MongoDB database, dropped after the session."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[TEST_DB_NAME]
    yield db
    await client.drop_database(TEST_DB_NAME)
    client.close()


@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

async def create_test_user(client: AsyncClient, phone: str = "+911234567890") -> dict:
    """Register and authenticate a test user, returning auth headers.

    Uses development mode — OTP is returned in the send-otp response body.
    """
    send_resp = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    assert send_resp.status_code == 200, f"send-otp failed: {send_resp.text}"

    otp = send_resp.json().get("otp")
    assert otp, "OTP not returned — ensure IS_DEVELOPMENT=true in test environment"

    verify_resp = await client.post(
        "/api/v1/auth/verify-otp", json={"phone": phone, "otp": otp}
    )
    assert verify_resp.status_code == 200, f"verify-otp failed: {verify_resp.text}"

    token = verify_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_test_user_with_tokens(
    client: AsyncClient, phone: str = "+911234567890"
) -> dict:
    """Returns access_token, refresh_token, and user data."""
    send_resp = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    otp = send_resp.json()["otp"]

    verify_resp = await client.post(
        "/api/v1/auth/verify-otp", json={"phone": phone, "otp": otp}
    )
    return verify_resp.json()


async def seed_route(db) -> str:
    """Insert a test route and return its _id."""
    from bson import ObjectId
    route = {
        "_id": str(ObjectId()),
        "name": "Leh to Kargil",
        "slug": "leh-kargil",
        "origin": {"name": "Leh", "lat": 34.1526, "lng": 77.5771},
        "destination": {"name": "Kargil", "lat": 34.5596, "lng": 76.1310},
        "base_fare": 600.0,
        "distance_km": 234,
        "duration_minutes": 420,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db["routes"].insert_one(route)
    return route["_id"]

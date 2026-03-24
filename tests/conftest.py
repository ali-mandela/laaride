"""Shared pytest fixtures for LaaRide test suite."""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.core.config import settings

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
    """Register and authenticate a test user, returning auth headers."""
    # TODO: mock OTP verification to bypass SMS in tests
    await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    resp = await client.post("/api/v1/auth/verify-otp", json={"phone": phone, "otp": "123456"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

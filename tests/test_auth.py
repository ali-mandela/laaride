"""Tests for OTP authentication flow."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_otp_valid_phone(client: AsyncClient):
    """Sending OTP to a valid phone returns 200."""
    resp = await client.post("/api/v1/auth/send-otp", json={"phone": "+911234567890"})
    assert resp.status_code == 200
    assert "message" in resp.json()


@pytest.mark.asyncio
async def test_send_otp_invalid_phone(client: AsyncClient):
    """Sending OTP to an invalid phone returns 422."""
    resp = await client.post("/api/v1/auth/send-otp", json={"phone": "not-a-phone"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_verify_otp_wrong_code(client: AsyncClient):
    """Verifying with wrong OTP returns 400."""
    await client.post("/api/v1/auth/send-otp", json={"phone": "+911234567891"})
    resp = await client.post(
        "/api/v1/auth/verify-otp", json={"phone": "+911234567891", "otp": "000000"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Valid refresh token returns new access token."""
    # TODO: Create user with known OTP (mock), get refresh token, exchange it
    pass


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    """GET /me without token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401

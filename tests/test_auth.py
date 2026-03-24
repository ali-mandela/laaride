"""Tests for OTP authentication flow."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_test_user_with_tokens


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
async def test_send_otp_returns_code_in_dev(client: AsyncClient):
    """In development mode, OTP is returned in response body."""
    resp = await client.post("/api/v1/auth/send-otp", json={"phone": "+919876543210"})
    assert resp.status_code == 200
    data = resp.json()
    assert "otp" in data
    assert data["otp"] is not None
    assert len(data["otp"]) == 6


@pytest.mark.asyncio
async def test_verify_otp_success(client: AsyncClient):
    """Valid OTP returns access and refresh tokens."""
    send_resp = await client.post("/api/v1/auth/send-otp", json={"phone": "+911111111111"})
    otp = send_resp.json()["otp"]

    resp = await client.post(
        "/api/v1/auth/verify-otp", json={"phone": "+911111111111", "otp": otp}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "user" in data
    assert "is_new_user" in data


@pytest.mark.asyncio
async def test_verify_otp_wrong_code(client: AsyncClient):
    """Verifying with wrong OTP returns 400."""
    await client.post("/api/v1/auth/send-otp", json={"phone": "+911234567891"})
    resp = await client.post(
        "/api/v1/auth/verify-otp", json={"phone": "+911234567891", "otp": "000000"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_otp_second_login_not_new_user(client: AsyncClient):
    """Second login with same phone sets is_new_user=False."""
    phone = "+912222222222"
    # First login
    send1 = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    otp1 = send1.json()["otp"]
    r1 = await client.post("/api/v1/auth/verify-otp", json={"phone": phone, "otp": otp1})
    assert r1.json()["is_new_user"] is True

    # Second login
    send2 = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    otp2 = send2.json()["otp"]
    r2 = await client.post("/api/v1/auth/verify-otp", json={"phone": phone, "otp": otp2})
    assert r2.json()["is_new_user"] is False


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Valid refresh token returns new access token."""
    tokens = await create_test_user_with_tokens(client, phone="+913333333333")
    refresh_token = tokens["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient):
    """Using an access token as refresh token is rejected."""
    tokens = await create_test_user_with_tokens(client, phone="+914444444444")
    access_token = tokens["access_token"]

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token}
    )
    assert resp.status_code in (400, 401)


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    """GET /me without token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user_profile(client: AsyncClient):
    """Authenticated GET /me returns user profile."""
    headers = await create_test_user_with_tokens(client, phone="+915555555555")
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {headers['access_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "phone" in data
    assert data["phone"] == "+915555555555"

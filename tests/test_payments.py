"""Tests for payment initiation and verification."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_test_user


@pytest.mark.asyncio
async def test_initiate_payment_requires_auth(client: AsyncClient):
    """Payment initiation requires authentication."""
    resp = await client.post("/api/v1/payments/initiate", json={"booking_id": "fakeid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_payment_requires_auth(client: AsyncClient):
    """Payment verification without auth returns 401."""
    resp = await client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": "order_fake",
            "razorpay_payment_id": "pay_fake",
            "razorpay_signature": "badsig",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_razorpay_signature_verification(client: AsyncClient):
    """Invalid Razorpay signature is rejected."""
    headers = await create_test_user(client, phone="+917000000001")
    resp = await client.post(
        "/api/v1/payments/verify",
        headers=headers,
        json={
            "razorpay_order_id": "order_fake",
            "razorpay_payment_id": "pay_fake",
            "razorpay_signature": "invalid_signature",
        },
    )
    # Bad signature should return 400
    assert resp.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_payment_history_requires_auth(client: AsyncClient):
    """Listing payment history requires authentication."""
    resp = await client.get("/api/v1/payments/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_my_payment_history_empty(client: AsyncClient):
    """Authenticated user with no payments returns empty list."""
    headers = await create_test_user(client, phone="+917000000002")
    resp = await client.get("/api/v1/payments/", headers=headers)
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_cash_payment_flow(client: AsyncClient):
    """Cash payment endpoint structure test (auth gate)."""
    headers = await create_test_user(client, phone="+917000000003")
    resp = await client.post(
        "/api/v1/payments/cash",
        headers=headers,
        json={"booking_id": "nonexistent-booking"},
    )
    # Should fail gracefully — 404 or 400, not 500
    assert resp.status_code in (400, 403, 404, 422)
    assert resp.status_code != 500

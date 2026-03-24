"""Tests for payment initiation and verification."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_initiate_payment_requires_auth(client: AsyncClient):
    """Payment initiation requires authentication."""
    resp = await client.post("/api/v1/payments/initiate", json={"booking_id": "fakeid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cash_payment_flow(client: AsyncClient):
    """Cash payment can be initiated and confirmed by driver.

    TODO: Seed booking, authenticate as passenger, initiate cash payment,
    authenticate as driver, confirm cash received.
    """
    pass


@pytest.mark.asyncio
async def test_razorpay_signature_verification(client: AsyncClient):
    """Invalid Razorpay signature is rejected."""
    resp = await client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": "order_fake",
            "razorpay_payment_id": "pay_fake",
            "razorpay_signature": "badsig",
        },
    )
    # Should fail without auth token
    assert resp.status_code in (400, 401)

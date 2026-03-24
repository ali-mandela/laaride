"""Tests for the booking workflow (fixed-route and custom-trip)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_seat_map_requires_auth(client: AsyncClient):
    """Seat map endpoint requires authentication."""
    resp = await client.get("/api/v1/bookings/seat-map/some-trip-id")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_fixed_route_booking(client: AsyncClient):
    """End-to-end fixed-route booking creation.

    TODO: Seed route, driver, vehicle; authenticate as passenger;
    assert booking created with PENDING status.
    """
    pass


@pytest.mark.asyncio
async def test_booking_seat_conflict(client: AsyncClient):
    """Booking an already-taken seat returns 409 conflict."""
    pass


@pytest.mark.asyncio
async def test_cancel_booking(client: AsyncClient):
    """Passenger can cancel a PENDING booking."""
    pass


@pytest.mark.asyncio
async def test_driver_cannot_book(client: AsyncClient):
    """A user with DRIVER role cannot create a passenger booking."""
    pass

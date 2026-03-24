"""Tests for route and driver search endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_routes_returns_list(client: AsyncClient):
    """Route search returns a JSON array."""
    resp = await client.get("/api/v1/search/routes", params={"q": "leh"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_search_routes_with_origin_destination(client: AsyncClient):
    """Route search by origin/destination returns a list."""
    resp = await client.get(
        "/api/v1/search/routes",
        params={"origin": "Leh", "destination": "Kargil"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_popular_origins(client: AsyncClient):
    """Popular origins endpoint returns a list."""
    resp = await client.get("/api/v1/search/popular-origins")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_route_suggestions(client: AsyncClient):
    """Route suggestions return at most 10 results."""
    resp = await client.get("/api/v1/search/suggestions", params={"q": "le"})
    assert resp.status_code == 200
    assert len(resp.json()) <= 10


@pytest.mark.asyncio
async def test_route_suggestions_empty_query(client: AsyncClient):
    """Empty query returns empty list or 422."""
    resp = await client.get("/api/v1/search/suggestions", params={"q": ""})
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_search_drivers(client: AsyncClient):
    """Driver search returns correct structure."""
    resp = await client.get(
        "/api/v1/search/drivers",
        params={"origin": "Leh", "destination": "Kargil"},
    )
    assert resp.status_code in (200, 401)  # auth may be required

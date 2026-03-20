"""
Search & Discovery Module API Tests
====================================
Prerequisites:
  1. Server running: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
  2. Routes seeded (POST /api/v1/routes/seed with admin token)

Usage:
  Replace ROUTE_ID below, then run:
    uv run python test_search_api.py

  NOTE: Search endpoints are PUBLIC — no auth token needed!
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

# ──────────────────────────────────────────────────────────────────
# Replace with a real route_id from your seeded data
# (get one from GET /api/v1/routes/ or GET /api/v1/search/routes?q=leh)
# ──────────────────────────────────────────────────────────────────
ROUTE_ID = "YOUR_ROUTE_ID"
# ──────────────────────────────────────────────────────────────────


def pretty(resp):
    print(f"  Status: {resp.status_code}")
    try:
        print(f"  Body:   {json.dumps(resp.json(), indent=2, default=str)}")
    except Exception:
        print(f"  Body:   {resp.text}")
    print()


def test_1_search_routes():
    """1. Search routes with query 'leh'."""
    print("=" * 60)
    print("1. SEARCH ROUTES: 'leh'")
    print("=" * 60)
    resp = requests.get(f"{BASE_URL}/search/routes", params={"q": "leh"})
    pretty(resp)
    # Extract a route_id for use in later tests
    if resp.status_code == 200:
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get("_id") or data[0].get("id")
    return None


def test_2_route_suggestions():
    """2. Route suggestions for 'man'."""
    print("=" * 60)
    print("2. ROUTE SUGGESTIONS: 'man'")
    print("=" * 60)
    resp = requests.get(f"{BASE_URL}/search/routes/suggestions", params={"q": "man"})
    pretty(resp)
    return resp


def test_3_routes_from_origin():
    """3. All routes from 'Leh'."""
    print("=" * 60)
    print("3. ROUTES FROM ORIGIN: 'Leh'")
    print("=" * 60)
    resp = requests.get(f"{BASE_URL}/search/routes/from/Leh")
    pretty(resp)
    return resp


def test_4_search_drivers(route_id: str):
    """4. Search available drivers for a route+date."""
    print("=" * 60)
    print(f"4. SEARCH DRIVERS (route: {route_id})")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/search/drivers",
        params={
            "origin": "Leh",
            "destination": "Kargil",
            "trip_date": "2026-04-01",
        },
    )
    pretty(resp)
    return resp


def test_5_trip_summary(route_id: str):
    """5. Get trip summary."""
    print("=" * 60)
    print(f"5. TRIP SUMMARY (route: {route_id})")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/search/trip-summary",
        params={"route_id": route_id, "trip_date": "2026-04-01"},
    )
    pretty(resp)
    return resp


def test_6_popular_origins():
    """6. Get popular origins."""
    print("=" * 60)
    print("6. POPULAR ORIGINS")
    print("=" * 60)
    resp = requests.get(f"{BASE_URL}/search/popular-origins")
    pretty(resp)
    return resp


if __name__ == "__main__":
    # Test 1 — search routes (also extract a route_id)
    route_id = test_1_search_routes()
    if route_id:
        print(f"  → Using route_id: {route_id}\n")
    elif ROUTE_ID != "YOUR_ROUTE_ID":
        route_id = ROUTE_ID
    else:
        print("  → No routes found and no ROUTE_ID set. Trip summary test will be skipped.\n")

    # Test 2 — autocomplete
    test_2_route_suggestions()

    # Test 3 — routes from origin
    test_3_routes_from_origin()

    # Test 4 — search drivers
    test_4_search_drivers(route_id or "N/A")

    # Test 5 — trip summary
    if route_id:
        test_5_trip_summary(route_id)
    else:
        print("⚠  Skipping trip summary — no route_id available\n")

    # Test 6 — popular origins
    test_6_popular_origins()

    print("\n✅ All tests executed. Check statuses above for results.")

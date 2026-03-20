"""
Routes Module API Tests
=======================
Prerequisites:
  1. Server running: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
  2. Valid JWT tokens from auth flow.

Usage:
  Replace TOKEN and ADMIN_TOKEN below, then run:
    uv run python test_route_api.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

# ──────────────────────────────────────────────────────────────────
# REPLACE THESE with real tokens from your auth flow
# ──────────────────────────────────────────────────────────────────
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OWJkODRmZjQ1Y2VlNmIxNGVhNzgxY2YiLCJleHAiOjE3NzQwMzA5NzIsInR5cGUiOiJhY2Nlc3MifQ.SQEmtWwghkR4oy9naFohfzJ60KQPVu7N5pvTMn6xzsg"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OWJkODkwNDY2MjNkNGM3NWMwYjZiOWEiLCJleHAiOjE3NzQwMzExMzIsInR5cGUiOiJhY2Nlc3MifQ.tnbYIFlVv7Sc_XydnUAKfebQyPZg6jz_zbJlmLskfp0"
# ──────────────────────────────────────────────────────────────────

USER_HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"}


def pretty(resp):
    print(f"  Status: {resp.status_code}")
    try:
        print(f"  Body:   {json.dumps(resp.json(), indent=2, default=str)}")
    except Exception:
        print(f"  Body:   {resp.text}")
    print()


def test_1_seed_routes():
    """1. Seed default routes (admin)."""
    print("=" * 60)
    print("1. SEED DEFAULT ROUTES")
    print("=" * 60)
    resp = requests.post(
        f"{BASE_URL}/routes/seed",
        headers=ADMIN_HEADERS,
    )
    pretty(resp)
    return resp


def test_2_list_all_routes():
    """2. List all routes."""
    print("=" * 60)
    print("2. LIST ALL ROUTES")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/routes/",
        headers=USER_HEADERS,
        params={"skip": 0, "limit": 10},
    )
    pretty(resp)
    return resp


def test_3_search_by_origin():
    """3. Search routes by origin name (leh)."""
    print("=" * 60)
    print("3. SEARCH BY ORIGIN: leh")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/routes/",
        headers=USER_HEADERS,
        params={"origin_name": "leh"},
    )
    pretty(resp)
    return resp


def test_4_get_by_slug():
    """4. Get route by slug."""
    print("=" * 60)
    print("4. GET BY SLUG: leh-kargil")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/routes/slug/leh-kargil",
        headers=USER_HEADERS,
    )
    pretty(resp)
    return resp


def test_5_popular_routes():
    """5. Get popular routes."""
    print("=" * 60)
    print("5. POPULAR ROUTES")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/routes/popular",
        headers=USER_HEADERS,
        params={"limit": 5},
    )
    pretty(resp)
    return resp


def test_6_search_by_tag():
    """6. Search routes by tag."""
    print("=" * 60)
    print("6. SEARCH BY TAG: high-altitude")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/routes/",
        headers=USER_HEADERS,
        params={"tag": "high-altitude"},
    )
    pretty(resp)
    return resp


def test_7_search_by_max_fare():
    """7. Search routes by max fare."""
    print("=" * 60)
    print("7. SEARCH BY MAX FARE: 800")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/routes/",
        headers=USER_HEADERS,
        params={"max_fare": 800},
    )
    pretty(resp)
    return resp


if __name__ == "__main__":
    if TOKEN == "YOUR_USER_JWT_TOKEN_HERE":
        print("⚠  Please set TOKEN and ADMIN_TOKEN at the top of this file first!")
        print("   Get tokens via POST /api/v1/auth/send-otp → POST /api/v1/auth/verify-otp")
        sys.exit(1)

    test_1_seed_routes()
    test_2_list_all_routes()
    test_3_search_by_origin()
    test_4_get_by_slug()
    test_5_popular_routes()
    test_6_search_by_tag()
    test_7_search_by_max_fare()

    print("\n✅ All tests executed. Check statuses above for results.")

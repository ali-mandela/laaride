"""
Notifications + Admin Module API Tests
=======================================
Prerequisites:
  1. Server running: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
  2. Valid JWT tokens.

Usage:
  Replace tokens below, then run:
    uv run python test_notifications_admin_api.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

# ──────────────────────────────────────────────────────────────────
# REPLACE THESE with real tokens from your auth flow
# ──────────────────────────────────────────────────────────────────
TOKEN = "YOUR_USER_JWT_TOKEN"
ADMIN_TOKEN = "YOUR_ADMIN_JWT_TOKEN"
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


def test_1_register_fcm_token():
    """1. Register FCM token."""
    print("=" * 60)
    print("1. REGISTER FCM TOKEN")
    print("=" * 60)
    resp = requests.post(
        f"{BASE_URL}/notifications/fcm-token",
        headers=USER_HEADERS,
        json={"token": "test-fcm-token-12345"},
    )
    pretty(resp)
    return resp


def test_2_get_notifications():
    """2. Get notifications (empty initially)."""
    print("=" * 60)
    print("2. GET NOTIFICATIONS")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/notifications/",
        headers=USER_HEADERS,
        params={"skip": 0, "limit": 20},
    )
    pretty(resp)
    return resp


def test_3_unread_count():
    """3. Get unread count."""
    print("=" * 60)
    print("3. UNREAD COUNT")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/notifications/unread-count",
        headers=USER_HEADERS,
    )
    pretty(resp)
    return resp


def test_4_admin_dashboard():
    """4. Admin dashboard stats."""
    print("=" * 60)
    print("4. ADMIN DASHBOARD STATS")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/admin/dashboard",
        headers=ADMIN_HEADERS,
    )
    pretty(resp)
    return resp


def test_5_pending_drivers():
    """5. Pending driver approvals."""
    print("=" * 60)
    print("5. PENDING DRIVER APPROVALS")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/admin/drivers/pending",
        headers=ADMIN_HEADERS,
    )
    pretty(resp)
    return resp


def test_6_revenue_summary():
    """6. Revenue summary."""
    print("=" * 60)
    print("6. REVENUE SUMMARY")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/admin/revenue",
        headers=ADMIN_HEADERS,
        params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
    )
    pretty(resp)
    return resp


def test_7_recent_activity():
    """7. Recent activity feed."""
    print("=" * 60)
    print("7. RECENT ACTIVITY FEED")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/admin/activity",
        headers=ADMIN_HEADERS,
        params={"limit": 10},
    )
    pretty(resp)
    return resp


def test_8_search_users():
    """8. Search users."""
    print("=" * 60)
    print("8. SEARCH USERS")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/admin/users/search",
        headers=ADMIN_HEADERS,
        params={"q": "9", "limit": 10},
    )
    pretty(resp)
    return resp


if __name__ == "__main__":
    if TOKEN == "YOUR_USER_JWT_TOKEN":
        print("⚠  Please set TOKEN and ADMIN_TOKEN at the top of this file first!")
        sys.exit(1)

    test_1_register_fcm_token()
    test_2_get_notifications()
    test_3_unread_count()
    test_4_admin_dashboard()
    test_5_pending_drivers()
    test_6_revenue_summary()
    test_7_recent_activity()
    test_8_search_users()

    print("\n✅ All tests executed. Check statuses above for results.")

"""
Driver Module API Tests
=======================
Prerequisites:
  1. Server running: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
  2. You need a valid JWT token. Get one via the auth flow:
     - POST /api/v1/auth/send-otp  (with your phone)
     - POST /api/v1/auth/verify-otp (with phone + OTP)
  3. For admin endpoints you need a user with role=admin.

Usage:
  Replace TOKEN and ADMIN_TOKEN below, then run:
    uv run python test_driver_api.py
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
    """Pretty-print a response."""
    print(f"  Status: {resp.status_code}")
    try:
        print(f"  Body:   {json.dumps(resp.json(), indent=2, default=str)}")
    except Exception:
        print(f"  Body:   {resp.text}")
    print()


def test_1_apply_as_driver():
    """1. Apply as driver (any logged-in user)."""
    print("=" * 60)
    print("1. APPLY AS DRIVER")
    print("=" * 60)
    resp = requests.post(
        f"{BASE_URL}/drivers/apply",
        headers=USER_HEADERS,
        json={
            "license_number": "DL-1234567890",
            "license_expiry": "2028-12-31",
        },
    )
    pretty(resp)
    return resp


def test_2_list_drivers_admin():
    """2. List all drivers as admin."""
    print("=" * 60)
    print("2. LIST DRIVERS (ADMIN)")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/drivers/",
        headers=ADMIN_HEADERS,
        params={"skip": 0, "limit": 10},
    )
    pretty(resp)
    return resp


def test_3_approve_driver(driver_id: str):
    """3. Approve a driver (admin)."""
    print("=" * 60)
    print(f"3. APPROVE DRIVER: {driver_id}")
    print("=" * 60)
    resp = requests.post(
        f"{BASE_URL}/drivers/{driver_id}/approve",
        headers=ADMIN_HEADERS,
    )
    pretty(resp)
    return resp


def test_4_toggle_availability():
    """4. Toggle availability (needs driver role — run after approval)."""
    print("=" * 60)
    print("4. TOGGLE AVAILABILITY → ONLINE")
    print("=" * 60)
    # NOTE: After approval the user's role becomes "driver",
    # so you may need to re-login to get a new token with role=driver.
    resp = requests.put(
        f"{BASE_URL}/drivers/me/availability",
        headers=USER_HEADERS,
        json={"availability": "online"},
    )
    pretty(resp)
    return resp


def test_5_add_vehicle():
    """5. Add a vehicle (auto-generates seat layout for SUV)."""
    print("=" * 60)
    print("5. ADD VEHICLE")
    print("=" * 60)
    resp = requests.post(
        f"{BASE_URL}/drivers/me/vehicles",
        headers=USER_HEADERS,
        json={
            "vehicle_type": "suv",
            "make": "Toyota",
            "model": "Innova Crysta",
            "year": 2024,
            "registration_number": "LA-01-AB-1234",
            "capacity": 7,
        },
    )
    pretty(resp)
    return resp


def test_6_get_driver_stats():
    """6. Get driver stats."""
    print("=" * 60)
    print("6. GET DRIVER STATS")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/drivers/me/stats",
        headers=USER_HEADERS,
    )
    pretty(resp)
    return resp


def test_7_get_my_profile():
    """7. Get own driver profile."""
    print("=" * 60)
    print("7. GET MY DRIVER PROFILE")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/drivers/me",
        headers=USER_HEADERS,
    )
    pretty(resp)
    return resp


def test_8_list_my_vehicles():
    """8. List own vehicles."""
    print("=" * 60)
    print("8. LIST MY VEHICLES")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/drivers/me/vehicles",
        headers=USER_HEADERS,
    )
    pretty(resp)
    return resp


if __name__ == "__main__":
    if TOKEN == "YOUR_USER_JWT_TOKEN_HERE":
        print("⚠  Please set TOKEN and ADMIN_TOKEN at the top of this file first!")
        print("   Get tokens via POST /api/v1/auth/send-otp → POST /api/v1/auth/verify-otp")
        sys.exit(1)

    # Step 1: Apply as driver
    r1 = test_1_apply_as_driver()
    driver_id = None
    if r1.status_code == 201:
        driver_id = r1.json().get("_id") or r1.json().get("id")
        print(f"  → Driver ID: {driver_id}\n")

    # Step 2: List drivers (admin)
    r2 = test_2_list_drivers_admin()
    # If we didn't get driver_id from step 1, try to grab from admin listing
    if not driver_id and r2.status_code == 200:
        data = r2.json().get("data", [])
        if data:
            driver_id = data[0].get("_id") or data[0].get("id")
            print(f"  → Using Driver ID from listing: {driver_id}\n")

    # Step 3: Approve driver (admin)
    if driver_id:
        test_3_approve_driver(driver_id)
    else:
        print("⚠  Skipping approval — no driver_id available\n")

    print("\n" + "─" * 60)
    print("NOTE: After approval, the user's role changes to 'driver'.")
    print("You may need to RE-LOGIN to get a fresh JWT with role=driver")
    print("before steps 4-8 will work (get_current_driver check).")
    print("─" * 60 + "\n")

    # Steps 4-8: These require role=driver token
    test_4_toggle_availability()
    test_5_add_vehicle()
    test_6_get_driver_stats()
    test_7_get_my_profile()
    test_8_list_my_vehicles()

    print("\n✅ All tests executed. Check statuses above for results.")

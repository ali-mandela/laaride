"""
Booking Module API Tests
========================
Prerequisites:
  1. Server running: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
  2. Valid JWT tokens from auth flow.
  3. Routes seeded: POST /api/v1/routes/seed
  4. A driver approved and with a vehicle added.

Usage:
  Replace TOKEN, DRIVER_TOKEN, ADMIN_TOKEN, and IDs below, then run:
    uv run python test_booking_api.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

# ──────────────────────────────────────────────────────────────────
# REPLACE THESE with real values
# ──────────────────────────────────────────────────────────────────
PASSENGER_TOKEN = "YOUR_PASSENGER_JWT_TOKEN"
DRIVER_TOKEN = "YOUR_DRIVER_JWT_TOKEN"
ADMIN_TOKEN = "YOUR_ADMIN_JWT_TOKEN"

# IDs from your data (get these from previous test outputs)
ROUTE_ID = "YOUR_ROUTE_ID"         # from GET /api/v1/routes/ or seed
VEHICLE_ID = "YOUR_VEHICLE_ID"     # from GET /api/v1/drivers/me/vehicles
DRIVER_DOC_ID = "YOUR_DRIVER_DOC_ID"  # from GET /api/v1/drivers/me (_id)
# ──────────────────────────────────────────────────────────────────

PASSENGER_HEADERS = {"Authorization": f"Bearer {PASSENGER_TOKEN}", "Content-Type": "application/json"}
DRIVER_HEADERS = {"Authorization": f"Bearer {DRIVER_TOKEN}", "Content-Type": "application/json"}
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"}


def pretty(resp):
    print(f"  Status: {resp.status_code}")
    try:
        print(f"  Body:   {json.dumps(resp.json(), indent=2, default=str)}")
    except Exception:
        print(f"  Body:   {resp.text}")
    print()


def test_1_get_seat_map():
    """1. Get seat map for a vehicle+route+date."""
    print("=" * 60)
    print("1. GET SEAT MAP")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/bookings/seat-map",
        headers=PASSENGER_HEADERS,
        params={
            "vehicle_id": VEHICLE_ID,
            "route_id": ROUTE_ID,
            "trip_date": "2026-04-01",
        },
    )
    pretty(resp)
    return resp


def test_2_create_fixed_route_booking():
    """2. Create a fixed route booking with seat selection."""
    print("=" * 60)
    print("2. CREATE FIXED ROUTE BOOKING")
    print("=" * 60)
    resp = requests.post(
        f"{BASE_URL}/bookings/fixed-route",
        headers=PASSENGER_HEADERS,
        json={
            "route_id": ROUTE_ID,
            "vehicle_id": VEHICLE_ID,
            "driver_id": DRIVER_DOC_ID,
            "seats_booked": ["2A", "2B"],
            "trip_date": "2026-04-01",
            "scheduled_at": "2026-04-01T08:00:00",
            "notes": "Window seats preferred",
        },
    )
    pretty(resp)
    return resp


def test_3_driver_confirm(booking_id: str):
    """3. Driver confirms the booking."""
    print("=" * 60)
    print(f"3. DRIVER CONFIRM BOOKING: {booking_id}")
    print("=" * 60)
    resp = requests.put(
        f"{BASE_URL}/bookings/{booking_id}/status",
        headers=DRIVER_HEADERS,
        json={"status": "confirmed"},
    )
    pretty(resp)
    return resp


def test_4_booking_stats():
    """4. Get booking stats (admin)."""
    print("=" * 60)
    print("4. BOOKING STATS (ADMIN)")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/bookings/stats",
        headers=ADMIN_HEADERS,
    )
    pretty(resp)
    return resp


def test_5_create_custom_trip():
    """5. Create a custom trip booking."""
    print("=" * 60)
    print("5. CREATE CUSTOM TRIP BOOKING")
    print("=" * 60)
    resp = requests.post(
        f"{BASE_URL}/bookings/custom-trip",
        headers=PASSENGER_HEADERS,
        json={
            "pickup_location": {"name": "Leh Main Bazaar", "lat": 34.1526, "lng": 77.5771},
            "drop_location": {"name": "Hemis Monastery", "lat": 33.9108, "lng": 77.6977},
            "scheduled_at": "2026-04-02T09:00:00",
            "preferred_vehicle_type": "suv",
            "notes": "Family trip, need space for luggage",
        },
    )
    pretty(resp)
    return resp


def test_6_find_available_drivers():
    """6. Find available drivers for custom trip."""
    print("=" * 60)
    print("6. FIND AVAILABLE DRIVERS")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/bookings/custom-trip/available-drivers",
        headers=PASSENGER_HEADERS,
        params={"preferred_vehicle_type": "suv"},
    )
    pretty(resp)
    return resp


def test_7_list_my_bookings():
    """7. List my bookings."""
    print("=" * 60)
    print("7. LIST MY BOOKINGS")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/bookings/my",
        headers=PASSENGER_HEADERS,
    )
    pretty(resp)
    return resp


def test_8_driver_pending():
    """8. List driver pending bookings."""
    print("=" * 60)
    print("8. DRIVER PENDING BOOKINGS")
    print("=" * 60)
    resp = requests.get(
        f"{BASE_URL}/bookings/driver/pending",
        headers=DRIVER_HEADERS,
    )
    pretty(resp)
    return resp


if __name__ == "__main__":
    if PASSENGER_TOKEN == "YOUR_PASSENGER_JWT_TOKEN":
        print("⚠  Please set tokens and IDs at the top of this file first!")
        sys.exit(1)

    # 1. Seat map
    test_1_get_seat_map()

    # 2. Fixed route booking
    r2 = test_2_create_fixed_route_booking()
    booking_id = None
    if r2.status_code == 201:
        booking_id = r2.json().get("_id") or r2.json().get("id")
        print(f"  → Booking ID: {booking_id}\n")

    # 3. Driver confirm
    if booking_id:
        test_3_driver_confirm(booking_id)
    else:
        print("⚠  Skipping confirm — no booking_id\n")

    # 4. Stats
    test_4_booking_stats()

    # 5. Custom trip
    test_5_create_custom_trip()

    # 6. Available drivers
    test_6_find_available_drivers()

    # 7-8. Listing
    test_7_list_my_bookings()
    test_8_driver_pending()

    print("\n✅ All tests executed. Check statuses above for results.")

"""Search & Discovery service — route search, driver availability, trip summary."""

import asyncio
import logging
from datetime import date, datetime
from typing import Any, Optional

from bson import ObjectId, errors
from fastapi import HTTPException, status

from app.core.database import (
    BOOKINGS_COLLECTION,
    DRIVERS_COLLECTION,
    ROUTES_COLLECTION,
    VEHICLES_COLLECTION,
)
from app.enums.common import (
    AvailabilityStatus,
    BookingStatus,
    DriverStatus,
    VehicleType,
)
from app.schemas.route import RouteResponse

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────


def _to_object_id(value: str, label: str = "ID") -> ObjectId:
    try:
        return ObjectId(value)
    except errors.InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label} format",
        )


def _all_seats_from_layout(seat_layout: Optional[dict]) -> list[str]:
    if not seat_layout:
        return []
    rows = seat_layout.get("rows", 0)
    columns = seat_layout.get("columns", [])
    unavailable = set(seat_layout.get("unavailable_seats", []))
    seats = []
    for r in range(1, rows + 1):
        for c in columns:
            seat_id = f"{r}{c}"
            if seat_id not in unavailable:
                seats.append(seat_id)
    return seats


WEATHER_ADVISORIES = {
    "manali-leh": "High altitude route. Subject to road closures. Check conditions before travel.",
    "leh-manali": "High altitude route. Subject to road closures. Check conditions before travel.",
    "srinagar-leh": "High altitude route. Subject to road closures. Check conditions before travel.",
    "leh-srinagar": "High altitude route. Subject to road closures. Check conditions before travel.",
    "manali-spiti": "High altitude route. Subject to road closures. Check conditions before travel.",
    "spiti-manali": "High altitude route. Subject to road closures. Check conditions before travel.",
    "leh-nubra-valley": "Permit required. Carry valid ID and inner line permit.",
    "nubra-valley-leh": "Permit required. Carry valid ID and inner line permit.",
    "leh-pangong-lake": "Permit required. Carry valid ID and inner line permit.",
    "pangong-lake-leh": "Permit required. Carry valid ID and inner line permit.",
    "leh-tso-moriri": "Permit required. Carry valid ID and inner line permit.",
    "tso-moriri-leh": "Permit required. Carry valid ID and inner line permit.",
}


# ── 1. Search Routes ──────────────────────────────────────────────────────


async def search_routes(query: str, db: Any) -> list[dict]:
    """Full-text + partial string search on routes. Returns active routes only."""
    if not query or not query.strip():
        return []

    query = query.strip()
    current_month = datetime.utcnow().month
    results = []

    # Try text search first (if index exists)
    try:
        text_cursor = db[ROUTES_COLLECTION].find(
            {"$text": {"$search": query}, "is_active": True},
            {"score": {"$meta": "textScore"}},
        ).sort([("score", {"$meta": "textScore"})]).limit(20)
        async for doc in text_cursor:
            route = RouteResponse(**doc).model_dump()
            route["_id"] = str(doc["_id"])
            # Add seasonal warning
            if doc.get("is_seasonal"):
                s_start = doc.get("season_start_month", 1)
                s_end = doc.get("season_end_month", 12)
                if not (s_start <= current_month <= s_end):
                    route["seasonal_warning"] = (
                        f"This route is seasonal (open months {s_start}-{s_end}). "
                        f"Currently outside season."
                    )
            results.append(route)
        if results:
            return results
    except Exception:
        # Text index may not exist — fall through to regex search
        pass

    # Fallback: regex partial match
    regex_filter = {
        "is_active": True,
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"origin.name": {"$regex": query, "$options": "i"}},
            {"destination.name": {"$regex": query, "$options": "i"}},
        ],
    }
    cursor = db[ROUTES_COLLECTION].find(regex_filter).sort("name", 1).limit(20)
    async for doc in cursor:
        route = RouteResponse(**doc).model_dump()
        route["_id"] = str(doc["_id"])
        if doc.get("is_seasonal"):
            s_start = doc.get("season_start_month", 1)
            s_end = doc.get("season_end_month", 12)
            if not (s_start <= current_month <= s_end):
                route["seasonal_warning"] = (
                    f"This route is seasonal (open months {s_start}-{s_end}). "
                    f"Currently outside season."
                )
        results.append(route)

    return results


# ── 2. Routes From Origin ─────────────────────────────────────────────────


async def get_routes_from_origin(origin_name: str, db: Any) -> list[dict]:
    """Find all active routes where origin.name matches (case-insensitive contains)."""
    cursor = (
        db[ROUTES_COLLECTION]
        .find({"origin.name": {"$regex": origin_name, "$options": "i"}, "is_active": True})
        .sort("name", 1)
    )
    results = []
    async for doc in cursor:
        route = RouteResponse(**doc).model_dump()
        route["_id"] = str(doc["_id"])
        results.append(route)
    return results


# ── 3. Available Drivers For Route ─────────────────────────────────────────


async def get_available_drivers_for_route(
    route_id: str,
    trip_date: date,
    db: Any,
    vehicle_type: Optional[VehicleType] = None,
    limit: int = 20,
) -> list[dict]:
    """Find available drivers with seats for a route+date combo."""
    route_obj_id = _to_object_id(route_id, "Route ID")
    route = await db[ROUTES_COLLECTION].find_one({"_id": route_obj_id})
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    if trip_date < date.today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip date cannot be in the past")

    # Find all APPROVED + ONLINE drivers
    driver_cursor = db[DRIVERS_COLLECTION].find({
        "status": DriverStatus.APPROVED.value,
        "availability": AvailabilityStatus.ONLINE.value,
    })

    results = []
    async for driver in driver_cursor:
        driver_id = str(driver["_id"])

        # Find vehicles for this driver
        veh_query: dict = {"driver_id": driver_id, "is_active": True}
        if vehicle_type:
            veh_query["vehicle_type"] = vehicle_type.value

        vehicles = await db[VEHICLES_COLLECTION].find(veh_query).to_list(length=10)
        if not vehicles:
            continue

        for vehicle in vehicles:
            vehicle_id = str(vehicle["_id"])
            all_seats = _all_seats_from_layout(vehicle.get("seat_layout"))
            if not all_seats:
                continue

            # Get booked seats
            booked_cursor = db[BOOKINGS_COLLECTION].find(
                {
                    "vehicle_id": vehicle_id,
                    "route_id": route_id,
                    "trip_date": trip_date.isoformat(),
                    "status": {"$in": [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]},
                },
                {"seats_booked": 1},
            )
            booked_seats: set[str] = set()
            async for booking in booked_cursor:
                booked_seats.update(booking.get("seats_booked", []))

            available_count = len(all_seats) - len(booked_seats)
            if available_count <= 0:
                continue

            base_fare = route.get("base_fare", 0)

            results.append({
                "driver": {
                    "_id": driver_id,
                    "user_id": driver.get("user_id"),
                    "rating": driver.get("rating", 0.0),
                    "total_trips": driver.get("total_trips", 0),
                },
                "vehicle": {
                    "_id": vehicle_id,
                    "vehicle_type": vehicle.get("vehicle_type"),
                    "make": vehicle.get("make"),
                    "model": vehicle.get("model"),
                    "capacity": vehicle.get("capacity"),
                    "registration_number": vehicle.get("registration_number"),
                },
                "available_seats": available_count,
                "total_seats": len(all_seats),
                "fare_per_seat": base_fare,
            })

            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    return results


# ── 4. Unified Driver Search ──────────────────────────────────────────────


async def search_drivers(
    db: Any,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    trip_date: Optional[date] = None,
    vehicle_type: Optional[VehicleType] = None,
    min_seats: Optional[int] = None,
    limit: int = 20,
) -> list[dict]:
    """Unified driver search combining route + availability."""
    # If origin+destination, find matching route first
    route = None
    if origin and destination:
        route = await db[ROUTES_COLLECTION].find_one({
            "origin.name": {"$regex": origin, "$options": "i"},
            "destination.name": {"$regex": destination, "$options": "i"},
            "is_active": True,
        })

    if route and trip_date:
        # Use the specific route+date search
        results = await get_available_drivers_for_route(
            str(route["_id"]), trip_date, db, vehicle_type=vehicle_type, limit=limit
        )
        if min_seats:
            results = [r for r in results if r["available_seats"] >= min_seats]
        return results

    # General driver search — APPROVED + ONLINE, optionally filtered by vehicle type
    driver_cursor = db[DRIVERS_COLLECTION].find({
        "status": DriverStatus.APPROVED.value,
        "availability": AvailabilityStatus.ONLINE.value,
    })

    results = []
    async for driver in driver_cursor:
        driver_id = str(driver["_id"])
        veh_query: dict = {"driver_id": driver_id, "is_active": True}
        if vehicle_type:
            veh_query["vehicle_type"] = vehicle_type.value

        vehicles = await db[VEHICLES_COLLECTION].find(veh_query).to_list(length=10)
        if not vehicles:
            continue

        for vehicle in vehicles:
            all_seats = _all_seats_from_layout(vehicle.get("seat_layout"))
            total = len(all_seats) if all_seats else vehicle.get("capacity", 0)

            entry = {
                "driver": {
                    "_id": driver_id,
                    "user_id": driver.get("user_id"),
                    "rating": driver.get("rating", 0.0),
                    "total_trips": driver.get("total_trips", 0),
                },
                "vehicle": {
                    "_id": str(vehicle["_id"]),
                    "vehicle_type": vehicle.get("vehicle_type"),
                    "make": vehicle.get("make"),
                    "model": vehicle.get("model"),
                    "capacity": vehicle.get("capacity"),
                    "registration_number": vehicle.get("registration_number"),
                },
                "available_seats": total,
                "total_seats": total,
            }
            if min_seats and total < min_seats:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    return results


# ── 5. Route Suggestions (Autocomplete) ───────────────────────────────────


async def get_route_suggestions(partial_query: str, db: Any) -> list[dict]:
    """Fast autocomplete — match origin/destination starting with partial query. Max 10."""
    if not partial_query or len(partial_query) < 1:
        return []

    regex = f"^{partial_query}"
    cursor = db[ROUTES_COLLECTION].find(
        {
            "is_active": True,
            "$or": [
                {"origin.name": {"$regex": regex, "$options": "i"}},
                {"destination.name": {"$regex": regex, "$options": "i"}},
            ],
        },
        {"name": 1, "slug": 1, "origin.name": 1, "destination.name": 1},  # projection
    ).limit(10)

    results = []
    async for doc in cursor:
        origin_name = doc.get("origin", {}).get("name", "")
        dest_name = doc.get("destination", {}).get("name", "")
        results.append({
            "label": f"{origin_name} → {dest_name}",
            "route_id": str(doc["_id"]),
            "slug": doc.get("slug", ""),
        })
    return results


# ── 6. Popular Origins ────────────────────────────────────────────────────


async def get_popular_origins(db: Any) -> list[dict]:
    """Most booked origin cities. Fallback to route origins if no bookings."""
    # Aggregate from bookings
    pipeline = [
        {"$match": {"booking_type": "fixed_route", "route_id": {"$ne": None}}},
        {"$group": {"_id": "$pickup_location.name", "booking_count": {"$sum": 1}}},
        {"$sort": {"booking_count": -1}},
        {"$limit": 8},
    ]
    agg_results = await db[BOOKINGS_COLLECTION].aggregate(pipeline).to_list(length=8)

    if agg_results:
        results = []
        for item in agg_results:
            origin_name = item["_id"]
            if not origin_name:
                continue
            route_count = await db[ROUTES_COLLECTION].count_documents(
                {"origin.name": origin_name, "is_active": True}
            )
            results.append({
                "name": origin_name,
                "route_count": route_count,
                "booking_count": item["booking_count"],
            })
        if results:
            return results

    # Fallback: unique origins from routes
    origin_pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$origin.name", "route_count": {"$sum": 1}}},
        {"$sort": {"route_count": -1}},
        {"$limit": 8},
    ]
    origin_results = await db[ROUTES_COLLECTION].aggregate(origin_pipeline).to_list(length=8)
    return [
        {"name": item["_id"], "route_count": item["route_count"], "booking_count": 0}
        for item in origin_results
        if item["_id"]
    ]


# ── 7. Trip Summary ───────────────────────────────────────────────────────


async def get_trip_summary(route_id: str, trip_date: date, db: Any) -> dict:
    """Full pre-booking summary: route info, available drivers/seats, fares, advisories."""
    if trip_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Trip date cannot be in the past"
        )

    route_obj_id = _to_object_id(route_id, "Route ID")

    # Parallel fetch: route + available drivers
    route_task = db[ROUTES_COLLECTION].find_one({"_id": route_obj_id})
    drivers_task = get_available_drivers_for_route(route_id, trip_date, db)

    route, available_drivers = await asyncio.gather(route_task, drivers_task)

    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    route_resp = RouteResponse(**route).model_dump()
    route_resp["_id"] = str(route["_id"])

    # Compute aggregated stats
    total_available = sum(d["available_seats"] for d in available_drivers)
    fares = [d["fare_per_seat"] for d in available_drivers] if available_drivers else [route.get("base_fare", 0)]
    min_fare = min(fares) if fares else 0
    max_fare = max(fares) if fares else 0

    # Seasonal check
    current_month = datetime.utcnow().month
    is_peak_season = False
    if route.get("is_seasonal"):
        s_start = route.get("season_start_month", 1)
        s_end = route.get("season_end_month", 12)
        is_peak_season = s_start <= current_month <= s_end

    # Weather advisory
    slug = route.get("slug", "")
    weather_advisory = WEATHER_ADVISORIES.get(slug)

    return {
        "route": route_resp,
        "available_drivers": available_drivers,
        "total_available_seats": total_available,
        "min_fare": min_fare,
        "max_fare": max_fare,
        "is_peak_season": is_peak_season,
        "weather_advisory": weather_advisory,
    }

"""Trip service — business logic for driver-listed trips."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from bson import ObjectId, errors
from fastapi import HTTPException, status

from app.core.database import (
    DRIVERS_COLLECTION,
    ROUTES_COLLECTION,
    TRIPS_COLLECTION,
    VEHICLES_COLLECTION,
)
from app.enums.common import TripStatus
from app.schemas.trip import SeatMapResponse, TripCreate, TripResponse, TripUpdate


def _to_object_id(value: str, label: str = "ID") -> ObjectId:
    try:
        return ObjectId(value)
    except errors.InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label} format",
        )


def _doc_to_response(doc: dict) -> TripResponse:
    return TripResponse(**doc)


# ── Create ─────────────────────────────────────────────────────────────────


async def create_trip(driver_user_id: str, data: TripCreate, db: Any) -> TripResponse:
    """Driver creates a new trip listing for a fixed route."""
    # Validate route
    route = await db[ROUTES_COLLECTION].find_one(
        {"_id": _to_object_id(data.route_id, "Route ID"), "is_active": True}
    )
    if not route:
        raise HTTPException(status_code=404, detail="Route not found or inactive")

    # Validate vehicle belongs to this driver
    vehicle = await db[VEHICLES_COLLECTION].find_one(
        {
            "_id": _to_object_id(data.vehicle_id, "Vehicle ID"),
            "driver_id": driver_user_id,
            "is_active": True,
        }
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found or not owned by driver")

    # Prevent duplicate trip (same driver, route, vehicle, date, time)
    existing = await db[TRIPS_COLLECTION].find_one(
        {
            "driver_id": driver_user_id,
            "route_id": data.route_id,
            "trip_date": data.trip_date.isoformat(),
            "departure_time": data.departure_time,
            "status": {"$nin": [TripStatus.CANCELLED]},
        }
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A trip for this route, date, and departure time already exists",
        )

    # Fetch driver info for denormalization
    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": driver_user_id})
    driver_name = driver.get("full_name", "") if driver else ""
    driver_phone = driver.get("phone", "") if driver else ""
    driver_rating = driver.get("rating", 0.0) if driver else 0.0

    total_seats = vehicle.get("capacity", 4)
    now = datetime.utcnow()

    doc = {
        "route_id": data.route_id,
        "driver_id": driver_user_id,
        "vehicle_id": data.vehicle_id,
        "trip_date": data.trip_date.isoformat(),
        "departure_time": data.departure_time,
        "total_seats": total_seats,
        "available_seats": total_seats,
        "booked_seat_ids": [],
        "fare_per_seat": data.fare_per_seat,
        "status": TripStatus.SCHEDULED,
        "route_name": route.get("name", ""),
        "origin": route.get("origin", {}),
        "destination": route.get("destination", {}),
        "distance_km": route.get("distance_km"),
        "estimated_duration_mins": route.get("estimated_duration_mins"),
        "driver_name": driver_name,
        "driver_phone": driver_phone,
        "driver_rating": driver_rating,
        "vehicle_number": vehicle.get("registration_number", ""),
        "vehicle_type": vehicle.get("vehicle_type", ""),
        "vehicle_model": vehicle.get("model", ""),
        "notes": data.notes,
        "created_at": now,
        "updated_at": now,
    }

    result = await db[TRIPS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_response(doc)


# ── List driver trips ──────────────────────────────────────────────────────


async def list_driver_trips(
    driver_user_id: str,
    skip: int,
    limit: int,
    db: Any,
    trip_status: Optional[TripStatus] = None,
) -> dict:
    """Return paginated trips listed by a driver."""
    query: dict = {"driver_id": driver_user_id}
    if trip_status:
        query["status"] = trip_status

    total = await db[TRIPS_COLLECTION].count_documents(query)
    cursor = (
        db[TRIPS_COLLECTION]
        .find(query)
        .sort("trip_date", -1)
        .skip(skip)
        .limit(limit)
    )
    trips = [_doc_to_response(doc) async for doc in cursor]
    return {"data": trips, "total": total, "skip": skip, "limit": limit}


# ── Get single trip ────────────────────────────────────────────────────────


async def get_trip_by_id(trip_id: str, db: Any) -> TripResponse:
    oid = _to_object_id(trip_id, "Trip ID")
    doc = await db[TRIPS_COLLECTION].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Trip not found")
    return _doc_to_response(doc)


# ── Update trip ────────────────────────────────────────────────────────────


async def update_trip(
    trip_id: str, driver_user_id: str, data: TripUpdate, db: Any
) -> TripResponse:
    oid = _to_object_id(trip_id, "Trip ID")
    doc = await db[TRIPS_COLLECTION].find_one({"_id": oid, "driver_id": driver_user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Trip not found or not owned by driver")

    if doc["status"] == TripStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot update a completed trip")

    fields = data.model_dump(exclude_unset=True)
    fields["updated_at"] = datetime.utcnow()

    await db[TRIPS_COLLECTION].update_one({"_id": oid}, {"$set": fields})
    updated = await db[TRIPS_COLLECTION].find_one({"_id": oid})
    return _doc_to_response(updated)


# ── Cancel trip ────────────────────────────────────────────────────────────


async def cancel_trip(trip_id: str, driver_user_id: str, db: Any) -> dict:
    oid = _to_object_id(trip_id, "Trip ID")
    doc = await db[TRIPS_COLLECTION].find_one({"_id": oid, "driver_id": driver_user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Trip not found or not owned by driver")

    if doc["status"] in (TripStatus.COMPLETED, TripStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail=f"Trip is already {doc['status']}",
        )

    await db[TRIPS_COLLECTION].update_one(
        {"_id": oid},
        {"$set": {"status": TripStatus.CANCELLED, "updated_at": datetime.utcnow()}},
    )
    return {"message": "Trip cancelled successfully"}


# ── Seat map ───────────────────────────────────────────────────────────────


async def get_trip_seat_map(trip_id: str, db: Any) -> SeatMapResponse:
    """Return seat availability for a trip."""
    oid = _to_object_id(trip_id, "Trip ID")
    doc = await db[TRIPS_COLLECTION].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Fetch seat layout from vehicle
    vehicle = await db[VEHICLES_COLLECTION].find_one(
        {"_id": _to_object_id(doc["vehicle_id"], "Vehicle ID")}
    )
    seat_layout = vehicle.get("seat_layout", []) if vehicle else []

    return SeatMapResponse(
        trip_id=str(doc["_id"]),
        vehicle_id=doc["vehicle_id"],
        total_seats=doc["total_seats"],
        available_seats=doc["available_seats"],
        booked_seat_ids=doc.get("booked_seat_ids", []),
        seat_layout=seat_layout,
    )


# ── Search trips ───────────────────────────────────────────────────────────


async def search_trips(
    origin: Optional[str],
    destination: Optional[str],
    trip_date: Optional[date],
    seats: Optional[int],
    skip: int,
    limit: int,
    db: Any,
) -> dict:
    """Search available trips by origin, destination, date, and seat count."""
    query: dict = {"status": TripStatus.SCHEDULED}

    if origin:
        query["origin.name"] = {"$regex": origin, "$options": "i"}
    if destination:
        query["destination.name"] = {"$regex": destination, "$options": "i"}
    if trip_date:
        query["trip_date"] = trip_date.isoformat()
    if seats:
        query["available_seats"] = {"$gte": seats}

    total = await db[TRIPS_COLLECTION].count_documents(query)
    cursor = (
        db[TRIPS_COLLECTION]
        .find(query)
        .sort([("trip_date", 1), ("departure_time", 1)])
        .skip(skip)
        .limit(limit)
    )
    trips = [_doc_to_response(doc) async for doc in cursor]
    return {"data": trips, "total": total, "skip": skip, "limit": limit}

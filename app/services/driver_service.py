"""Driver service — all business logic for driver module."""

from datetime import datetime
from typing import Any, Optional

from bson import ObjectId, errors
from fastapi import HTTPException, status

from app.core.database import (
    DRIVERS_COLLECTION,
    USERS_COLLECTION,
    VEHICLES_COLLECTION,
)
from app.enums.common import (
    AvailabilityStatus,
    DriverStatus,
    UserRole,
    VehicleType,
)
from app.schemas.driver import DriverCreate, DriverResponse, DriverUpdate
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate


# ── Helpers ────────────────────────────────────────────────────────────────


def _to_object_id(value: str, label: str = "ID") -> ObjectId:
    """Convert a string to ObjectId, raise 400 on invalid format."""
    try:
        return ObjectId(value)
    except errors.InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label} format",
        )


def _generate_seat_layout(vehicle_type: VehicleType) -> Optional[dict]:
    """Auto-generate a seat layout based on vehicle type."""
    layouts = {
        VehicleType.SEDAN: {
            "rows": 3,
            "columns": ["A", "B"],
            "unavailable_seats": ["1A"],
        },
        VehicleType.SUV: {
            "rows": 4,
            "columns": ["A", "B", "C"],
            "unavailable_seats": ["1A"],
        },
        VehicleType.TEMPO_TRAVELLER: {
            "rows": 5,
            "columns": ["A", "B", "C"],
            "unavailable_seats": ["1A"],
        },
        VehicleType.BUS: {
            "rows": 10,
            "columns": ["A", "B", "C", "D"],
            "unavailable_seats": ["1A"],
        },
    }
    return layouts.get(vehicle_type)  # bike → None


# ── Driver self-service ────────────────────────────────────────────────────


async def apply_as_driver(
    user_id: str, data: DriverCreate, db: Any
) -> DriverResponse:
    """Create a new driver profile linked to the current user."""
    obj_id = _to_object_id(user_id, "User ID")

    # Check user exists and is active
    user = await db[USERS_COLLECTION].find_one({"_id": obj_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not user.get("is_active", True) is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User account is inactive"
        )

    # Ensure no existing driver profile
    existing = await db[DRIVERS_COLLECTION].find_one({"user_id": user_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a driver profile",
        )

    now = datetime.utcnow()
    driver_doc = {
        "user_id": user_id,
        "license_number": data.license_number,
        "license_expiry": data.license_expiry.isoformat(),
        "status": DriverStatus.PENDING_APPROVAL.value,
        "availability": AvailabilityStatus.OFFLINE.value,
        "current_location": None,
        "rating": 0.0,
        "total_trips": 0,
        "created_at": now,
        "updated_at": now,
    }

    result = await db[DRIVERS_COLLECTION].insert_one(driver_doc)
    driver_doc["_id"] = result.inserted_id
    return DriverResponse(**driver_doc)


async def get_driver_profile(user_id: str, db: Any) -> DriverResponse:
    """Fetch the driver profile for a given user_id."""
    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": user_id})
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found"
        )
    return DriverResponse(**driver)


async def update_driver_profile(
    user_id: str, data: DriverUpdate, db: Any
) -> DriverResponse:
    """Partially update the driver profile (license_expiry, current_location)."""
    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    # Convert date to isoformat string for MongoDB
    if "license_expiry" in update_fields and update_fields["license_expiry"] is not None:
        update_fields["license_expiry"] = update_fields["license_expiry"].isoformat()

    update_fields["updated_at"] = datetime.utcnow()

    result = await db[DRIVERS_COLLECTION].update_one(
        {"user_id": user_id}, {"$set": update_fields}
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found"
        )
    return await get_driver_profile(user_id, db)


async def toggle_availability(
    user_id: str, new_status: AvailabilityStatus, db: Any
) -> DriverResponse:
    """Toggle driver availability. Only APPROVED drivers; ON_TRIP cannot be set manually."""
    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": user_id})
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found"
        )

    if driver["status"] != DriverStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only approved drivers can toggle availability",
        )

    if new_status == AvailabilityStatus.ON_TRIP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot manually set ON_TRIP status — system only",
        )

    await db[DRIVERS_COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": {"availability": new_status.value, "updated_at": datetime.utcnow()}},
    )
    return await get_driver_profile(user_id, db)


# ── Vehicle management ─────────────────────────────────────────────────────


async def add_vehicle(
    user_id: str, data: VehicleCreate, db: Any
) -> VehicleResponse:
    """Add a vehicle for the current driver."""
    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": user_id})
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found"
        )
    if driver["status"] != DriverStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only approved drivers can add vehicles",
        )

    # Check unique registration number
    existing = await db[VEHICLES_COLLECTION].find_one(
        {"registration_number": data.registration_number}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle with this registration number already exists",
        )

    # Resolve seat layout
    seat_layout = data.seat_layout
    if seat_layout is None:
        seat_layout = _generate_seat_layout(data.vehicle_type)

    driver_id = str(driver["_id"])
    now = datetime.utcnow()
    vehicle_doc = {
        "driver_id": driver_id,
        "vehicle_type": data.vehicle_type.value,
        "make": data.make,
        "model": data.model,
        "year": data.year,
        "registration_number": data.registration_number,
        "capacity": data.capacity,
        "is_active": True,
        "seat_layout": seat_layout,
        "created_at": now,
        "updated_at": now,
    }

    result = await db[VEHICLES_COLLECTION].insert_one(vehicle_doc)
    vehicle_doc["_id"] = result.inserted_id
    return VehicleResponse(**vehicle_doc)


async def get_driver_vehicles(
    user_id: str, db: Any
) -> list[VehicleResponse]:
    """Fetch all vehicles belonging to the driver."""
    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": user_id})
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found"
        )
    driver_id = str(driver["_id"])
    cursor = db[VEHICLES_COLLECTION].find({"driver_id": driver_id})
    return [VehicleResponse(**doc) async for doc in cursor]


async def update_vehicle(
    user_id: str, vehicle_id: str, data: VehicleUpdate, db: Any
) -> VehicleResponse:
    """Update a vehicle — verify it belongs to the requesting driver."""
    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": user_id})
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found"
        )

    veh_obj_id = _to_object_id(vehicle_id, "Vehicle ID")
    vehicle = await db[VEHICLES_COLLECTION].find_one({"_id": veh_obj_id})
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )

    if vehicle["driver_id"] != str(driver["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own vehicles",
        )

    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    update_fields["updated_at"] = datetime.utcnow()

    await db[VEHICLES_COLLECTION].update_one(
        {"_id": veh_obj_id}, {"$set": update_fields}
    )
    updated = await db[VEHICLES_COLLECTION].find_one({"_id": veh_obj_id})
    return VehicleResponse(**updated)


# ── Stats ──────────────────────────────────────────────────────────────────


async def get_driver_stats(user_id: str, db: Any) -> dict:
    """Return basic stats for the driver."""
    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": user_id})
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found"
        )
    return {
        "total_trips": driver.get("total_trips", 0),
        "rating": driver.get("rating", 0.0),
        "availability": driver.get("availability", AvailabilityStatus.OFFLINE.value),
        "total_earnings": 0.0,
    }


# ── Admin services ─────────────────────────────────────────────────────────


async def list_drivers(
    skip: int,
    limit: int,
    db: Any,
    status_filter: Optional[DriverStatus] = None,
) -> dict:
    """Admin: list all drivers, with optional status filter, paginated."""
    query: dict = {}
    if status_filter is not None:
        query["status"] = status_filter.value

    total = await db[DRIVERS_COLLECTION].count_documents(query)
    cursor = (
        db[DRIVERS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    drivers = [DriverResponse(**doc) async for doc in cursor]

    return {
        "data": drivers,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


async def get_driver_by_id(driver_id: str, db: Any) -> DriverResponse:
    """Admin: get a driver by its document _id."""
    obj_id = _to_object_id(driver_id, "Driver ID")
    driver = await db[DRIVERS_COLLECTION].find_one({"_id": obj_id})
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found"
        )
    return DriverResponse(**driver)


async def approve_driver(driver_id: str, db: Any) -> DriverResponse:
    """Admin: approve a pending driver, and update the linked user's role to DRIVER."""
    obj_id = _to_object_id(driver_id, "Driver ID")

    driver = await db[DRIVERS_COLLECTION].find_one({"_id": obj_id})
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found"
        )

    now = datetime.utcnow()
    await db[DRIVERS_COLLECTION].update_one(
        {"_id": obj_id},
        {"$set": {"status": DriverStatus.APPROVED.value, "updated_at": now}},
    )

    # Update linked user's role to driver
    user_obj_id = _to_object_id(driver["user_id"], "User ID")
    await db[USERS_COLLECTION].update_one(
        {"_id": user_obj_id},
        {"$set": {"role": UserRole.DRIVER.value, "updated_at": now}},
    )

    updated = await db[DRIVERS_COLLECTION].find_one({"_id": obj_id})
    return DriverResponse(**updated)


async def suspend_driver(
    driver_id: str, reason: str, db: Any
) -> DriverResponse:
    """Admin: suspend a driver and set availability to OFFLINE."""
    obj_id = _to_object_id(driver_id, "Driver ID")

    driver = await db[DRIVERS_COLLECTION].find_one({"_id": obj_id})
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found"
        )

    now = datetime.utcnow()
    await db[DRIVERS_COLLECTION].update_one(
        {"_id": obj_id},
        {
            "$set": {
                "status": DriverStatus.SUSPENDED.value,
                "availability": AvailabilityStatus.OFFLINE.value,
                "updated_at": now,
            }
        },
    )

    updated = await db[DRIVERS_COLLECTION].find_one({"_id": obj_id})
    return DriverResponse(**updated)

"""Booking service — all business logic for the booking module."""

from datetime import date, datetime
from typing import Any, Optional

from bson import ObjectId, errors
from fastapi import HTTPException, status

from app.core.database import (
    BOOKINGS_COLLECTION,
    DRIVERS_COLLECTION,
    ROUTES_COLLECTION,
    USERS_COLLECTION,
    VEHICLES_COLLECTION,
)
from app.core.exceptions import NotFoundError, ValidationError, ConflictError, AuthorizationError
from app.core.logging import get_logger
from app.enums.common import (
    AvailabilityStatus,
    BookingStatus,
    BookingType,
    DriverStatus,
    VehicleType,
)
from app.schemas.booking import (
    BookingResponse,
    BookingStatusUpdate,
    CustomTripBookingCreate,
    FixedRouteBookingCreate,
    SeatMapResponse,
)
from app.services import notification_service

logger = get_logger("laaride.booking")


# ── Helpers ────────────────────────────────────────────────────────────────


def _to_object_id(value: str, label: str = "ID") -> ObjectId:
    try:
        return ObjectId(value)
    except errors.InvalidId:
        raise ValidationError(message=f"Invalid {label} format", code="INVALID_ID")


def _all_seats_from_layout(seat_layout: Optional[dict]) -> list[str]:
    """Generate all seat IDs from a seat layout, excluding permanently unavailable."""
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


# ── Seat Map ───────────────────────────────────────────────────────────────


async def get_seat_map(
    vehicle_id: str, route_id: str, trip_date: date, db: Any
) -> SeatMapResponse:
    """Build a seat map showing booked/available seats for a vehicle+route+date."""
    veh_obj_id = _to_object_id(vehicle_id, "Vehicle ID")
    vehicle = await db[VEHICLES_COLLECTION].find_one({"_id": veh_obj_id})
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )

    seat_layout = vehicle.get("seat_layout")
    all_seats = _all_seats_from_layout(seat_layout)

    # Find all active bookings (PENDING or CONFIRMED) for this combo
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
    async for doc in booked_cursor:
        booked_seats.update(doc.get("seats_booked", []))

    available_seats = [s for s in all_seats if s not in booked_seats]

    return SeatMapResponse(
        vehicle_id=vehicle_id,
        route_id=route_id,
        trip_date=trip_date,
        seat_layout=seat_layout,
        booked_seats=sorted(booked_seats),
        available_seats=sorted(available_seats),
        total_capacity=len(all_seats),
        available_count=len(available_seats),
    )


# ── Fixed Route Booking ───────────────────────────────────────────────────


async def create_fixed_route_booking(
    passenger_id: str, data: FixedRouteBookingCreate, db: Any
) -> BookingResponse:
    """Create a fixed-route booking with seat selection."""

    # 1. Validate route
    route_obj_id = _to_object_id(data.route_id, "Route ID")
    route = await db[ROUTES_COLLECTION].find_one({"_id": route_obj_id})
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    if not route.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Route is inactive")

    # 2. Validate vehicle and driver relationship
    veh_obj_id = _to_object_id(data.vehicle_id, "Vehicle ID")
    vehicle = await db[VEHICLES_COLLECTION].find_one({"_id": veh_obj_id})
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    driver_obj_id = _to_object_id(data.driver_id, "Driver ID")
    driver = await db[DRIVERS_COLLECTION].find_one({"_id": driver_obj_id})
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    if vehicle.get("driver_id") != data.driver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle does not belong to specified driver",
        )

    # 3. Validate driver status
    if driver.get("status") != DriverStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Driver is not approved"
        )
    if driver.get("availability") != AvailabilityStatus.ONLINE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Driver is not currently online"
        )

    # 4. Validate trip_date
    today = date.today()
    if data.trip_date < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Trip date cannot be in the past"
        )

    # 5. Atomic seat availability check
    # Find all booked seats for this vehicle+route+date combo
    booked_cursor = db[BOOKINGS_COLLECTION].find(
        {
            "vehicle_id": data.vehicle_id,
            "route_id": data.route_id,
            "trip_date": data.trip_date.isoformat(),
            "status": {"$in": [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]},
        },
        {"seats_booked": 1},
    )
    already_booked: set[str] = set()
    async for doc in booked_cursor:
        already_booked.update(doc.get("seats_booked", []))

    conflicts = set(data.seats_booked) & already_booked
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Seats already booked: {', '.join(sorted(conflicts))}",
        )

    # Validate requested seats exist in layout
    all_seats = set(_all_seats_from_layout(vehicle.get("seat_layout")))
    if all_seats:
        invalid_seats = set(data.seats_booked) - all_seats
        if invalid_seats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid seat IDs: {', '.join(sorted(invalid_seats))}",
            )

    # 6. Fetch passenger info for denormalization
    passenger_obj_id = _to_object_id(passenger_id, "Passenger ID")
    passenger = await db[USERS_COLLECTION].find_one({"_id": passenger_obj_id})
    passenger_name = passenger.get("name", "") if passenger else ""
    passenger_phone = passenger.get("phone", "") if passenger else ""

    # 7. Calculate fare
    fare = route.get("base_fare", 0) * len(data.seats_booked)

    now = datetime.utcnow()
    booking_doc = {
        "passenger_id": passenger_id,
        "driver_id": data.driver_id,
        "vehicle_id": data.vehicle_id,
        "booking_type": BookingType.FIXED_ROUTE.value,
        "route_id": data.route_id,
        "pickup_location": route.get("origin", {}),
        "drop_location": route.get("destination", {}),
        "scheduled_at": data.scheduled_at,
        "status": BookingStatus.PENDING.value,
        "fare": fare,
        "notes": data.notes,
        "seats_booked": data.seats_booked,
        "total_passengers": len(data.seats_booked),
        "trip_date": data.trip_date.isoformat(),
        "preferred_vehicle_type": None,
        "distance_estimate_km": None,
        "duration_estimate_mins": None,
        "passenger_name": passenger_name,
        "passenger_phone": passenger_phone,
        "cancellation_reason": None,
        "cancelled_by": None,
        "confirmed_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await db[BOOKINGS_COLLECTION].insert_one(booking_doc)
    booking_doc["_id"] = result.inserted_id

    # Notify driver about new booking
    try:
        route_name = route.get("name", "Unknown route")
        driver_user_id = driver.get("user_id")
        if driver_user_id:
            await notification_service.send_push_notification(
                driver_user_id,
                "New Booking Request",
                f"You have a new booking request for {route_name} on {data.trip_date}",
                db,
                data={"booking_id": str(result.inserted_id), "type": "new_booking"},
                notification_type="booking_update",
                reference_id=str(result.inserted_id),
            )
    except Exception as e:
        logger.error(f"Failed to send booking notification: {e}")

    return BookingResponse(**booking_doc)


# ── Custom Trip Booking ────────────────────────────────────────────────────


async def create_custom_trip_booking(
    passenger_id: str, data: CustomTripBookingCreate, db: Any
) -> BookingResponse:
    """Create a custom trip booking (no seats, no route)."""

    # Validate scheduled_at is future
    if data.scheduled_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must be in the future",
        )

    # Fetch passenger info
    passenger_obj_id = _to_object_id(passenger_id, "Passenger ID")
    passenger = await db[USERS_COLLECTION].find_one({"_id": passenger_obj_id})
    passenger_name = passenger.get("name", "") if passenger else ""
    passenger_phone = passenger.get("phone", "") if passenger else ""

    now = datetime.utcnow()
    booking_doc = {
        "passenger_id": passenger_id,
        "driver_id": None,
        "vehicle_id": None,
        "booking_type": BookingType.CUSTOM_TRIP.value,
        "route_id": None,
        "pickup_location": data.pickup_location,
        "drop_location": data.drop_location,
        "scheduled_at": data.scheduled_at,
        "status": BookingStatus.PENDING.value,
        "fare": None,
        "notes": data.notes,
        "seats_booked": [],
        "total_passengers": 1,
        "trip_date": None,
        "preferred_vehicle_type": data.preferred_vehicle_type.value if data.preferred_vehicle_type else None,
        "distance_estimate_km": None,
        "duration_estimate_mins": None,
        "passenger_name": passenger_name,
        "passenger_phone": passenger_phone,
        "cancellation_reason": None,
        "cancelled_by": None,
        "confirmed_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await db[BOOKINGS_COLLECTION].insert_one(booking_doc)
    booking_doc["_id"] = result.inserted_id
    return BookingResponse(**booking_doc)


async def find_available_drivers_for_custom_trip(
    data: CustomTripBookingCreate, db: Any
) -> list[dict]:
    """Find APPROVED + ONLINE drivers, optionally filtered by vehicle type."""
    query = {
        "status": DriverStatus.APPROVED.value,
        "availability": AvailabilityStatus.ONLINE.value,
    }
    cursor = db[DRIVERS_COLLECTION].find(query)
    results = []
    async for driver in cursor:
        driver_id = str(driver["_id"])
        # Fetch vehicles for this driver
        veh_query: dict = {"driver_id": driver_id, "is_active": True}
        if data.preferred_vehicle_type:
            veh_query["vehicle_type"] = data.preferred_vehicle_type.value

        vehicles = await db[VEHICLES_COLLECTION].find(veh_query).to_list(length=10)
        if not vehicles:
            continue  # skip drivers without matching vehicles

        results.append(
            {
                "driver_id": driver_id,
                "user_id": driver.get("user_id"),
                "rating": driver.get("rating", 0.0),
                "total_trips": driver.get("total_trips", 0),
                "vehicles": [
                    {
                        "vehicle_id": str(v["_id"]),
                        "vehicle_type": v.get("vehicle_type"),
                        "make": v.get("make"),
                        "model": v.get("model"),
                        "capacity": v.get("capacity"),
                        "registration_number": v.get("registration_number"),
                    }
                    for v in vehicles
                ],
            }
        )
    return results


# ── Shared ─────────────────────────────────────────────────────────────────


async def get_booking_by_id(
    booking_id: str, requester_id: str, requester_role: str, db: Any
) -> BookingResponse:
    """Get a booking by ID. Access control based on role."""
    obj_id = _to_object_id(booking_id, "Booking ID")
    booking = await db[BOOKINGS_COLLECTION].find_one({"_id": obj_id})
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
        )

    # Access control
    if requester_role == "passenger" and booking.get("passenger_id") != requester_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own bookings",
        )
    if requester_role == "driver":
        # Driver needs their driver doc ID, which we match via user_id
        driver = await db[DRIVERS_COLLECTION].find_one({"user_id": requester_id})
        driver_doc_id = str(driver["_id"]) if driver else None
        if booking.get("driver_id") != driver_doc_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view bookings assigned to you",
            )

    return BookingResponse(**booking)


async def update_booking_status(
    booking_id: str,
    updater_id: str,
    updater_role: str,
    data: BookingStatusUpdate,
    db: Any,
) -> BookingResponse:
    """Update booking status with strict lifecycle enforcement."""
    obj_id = _to_object_id(booking_id, "Booking ID")
    booking = await db[BOOKINGS_COLLECTION].find_one({"_id": obj_id})
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
        )

    current_status = booking.get("status")
    new_status = data.status.value

    # ── Lifecycle validation ──
    valid_transitions = {
        BookingStatus.PENDING.value: {
            BookingStatus.CONFIRMED.value,
            BookingStatus.REJECTED.value,
            BookingStatus.CANCELLED.value,
        },
        BookingStatus.CONFIRMED.value: {
            BookingStatus.COMPLETED.value,
            BookingStatus.CANCELLED.value,
        },
    }
    allowed = valid_transitions.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{current_status}' to '{new_status}'",
        )

    now = datetime.utcnow()
    update_fields: dict = {"status": new_status, "updated_at": now}

    # ── Role-based authorization ──
    if new_status in (BookingStatus.CONFIRMED.value, BookingStatus.REJECTED.value):
        # Only the assigned driver can confirm/reject
        if updater_role != "driver" and updater_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned driver can confirm or reject bookings",
            )
        if updater_role == "driver":
            driver = await db[DRIVERS_COLLECTION].find_one({"user_id": updater_id})
            driver_doc_id = str(driver["_id"]) if driver else None
            if booking.get("driver_id") != driver_doc_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only confirm/reject bookings assigned to you",
                )

    if new_status == BookingStatus.COMPLETED.value:
        if updater_role != "driver" and updater_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the driver can mark a booking as completed",
            )

    if new_status == BookingStatus.CANCELLED.value:
        if updater_role == "passenger" and booking.get("passenger_id") != updater_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own bookings",
            )
        update_fields["cancellation_reason"] = data.cancellation_reason or "No reason provided"
        update_fields["cancelled_by"] = updater_id

    # ── Side effects ──
    if new_status == BookingStatus.CONFIRMED.value:
        update_fields["confirmed_at"] = now
        # Set driver availability to ON_TRIP
        if booking.get("driver_id"):
            driver_obj = _to_object_id(booking["driver_id"], "Driver ID")
            await db[DRIVERS_COLLECTION].update_one(
                {"_id": driver_obj},
                {"$set": {"availability": AvailabilityStatus.ON_TRIP.value, "updated_at": now}},
            )
        # Notify passenger
        try:
            route_name = booking.get("pickup_location", {}).get("name", "") + " → " + booking.get("drop_location", {}).get("name", "")
            await notification_service.send_push_notification(
                booking["passenger_id"], "Booking Confirmed",
                f"Your booking for {route_name} has been confirmed",
                db, data={"booking_id": booking_id}, notification_type="booking_update", reference_id=booking_id,
            )
        except Exception as e:
            logger.error(f"Notification error: {e}")

    if new_status == BookingStatus.COMPLETED.value:
        update_fields["completed_at"] = now
        # Increment driver trips and set availability back to ONLINE
        if booking.get("driver_id"):
            driver_obj = _to_object_id(booking["driver_id"], "Driver ID")
            await db[DRIVERS_COLLECTION].update_one(
                {"_id": driver_obj},
                {
                    "$inc": {"total_trips": 1},
                    "$set": {
                        "availability": AvailabilityStatus.ONLINE.value,
                        "updated_at": now,
                    },
                },
            )
        # Notify passenger
        try:
            dest = booking.get("drop_location", {}).get("name", "your destination")
            await notification_service.send_push_notification(
                booking["passenger_id"], "Trip Completed",
                f"Your trip to {dest} is complete. Thank you for riding with LaaRide!",
                db, data={"booking_id": booking_id}, notification_type="booking_update", reference_id=booking_id,
            )
        except Exception as e:
            logger.error(f"Notification error: {e}")

    if new_status in (BookingStatus.CANCELLED.value, BookingStatus.REJECTED.value):
        # Release seats (no action needed — next seat map query will exclude cancelled/rejected)
        # Set driver back to ONLINE if they were ON_TRIP for this booking
        if booking.get("driver_id"):
            driver_obj = _to_object_id(booking["driver_id"], "Driver ID")
            driver = await db[DRIVERS_COLLECTION].find_one({"_id": driver_obj})
            if driver and driver.get("availability") == AvailabilityStatus.ON_TRIP.value:
                await db[DRIVERS_COLLECTION].update_one(
                    {"_id": driver_obj},
                    {"$set": {"availability": AvailabilityStatus.ONLINE.value, "updated_at": now}},
                )
        # Notifications
        try:
            route_name = booking.get("pickup_location", {}).get("name", "") + " → " + booking.get("drop_location", {}).get("name", "")
            if new_status == BookingStatus.CANCELLED.value and booking.get("driver_id"):
                # Notify driver about cancellation
                drv = await db[DRIVERS_COLLECTION].find_one({"_id": _to_object_id(booking["driver_id"], "D")})
                if drv:
                    await notification_service.send_push_notification(
                        drv["user_id"], "Booking Cancelled",
                        f"A booking for {route_name} has been cancelled",
                        db, data={"booking_id": booking_id}, notification_type="booking_update", reference_id=booking_id,
                    )
            elif new_status == BookingStatus.REJECTED.value:
                # Notify passenger about rejection
                await notification_service.send_push_notification(
                    booking["passenger_id"], "Booking Rejected",
                    f"Your booking for {route_name} was rejected",
                    db, data={"booking_id": booking_id}, notification_type="booking_update", reference_id=booking_id,
                )
        except Exception as e:
            logger.error(f"Notification error: {e}")

    await db[BOOKINGS_COLLECTION].update_one({"_id": obj_id}, {"$set": update_fields})
    updated = await db[BOOKINGS_COLLECTION].find_one({"_id": obj_id})
    return BookingResponse(**updated)


# ── Listing ────────────────────────────────────────────────────────────────


async def list_passenger_bookings(
    passenger_id: str,
    skip: int,
    limit: int,
    db: Any,
    status_filter: Optional[BookingStatus] = None,
) -> dict:
    """List bookings for a passenger, sorted by created_at desc."""
    query: dict = {"passenger_id": passenger_id}
    if status_filter:
        query["status"] = status_filter.value

    total = await db[BOOKINGS_COLLECTION].count_documents(query)
    cursor = (
        db[BOOKINGS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    bookings = [BookingResponse(**doc) async for doc in cursor]
    return {"data": bookings, "total": total, "skip": skip, "limit": limit}


async def list_driver_bookings(
    driver_doc_id: str,
    skip: int,
    limit: int,
    db: Any,
    status_filter: Optional[BookingStatus] = None,
) -> dict:
    """List bookings assigned to a driver, sorted by scheduled_at asc."""
    query: dict = {"driver_id": driver_doc_id}
    if status_filter:
        query["status"] = status_filter.value

    total = await db[BOOKINGS_COLLECTION].count_documents(query)
    cursor = (
        db[BOOKINGS_COLLECTION]
        .find(query)
        .sort("scheduled_at", 1)
        .skip(skip)
        .limit(limit)
    )
    bookings = [BookingResponse(**doc) async for doc in cursor]
    return {"data": bookings, "total": total, "skip": skip, "limit": limit}


async def list_driver_pending_bookings(driver_doc_id: str, db: Any) -> list[BookingResponse]:
    """List PENDING bookings for a driver."""
    cursor = (
        db[BOOKINGS_COLLECTION]
        .find({"driver_id": driver_doc_id, "status": BookingStatus.PENDING.value})
        .sort("scheduled_at", 1)
    )
    return [BookingResponse(**doc) async for doc in cursor]


# ── Admin ──────────────────────────────────────────────────────────────────


async def list_all_bookings(
    skip: int,
    limit: int,
    db: Any,
    status_filter: Optional[BookingStatus] = None,
    booking_type_filter: Optional[BookingType] = None,
) -> dict:
    """Admin: list all bookings with optional filters."""
    query: dict = {}
    if status_filter:
        query["status"] = status_filter.value
    if booking_type_filter:
        query["booking_type"] = booking_type_filter.value

    total = await db[BOOKINGS_COLLECTION].count_documents(query)
    cursor = (
        db[BOOKINGS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    bookings = [BookingResponse(**doc) async for doc in cursor]
    return {"data": bookings, "total": total, "skip": skip, "limit": limit}


async def get_booking_stats(db: Any) -> dict:
    """Admin: booking statistics."""
    total = await db[BOOKINGS_COLLECTION].count_documents({})

    # By status
    by_status = {}
    for s in BookingStatus:
        by_status[s.value] = await db[BOOKINGS_COLLECTION].count_documents({"status": s.value})

    # By type
    by_type = {}
    for t in BookingType:
        by_type[t.value] = await db[BOOKINGS_COLLECTION].count_documents({"booking_type": t.value})

    # Today's bookings
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await db[BOOKINGS_COLLECTION].count_documents(
        {"created_at": {"$gte": today_start}}
    )

    return {
        "total_bookings": total,
        "by_status": by_status,
        "by_type": by_type,
        "today_bookings": today_count,
    }

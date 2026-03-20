"""Booking endpoints — passenger, driver, and admin booking operations."""

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.database import get_database
from app.core.security import get_current_active_user, get_current_admin, get_current_driver
from app.enums.common import BookingStatus, BookingType
from app.models.user import UserDocument
from app.schemas.booking import (
    BookingResponse,
    BookingStatusUpdate,
    CustomTripBookingCreate,
    FixedRouteBookingCreate,
    SeatMapResponse,
)
from app.services import booking_service

router = APIRouter(tags=["Bookings"])


# ── Passenger endpoints ────────────────────────────────────────────────────


@router.get("/seat-map", response_model=SeatMapResponse, summary="Get seat map")
async def get_seat_map(
    vehicle_id: str = Query(...),
    route_id: str = Query(...),
    trip_date: date = Query(...),
    _user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Get the seat map for a vehicle+route+date showing booked/available seats."""
    return await booking_service.get_seat_map(vehicle_id, route_id, trip_date, db)


@router.post(
    "/fixed-route",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create fixed route booking",
)
async def create_fixed_route_booking(
    data: FixedRouteBookingCreate,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Book seats on a fixed intercity route."""
    return await booking_service.create_fixed_route_booking(
        str(current_user.id), data, db
    )


@router.post(
    "/custom-trip",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create custom trip booking",
)
async def create_custom_trip_booking(
    data: CustomTripBookingCreate,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Create a custom trip booking (point-to-point)."""
    return await booking_service.create_custom_trip_booking(
        str(current_user.id), data, db
    )


@router.get(
    "/custom-trip/available-drivers",
    summary="Find available drivers for custom trip",
)
async def find_available_drivers(
    preferred_vehicle_type: Optional[str] = Query(default=None),
    _user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Find available online drivers, optionally filtered by vehicle type."""
    from app.enums.common import VehicleType as VT

    data = CustomTripBookingCreate(
        pickup_location={"name": "temp", "lat": 0, "lng": 0},
        drop_location={"name": "temp", "lat": 0, "lng": 0},
        scheduled_at="2099-01-01T00:00:00",
        preferred_vehicle_type=preferred_vehicle_type,
    )
    return await booking_service.find_available_drivers_for_custom_trip(data, db)


@router.get("/my", summary="List my bookings")
async def list_my_bookings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[BookingStatus] = Query(default=None, alias="status"),
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """List the current passenger's bookings."""
    return await booking_service.list_passenger_bookings(
        str(current_user.id), skip, limit, db, status_filter=status_filter
    )


@router.get("/stats", summary="Booking statistics (admin)")
async def get_booking_stats(
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: get overall booking statistics."""
    return await booking_service.get_booking_stats(db)


# ── Driver endpoints ──────────────────────────────────────────────────────


@router.get("/driver/pending", summary="List pending bookings for driver")
async def list_driver_pending(
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """List PENDING bookings assigned to the current driver."""
    from app.core.database import DRIVERS_COLLECTION

    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": str(current_user.id)})
    if not driver:
        return []
    return await booking_service.list_driver_pending_bookings(str(driver["_id"]), db)


@router.get("/driver/my", summary="List driver's bookings")
async def list_driver_bookings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[BookingStatus] = Query(default=None, alias="status"),
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """List all bookings assigned to the current driver."""
    from app.core.database import DRIVERS_COLLECTION

    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": str(current_user.id)})
    if not driver:
        return {"data": [], "total": 0, "skip": skip, "limit": limit}
    return await booking_service.list_driver_bookings(
        str(driver["_id"]), skip, limit, db, status_filter=status_filter
    )


@router.put(
    "/{booking_id}/status",
    response_model=BookingResponse,
    summary="Update booking status (driver)",
)
async def update_booking_status(
    booking_id: str,
    data: BookingStatusUpdate,
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """Driver: confirm, reject, or complete a booking."""
    return await booking_service.update_booking_status(
        booking_id, str(current_user.id), current_user.role.value, data, db
    )


# ── Passenger cancel ──────────────────────────────────────────────────────


@router.put(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Cancel own booking",
)
async def cancel_booking(
    booking_id: str,
    data: BookingStatusUpdate,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Passenger: cancel own booking."""
    cancel_data = BookingStatusUpdate(
        status=BookingStatus.CANCELLED,
        cancellation_reason=data.cancellation_reason,
    )
    return await booking_service.update_booking_status(
        booking_id, str(current_user.id), current_user.role.value, cancel_data, db
    )


# ── Admin endpoints ───────────────────────────────────────────────────────


@router.get("/", summary="List all bookings (admin)")
async def list_all_bookings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[BookingStatus] = Query(default=None, alias="status"),
    booking_type: Optional[BookingType] = Query(default=None),
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: list all bookings with filters."""
    return await booking_service.list_all_bookings(
        skip, limit, db, status_filter=status_filter, booking_type_filter=booking_type
    )


@router.put(
    "/{booking_id}/admin-cancel",
    response_model=BookingResponse,
    summary="Admin cancel any booking",
)
async def admin_cancel_booking(
    booking_id: str,
    data: BookingStatusUpdate,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: cancel any booking."""
    cancel_data = BookingStatusUpdate(
        status=BookingStatus.CANCELLED,
        cancellation_reason=data.cancellation_reason or "Cancelled by admin",
    )
    return await booking_service.update_booking_status(
        booking_id, str(_admin.id), "admin", cancel_data, db
    )


# ── Get booking detail (must be AFTER all static paths) ───────────────────


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get booking detail",
)
async def get_booking(
    booking_id: str,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Get booking details. Access controlled by role."""
    return await booking_service.get_booking_by_id(
        booking_id, str(current_user.id), current_user.role.value, db
    )

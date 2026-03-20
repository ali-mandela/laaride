"""Driver routes — all driver and vehicle endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.database import get_database
from app.core.security import get_current_active_user, get_current_admin, get_current_driver
from app.enums.common import DriverStatus
from app.models.user import UserDocument
from app.schemas.driver import (
    AvailabilityToggle,
    DriverCreate,
    DriverResponse,
    DriverUpdate,
    SuspendRequest,
)
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services import driver_service

router = APIRouter(tags=["Drivers"])


# ── Driver self-service ────────────────────────────────────────────────────


@router.post(
    "/apply",
    response_model=DriverResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply as a driver",
)
async def apply_as_driver(
    data: DriverCreate,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Any logged-in user can submit a driver application."""
    return await driver_service.apply_as_driver(str(current_user.id), data, db)


@router.get(
    "/me",
    response_model=DriverResponse,
    summary="Get own driver profile",
)
async def get_my_profile(
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """Return the driver profile of the currently authenticated driver."""
    return await driver_service.get_driver_profile(str(current_user.id), db)


@router.put(
    "/me",
    response_model=DriverResponse,
    summary="Update own driver profile",
)
async def update_my_profile(
    data: DriverUpdate,
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """Update license_expiry or current_location."""
    return await driver_service.update_driver_profile(str(current_user.id), data, db)


@router.put(
    "/me/availability",
    response_model=DriverResponse,
    summary="Toggle availability",
)
async def toggle_availability(
    data: AvailabilityToggle,
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """Set availability to ONLINE or OFFLINE. Cannot set ON_TRIP manually."""
    return await driver_service.toggle_availability(
        str(current_user.id), data.availability, db
    )


@router.get("/me/stats", summary="Get own driver stats")
async def get_my_stats(
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """Return total_trips, rating, availability, and total_earnings."""
    return await driver_service.get_driver_stats(str(current_user.id), db)


# ── Vehicle management ─────────────────────────────────────────────────────


@router.post(
    "/me/vehicles",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a vehicle",
)
async def add_vehicle(
    data: VehicleCreate,
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """Register a new vehicle. Seat layout is auto-generated if not provided."""
    return await driver_service.add_vehicle(str(current_user.id), data, db)


@router.get(
    "/me/vehicles",
    response_model=list[VehicleResponse],
    summary="List own vehicles",
)
async def list_my_vehicles(
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """Return all vehicles belonging to the current driver."""
    return await driver_service.get_driver_vehicles(str(current_user.id), db)


@router.put(
    "/me/vehicles/{vehicle_id}",
    response_model=VehicleResponse,
    summary="Update a vehicle",
)
async def update_my_vehicle(
    vehicle_id: str,
    data: VehicleUpdate,
    current_user: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """Update a vehicle you own (is_active, capacity, seat_layout)."""
    return await driver_service.update_vehicle(
        str(current_user.id), vehicle_id, data, db
    )


# ── Admin routes ───────────────────────────────────────────────────────────


@router.get("/", summary="List all drivers (admin)")
async def list_drivers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[DriverStatus] = Query(default=None, alias="status"),
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: list all drivers with optional status filter."""
    return await driver_service.list_drivers(skip, limit, db, status_filter=status_filter)


@router.get(
    "/{driver_id}",
    response_model=DriverResponse,
    summary="Get driver by ID (admin)",
)
async def get_driver(
    driver_id: str,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: retrieve any driver profile by its document ID."""
    return await driver_service.get_driver_by_id(driver_id, db)


@router.post(
    "/{driver_id}/approve",
    response_model=DriverResponse,
    summary="Approve a driver (admin)",
)
async def approve_driver(
    driver_id: str,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: approve a pending driver and update user role to DRIVER."""
    return await driver_service.approve_driver(driver_id, db)


@router.post(
    "/{driver_id}/suspend",
    response_model=DriverResponse,
    summary="Suspend a driver (admin)",
)
async def suspend_driver(
    driver_id: str,
    data: SuspendRequest,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: suspend a driver and set availability to OFFLINE."""
    return await driver_service.suspend_driver(driver_id, data.reason, db)

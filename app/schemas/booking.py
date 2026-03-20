from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.enums.common import BookingStatus, BookingType, VehicleType
from app.models.base import PyObjectId


# ── Create schemas ─────────────────────────────────────────────────────────


class FixedRouteBookingCreate(BaseModel):
    """Schema for creating a fixed-route booking with seat selection."""

    route_id: str = Field(..., description="Route ID")
    vehicle_id: str = Field(..., description="Vehicle ID")
    driver_id: str = Field(..., description="Driver (document) ID")
    seats_booked: list[str] = Field(
        ..., min_length=1, description="Seat IDs to book (e.g. ['2A', '2B'])"
    )
    trip_date: date = Field(..., description="Date of trip (must be future)")
    scheduled_at: datetime = Field(..., description="Scheduled departure time")
    notes: Optional[str] = Field(None, description="Additional notes")


class CustomTripBookingCreate(BaseModel):
    """Schema for creating a custom trip booking."""

    pickup_location: dict = Field(
        ..., description="Pickup location with name, lat, lng"
    )
    drop_location: dict = Field(
        ..., description="Drop location with name, lat, lng"
    )
    scheduled_at: datetime = Field(..., description="Scheduled pickup time (must be future)")
    preferred_vehicle_type: Optional[VehicleType] = Field(
        None, description="Preferred vehicle type"
    )
    notes: Optional[str] = Field(None, description="Additional notes")


# ── Update schemas ─────────────────────────────────────────────────────────


class BookingStatusUpdate(BaseModel):
    """Schema for updating booking status."""

    status: BookingStatus = Field(..., description="New booking status")
    cancellation_reason: Optional[str] = Field(
        None, description="Reason for cancellation (required when cancelling)"
    )


# ── Response schemas ───────────────────────────────────────────────────────


class BookingResponse(BaseModel):
    """Full booking API response."""

    id: Optional[PyObjectId] = Field(None, alias="_id")
    passenger_id: str
    driver_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    booking_type: BookingType
    route_id: Optional[str] = None
    pickup_location: dict
    drop_location: dict
    scheduled_at: datetime
    status: BookingStatus
    fare: Optional[float] = None
    notes: Optional[str] = None

    # Fixed route
    seats_booked: list[str] = []
    total_passengers: int = 0
    trip_date: Optional[date] = None

    # Custom trip
    preferred_vehicle_type: Optional[VehicleType] = None
    distance_estimate_km: Optional[float] = None
    duration_estimate_mins: Optional[int] = None

    # Denormalized
    passenger_name: str = ""
    passenger_phone: str = ""

    # Lifecycle
    cancellation_reason: Optional[str] = None
    cancelled_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class SeatMapResponse(BaseModel):
    """Seat map for a specific vehicle+route+date combination."""

    vehicle_id: str
    route_id: str
    trip_date: date
    seat_layout: Optional[dict] = None
    booked_seats: list[str] = []
    available_seats: list[str] = []
    total_capacity: int = 0
    available_count: int = 0

from datetime import date, datetime
from typing import Optional

from pydantic import Field

from app.enums.common import BookingStatus, BookingType, PaymentMethod, PaymentStatus, VehicleType
from app.models.base import MongoBaseDocument


class BookingDocument(MongoBaseDocument):
    """MongoDB document model for bookings."""

    # Core references
    passenger_id: str = Field(..., description="Reference to User (passenger)")
    driver_id: Optional[str] = Field(
        None, description="Reference to Driver (assigned after accept)"
    )
    vehicle_id: Optional[str] = Field(None, description="Reference to Vehicle")
    booking_type: BookingType = Field(..., description="Type of booking")
    route_id: Optional[str] = Field(
        None, description="Reference to Route (for FIXED_ROUTE bookings)"
    )

    # Locations
    pickup_location: dict = Field(
        ..., description="Pickup location with name, lat, and lng"
    )
    drop_location: dict = Field(
        ..., description="Drop location with name, lat, and lng"
    )

    # Scheduling
    scheduled_at: datetime = Field(..., description="Scheduled pickup time")
    status: BookingStatus = Field(
        default=BookingStatus.PENDING, description="Booking status"
    )
    fare: Optional[float] = Field(None, description="Calculated or agreed fare")
    notes: Optional[str] = Field(None, description="Additional notes from passenger")

    # Fixed route fields
    seats_booked: list[str] = Field(
        default_factory=list, description="Seat IDs booked (e.g. ['2A', '2B'])"
    )
    total_passengers: int = Field(default=0, description="Number of passengers")
    trip_date: Optional[date] = Field(
        None, description="Trip date for fixed route bookings"
    )

    # Custom trip fields
    preferred_vehicle_type: Optional[VehicleType] = Field(
        None, description="Preferred vehicle type for custom trips"
    )
    distance_estimate_km: Optional[float] = Field(
        None, description="Estimated distance for custom trips"
    )
    duration_estimate_mins: Optional[int] = Field(
        None, description="Estimated duration for custom trips"
    )

    # Denormalized passenger info
    passenger_name: str = Field(default="", description="Passenger name for display")
    passenger_phone: str = Field(default="", description="Passenger phone for display")

    # Lifecycle timestamps
    cancellation_reason: Optional[str] = Field(None, description="Reason for cancellation")
    cancelled_by: Optional[str] = Field(None, description="User ID who cancelled")
    confirmed_at: Optional[datetime] = Field(None, description="When booking was confirmed")
    completed_at: Optional[datetime] = Field(None, description="When booking was completed")

    # Payment
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.UNPAID, description="Payment status"
    )
    payment_method: Optional[PaymentMethod] = Field(None, description="Payment method")
    payment_id: Optional[str] = Field(None, description="Reference to PaymentDocument")

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.enums.common import BookingStatus, BookingType
from app.models.base import MongoBaseDocument


class BookingDocument(MongoBaseDocument):
    """MongoDB document model for bookings."""

    passenger_id: str = Field(..., description="Reference to User (passenger)")
    driver_id: Optional[str] = Field(
        None, description="Reference to Driver (assigned after accept)"
    )
    vehicle_id: Optional[str] = Field(
        None, description="Reference to Vehicle"
    )
    booking_type: BookingType = Field(..., description="Type of booking")
    route_id: Optional[str] = Field(
        None, description="Reference to Route (for FIXED_ROUTE bookings)"
    )
    pickup_location: dict = Field(
        ..., description="Pickup location with name, lat, and lng"
    )
    drop_location: dict = Field(
        ..., description="Drop location with name, lat, and lng"
    )
    scheduled_at: datetime = Field(..., description="Scheduled pickup time")
    status: BookingStatus = Field(
        default=BookingStatus.PENDING, description="Booking status"
    )
    fare: Optional[float] = Field(None, description="Calculated or agreed fare")
    notes: Optional[str] = Field(None, description="Additional notes from passenger")

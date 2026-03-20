from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.enums.common import BookingStatus, BookingType
from app.models.base import PyObjectId


class BookingCreate(BaseModel):
    """Schema for creating a new booking."""

    booking_type: BookingType = Field(..., description="Type of booking")
    pickup_location: dict = Field(
        ..., description="Pickup location with name, lat, lng"
    )
    drop_location: dict = Field(
        ..., description="Drop location with name, lat, lng"
    )
    scheduled_at: datetime = Field(..., description="Scheduled pickup time")
    route_id: Optional[str] = Field(
        None, description="Route ID (required for FIXED_ROUTE bookings)"
    )
    notes: Optional[str] = Field(None, description="Additional notes")


class BookingUpdate(BaseModel):
    """Schema for updating a booking."""

    status: Optional[BookingStatus] = Field(None, description="Booking status")
    driver_id: Optional[str] = Field(None, description="Assigned driver ID")
    vehicle_id: Optional[str] = Field(None, description="Assigned vehicle ID")
    fare: Optional[float] = Field(None, description="Final fare")


class BookingResponse(BaseModel):
    """Schema for booking API response."""

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
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}

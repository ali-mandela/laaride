from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.enums.common import AvailabilityStatus, DriverStatus


class DriverCreate(BaseModel):
    """Schema for creating a new driver profile."""

    user_id: str = Field(..., description="Reference to existing User")
    license_number: str = Field(..., description="Driver's license number")
    license_expiry: date = Field(..., description="License expiry date")


class DriverUpdate(BaseModel):
    """Schema for updating driver profile."""

    license_expiry: Optional[date] = Field(None, description="License expiry date")
    availability: Optional[AvailabilityStatus] = Field(
        None, description="Current availability"
    )
    current_location: Optional[dict] = Field(
        None, description="Current location with lat and lng"
    )


class DriverResponse(BaseModel):
    """Schema for driver API response."""

    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    license_number: str
    license_expiry: date
    status: DriverStatus
    availability: AvailabilityStatus
    current_location: Optional[dict] = None
    rating: float
    total_trips: int
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}

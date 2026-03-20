import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.enums.common import AvailabilityStatus, DriverStatus


class DriverCreate(BaseModel):
    """Schema for applying as a driver. user_id comes from auth token."""

    license_number: str = Field(..., description="Driver's license number")
    license_expiry: date = Field(..., description="License expiry date")

    @field_validator("license_number")
    @classmethod
    def validate_license(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9]+$", v):
            raise ValueError("License number must be alphanumeric")
        return v


class DriverUpdate(BaseModel):
    """Schema for updating driver profile (driver-editable fields only)."""

    license_expiry: Optional[date] = Field(None, description="License expiry date")
    current_location: Optional[dict] = Field(
        None, description="Current location with lat and lng"
    )


class AvailabilityToggle(BaseModel):
    """Schema for toggling driver availability."""

    availability: AvailabilityStatus = Field(..., description="New availability status")


class SuspendRequest(BaseModel):
    """Schema for admin suspending a driver."""

    reason: str = Field(..., description="Reason for suspension")


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

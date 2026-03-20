from datetime import date
from typing import Optional

from pydantic import Field

from app.enums.common import AvailabilityStatus, DriverStatus
from app.models.base import MongoBaseDocument


class DriverDocument(MongoBaseDocument):
    """MongoDB document model for drivers."""

    user_id: str = Field(..., description="Reference to User document")
    license_number: str = Field(..., description="Driver's license number")
    license_expiry: date = Field(..., description="License expiry date")
    status: DriverStatus = Field(
        default=DriverStatus.PENDING_APPROVAL, description="Driver approval status"
    )
    availability: AvailabilityStatus = Field(
        default=AvailabilityStatus.OFFLINE, description="Current availability status"
    )
    current_location: Optional[dict] = Field(
        None, description="Current location with lat and lng"
    )
    rating: float = Field(default=0.0, description="Average rating")
    total_trips: int = Field(default=0, description="Total completed trips")

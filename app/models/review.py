"""Review document model for driver ratings and passenger feedback."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from app.models.base import MongoBaseDocument, PyObjectId


class ReviewDocument(MongoBaseDocument):
    """Stores a passenger's review of a driver after trip completion."""

    booking_id: PyObjectId
    passenger_id: PyObjectId
    driver_id: PyObjectId

    # Rating 1-5 stars
    rating: float = Field(..., ge=1.0, le=5.0)
    comment: Optional[str] = Field(None, max_length=500)

    # Denormalised for quick display
    passenger_name: str
    driver_name: str

    # Moderation
    is_visible: bool = True
    flagged: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("rating")
    @classmethod
    def round_rating(cls, v: float) -> float:
        """Ratings are stored in 0.5 increments."""
        return round(v * 2) / 2

    class Settings:
        name = "reviews"

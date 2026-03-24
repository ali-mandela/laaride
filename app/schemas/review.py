"""Pydantic schemas for the review/rating system."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    booking_id: str
    rating: float = Field(..., ge=1.0, le=5.0, description="Star rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=500)


class ReviewResponse(BaseModel):
    id: str
    booking_id: str
    passenger_id: str
    driver_id: str
    rating: float
    comment: Optional[str]
    passenger_name: str
    created_at: datetime


class DriverRatingSummary(BaseModel):
    driver_id: str
    average_rating: float
    total_reviews: int
    rating_breakdown: dict[str, int]  # {"5": 12, "4": 8, ...}

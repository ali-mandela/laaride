"""Earnings document model for tracking driver income per trip."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.models.base import MongoBaseDocument, PyObjectId


class EarningsStatus(str, Enum):
    PENDING = "pending"         # Trip completed, awaiting settlement
    SETTLED = "settled"         # Paid out to driver
    ON_HOLD = "on_hold"         # Under dispute or admin review


class EarningsDocument(MongoBaseDocument):
    """Records driver earnings for a single completed trip."""

    driver_id: PyObjectId
    booking_id: PyObjectId
    route_id: Optional[PyObjectId] = None

    gross_amount: float           # Full fare paid by passenger
    platform_fee: float           # LaaRide commission (e.g. 10%)
    net_amount: float             # gross_amount - platform_fee

    payment_method: str           # "cash" | "razorpay"
    status: EarningsStatus = EarningsStatus.PENDING

    trip_date: datetime
    settled_at: Optional[datetime] = None

    # Denormalised for quick reporting
    route_name: Optional[str] = None
    passenger_count: int = 1

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "earnings"

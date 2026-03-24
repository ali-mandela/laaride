"""Pydantic schemas for driver earnings."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EarningsResponse(BaseModel):
    id: str
    booking_id: str
    route_name: Optional[str]
    gross_amount: float
    platform_fee: float
    net_amount: float
    payment_method: str
    status: str
    trip_date: datetime
    passenger_count: int


class EarningsSummary(BaseModel):
    driver_id: str
    total_gross: float
    total_platform_fee: float
    total_net: float
    total_trips: int
    period_start: datetime
    period_end: datetime
    by_day: list[dict]   # [{"date": "2025-01-01", "net": 1200.0, "trips": 3}]
    by_route: list[dict] # [{"route": "Leh-Kargil", "net": 5000.0, "trips": 12}]


class EarningsFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    route_id: Optional[str] = None

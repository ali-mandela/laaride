from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.enums.common import TripStatus


class TripCreate(BaseModel):
    """Payload to create a new trip listing."""

    route_id: str = Field(..., description="Route to operate on")
    vehicle_id: str = Field(..., description="Vehicle to use")
    trip_date: date = Field(..., description="Date of the trip (YYYY-MM-DD)")
    departure_time: str = Field(
        ...,
        pattern=r"^\d{2}:\d{2}$",
        description="Departure time in HH:MM (24-hour)",
    )
    fare_per_seat: float = Field(..., gt=0, description="Fare charged per seat")
    notes: Optional[str] = Field(None, description="Optional driver notes")

    @field_validator("trip_date")
    @classmethod
    def date_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("trip_date cannot be in the past")
        return v


class TripUpdate(BaseModel):
    """Partial update for a trip."""

    departure_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    fare_per_seat: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None
    status: Optional[TripStatus] = None


class TripResponse(BaseModel):
    """Full trip detail returned to clients."""

    id: Optional[str] = Field(None, alias="_id")
    route_id: str
    driver_id: str
    vehicle_id: str
    trip_date: date
    departure_time: str
    total_seats: int
    available_seats: int
    booked_seat_ids: list[str] = []
    fare_per_seat: float
    status: TripStatus
    route_name: str
    origin: dict
    destination: dict
    distance_km: Optional[float] = None
    estimated_duration_mins: Optional[int] = None
    driver_name: str = ""
    driver_phone: str = ""
    driver_rating: float = 0.0
    vehicle_number: str = ""
    vehicle_type: str = ""
    vehicle_model: str = ""
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class TripSearchParams(BaseModel):
    """Query parameters for trip search."""

    origin: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[date] = None
    seats: Optional[int] = Field(None, ge=1)


class SeatMapResponse(BaseModel):
    """Seat availability for a trip."""

    trip_id: str
    vehicle_id: str
    total_seats: int
    available_seats: int
    booked_seat_ids: list[str]
    seat_layout: list[dict] = []

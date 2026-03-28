from datetime import date, datetime
from typing import Optional

from pydantic import Field

from app.enums.common import TripStatus
from app.models.base import MongoBaseDocument


class TripDocument(MongoBaseDocument):
    """MongoDB document for a driver-listed trip on a fixed route."""

    # Core references
    route_id: str = Field(..., description="Reference to Route")
    driver_id: str = Field(..., description="Reference to Driver (user_id)")
    vehicle_id: str = Field(..., description="Reference to Vehicle")

    # Trip schedule
    trip_date: date = Field(..., description="Date of the trip")
    departure_time: str = Field(..., description="Departure time (HH:MM 24h)")

    # Seat tracking
    total_seats: int = Field(..., gt=0, description="Total seats in vehicle")
    available_seats: int = Field(..., ge=0, description="Remaining bookable seats")
    booked_seat_ids: list[str] = Field(
        default_factory=list, description="Seat IDs already booked"
    )

    # Pricing
    fare_per_seat: float = Field(..., gt=0, description="Fare per seat for this trip")

    # Status
    status: TripStatus = Field(default=TripStatus.SCHEDULED)

    # Denormalized for fast lookups (avoids joins on search)
    route_name: str = Field(default="", description="Cached route name")
    origin: dict = Field(default_factory=dict, description="Origin {name, lat, lng}")
    destination: dict = Field(
        default_factory=dict, description="Destination {name, lat, lng}"
    )
    distance_km: Optional[float] = Field(None)
    estimated_duration_mins: Optional[int] = Field(None)

    # Denormalized driver info
    driver_name: str = Field(default="", description="Driver display name")
    driver_phone: str = Field(default="", description="Driver phone")
    driver_rating: float = Field(default=0.0)

    # Denormalized vehicle info
    vehicle_number: str = Field(default="", description="Registration number")
    vehicle_type: str = Field(default="")
    vehicle_model: str = Field(default="")

    # Notes
    notes: Optional[str] = Field(None, description="Driver notes for this trip")

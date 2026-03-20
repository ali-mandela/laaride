from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.enums.common import VehicleType


class VehicleCreate(BaseModel):
    """Schema for registering a new vehicle. driver_id comes from driver lookup."""

    vehicle_type: VehicleType = Field(..., description="Type of vehicle")
    make: str = Field(..., description="Vehicle make (e.g. Innova)")
    model: str = Field(..., description="Vehicle model")
    year: int = Field(..., description="Manufacturing year")
    registration_number: str = Field(
        ..., description="Unique registration number"
    )
    capacity: int = Field(..., description="Passenger capacity")
    seat_layout: Optional[dict] = Field(
        None,
        description="Seat layout with rows, columns, unavailable_seats. Auto-generated if not provided.",
    )


class VehicleUpdate(BaseModel):
    """Schema for updating vehicle details."""

    is_active: Optional[bool] = Field(None, description="Whether the vehicle is active")
    capacity: Optional[int] = Field(None, description="Passenger capacity")
    seat_layout: Optional[dict] = Field(None, description="Updated seat layout")


class VehicleResponse(BaseModel):
    """Schema for vehicle API response."""

    id: Optional[str] = Field(None, alias="_id")
    driver_id: str
    vehicle_type: VehicleType
    make: str
    model: str
    year: int
    registration_number: str
    capacity: int
    is_active: bool
    seat_layout: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}

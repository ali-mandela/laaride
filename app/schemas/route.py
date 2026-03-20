from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RouteCreate(BaseModel):
    """Schema for creating a new route."""

    name: str = Field(..., description="Route name (e.g. 'Leh to Kargil')")
    origin: dict = Field(..., description="Origin with name, lat, lng")
    destination: dict = Field(..., description="Destination with name, lat, lng")
    distance_km: float = Field(..., description="Distance in kilometers")
    estimated_duration_mins: int = Field(
        ..., description="Estimated travel duration in minutes"
    )
    base_fare: float = Field(..., description="Base fare for this route")


class RouteUpdate(BaseModel):
    """Schema for updating route details."""

    base_fare: Optional[float] = Field(None, description="Base fare")
    is_active: Optional[bool] = Field(None, description="Whether the route is active")
    estimated_duration_mins: Optional[int] = Field(
        None, description="Estimated duration in minutes"
    )


class RouteResponse(BaseModel):
    """Schema for route API response."""

    id: Optional[str] = Field(None, alias="_id")
    name: str
    origin: dict
    destination: dict
    distance_km: float
    estimated_duration_mins: int
    base_fare: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}

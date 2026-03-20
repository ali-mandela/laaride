from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RouteCreate(BaseModel):
    """Schema for creating a new route."""

    name: str = Field(..., min_length=3, max_length=200, description="Route name (e.g. 'Leh to Kargil')")
    origin: dict = Field(..., description="Origin with name, lat, lng")
    destination: dict = Field(..., description="Destination with name, lat, lng")
    distance_km: float = Field(..., gt=0, description="Distance in kilometers")
    estimated_duration_mins: int = Field(
        ..., gt=0, description="Estimated travel duration in minutes"
    )
    base_fare: float = Field(..., gt=0, description="Base fare for this route")
    waypoints: list[dict] = Field(
        default_factory=list,
        description="Stops along the route with name, lat, lng, order, distance_from_origin_km",
    )
    tags: list[str] = Field(default_factory=list, description="Tags like scenic, high-altitude")
    is_seasonal: bool = Field(default=False, description="Whether route is seasonal")
    season_start_month: Optional[int] = Field(None, description="Season start month (1-12)")
    season_end_month: Optional[int] = Field(None, description="Season end month (1-12)")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class RouteUpdate(BaseModel):
    """Schema for updating route details."""

    name: Optional[str] = Field(None, description="Route name")
    origin: Optional[dict] = Field(None, description="Origin with name, lat, lng")
    destination: Optional[dict] = Field(None, description="Destination with name, lat, lng")
    distance_km: Optional[float] = Field(None, description="Distance in kilometers")
    base_fare: Optional[float] = Field(None, description="Base fare")
    is_active: Optional[bool] = Field(None, description="Whether the route is active")
    estimated_duration_mins: Optional[int] = Field(
        None, description="Estimated duration in minutes"
    )
    waypoints: Optional[list[dict]] = Field(None, description="Route waypoints")
    tags: Optional[list[str]] = Field(None, description="Route tags")
    is_seasonal: Optional[bool] = Field(None, description="Whether route is seasonal")
    season_start_month: Optional[int] = Field(None, description="Season start month")
    season_end_month: Optional[int] = Field(None, description="Season end month")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")


class RouteResponse(BaseModel):
    """Schema for route API response."""

    id: Optional[str] = Field(None, alias="_id")
    name: str
    slug: str
    origin: dict
    destination: dict
    distance_km: float
    estimated_duration_mins: int
    base_fare: float
    is_active: bool
    waypoints: list[dict] = []
    tags: list[str] = []
    is_seasonal: bool = False
    season_start_month: Optional[int] = None
    season_end_month: Optional[int] = None
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class RouteSearchParams(BaseModel):
    """Query parameters for route search/filtering."""

    origin_name: Optional[str] = None
    destination_name: Optional[str] = None
    max_fare: Optional[float] = None
    is_active: Optional[bool] = None
    tag: Optional[str] = None

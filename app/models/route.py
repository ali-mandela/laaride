from typing import Optional

from pydantic import Field

from app.models.base import MongoBaseDocument


class RouteDocument(MongoBaseDocument):
    """MongoDB document model for routes."""

    name: str = Field(..., description="Route name (e.g. 'Leh to Kargil')")
    slug: str = Field(..., description="URL-friendly slug (e.g. 'leh-kargil')")
    origin: dict = Field(
        ..., description="Origin location with name, lat, and lng"
    )
    destination: dict = Field(
        ..., description="Destination location with name, lat, and lng"
    )
    distance_km: float = Field(..., description="Distance in kilometers")
    estimated_duration_mins: int = Field(
        ..., description="Estimated travel duration in minutes"
    )
    base_fare: float = Field(..., description="Base fare for this route")
    is_active: bool = Field(default=True, description="Whether the route is active")
    waypoints: list[dict] = Field(
        default_factory=list,
        description="Ordered stops along the route with name, lat, lng, order, distance_from_origin_km",
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags like scenic, high-altitude, seasonal"
    )
    is_seasonal: bool = Field(default=False, description="Whether route is seasonal")
    season_start_month: Optional[int] = Field(
        None, description="Season start month (1-12)"
    )
    season_end_month: Optional[int] = Field(
        None, description="Season end month (1-12)"
    )
    thumbnail_url: Optional[str] = Field(None, description="Route thumbnail image URL")

from pydantic import Field

from app.models.base import MongoBaseDocument


class RouteDocument(MongoBaseDocument):
    """MongoDB document model for routes."""

    name: str = Field(..., description="Route name (e.g. 'Leh to Kargil')")
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

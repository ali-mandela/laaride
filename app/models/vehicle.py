from pydantic import Field

from app.enums.common import VehicleType
from app.models.base import MongoBaseDocument


class VehicleDocument(MongoBaseDocument):
    """MongoDB document model for vehicles."""

    driver_id: str = Field(..., description="Reference to Driver document")
    vehicle_type: VehicleType = Field(..., description="Type of vehicle")
    make: str = Field(..., description="Vehicle make (e.g. Innova)")
    model: str = Field(..., description="Vehicle model")
    year: int = Field(..., description="Manufacturing year")
    registration_number: str = Field(
        ..., description="Unique vehicle registration number"
    )
    capacity: int = Field(..., description="Passenger capacity")
    is_active: bool = Field(default=True, description="Whether the vehicle is active")

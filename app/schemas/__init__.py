from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.driver import DriverCreate, DriverUpdate, DriverResponse, AvailabilityToggle, SuspendRequest
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse
from app.schemas.route import RouteCreate, RouteUpdate, RouteResponse, RouteSearchParams
from app.schemas.booking import BookingCreate, BookingUpdate, BookingResponse

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Driver
    "DriverCreate",
    "DriverUpdate",
    "DriverResponse",
    "AvailabilityToggle",
    "SuspendRequest",
    # Vehicle
    "VehicleCreate",
    "VehicleUpdate",
    "VehicleResponse",
    # Route
    "RouteCreate",
    "RouteUpdate",
    "RouteResponse",
    "RouteSearchParams",
    # Booking
    "BookingCreate",
    "BookingUpdate",
    "BookingResponse",
]


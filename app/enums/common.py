from enum import Enum


class UserRole(str, Enum):
    PASSENGER = "passenger"
    DRIVER = "driver"
    ADMIN = "admin"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    REJECTED = "rejected"


class BookingType(str, Enum):
    FIXED_ROUTE = "fixed_route"
    CUSTOM_TRIP = "custom_trip"


class DriverStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SUSPENDED = "suspended"


class AvailabilityStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ON_TRIP = "on_trip"


class VehicleType(str, Enum):
    SEDAN = "sedan"
    SUV = "suv"
    TEMPO_TRAVELLER = "tempo_traveller"
    BUS = "bus"
    BIKE = "bike"

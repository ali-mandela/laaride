from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# Collection names
USERS_COLLECTION = "users"
DRIVERS_COLLECTION = "drivers"
VEHICLES_COLLECTION = "vehicles"
ROUTES_COLLECTION = "routes"
BOOKINGS_COLLECTION = "bookings"
OTP_COLLECTION = "otps"
NOTIFICATIONS_COLLECTION = "notifications"


class Database:
    client: AsyncIOMotorClient = None
    db = None


db_instance = Database()


async def get_database():
    """Dependency to get the database instance."""
    return db_instance.db

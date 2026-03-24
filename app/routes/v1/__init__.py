from fastapi import APIRouter

from .default import router as default_router
from .users import router as users_router
from .auth import router as auth_router
from .drivers import router as drivers_router
from .routes import router as routes_router
from .bookings import router as bookings_router
from .notifications import router as notifications_router
from .admin import router as admin_router
from .search import router as search_router
from .payments import router as payments_router
from .disputes import router as disputes_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(default_router)
v1_router.include_router(users_router, prefix="/users")
v1_router.include_router(auth_router)
v1_router.include_router(drivers_router, prefix="/drivers")
v1_router.include_router(routes_router, prefix="/routes")
v1_router.include_router(bookings_router, prefix="/bookings")
v1_router.include_router(notifications_router, prefix="/notifications")
v1_router.include_router(admin_router, prefix="/admin")
v1_router.include_router(search_router, prefix="/search")
v1_router.include_router(payments_router)
v1_router.include_router(disputes_router, prefix="/disputes")


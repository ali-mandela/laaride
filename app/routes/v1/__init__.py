from fastapi import APIRouter

from .default import router as default_router
from .users import router as users_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(default_router)
v1_router.include_router(users_router)

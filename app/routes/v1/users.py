from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pydantic import BaseModel

from app.core.database import get_database
from app.core.security import get_current_active_user, get_current_admin
from app.enums.common import UserRole
from app.models.user import UserDocument
from app.schemas.user import UserResponse, UserUpdate
from app.services import notification_service, user_service


class FcmTokenRequest(BaseModel):
    token: str

router = APIRouter(tags=["Users"])


# ── Protected routes (any authenticated active user) ──────────────────────


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(
    current_user: UserDocument = Depends(get_current_active_user),
):
    """Return the profile of the currently authenticated user."""
    return UserResponse(**current_user.model_dump())


@router.put("/me", response_model=UserResponse, summary="Update current user profile")
async def update_me(
    data: UserUpdate,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Partially update the current user's profile (name, email, etc.)."""
    return await user_service.update_user(str(current_user.id), data, db)


@router.post(
    "/me/photo",
    response_model=UserResponse,
    summary="Upload profile photo",
)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Upload a profile photo (jpg, png, webp — max 2 MB)."""
    return await user_service.upload_profile_photo(str(current_user.id), file, db)


@router.get("/me/bookings", summary="Get booking history")
async def get_my_bookings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Retrieve the current user's booking history (paginated)."""
    return await user_service.get_user_booking_history(
        str(current_user.id), skip, limit, db
    )


@router.post(
    "/me/fcm-token",
    summary="Register FCM push notification token",
    status_code=status.HTTP_200_OK,
)
async def register_fcm_token(
    data: FcmTokenRequest,
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Register or refresh an FCM token for push notifications."""
    return await notification_service.register_fcm_token(str(current_user.id), data.token, db)


@router.delete("/me", summary="Deactivate account")
async def deactivate_me(
    current_user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Soft-delete the current user's account (sets is_active = False)."""
    return await user_service.deactivate_user(str(current_user.id), db)


# ── Admin-only routes ─────────────────────────────────────────────────────


@router.get("/", summary="List all users (admin)")
async def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    role: Optional[UserRole] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: list all users with optional filters (role, is_active)."""
    return await user_service.list_users(skip, limit, db, role=role, is_active=is_active)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get any user by ID (admin)",
)
async def get_user(
    user_id: str,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: retrieve any user's profile by their ID."""
    return await user_service.get_user_by_id(user_id, db)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update any user (admin)",
)
async def update_user(
    user_id: str,
    data: UserUpdate,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: update any user's profile."""
    return await user_service.update_user(user_id, data, db)

from typing import Any
from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_database
from app.core.security import get_current_user
from app.models.user import UserDocument
from app.schemas.auth import (
    SendOTPRequest,
    SendOTPResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

limiter = Limiter(key_func=get_remote_address)


@router.post("/send-otp", response_model=SendOTPResponse)
@limiter.limit("5/10minutes")
async def send_otp(
    request: Request,
    data: SendOTPRequest,
    db: Any = Depends(get_database),
):
    """
    Send an OTP to the user's phone number.
    Rate limited: 5 requests per 10 minutes.
    """
    return await auth_service.send_otp(data.phone, db)


@router.post("/verify-otp", response_model=VerifyOTPResponse)
@limiter.limit("10/10minutes")
async def verify_otp(
    request: Request,
    data: VerifyOTPRequest,
    db: Any = Depends(get_database),
):
    """
    Verify the OTP and return JWT tokens.
    Rate limited: 10 requests per 10 minutes.
    """
    return await auth_service.verify_otp(data.phone, data.otp, db)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: Any = Depends(get_database),
):
    """Refresh the access token using a valid refresh token."""
    return await auth_service.refresh_access_token(data.refresh_token, db)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserDocument = Depends(get_current_user),
):
    """Get the current authenticated user's profile."""
    return UserResponse(**current_user.model_dump())

from typing import Any
from fastapi import APIRouter, Depends, status

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


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(
    request: SendOTPRequest,
    db: Any = Depends(get_database)
):
    """
    Send an OTP to the user's phone number.
    Returns the OTP in response if in development mode.
    """
    return await auth_service.send_otp(request.phone, db)


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(
    request: VerifyOTPRequest,
    db: Any = Depends(get_database)
):
    """
    Verify the OTP and return JWT tokens.
    If the user doesn't exist, a new user will be created.
    """
    return await auth_service.verify_otp(request.phone, request.otp, db)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Any = Depends(get_database)
):
    """
    Refresh the access token using a valid refresh token.
    """
    return await auth_service.refresh_access_token(request.refresh_token, db)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Get the current authenticated user's profile.
    """
    return UserResponse(**current_user.model_dump())

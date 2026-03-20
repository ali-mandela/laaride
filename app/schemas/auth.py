import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserResponse


class SendOTPRequest(BaseModel):
    """Schema for requesting an OTP."""

    phone: str = Field(..., description="Phone number in E.164 format")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        # Strict E.164: + followed by 10-15 digits
        if not re.match(r"^\+\d{10,15}$", v):
            raise ValueError("Phone number must be in E.164 format (e.g., +919876543210)")
        return v


class SendOTPResponse(BaseModel):
    """Schema for OTP request response."""

    message: str
    otp: Optional[str] = Field(None, description="OTP value (only in development)")


class VerifyOTPRequest(BaseModel):
    """Schema for verifying an OTP."""

    phone: str = Field(..., description="Phone number")
    otp: str = Field(..., description="6-digit OTP")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\+\d{10,15}$", v):
            raise ValueError("Phone number must be in E.164 format")
        return v

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits")
        return v


class VerifyOTPResponse(BaseModel):
    """Schema for OTP verification response including tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool


class RefreshTokenRequest(BaseModel):
    """Schema for refreshing access token."""

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response."""

    access_token: str
    token_type: str = "bearer"

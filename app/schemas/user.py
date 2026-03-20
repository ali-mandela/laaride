from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.enums.common import UserRole
from app.models.base import PyObjectId


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    phone: str = Field(..., description="Phone number (unique)")
    name: str = Field(..., description="Full name")
    email: Optional[str] = Field(None, description="Email address")

    model_config = {"json_schema_extra": {"example": {"phone": "+919876543210", "name": "Rahul Sharma"}}}


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    name: Optional[str] = Field(None, description="Full name")
    email: Optional[str] = Field(None, description="Email address")
    profile_photo: Optional[str] = Field(None, description="Profile photo URL")


class UserResponse(BaseModel):
    """Schema for user API response."""

    id: Optional[PyObjectId] = Field(None, alias="_id")
    phone: str
    name: str
    email: Optional[str] = None
    role: UserRole
    is_active: bool
    profile_photo: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}

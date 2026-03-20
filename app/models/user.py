from typing import Optional

from pydantic import Field

from app.enums.common import UserRole
from app.models.base import MongoBaseDocument


class UserDocument(MongoBaseDocument):
    """MongoDB document model for users."""

    phone: str = Field(..., description="Unique phone number")
    name: str = Field(..., description="Full name of the user")
    email: Optional[str] = Field(None, description="Email address")
    role: UserRole = Field(default=UserRole.PASSENGER, description="User role")
    is_active: bool = Field(default=True, description="Whether the user is active")
    profile_photo: Optional[str] = Field(
        None, description="URL of the profile photo"
    )
    fcm_tokens: list[str] = Field(
        default_factory=list, description="FCM device tokens for push notifications"
    )

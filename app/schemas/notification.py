from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import PyObjectId


class NotificationResponse(BaseModel):
    """Schema for notification API response."""

    id: Optional[PyObjectId] = Field(None, alias="_id")
    user_id: str
    title: str
    body: str
    data: Optional[dict] = None
    is_read: bool = False
    notification_type: str
    reference_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class MarkReadRequest(BaseModel):
    """Schema for marking notifications as read."""

    notification_ids: list[str] = Field(
        default_factory=list,
        description="IDs of notifications to mark as read. Empty = mark all as read.",
    )


class FCMTokenRequest(BaseModel):
    """Schema for registering/removing an FCM token."""

    token: str = Field(..., min_length=1, description="FCM device token")


class BroadcastRequest(BaseModel):
    """Schema for admin broadcast notification."""

    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Optional[dict] = Field(None, description="Extra payload")
    role_filter: Optional[str] = Field(
        None, description="Filter by user role (passenger, driver, admin). None = all users."
    )

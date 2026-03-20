from datetime import datetime
from typing import Optional

from pydantic import Field

from app.models.base import MongoBaseDocument


class NotificationDocument(MongoBaseDocument):
    """MongoDB document model for notifications."""

    user_id: str = Field(..., description="User this notification is for")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body text")
    data: Optional[dict] = Field(None, description="Extra payload data")
    is_read: bool = Field(default=False, description="Whether notification has been read")
    notification_type: str = Field(
        ..., description="Type: booking_update, driver_approval, system"
    )
    reference_id: Optional[str] = Field(
        None, description="Related entity ID (booking_id, driver_id, etc.)"
    )

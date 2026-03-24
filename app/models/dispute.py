"""Dispute/complaint document model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.models.base import MongoBaseDocument, PyObjectId


class DisputeType(str, Enum):
    PAYMENT_ISSUE = "payment_issue"
    DRIVER_BEHAVIOUR = "driver_behaviour"
    ROUTE_DEVIATION = "route_deviation"
    REFUND_REQUEST = "refund_request"
    OVERCHARGE = "overcharge"
    OTHER = "other"


class DisputeStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class DisputeMessage(MongoBaseDocument):
    """A single message in a dispute thread."""
    dispute_id: PyObjectId
    sender_id: PyObjectId
    sender_role: str           # "passenger" | "driver" | "admin"
    message: str = Field(..., max_length=2000)
    attachments: list[str] = Field(default_factory=list)  # file URLs
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "dispute_messages"


class DisputeDocument(MongoBaseDocument):
    """Stores a dispute raised by a passenger or driver."""

    booking_id: PyObjectId
    raised_by: PyObjectId          # user_id of complainant
    raised_against: PyObjectId     # user_id of other party

    dispute_type: DisputeType
    description: str = Field(..., max_length=2000)
    status: DisputeStatus = DisputeStatus.OPEN

    assigned_admin_id: Optional[PyObjectId] = None
    resolution_note: Optional[str] = None
    refund_amount: Optional[float] = None

    # Denormalised
    booking_reference: str
    complainant_name: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    class Settings:
        name = "disputes"

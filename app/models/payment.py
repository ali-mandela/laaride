from datetime import datetime
from typing import Optional

from pydantic import Field

from app.enums.common import PaymentMethod, PaymentStatus
from app.models.base import MongoBaseDocument


class PaymentDocument(MongoBaseDocument):
    """MongoDB document model for payments."""

    booking_id: str = Field(..., description="Reference to BookingDocument")
    passenger_id: str = Field(..., description="Reference to User (passenger)")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(default="INR", description="Currency code")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.UNPAID, description="Payment status"
    )

    # Razorpay fields (online payments only)
    razorpay_order_id: Optional[str] = Field(None, description="Razorpay order ID")
    razorpay_payment_id: Optional[str] = Field(None, description="Razorpay payment ID")
    razorpay_signature: Optional[str] = Field(None, description="Razorpay signature")

    # Failure / Refund
    failure_reason: Optional[str] = Field(None, description="Reason for failure")
    refund_id: Optional[str] = Field(None, description="Razorpay refund ID")
    refunded_at: Optional[datetime] = Field(None, description="When refund was processed")
    paid_at: Optional[datetime] = Field(None, description="When payment was completed")

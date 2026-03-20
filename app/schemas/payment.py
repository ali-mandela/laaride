from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.enums.common import PaymentMethod, PaymentStatus
from app.models.base import PyObjectId


class InitiatePaymentRequest(BaseModel):
    """Schema for initiating a payment."""

    booking_id: str = Field(..., description="Booking ID to pay for")
    payment_method: PaymentMethod = Field(..., description="Payment method: online or cash")


class InitiatePaymentResponse(BaseModel):
    """Schema for initiate payment response."""

    payment_id: str
    razorpay_order_id: Optional[str] = None
    amount: float
    currency: str
    payment_method: PaymentMethod
    key_id: Optional[str] = None  # Razorpay key_id for frontend SDK


class VerifyPaymentRequest(BaseModel):
    """Schema for verifying a Razorpay payment."""

    payment_id: str = Field(..., description="PaymentDocument ID")
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="Razorpay signature")


class VerifyPaymentResponse(BaseModel):
    """Schema for payment verification response."""

    success: bool
    payment_status: PaymentStatus
    booking_id: str
    message: str


class CashPaymentConfirmRequest(BaseModel):
    """Schema for driver confirming cash received."""

    booking_id: str = Field(..., description="Booking ID")


class RefundRequest(BaseModel):
    """Schema for admin-initiated refund."""

    payment_id: str = Field(..., description="PaymentDocument ID")
    reason: str = Field(..., description="Reason for refund")


class PaymentResponse(BaseModel):
    """Full payment API response."""

    id: Optional[PyObjectId] = Field(None, alias="_id")
    booking_id: str
    passenger_id: str
    amount: float
    currency: str = "INR"
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    failure_reason: Optional[str] = None
    refund_id: Optional[str] = None
    refunded_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}

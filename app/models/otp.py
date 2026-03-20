from datetime import datetime, timedelta
from pydantic import Field
from app.models.base import MongoBaseDocument


class OTPDocument(MongoBaseDocument):
    """MongoDB document model for OTPs."""

    phone: str = Field(..., description="Phone number associated with the OTP")
    otp_hash: str = Field(..., description="Hashed OTP value")
    is_used: bool = Field(default=False, description="Whether the OTP has been used")
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=10),
        description="Expiration time of the OTP",
    )

    model_config = {
        "collection": "otps",
    }

import random
import string
from datetime import datetime, timedelta
from typing import Any, Tuple

from app.core.config import settings
from app.core.database import USERS_COLLECTION, OTP_COLLECTION
from app.core.exceptions import AuthenticationError, ValidationError, NotFoundError
from app.core.logging import get_logger
from app.services.sms_service import send_otp_sms
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_otp,
    verify_otp as security_verify_otp,
    verify_token,
)
from app.models.otp import OTPDocument
from app.models.user import UserDocument
from app.schemas.auth import (
    SendOTPResponse,
    VerifyOTPResponse,
    RefreshTokenResponse,
)
from app.schemas.user import UserResponse
from app.enums.common import UserRole

logger = get_logger("laaride.auth")


def _mask_phone(phone: str) -> str:
    """Mask phone for logging: +91****1234"""
    if len(phone) > 6:
        return phone[:3] + "****" + phone[-4:]
    return "****"


async def send_otp(phone: str, db: Any) -> SendOTPResponse:
    """Generate and send an OTP to the specified phone number."""
    # Invalidate previous OTPs for this phone
    await db[OTP_COLLECTION].update_many(
        {"phone": phone, "is_used": False},
        {"$set": {"is_used": True}}
    )

    # Generate 6-digit numeric OTP
    otp_code = "".join(random.choices(string.digits, k=6))
    otp_hash = hash_otp(otp_code)

    # Create and store OTP document
    otp_doc = OTPDocument(
        phone=phone,
        otp_hash=otp_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    await db[OTP_COLLECTION].insert_one(otp_doc.model_dump(by_alias=True, exclude_none=True))

    # Attempt SMS delivery via Fast2SMS
    sms_delivered = send_otp_sms(phone, otp_code)
    logger.info("otp_generated", phone=_mask_phone(phone), sms_delivered=sms_delivered)

    message = "OTP sent" if sms_delivered else "OTP generated (SMS unavailable in this environment)"
    return SendOTPResponse(
        message=message,
        otp=otp_code if settings.IS_DEVELOPMENT else None
    )


async def verify_otp(phone: str, otp: str, db: Any) -> VerifyOTPResponse:
    """Verify the provided OTP and return authentication tokens."""
    # Find latest unused non-expired OTP for phone
    otp_data = await db[OTP_COLLECTION].find_one(
        {
            "phone": phone,
            "is_used": False,
            "expires_at": {"$gt": datetime.utcnow()}
        },
        sort=[("created_at", -1)]
    )

    if not otp_data:
        logger.warning("otp_verification_failed", phone=_mask_phone(phone), reason="expired_or_not_found")
        raise ValidationError(message="OTP expired or not found", code="OTP_EXPIRED")

    if not security_verify_otp(otp, otp_data["otp_hash"]):
        logger.warning("otp_verification_failed", phone=_mask_phone(phone), reason="invalid_otp")
        raise ValidationError(message="Invalid OTP", code="INVALID_OTP")

    # Mark OTP as used
    await db[OTP_COLLECTION].update_one(
        {"_id": otp_data["_id"]},
        {"$set": {"is_used": True}}
    )

    # Find or create user
    user_data = await db[USERS_COLLECTION].find_one({"phone": phone})
    is_new_user = False

    if not user_data:
        is_new_user = True
        new_user = UserDocument(
            phone=phone,
            name="New User",
            role=UserRole.PASSENGER
        )
        result = await db[USERS_COLLECTION].insert_one(new_user.model_dump(by_alias=True, exclude_none=True))
        user_data = await db[USERS_COLLECTION].find_one({"_id": result.inserted_id})

    user = UserDocument(**user_data)

    # Generate tokens
    user_id = str(user.id)
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    logger.info("login_success", user_id=user_id, is_new_user=is_new_user, phone=_mask_phone(phone))

    return VerifyOTPResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(**user.model_dump()),
        is_new_user=is_new_user
    )


async def refresh_access_token(token: str, db: Any) -> RefreshTokenResponse:
    """Refresh an access token using a valid refresh token."""
    payload = verify_token(token)

    if payload.get("type") != "refresh":
        raise AuthenticationError(message="Invalid token type", code="INVALID_TOKEN_TYPE")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError(message="Invalid refresh token payload", code="INVALID_TOKEN")

    # Check if user still exists/is active
    user_data = await db[USERS_COLLECTION].find_one({"_id": user_id})
    if not user_data or not user_data.get("is_active", True):
        raise AuthenticationError(message="User not found or inactive", code="USER_INACTIVE")

    new_access_token = create_access_token(data={"sub": user_id})

    return RefreshTokenResponse(
        access_token=new_access_token
    )

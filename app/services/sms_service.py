"""Fast2SMS integration for OTP delivery on Indian phone numbers."""
import re

import requests

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("laaride.sms")

_FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"
_TIMEOUT = 10  # seconds


def _extract_indian_number(phone: str) -> str | None:
    """Extract 10-digit number from E.164 Indian phone (+91XXXXXXXXXX)."""
    match = re.fullmatch(r"\+91(\d{10})", phone)
    return match.group(1) if match else None


def send_otp_sms(phone: str, otp: str) -> bool:
    """Send OTP via Fast2SMS. Returns True on success, False on failure.

    Falls back gracefully when FAST2SMS_API_KEY is not configured — in that
    case the OTP is still returned in the API response body (dev mode only).
    """
    if not settings.FAST2SMS_API_KEY:
        logger.warning("fast2sms_skipped", reason="FAST2SMS_API_KEY not configured")
        return False

    number = _extract_indian_number(phone)
    if not number:
        logger.warning("fast2sms_skipped", reason="non_indian_number", phone=phone[:3] + "****")
        return False

    try:
        response = requests.get(
            _FAST2SMS_URL,
            headers={"authorization": settings.FAST2SMS_API_KEY, "Accept": "application/json"},
            params={
                "variables_values": otp,
                "route": "otp",
                "numbers": number,
            },
            timeout=_TIMEOUT,
        )
        data = response.json()

        if response.ok and data.get("return") is True:
            logger.info("sms_sent", number=f"****{number[-4:]}")
            return True

        logger.error(
            "fast2sms_error",
            status_code=response.status_code,
            message=data.get("message", "unknown"),
        )
        return False

    except requests.Timeout:
        logger.error("fast2sms_timeout", number=f"****{number[-4:]}")
        return False
    except Exception as exc:
        logger.error("fast2sms_exception", error=str(exc))
        return False

"""Tests for Razorpay webhook signature validation."""

import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import payment_service
from app.enums.common import PaymentStatus


@pytest.mark.asyncio
async def test_webhook_signature_validation_success():
    """Test that valid webhook signatures are accepted."""
    # Test data
    webhook_secret = "test_webhook_secret_key"
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_123456789",
                    "order_id": "order_test_123",
                }
            }
        },
    }

    # Compute valid signature
    signature = hmac.new(
        webhook_secret.encode("utf-8"),
        json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Mock database
    db = {
        "payments": AsyncMock(),
        "bookings": AsyncMock(),
    }

    # Setup mocks
    db["payments"].find_one = AsyncMock(
        return_value={
            "_id": "payment_id_123",
            "booking_id": "booking_123",
            "payment_status": PaymentStatus.PAYMENT_INITIATED.value,
        }
    )
    db["bookings"].update_one = AsyncMock()

    # Patch settings
    with patch("app.services.payment_service.settings") as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = webhook_secret

        result = await payment_service.handle_razorpay_webhook(
            payload, signature, db
        )

        assert result["status"] == "processed"
        # Verify payment was updated
        assert db["payments"].find_one.called
        assert db["bookings"].update_one.called


@pytest.mark.asyncio
async def test_webhook_signature_validation_failure():
    """Test that invalid webhook signatures are rejected."""
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_123456789",
                    "order_id": "order_test_123",
                }
            }
        },
    }

    # Invalid signature
    invalid_signature = "invalid_signature_here"

    db = {
        "payments": AsyncMock(),
        "bookings": AsyncMock(),
    }

    with patch("app.services.payment_service.settings") as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret_key"

        result = await payment_service.handle_razorpay_webhook(
            payload, invalid_signature, db
        )

        # Should return invalid signature status
        assert result["status"] == "invalid_signature"
        # Should NOT update payment
        assert not db["payments"].find_one.called


@pytest.mark.asyncio
async def test_webhook_no_secret_configured():
    """Test webhook handling when secret is not configured."""
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_123456789",
                    "order_id": "order_test_123",
                }
            }
        },
    }

    db = {}

    with patch("app.services.payment_service.settings") as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = None

        result = await payment_service.handle_razorpay_webhook(
            payload, "any_signature", db
        )

        # Should be ignored if no secret
        assert result["status"] == "ignored"

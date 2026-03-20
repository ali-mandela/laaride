"""Payment service — Razorpay integration + cash payment management."""

import hashlib
import hmac
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId, errors

from app.core.config import settings
from app.core.database import BOOKINGS_COLLECTION, DRIVERS_COLLECTION, USERS_COLLECTION
from app.core.exceptions import (
    ExternalServiceError,
    NotFoundError,
    ValidationError,
    AuthorizationError,
)
from app.core.logging import get_logger
from app.enums.common import BookingStatus, PaymentMethod, PaymentStatus
from app.schemas.payment import (
    CashPaymentConfirmRequest,
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    PaymentResponse,
    RefundRequest,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.services import notification_service

PAYMENTS_COLLECTION = "payments"

logger = get_logger("laaride.payment")


# ── Helpers ────────────────────────────────────────────────────────────────


def _to_object_id(value: str, label: str = "ID") -> ObjectId:
    try:
        return ObjectId(value)
    except errors.InvalidId:
        raise ValidationError(message=f"Invalid {label} format", code="INVALID_ID")


def _ensure_razorpay_configured():
    """Raise if Razorpay keys are not configured."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ExternalServiceError(
            message="Online payments not configured",
            code="PAYMENTS_NOT_CONFIGURED",
        )


# ── Initiate Payment ──────────────────────────────────────────────────────


async def initiate_payment(
    passenger_id: str, data: InitiatePaymentRequest, db: Any
) -> InitiatePaymentResponse:
    """Create a payment for a confirmed booking."""
    booking_oid = _to_object_id(data.booking_id, "Booking ID")
    booking = await db[BOOKINGS_COLLECTION].find_one({"_id": booking_oid})

    if not booking:
        raise NotFoundError(message="Booking not found", code="BOOKING_NOT_FOUND")
    if booking["passenger_id"] != passenger_id:
        raise AuthorizationError(
            message="You can only pay for your own bookings", code="NOT_YOUR_BOOKING"
        )
    if booking["status"] != BookingStatus.CONFIRMED.value:
        raise ValidationError(
            message="Can only pay for confirmed bookings", code="BOOKING_NOT_CONFIRMED"
        )
    if booking.get("payment_status") == PaymentStatus.PAID.value:
        raise ValidationError(message="Booking already paid", code="ALREADY_PAID")

    fare = booking.get("fare")
    if not fare or fare <= 0:
        raise ValidationError(
            message="Fare not set on this booking", code="FARE_NOT_SET"
        )

    now = datetime.utcnow()

    if data.payment_method == PaymentMethod.CASH:
        # Cash payment — no Razorpay
        payment_doc = {
            "booking_id": data.booking_id,
            "passenger_id": passenger_id,
            "amount": fare,
            "currency": "INR",
            "payment_method": PaymentMethod.CASH.value,
            "payment_status": PaymentStatus.PENDING_CASH.value,
            "created_at": now,
            "updated_at": now,
        }
        result = await db[PAYMENTS_COLLECTION].insert_one(payment_doc)
        payment_id = str(result.inserted_id)

        # Update booking
        await db[BOOKINGS_COLLECTION].update_one(
            {"_id": booking_oid},
            {
                "$set": {
                    "payment_status": PaymentStatus.PENDING_CASH.value,
                    "payment_method": PaymentMethod.CASH.value,
                    "payment_id": payment_id,
                    "updated_at": now,
                }
            },
        )

        logger.info("cash_payment_initiated", booking_id=data.booking_id, amount=fare)

        return InitiatePaymentResponse(
            payment_id=payment_id,
            razorpay_order_id=None,
            amount=fare,
            currency="INR",
            payment_method=PaymentMethod.CASH,
            key_id=None,
        )

    # Online payment — Razorpay
    _ensure_razorpay_configured()

    try:
        import razorpay

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        order = client.order.create(
            {
                "amount": int(fare * 100),  # paise
                "currency": "INR",
                "receipt": f"booking_{data.booking_id}",
                "notes": {"booking_id": data.booking_id, "passenger_id": passenger_id},
            }
        )
    except ImportError:
        raise ExternalServiceError(
            message="Razorpay SDK not installed", code="RAZORPAY_SDK_MISSING"
        )
    except Exception as e:
        logger.error("razorpay_order_failed", error=str(e))
        raise ExternalServiceError(
            message="Failed to create payment order", code="RAZORPAY_ORDER_FAILED"
        )

    razorpay_order_id = order["id"]

    payment_doc = {
        "booking_id": data.booking_id,
        "passenger_id": passenger_id,
        "amount": fare,
        "currency": "INR",
        "payment_method": PaymentMethod.ONLINE.value,
        "payment_status": PaymentStatus.PAYMENT_INITIATED.value,
        "razorpay_order_id": razorpay_order_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db[PAYMENTS_COLLECTION].insert_one(payment_doc)
    payment_id = str(result.inserted_id)

    await db[BOOKINGS_COLLECTION].update_one(
        {"_id": booking_oid},
        {
            "$set": {
                "payment_status": PaymentStatus.PAYMENT_INITIATED.value,
                "payment_method": PaymentMethod.ONLINE.value,
                "payment_id": payment_id,
                "updated_at": now,
            }
        },
    )

    logger.info(
        "online_payment_initiated",
        booking_id=data.booking_id,
        amount=fare,
        razorpay_order_id=razorpay_order_id,
    )

    return InitiatePaymentResponse(
        payment_id=payment_id,
        razorpay_order_id=razorpay_order_id,
        amount=fare,
        currency="INR",
        payment_method=PaymentMethod.ONLINE,
        key_id=settings.RAZORPAY_KEY_ID,
    )


# ── Verify Payment ────────────────────────────────────────────────────────


async def verify_payment(
    data: VerifyPaymentRequest, db: Any
) -> VerifyPaymentResponse:
    """Verify Razorpay payment signature and mark as paid."""
    _ensure_razorpay_configured()

    payment_oid = _to_object_id(data.payment_id, "Payment ID")
    payment = await db[PAYMENTS_COLLECTION].find_one({"_id": payment_oid})
    if not payment:
        raise NotFoundError(message="Payment not found", code="PAYMENT_NOT_FOUND")

    # Verify signature
    message = f"{data.razorpay_order_id}|{data.razorpay_payment_id}"
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    now = datetime.utcnow()

    if not hmac.compare_digest(expected_signature, data.razorpay_signature):
        # Signature mismatch
        await db[PAYMENTS_COLLECTION].update_one(
            {"_id": payment_oid},
            {
                "$set": {
                    "payment_status": PaymentStatus.FAILED.value,
                    "failure_reason": "Signature mismatch",
                    "updated_at": now,
                }
            },
        )
        logger.warning("payment_signature_mismatch", payment_id=data.payment_id)
        raise ValidationError(
            message="Payment verification failed — invalid signature",
            code="INVALID_SIGNATURE",
        )

    # Valid — mark as PAID
    await db[PAYMENTS_COLLECTION].update_one(
        {"_id": payment_oid},
        {
            "$set": {
                "payment_status": PaymentStatus.PAID.value,
                "razorpay_payment_id": data.razorpay_payment_id,
                "razorpay_signature": data.razorpay_signature,
                "paid_at": now,
                "updated_at": now,
            }
        },
    )

    booking_id = payment["booking_id"]
    booking_oid = _to_object_id(booking_id, "Booking ID")
    await db[BOOKINGS_COLLECTION].update_one(
        {"_id": booking_oid},
        {"$set": {"payment_status": PaymentStatus.PAID.value, "updated_at": now}},
    )

    # Notify driver
    try:
        booking = await db[BOOKINGS_COLLECTION].find_one({"_id": booking_oid})
        if booking and booking.get("driver_id"):
            driver = await db[DRIVERS_COLLECTION].find_one(
                {"_id": _to_object_id(booking["driver_id"], "D")}
            )
            if driver:
                await notification_service.send_push_notification(
                    driver["user_id"],
                    "Payment Received",
                    f"Passenger has completed payment of ₹{payment['amount']} for booking",
                    db,
                    data={"booking_id": booking_id},
                    notification_type="payment",
                    reference_id=booking_id,
                )
    except Exception as e:
        logger.error("payment_notification_error", error=str(e))

    logger.info("payment_verified", payment_id=data.payment_id, booking_id=booking_id)

    return VerifyPaymentResponse(
        success=True,
        payment_status=PaymentStatus.PAID,
        booking_id=booking_id,
        message="Payment verified successfully",
    )


# ── Cash Payment Confirm ──────────────────────────────────────────────────


async def confirm_cash_payment(
    driver_id: str, data: CashPaymentConfirmRequest, db: Any
) -> PaymentResponse:
    """Driver confirms cash received for a booking."""
    booking_oid = _to_object_id(data.booking_id, "Booking ID")
    booking = await db[BOOKINGS_COLLECTION].find_one({"_id": booking_oid})

    if not booking:
        raise NotFoundError(message="Booking not found", code="BOOKING_NOT_FOUND")

    # Verify driver owns this booking
    if booking.get("driver_id") != driver_id:
        raise AuthorizationError(
            message="You can only confirm cash for your own bookings",
            code="NOT_YOUR_BOOKING",
        )

    if booking.get("payment_method") != PaymentMethod.CASH.value:
        raise ValidationError(
            message="This booking is not a cash payment", code="NOT_CASH_PAYMENT"
        )
    if booking.get("payment_status") != PaymentStatus.PENDING_CASH.value:
        raise ValidationError(
            message="Cash payment not in pending state", code="INVALID_PAYMENT_STATE"
        )

    now = datetime.utcnow()
    payment_id = booking.get("payment_id")

    if payment_id:
        payment_oid = _to_object_id(payment_id, "Payment ID")
        await db[PAYMENTS_COLLECTION].update_one(
            {"_id": payment_oid},
            {
                "$set": {
                    "payment_status": PaymentStatus.PAID.value,
                    "paid_at": now,
                    "updated_at": now,
                }
            },
        )

    await db[BOOKINGS_COLLECTION].update_one(
        {"_id": booking_oid},
        {"$set": {"payment_status": PaymentStatus.PAID.value, "updated_at": now}},
    )

    # Notify passenger
    try:
        await notification_service.send_push_notification(
            booking["passenger_id"],
            "Cash Payment Confirmed",
            "Driver has confirmed receipt of cash payment",
            db,
            data={"booking_id": data.booking_id},
            notification_type="payment",
            reference_id=data.booking_id,
        )
    except Exception as e:
        logger.error("cash_notify_error", error=str(e))

    logger.info("cash_payment_confirmed", booking_id=data.booking_id)

    if payment_id:
        updated = await db[PAYMENTS_COLLECTION].find_one(
            {"_id": _to_object_id(payment_id, "Payment ID")}
        )
        return PaymentResponse(**updated)

    # Shouldn't happen, but fallback
    return PaymentResponse(
        booking_id=data.booking_id,
        passenger_id=booking["passenger_id"],
        amount=booking.get("fare", 0),
        payment_method=PaymentMethod.CASH,
        payment_status=PaymentStatus.PAID,
        paid_at=now,
        created_at=now,
        updated_at=now,
    )


# ── Get Payment By Booking ────────────────────────────────────────────────


async def get_payment_by_booking(
    booking_id: str, requester_id: str, requester_role: str, db: Any
) -> PaymentResponse:
    """Get payment for a booking. Role-based access control."""
    payment = await db[PAYMENTS_COLLECTION].find_one({"booking_id": booking_id})
    if not payment:
        raise NotFoundError(message="Payment not found", code="PAYMENT_NOT_FOUND")

    # Access control
    if requester_role == "admin":
        pass  # admin sees all
    elif requester_role == "driver":
        booking = await db[BOOKINGS_COLLECTION].find_one(
            {"_id": _to_object_id(booking_id, "Booking ID")}
        )
        if not booking:
            raise NotFoundError(message="Booking not found", code="BOOKING_NOT_FOUND")
        driver = await db[DRIVERS_COLLECTION].find_one({"user_id": requester_id})
        if not driver or str(driver["_id"]) != booking.get("driver_id"):
            raise AuthorizationError(message="Access denied", code="FORBIDDEN")
    else:
        # passenger
        if payment["passenger_id"] != requester_id:
            raise AuthorizationError(message="Access denied", code="FORBIDDEN")

    return PaymentResponse(**payment)


# ── Refund ─────────────────────────────────────────────────────────────────


async def initiate_refund(
    admin_id: str, data: RefundRequest, db: Any
) -> PaymentResponse:
    """Admin-only: refund a paid payment."""
    payment_oid = _to_object_id(data.payment_id, "Payment ID")
    payment = await db[PAYMENTS_COLLECTION].find_one({"_id": payment_oid})

    if not payment:
        raise NotFoundError(message="Payment not found", code="PAYMENT_NOT_FOUND")
    if payment["payment_status"] != PaymentStatus.PAID.value:
        raise ValidationError(
            message="Can only refund paid payments", code="NOT_PAID"
        )

    now = datetime.utcnow()
    refund_id = None

    if payment["payment_method"] == PaymentMethod.ONLINE.value:
        _ensure_razorpay_configured()
        try:
            import razorpay

            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            refund = client.payment.refund(
                payment["razorpay_payment_id"],
                {"amount": int(payment["amount"] * 100), "notes": {"reason": data.reason}},
            )
            refund_id = refund.get("id")
        except ImportError:
            raise ExternalServiceError(
                message="Razorpay SDK not installed", code="RAZORPAY_SDK_MISSING"
            )
        except Exception as e:
            logger.error("razorpay_refund_failed", error=str(e))
            raise ExternalServiceError(
                message="Refund request failed", code="REFUND_FAILED"
            )

    await db[PAYMENTS_COLLECTION].update_one(
        {"_id": payment_oid},
        {
            "$set": {
                "payment_status": PaymentStatus.REFUNDED.value,
                "refund_id": refund_id,
                "refunded_at": now,
                "failure_reason": data.reason,
                "updated_at": now,
            }
        },
    )

    booking_oid = _to_object_id(payment["booking_id"], "Booking ID")
    await db[BOOKINGS_COLLECTION].update_one(
        {"_id": booking_oid},
        {"$set": {"payment_status": PaymentStatus.REFUNDED.value, "updated_at": now}},
    )

    # Notify passenger
    try:
        await notification_service.send_push_notification(
            payment["passenger_id"],
            "Refund Initiated",
            "Your refund has been initiated and will reflect in 5-7 business days",
            db,
            data={"payment_id": data.payment_id},
            notification_type="payment",
            reference_id=data.payment_id,
        )
    except Exception as e:
        logger.error("refund_notify_error", error=str(e))

    logger.info(
        "refund_initiated", payment_id=data.payment_id, refund_id=refund_id
    )

    updated = await db[PAYMENTS_COLLECTION].find_one({"_id": payment_oid})
    return PaymentResponse(**updated)


# ── Payment Stats ──────────────────────────────────────────────────────────


async def get_payment_stats(db: Any) -> dict:
    """Admin: payment statistics — total collected, refunded, by method, today's."""
    from datetime import date

    today_start = datetime.combine(date.today(), datetime.min.time())

    # Aggregations
    pipeline_total = [
        {"$match": {"payment_status": PaymentStatus.PAID.value}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    pipeline_refunded = [
        {"$match": {"payment_status": PaymentStatus.REFUNDED.value}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    pipeline_by_method = [
        {"$match": {"payment_status": PaymentStatus.PAID.value}},
        {
            "$group": {
                "_id": "$payment_method",
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }
        },
    ]
    pipeline_today = [
        {
            "$match": {
                "payment_status": PaymentStatus.PAID.value,
                "paid_at": {"$gte": today_start},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]

    total_result = await db[PAYMENTS_COLLECTION].aggregate(pipeline_total).to_list(1)
    refund_result = await db[PAYMENTS_COLLECTION].aggregate(pipeline_refunded).to_list(1)
    method_result = await db[PAYMENTS_COLLECTION].aggregate(pipeline_by_method).to_list(10)
    today_result = await db[PAYMENTS_COLLECTION].aggregate(pipeline_today).to_list(1)

    return {
        "total_collected": total_result[0]["total"] if total_result else 0,
        "total_paid_count": total_result[0]["count"] if total_result else 0,
        "total_refunded": refund_result[0]["total"] if refund_result else 0,
        "total_refund_count": refund_result[0]["count"] if refund_result else 0,
        "by_method": {
            item["_id"]: {"total": item["total"], "count": item["count"]}
            for item in method_result
        },
        "today_collection": today_result[0]["total"] if today_result else 0,
        "today_count": today_result[0]["count"] if today_result else 0,
    }


# ── Webhook Handler ───────────────────────────────────────────────────────


async def handle_razorpay_webhook(
    payload: dict, signature: str, db: Any
) -> dict:
    """Handle incoming Razorpay webhook. Verify signature, process events."""
    import json

    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.warning("webhook_secret_not_configured")
        return {"status": "ignored"}

    # Verify webhook signature
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning("webhook_signature_invalid")
        return {"status": "invalid_signature"}

    event = payload.get("event", "")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")

    if not order_id:
        return {"status": "no_order_id"}

    now = datetime.utcnow()

    if event == "payment.captured":
        payment = await db[PAYMENTS_COLLECTION].find_one(
            {"razorpay_order_id": order_id}
        )
        if payment and payment["payment_status"] != PaymentStatus.PAID.value:
            await db[PAYMENTS_COLLECTION].update_one(
                {"_id": payment["_id"]},
                {
                    "$set": {
                        "payment_status": PaymentStatus.PAID.value,
                        "razorpay_payment_id": payment_entity.get("id"),
                        "paid_at": now,
                        "updated_at": now,
                    }
                },
            )
            booking_oid = _to_object_id(payment["booking_id"], "Booking ID")
            await db[BOOKINGS_COLLECTION].update_one(
                {"_id": booking_oid},
                {"$set": {"payment_status": PaymentStatus.PAID.value, "updated_at": now}},
            )
            logger.info("webhook_payment_captured", order_id=order_id)

    elif event == "payment.failed":
        payment = await db[PAYMENTS_COLLECTION].find_one(
            {"razorpay_order_id": order_id}
        )
        if payment and payment["payment_status"] != PaymentStatus.PAID.value:
            error_desc = payment_entity.get("error_description", "Payment failed")
            await db[PAYMENTS_COLLECTION].update_one(
                {"_id": payment["_id"]},
                {
                    "$set": {
                        "payment_status": PaymentStatus.FAILED.value,
                        "failure_reason": error_desc,
                        "updated_at": now,
                    }
                },
            )
            logger.info("webhook_payment_failed", order_id=order_id)

    elif event == "refund.processed":
        refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
        rpay_payment_id = refund_entity.get("payment_id")
        if rpay_payment_id:
            payment = await db[PAYMENTS_COLLECTION].find_one(
                {"razorpay_payment_id": rpay_payment_id}
            )
            if payment and payment["payment_status"] != PaymentStatus.REFUNDED.value:
                await db[PAYMENTS_COLLECTION].update_one(
                    {"_id": payment["_id"]},
                    {
                        "$set": {
                            "payment_status": PaymentStatus.REFUNDED.value,
                            "refund_id": refund_entity.get("id"),
                            "refunded_at": now,
                            "updated_at": now,
                        }
                    },
                )
                logger.info("webhook_refund_processed", payment_id=rpay_payment_id)

    return {"status": "processed"}

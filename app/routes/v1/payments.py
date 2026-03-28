from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status

from app.core.database import get_database
from app.core.security import get_current_user, get_current_driver, get_current_admin
from app.models.user import UserDocument
from app.schemas.payment import (
    CashPaymentConfirmRequest,
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    PaymentResponse,
    RefundRequest,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


# ── Passenger Endpoints ──────────────────────────────────────────────────


@router.post("/initiate", response_model=InitiatePaymentResponse)
async def initiate_payment(
    request: InitiatePaymentRequest,
    current_user: UserDocument = Depends(get_current_user),
    db: Any = Depends(get_database),
):
    """Initiate a payment (online or cash) for a confirmed booking."""
    return await payment_service.initiate_payment(str(current_user.id), request, db)


@router.post("/create-order", response_model=InitiatePaymentResponse)
async def create_order(
    request: InitiatePaymentRequest,
    current_user: UserDocument = Depends(get_current_user),
    db: Any = Depends(get_database),
):
    """Alias for /initiate — create a Razorpay order for a confirmed booking."""
    return await payment_service.initiate_payment(str(current_user.id), request, db)


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: UserDocument = Depends(get_current_user),
    db: Any = Depends(get_database),
):
    """Verify a Razorpay payment signature."""
    return await payment_service.verify_payment(request, db)


@router.get("/booking/{booking_id}", response_model=PaymentResponse)
async def get_payment_by_booking(
    booking_id: str,
    current_user: UserDocument = Depends(get_current_user),
    db: Any = Depends(get_database),
):
    """Get payment details for a specific booking."""
    return await payment_service.get_payment_by_booking(
        booking_id, str(current_user.id), current_user.role, db
    )


# ── Driver Endpoints ───────────────────────────────────────────────────────


@router.post("/cash-confirm", response_model=PaymentResponse)
async def confirm_cash_payment(
    request: CashPaymentConfirmRequest,
    current_driver: UserDocument = Depends(get_current_driver),
    db: Any = Depends(get_database),
):
    """Driver confirms receipt of cash payment."""
    return await payment_service.confirm_cash_payment(str(current_driver.id), request, db)


# ── Admin Endpoints ────────────────────────────────────────────────────────


@router.post("/refund", response_model=PaymentResponse)
async def initiate_refund(
    request: RefundRequest,
    current_admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin-initiated refund for a paid payment."""
    return await payment_service.initiate_refund(str(current_admin.id), request, db)


@router.get("/stats")
async def get_payment_stats(
    current_admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Get summarized payment statistics."""
    return await payment_service.get_payment_stats(db)


# ── Webhook Endpoint ──────────────────────────────────────────────────────


@router.post("/webhook/razorpay")
async def razorpay_webhook_handler(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Any = Depends(get_database),
):
    """
    Handle incoming Razorpay webhooks.
    Always returns 200 OK to Razorpay.
    """
    try:
        payload = await request.json()
        return await payment_service.handle_razorpay_webhook(
            payload, x_razorpay_signature, db
        )
    except Exception:
        # Standard webhook practice: return 200 even on error to stop retries if appropriate,
        # but Razorpay specifically retries on non-2xx. We log internal errors in service.
        return {"status": "error_parsed"}

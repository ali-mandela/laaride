"""Business logic for dispute creation, messaging, and resolution."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import BOOKINGS_COLLECTION
from app.core.exceptions import LaaRideException, NotFoundError
from app.models.dispute import DisputeDocument, DisputeMessage, DisputeStatus
from app.schemas.dispute import DisputeCreate, DisputeResolve, DisputeResponse

DISPUTES_COLLECTION = "disputes"
DISPUTE_MESSAGES_COLLECTION = "dispute_messages"


def _doc_to_response(doc: dict) -> DisputeResponse:
    return DisputeResponse(
        id=str(doc["_id"]),
        booking_id=str(doc["booking_id"]),
        dispute_type=doc["dispute_type"],
        description=doc["description"],
        status=doc["status"],
        complainant_name=doc.get("complainant_name", ""),
        resolution_note=doc.get("resolution_note"),
        refund_amount=doc.get("refund_amount"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def raise_dispute(
    db: AsyncIOMotorDatabase,
    user_id: str,
    data: DisputeCreate,
) -> DisputeResponse:
    """Raise a new dispute for a booking."""
    # Verify booking exists and belongs to user
    booking = await db[BOOKINGS_COLLECTION].find_one({"_id": data.booking_id})
    if not booking:
        raise NotFoundError(message="Booking not found", code="BOOKING_NOT_FOUND")

    # Caller must be the passenger or the driver
    is_passenger = booking.get("passenger_id") == user_id
    is_driver = booking.get("driver_id") == user_id
    if not is_passenger and not is_driver:
        raise LaaRideException(
            status_code=403,
            message="You are not a participant in this booking",
            code="FORBIDDEN",
        )

    # Check no open dispute already exists for this booking
    existing = await db[DISPUTES_COLLECTION].find_one(
        {"booking_id": data.booking_id, "status": {"$in": [DisputeStatus.OPEN.value, DisputeStatus.UNDER_REVIEW.value]}}
    )
    if existing:
        raise LaaRideException(
            status_code=409,
            message="An open dispute already exists for this booking",
            code="DUPLICATE_DISPUTE",
        )

    # Fetch complainant info
    user = await db["users"].find_one({"_id": user_id})
    complainant_name = (user or {}).get("name", "User")

    # Determine raised_against
    raised_against = booking.get("driver_id") if is_passenger else booking.get("passenger_id")
    booking_reference = str(booking.get("_id", data.booking_id))

    dispute = DisputeDocument(
        booking_id=data.booking_id,
        raised_by=user_id,
        raised_against=raised_against or user_id,
        dispute_type=data.dispute_type,
        description=data.description,
        status=DisputeStatus.OPEN,
        booking_reference=booking_reference,
        complainant_name=complainant_name,
    )
    result = await db[DISPUTES_COLLECTION].insert_one(
        dispute.model_dump(by_alias=True, exclude_none=True)
    )
    inserted = await db[DISPUTES_COLLECTION].find_one({"_id": result.inserted_id})
    return _doc_to_response(inserted)


async def get_user_disputes(
    db: AsyncIOMotorDatabase,
    user_id: str,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> list[DisputeResponse]:
    """List disputes raised by or against a user."""
    query: dict = {"$or": [{"raised_by": user_id}, {"raised_against": user_id}]}
    if status:
        query["status"] = status
    skip = (page - 1) * page_size
    cursor = (
        db[DISPUTES_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs = await cursor.to_list(page_size)
    return [_doc_to_response(d) for d in docs]


async def add_dispute_message(
    db: AsyncIOMotorDatabase,
    dispute_id: str,
    sender_id: str,
    sender_role: str,
    message: str,
) -> dict:
    """Add a message to the dispute thread."""
    dispute = await db[DISPUTES_COLLECTION].find_one({"_id": dispute_id})
    if not dispute:
        raise NotFoundError(message="Dispute not found", code="DISPUTE_NOT_FOUND")

    if dispute.get("status") in (DisputeStatus.RESOLVED.value, DisputeStatus.REJECTED.value):
        raise LaaRideException(
            status_code=400,
            message="Cannot add messages to a closed dispute",
            code="DISPUTE_CLOSED",
        )

    msg = DisputeMessage(
        dispute_id=dispute_id,
        sender_id=sender_id,
        sender_role=sender_role,
        message=message,
    )
    await db[DISPUTE_MESSAGES_COLLECTION].insert_one(
        msg.model_dump(by_alias=True, exclude_none=True)
    )

    # Move to UNDER_REVIEW when a message is added to an OPEN dispute
    if dispute.get("status") == DisputeStatus.OPEN.value:
        await db[DISPUTES_COLLECTION].update_one(
            {"_id": dispute_id},
            {"$set": {"status": DisputeStatus.UNDER_REVIEW.value, "updated_at": datetime.utcnow()}},
        )

    return {"status": "message_added", "dispute_id": dispute_id}


async def resolve_dispute(
    db: AsyncIOMotorDatabase,
    dispute_id: str,
    admin_id: str,
    data: DisputeResolve,
) -> DisputeResponse:
    """Admin resolves a dispute with optional refund."""
    dispute = await db[DISPUTES_COLLECTION].find_one({"_id": dispute_id})
    if not dispute:
        raise NotFoundError(message="Dispute not found", code="DISPUTE_NOT_FOUND")

    now = datetime.utcnow()
    update: dict = {
        "status": data.status.value,
        "resolution_note": data.resolution_note,
        "assigned_admin_id": admin_id,
        "resolved_at": now,
        "updated_at": now,
    }
    if data.refund_amount is not None and data.refund_amount > 0:
        update["refund_amount"] = data.refund_amount
        # Trigger refund via payment_service if booking has a payment reference
        booking = await db[BOOKINGS_COLLECTION].find_one({"_id": dispute.get("booking_id")})
        if booking and booking.get("payment_id"):
            from app.services import payment_service  # local import to avoid circular
            try:
                await payment_service.process_refund(
                    db,
                    payment_id=booking["payment_id"],
                    amount=data.refund_amount,
                    reason=data.resolution_note,
                )
            except Exception:
                pass  # Refund failure doesn't block dispute resolution

    await db[DISPUTES_COLLECTION].update_one({"_id": dispute_id}, {"$set": update})
    updated = await db[DISPUTES_COLLECTION].find_one({"_id": dispute_id})
    return _doc_to_response(updated)


async def get_pending_disputes(
    db: AsyncIOMotorDatabase,
    page: int = 1,
    page_size: int = 20,
) -> list[DisputeResponse]:
    """Admin: list open and under-review disputes, oldest first."""
    query = {"status": {"$in": [DisputeStatus.OPEN.value, DisputeStatus.UNDER_REVIEW.value]}}
    skip = (page - 1) * page_size
    cursor = (
        db[DISPUTES_COLLECTION]
        .find(query)
        .sort("created_at", 1)
        .skip(skip)
        .limit(page_size)
    )
    docs = await cursor.to_list(page_size)
    return [_doc_to_response(d) for d in docs]

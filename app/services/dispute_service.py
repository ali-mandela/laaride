"""Business logic for dispute creation, messaging, and resolution."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.dispute import DisputeCreate, DisputeResolve, DisputeResponse


async def raise_dispute(
    db: AsyncIOMotorDatabase,
    user_id: str,
    data: DisputeCreate,
) -> DisputeResponse:
    """Raise a new dispute for a completed or active booking.

    Validates that:
    - The booking belongs to the user raising the dispute.
    - No open dispute already exists for this booking.
    Notifies the admin team via push notification.
    """
    # TODO: Implement
    raise NotImplementedError


async def get_user_disputes(
    db: AsyncIOMotorDatabase,
    user_id: str,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> list[DisputeResponse]:
    """List disputes raised by or against a user."""
    # TODO: Implement
    raise NotImplementedError


async def add_dispute_message(
    db: AsyncIOMotorDatabase,
    dispute_id: str,
    sender_id: str,
    sender_role: str,
    message: str,
) -> dict:
    """Add a message to the dispute thread.

    All parties (passenger, driver, admin) can communicate here.
    """
    # TODO: Implement
    raise NotImplementedError


async def resolve_dispute(
    db: AsyncIOMotorDatabase,
    dispute_id: str,
    admin_id: str,
    data: DisputeResolve,
) -> DisputeResponse:
    """Admin resolves a dispute with optional refund amount.

    If refund_amount > 0, triggers refund via payment_service.
    Notifies passenger and driver of resolution.
    """
    # TODO: Implement
    # 1. Update dispute status and resolution note
    # 2. If refund: call payment_service.process_refund()
    # 3. Send notifications to both parties
    raise NotImplementedError


async def get_pending_disputes(
    db: AsyncIOMotorDatabase,
    page: int = 1,
    page_size: int = 20,
) -> list[DisputeResponse]:
    """Admin: list open and under-review disputes."""
    # TODO: Implement
    raise NotImplementedError

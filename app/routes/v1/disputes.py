"""API routes for dispute and complaint resolution."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import get_current_user, require_role
from app.enums.common import UserRole
from app.schemas.dispute import DisputeCreate, DisputeMessageCreate, DisputeResolve, DisputeResponse
from app.services import dispute_service

router = APIRouter(prefix="/disputes", tags=["Disputes"])


@router.post("/", response_model=DisputeResponse, status_code=201)
async def raise_dispute(
    data: DisputeCreate,
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Raise a dispute for a booking."""
    return await dispute_service.raise_dispute(db, str(current_user.id), data)


@router.get("/me", response_model=list[DisputeResponse])
async def my_disputes(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List disputes associated with the current user."""
    return await dispute_service.get_user_disputes(db, str(current_user.id), status, page)


@router.post("/{dispute_id}/messages")
async def add_message(
    dispute_id: str,
    data: DisputeMessageCreate,
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Post a message in a dispute thread."""
    from app.enums.common import UserRole
    role = current_user.role.value
    return await dispute_service.add_dispute_message(
        db, dispute_id, str(current_user.id), role, data.message
    )


@router.get("/admin/pending", response_model=list[DisputeResponse])
async def pending_disputes(
    page: int = Query(1, ge=1),
    current_user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Admin: view all open / under-review disputes."""
    return await dispute_service.get_pending_disputes(db, page)


@router.patch("/admin/{dispute_id}/resolve", response_model=DisputeResponse)
async def resolve_dispute(
    dispute_id: str,
    data: DisputeResolve,
    current_user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Admin: resolve a dispute with optional refund."""
    return await dispute_service.resolve_dispute(db, dispute_id, str(current_user.id), data)

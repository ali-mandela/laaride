"""API routes for driver earnings dashboard."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import get_current_user, require_role
from app.enums.common import UserRole
from app.schemas.earnings import EarningsResponse, EarningsSummary
from app.services import earnings_service

router = APIRouter(prefix="/earnings", tags=["Earnings"])


@router.get("/me", response_model=list[EarningsResponse])
async def my_earnings(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Driver's paginated earnings history."""
    return await earnings_service.get_driver_earnings(
        db, str(current_user.id), start_date, end_date, page, page_size
    )


@router.get("/me/summary", response_model=EarningsSummary)
async def my_earnings_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Aggregated earnings summary with daily and per-route breakdowns."""
    return await earnings_service.get_earnings_summary(
        db, str(current_user.id), start_date, end_date
    )


@router.get("/drivers/{driver_id}/summary", response_model=EarningsSummary)
async def driver_earnings_admin(
    driver_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Admin view of a specific driver's earnings summary."""
    return await earnings_service.get_earnings_summary(db, driver_id, start_date, end_date)

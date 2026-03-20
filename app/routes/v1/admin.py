"""Admin endpoints — dashboard, activity, revenue, and management APIs."""

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from app.core.database import get_database
from app.core.security import get_current_admin
from app.enums.common import UserRole
from app.models.user import UserDocument
from app.services import admin_service

router = APIRouter(tags=["Admin"])


@router.get("/dashboard", summary="Dashboard stats")
async def get_dashboard(
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Consolidated dashboard statistics: users, drivers, bookings, routes."""
    return await admin_service.get_dashboard_stats(db)


@router.get("/activity", summary="Recent activity")
async def get_activity(
    limit: int = Query(default=20, ge=1, le=100),
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Recent bookings with passenger/driver info."""
    return await admin_service.get_recent_activity(limit, db)


@router.get("/revenue", summary="Revenue summary")
async def get_revenue(
    start_date: date = Query(...),
    end_date: date = Query(...),
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Revenue from completed bookings, grouped by route and day."""
    return await admin_service.get_revenue_summary(start_date, end_date, db)


@router.get("/drivers/pending", summary="Pending driver approvals")
async def get_pending_drivers(
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """List drivers awaiting approval, with user and vehicle info."""
    return await admin_service.list_pending_driver_approvals(db)


@router.get("/users/search", summary="Search users")
async def search_users(
    q: str = Query(..., min_length=1),
    role: Optional[UserRole] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Search users by name or phone, optionally filter by role."""
    return await admin_service.search_users(q, skip, limit, db, role=role)

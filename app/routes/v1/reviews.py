"""API routes for driver reviews and ratings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import get_current_user
from app.schemas.review import ReviewCreate, ReviewResponse, DriverRatingSummary
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewResponse, status_code=201)
async def submit_review(
    data: ReviewCreate,
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Submit a rating and optional comment after a completed trip."""
    return await review_service.submit_review(db, str(current_user.id), data)


@router.get("/drivers/{driver_id}", response_model=list[ReviewResponse])
async def list_driver_reviews(
    driver_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get paginated reviews for a specific driver."""
    return await review_service.get_driver_reviews(db, driver_id, page, page_size)


@router.get("/drivers/{driver_id}/summary", response_model=DriverRatingSummary)
async def driver_rating_summary(
    driver_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get aggregate rating stats and breakdown for a driver."""
    return await review_service.get_driver_rating_summary(db, driver_id)

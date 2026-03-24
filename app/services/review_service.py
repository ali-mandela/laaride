"""Business logic for driver ratings and passenger reviews."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import LaaRideException, NotFoundError
from app.schemas.review import ReviewCreate, ReviewResponse, DriverRatingSummary


async def submit_review(
    db: AsyncIOMotorDatabase,
    passenger_id: str,
    data: ReviewCreate,
) -> ReviewResponse:
    """Submit a rating/review for a completed booking.

    Validates that:
    - The booking belongs to the passenger.
    - The booking is in COMPLETED status.
    - A review hasn't already been submitted for this booking.

    Updates the driver's aggregate rating atomically.
    """
    # TODO: Implement full logic
    # 1. Fetch booking, verify passenger_id matches and status == COMPLETED
    # 2. Check no existing review for booking_id
    # 3. Insert ReviewDocument
    # 4. Recalculate driver average rating via aggregation and update DriverDocument
    raise NotImplementedError("submit_review not yet implemented")


async def get_driver_reviews(
    db: AsyncIOMotorDatabase,
    driver_id: str,
    page: int = 1,
    page_size: int = 20,
) -> list[ReviewResponse]:
    """Paginated list of visible reviews for a driver."""
    # TODO: Implement
    raise NotImplementedError


async def get_driver_rating_summary(db: AsyncIOMotorDatabase, driver_id: str) -> DriverRatingSummary:
    """Aggregate rating stats for a driver.

    Uses MongoDB aggregation pipeline to compute average and breakdown.
    """
    # TODO: Implement aggregation pipeline
    # pipeline = [
    #     {"$match": {"driver_id": ObjectId(driver_id), "is_visible": True}},
    #     {"$group": {
    #         "_id": "$driver_id",
    #         "average_rating": {"$avg": "$rating"},
    #         "total_reviews": {"$sum": 1},
    #         "breakdown": {"$push": "$rating"},
    #     }},
    # ]
    raise NotImplementedError


async def flag_review(db: AsyncIOMotorDatabase, review_id: str, admin_id: str) -> None:
    """Flag a review for moderation (admin only)."""
    # TODO: Implement
    raise NotImplementedError

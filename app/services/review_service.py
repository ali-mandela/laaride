"""Business logic for driver ratings and passenger reviews."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import BOOKINGS_COLLECTION, DRIVERS_COLLECTION
from app.core.exceptions import LaaRideException, NotFoundError
from app.enums.common import BookingStatus
from app.models.review import ReviewDocument
from app.schemas.review import ReviewCreate, ReviewResponse, DriverRatingSummary

REVIEWS_COLLECTION = "reviews"


def _doc_to_response(doc: dict) -> ReviewResponse:
    return ReviewResponse(
        id=str(doc["_id"]),
        booking_id=str(doc["booking_id"]),
        passenger_id=str(doc["passenger_id"]),
        driver_id=str(doc["driver_id"]),
        rating=doc["rating"],
        comment=doc.get("comment"),
        passenger_name=doc.get("passenger_name", ""),
        created_at=doc["created_at"],
    )


async def submit_review(
    db: AsyncIOMotorDatabase,
    passenger_id: str,
    data: ReviewCreate,
) -> ReviewResponse:
    """Submit a rating/review for a completed booking."""
    # Verify booking ownership and completion status
    booking = await db[BOOKINGS_COLLECTION].find_one({"_id": data.booking_id})
    if not booking or booking.get("passenger_id") != passenger_id:
        raise NotFoundError(message="Booking not found", code="BOOKING_NOT_FOUND")

    if booking.get("status") != BookingStatus.COMPLETED.value:
        raise LaaRideException(
            status_code=400,
            message="Reviews can only be submitted for completed trips",
            code="BOOKING_NOT_COMPLETED",
        )

    driver_id = booking.get("driver_id")
    if not driver_id:
        raise LaaRideException(status_code=400, message="No driver assigned to booking", code="NO_DRIVER")

    # Prevent duplicate reviews per booking
    if await db[REVIEWS_COLLECTION].find_one({"booking_id": data.booking_id}):
        raise LaaRideException(
            status_code=409,
            message="Review already submitted for this booking",
            code="DUPLICATE_REVIEW",
        )

    # Denormalise passenger and driver names
    passenger = await db["users"].find_one({"_id": passenger_id})
    passenger_name = (passenger or {}).get("name", "Passenger")
    driver_doc = await db[DRIVERS_COLLECTION].find_one({"_id": driver_id})
    driver_name = (driver_doc or {}).get("name", "Driver")

    # Round to 0.5 increments
    rounded_rating = round(float(data.rating) * 2) / 2

    review = ReviewDocument(
        booking_id=data.booking_id,
        passenger_id=passenger_id,
        driver_id=driver_id,
        rating=rounded_rating,
        comment=data.comment,
        passenger_name=passenger_name,
        driver_name=driver_name,
    )
    result = await db[REVIEWS_COLLECTION].insert_one(
        review.model_dump(by_alias=True, exclude_none=True)
    )

    # Recalculate driver aggregate rating
    pipeline = [
        {"$match": {"driver_id": driver_id, "is_visible": True}},
        {"$group": {"_id": "$driver_id", "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    agg = await db[REVIEWS_COLLECTION].aggregate(pipeline).to_list(1)
    if agg:
        await db[DRIVERS_COLLECTION].update_one(
            {"_id": driver_id},
            {"$set": {"rating": round(agg[0]["avg"], 2), "total_trips": agg[0]["count"]}},
        )

    inserted = await db[REVIEWS_COLLECTION].find_one({"_id": result.inserted_id})
    return _doc_to_response(inserted)


async def get_driver_reviews(
    db: AsyncIOMotorDatabase,
    driver_id: str,
    page: int = 1,
    page_size: int = 20,
) -> list[ReviewResponse]:
    """Paginated list of visible reviews for a driver."""
    skip = (page - 1) * page_size
    cursor = (
        db[REVIEWS_COLLECTION]
        .find({"driver_id": driver_id, "is_visible": True})
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs = await cursor.to_list(page_size)
    return [_doc_to_response(d) for d in docs]


async def get_driver_rating_summary(db: AsyncIOMotorDatabase, driver_id: str) -> DriverRatingSummary:
    """Aggregate rating stats for a driver using MongoDB aggregation."""
    pipeline = [
        {"$match": {"driver_id": driver_id, "is_visible": True}},
        {
            "$group": {
                "_id": "$driver_id",
                "average_rating": {"$avg": "$rating"},
                "total_reviews": {"$sum": 1},
                "ratings": {"$push": "$rating"},
            }
        },
    ]
    agg = await db[REVIEWS_COLLECTION].aggregate(pipeline).to_list(1)

    if not agg:
        return DriverRatingSummary(
            driver_id=driver_id,
            average_rating=0.0,
            total_reviews=0,
            rating_breakdown={"5": 0, "4": 0, "3": 0, "2": 0, "1": 0},
        )

    row = agg[0]
    breakdown: dict[str, int] = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    for r in row["ratings"]:
        key = str(int(round(r)))
        if key in breakdown:
            breakdown[key] += 1

    return DriverRatingSummary(
        driver_id=driver_id,
        average_rating=round(row["average_rating"], 2),
        total_reviews=row["total_reviews"],
        rating_breakdown=breakdown,
    )


async def flag_review(db: AsyncIOMotorDatabase, review_id: str, admin_id: str) -> None:
    """Flag a review for moderation (admin only)."""
    result = await db[REVIEWS_COLLECTION].update_one(
        {"_id": review_id},
        {"$set": {"flagged": True, "is_visible": False}},
    )
    if result.matched_count == 0:
        raise NotFoundError(message="Review not found", code="REVIEW_NOT_FOUND")

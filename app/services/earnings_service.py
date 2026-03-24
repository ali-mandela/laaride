"""Business logic for driver earnings tracking."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.earnings import EarningsDocument, EarningsStatus
from app.schemas.earnings import EarningsResponse, EarningsSummary

PLATFORM_FEE_RATE = 0.10  # 10% platform commission
EARNINGS_COLLECTION = "earnings"


def _doc_to_response(doc: dict) -> EarningsResponse:
    return EarningsResponse(
        id=str(doc["_id"]),
        booking_id=str(doc["booking_id"]),
        route_name=doc.get("route_name"),
        gross_amount=doc["gross_amount"],
        platform_fee=doc["platform_fee"],
        net_amount=doc["net_amount"],
        payment_method=doc["payment_method"],
        status=doc["status"],
        trip_date=doc["trip_date"],
        passenger_count=doc.get("passenger_count", 1),
    )


def _date_filter(start_date: Optional[datetime], end_date: Optional[datetime]) -> dict:
    f: dict = {}
    if start_date:
        f.setdefault("trip_date", {})["$gte"] = start_date
    if end_date:
        f.setdefault("trip_date", {})["$lte"] = end_date
    return f


async def record_trip_earnings(
    db: AsyncIOMotorDatabase,
    driver_id: str,
    booking_id: str,
    gross_amount: float,
    payment_method: str,
    trip_date: datetime,
    route_id: Optional[str] = None,
    passenger_count: int = 1,
    route_name: Optional[str] = None,
) -> EarningsResponse:
    """Create an earnings record when a booking is marked COMPLETED."""
    platform_fee = round(gross_amount * PLATFORM_FEE_RATE, 2)
    net_amount = round(gross_amount - platform_fee, 2)

    doc = EarningsDocument(
        driver_id=driver_id,
        booking_id=booking_id,
        route_id=route_id,
        gross_amount=gross_amount,
        platform_fee=platform_fee,
        net_amount=net_amount,
        payment_method=payment_method,
        status=EarningsStatus.PENDING,
        trip_date=trip_date,
        route_name=route_name,
        passenger_count=passenger_count,
    )
    result = await db[EARNINGS_COLLECTION].insert_one(
        doc.model_dump(by_alias=True, exclude_none=True)
    )
    inserted = await db[EARNINGS_COLLECTION].find_one({"_id": result.inserted_id})
    return _doc_to_response(inserted)


async def get_driver_earnings(
    db: AsyncIOMotorDatabase,
    driver_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> list[EarningsResponse]:
    """Paginated earnings history for a driver with optional date range filter."""
    query: dict = {"driver_id": driver_id, **_date_filter(start_date, end_date)}
    skip = (page - 1) * page_size
    cursor = (
        db[EARNINGS_COLLECTION]
        .find(query)
        .sort("trip_date", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs = await cursor.to_list(page_size)
    return [_doc_to_response(d) for d in docs]


async def get_earnings_summary(
    db: AsyncIOMotorDatabase,
    driver_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> EarningsSummary:
    """Aggregate earnings summary with daily and per-route breakdowns."""
    date_filter = _date_filter(start_date, end_date)
    match = {"driver_id": driver_id, **date_filter}

    # Overall totals
    totals_pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": None,
                "total_gross": {"$sum": "$gross_amount"},
                "total_fee": {"$sum": "$platform_fee"},
                "total_net": {"$sum": "$net_amount"},
                "total_trips": {"$sum": 1},
                "min_date": {"$min": "$trip_date"},
                "max_date": {"$max": "$trip_date"},
            }
        },
    ]
    totals_agg = await db[EARNINGS_COLLECTION].aggregate(totals_pipeline).to_list(1)

    # By-day breakdown
    by_day_pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$trip_date"}},
                "net": {"$sum": "$net_amount"},
                "trips": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    by_day_docs = await db[EARNINGS_COLLECTION].aggregate(by_day_pipeline).to_list(365)
    by_day = [{"date": d["_id"], "net": d["net"], "trips": d["trips"]} for d in by_day_docs]

    # By-route breakdown
    by_route_pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$route_name",
                "net": {"$sum": "$net_amount"},
                "trips": {"$sum": 1},
            }
        },
        {"$sort": {"net": -1}},
    ]
    by_route_docs = await db[EARNINGS_COLLECTION].aggregate(by_route_pipeline).to_list(100)
    by_route = [
        {"route": d["_id"] or "Unknown", "net": d["net"], "trips": d["trips"]}
        for d in by_route_docs
    ]

    now = datetime.now(tz=timezone.utc)
    if totals_agg:
        row = totals_agg[0]
        return EarningsSummary(
            driver_id=driver_id,
            total_gross=round(row["total_gross"], 2),
            total_platform_fee=round(row["total_fee"], 2),
            total_net=round(row["total_net"], 2),
            total_trips=row["total_trips"],
            period_start=row["min_date"] or (start_date or now),
            period_end=row["max_date"] or (end_date or now),
            by_day=by_day,
            by_route=by_route,
        )

    return EarningsSummary(
        driver_id=driver_id,
        total_gross=0.0,
        total_platform_fee=0.0,
        total_net=0.0,
        total_trips=0,
        period_start=start_date or now,
        period_end=end_date or now,
        by_day=[],
        by_route=[],
    )


async def settle_earnings(
    db: AsyncIOMotorDatabase,
    driver_id: str,
    earnings_ids: list[str],
    admin_id: str,
) -> int:
    """Mark selected earnings as settled (admin action). Returns count updated."""
    result = await db[EARNINGS_COLLECTION].update_many(
        {"_id": {"$in": earnings_ids}, "driver_id": driver_id, "status": EarningsStatus.PENDING.value},
        {
            "$set": {
                "status": EarningsStatus.SETTLED.value,
                "settled_at": datetime.utcnow(),
            }
        },
    )
    return result.modified_count

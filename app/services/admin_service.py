"""Admin service — consolidated dashboard, activity, revenue, and management APIs."""

from datetime import date, datetime
from typing import Any, Optional

from bson import ObjectId

from app.core.database import (
    BOOKINGS_COLLECTION,
    DRIVERS_COLLECTION,
    ROUTES_COLLECTION,
    USERS_COLLECTION,
    VEHICLES_COLLECTION,
)
from app.enums.common import (
    AvailabilityStatus,
    BookingStatus,
    BookingType,
    DriverStatus,
    UserRole,
)


# ── Dashboard ──────────────────────────────────────────────────────────────


async def get_dashboard_stats(db: Any) -> dict:
    """Return consolidated dashboard statistics."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Users
    total_users = await db[USERS_COLLECTION].count_documents({})
    active_users = await db[USERS_COLLECTION].count_documents({"is_active": True})
    passengers = await db[USERS_COLLECTION].count_documents({"role": UserRole.PASSENGER.value})
    driver_users = await db[USERS_COLLECTION].count_documents({"role": UserRole.DRIVER.value})
    new_users_today = await db[USERS_COLLECTION].count_documents(
        {"created_at": {"$gte": today_start}}
    )

    # Drivers
    total_drivers = await db[DRIVERS_COLLECTION].count_documents({})
    pending_approval = await db[DRIVERS_COLLECTION].count_documents(
        {"status": DriverStatus.PENDING_APPROVAL.value}
    )
    approved_drivers = await db[DRIVERS_COLLECTION].count_documents(
        {"status": DriverStatus.APPROVED.value}
    )
    suspended_drivers = await db[DRIVERS_COLLECTION].count_documents(
        {"status": DriverStatus.SUSPENDED.value}
    )
    online_now = await db[DRIVERS_COLLECTION].count_documents(
        {"availability": AvailabilityStatus.ONLINE.value}
    )

    # Bookings
    total_bookings = await db[BOOKINGS_COLLECTION].count_documents({})
    today_bookings = await db[BOOKINGS_COLLECTION].count_documents(
        {"created_at": {"$gte": today_start}}
    )
    pending_bookings = await db[BOOKINGS_COLLECTION].count_documents(
        {"status": BookingStatus.PENDING.value}
    )
    confirmed_bookings = await db[BOOKINGS_COLLECTION].count_documents(
        {"status": BookingStatus.CONFIRMED.value}
    )
    completed_bookings = await db[BOOKINGS_COLLECTION].count_documents(
        {"status": BookingStatus.COMPLETED.value}
    )
    cancelled_bookings = await db[BOOKINGS_COLLECTION].count_documents(
        {"status": BookingStatus.CANCELLED.value}
    )
    fixed_route_bookings = await db[BOOKINGS_COLLECTION].count_documents(
        {"booking_type": BookingType.FIXED_ROUTE.value}
    )
    custom_trip_bookings = await db[BOOKINGS_COLLECTION].count_documents(
        {"booking_type": BookingType.CUSTOM_TRIP.value}
    )

    # Routes
    total_routes = await db[ROUTES_COLLECTION].count_documents({})
    active_routes = await db[ROUTES_COLLECTION].count_documents({"is_active": True})
    seasonal_routes = await db[ROUTES_COLLECTION].count_documents({"is_seasonal": True})

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "passengers": passengers,
            "drivers": driver_users,
            "new_today": new_users_today,
        },
        "drivers": {
            "total": total_drivers,
            "pending_approval": pending_approval,
            "approved": approved_drivers,
            "suspended": suspended_drivers,
            "online_now": online_now,
        },
        "bookings": {
            "total": total_bookings,
            "today": today_bookings,
            "pending": pending_bookings,
            "confirmed": confirmed_bookings,
            "completed": completed_bookings,
            "cancelled": cancelled_bookings,
            "fixed_route": fixed_route_bookings,
            "custom_trip": custom_trip_bookings,
        },
        "routes": {
            "total": total_routes,
            "active": active_routes,
            "seasonal": seasonal_routes,
        },
    }


# ── Recent Activity ────────────────────────────────────────────────────────


async def get_recent_activity(limit: int, db: Any) -> list[dict]:
    """Last N bookings with passenger and driver info joined via aggregation."""
    pipeline = [
        {"$sort": {"created_at": -1}},
        {"$limit": limit},
        {
            "$addFields": {
                "passenger_oid": {"$toObjectId": "$passenger_id"},
            }
        },
        {
            "$lookup": {
                "from": USERS_COLLECTION,
                "localField": "passenger_oid",
                "foreignField": "_id",
                "as": "passenger_info",
            }
        },
        {"$unwind": {"path": "$passenger_info", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": {"$toString": "$_id"},
                "booking_type": 1,
                "status": 1,
                "fare": 1,
                "pickup_location": 1,
                "drop_location": 1,
                "scheduled_at": 1,
                "created_at": 1,
                "seats_booked": 1,
                "total_passengers": 1,
                "passenger_name": {"$ifNull": ["$passenger_info.name", "$passenger_name"]},
                "passenger_phone": {"$ifNull": ["$passenger_info.phone", "$passenger_phone"]},
                "driver_id": 1,
                "route_id": 1,
            }
        },
    ]
    result = await db[BOOKINGS_COLLECTION].aggregate(pipeline).to_list(length=limit)
    return result


# ── Revenue Summary ────────────────────────────────────────────────────────


async def get_revenue_summary(start_date: date, end_date: date, db: Any) -> dict:
    """Revenue from COMPLETED bookings in a date range, grouped by route and day."""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    base_match = {
        "status": BookingStatus.COMPLETED.value,
        "completed_at": {"$gte": start_dt, "$lte": end_dt},
        "fare": {"$ne": None},
    }

    # Total revenue
    total_pipeline = [
        {"$match": base_match},
        {"$group": {"_id": None, "total": {"$sum": "$fare"}, "count": {"$sum": 1}}},
    ]
    total_result = await db[BOOKINGS_COLLECTION].aggregate(total_pipeline).to_list(length=1)
    total_revenue = total_result[0]["total"] if total_result else 0
    total_count = total_result[0]["count"] if total_result else 0

    # Grouped by route
    route_pipeline = [
        {"$match": base_match},
        {
            "$group": {
                "_id": "$route_id",
                "revenue": {"$sum": "$fare"},
                "bookings": {"$sum": 1},
            }
        },
        {"$sort": {"revenue": -1}},
    ]
    by_route = await db[BOOKINGS_COLLECTION].aggregate(route_pipeline).to_list(length=100)

    # Grouped by day
    day_pipeline = [
        {"$match": base_match},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$completed_at"}
                },
                "revenue": {"$sum": "$fare"},
                "bookings": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    by_day = await db[BOOKINGS_COLLECTION].aggregate(day_pipeline).to_list(length=365)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_revenue": total_revenue,
        "total_completed_bookings": total_count,
        "by_route": by_route,
        "by_day": by_day,
    }


# ── Pending Driver Approvals ──────────────────────────────────────────────


async def list_pending_driver_approvals(db: Any) -> list[dict]:
    """Drivers with PENDING_APPROVAL status, joined with user and vehicle info."""
    pipeline = [
        {"$match": {"status": DriverStatus.PENDING_APPROVAL.value}},
        {"$sort": {"created_at": -1}},
        {
            "$addFields": {
                "user_oid": {"$toObjectId": "$user_id"},
            }
        },
        {
            "$lookup": {
                "from": USERS_COLLECTION,
                "localField": "user_oid",
                "foreignField": "_id",
                "as": "user_info",
            }
        },
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": VEHICLES_COLLECTION,
                "let": {"did": {"$toString": "$_id"}},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$driver_id", "$$did"]}}},
                ],
                "as": "vehicles",
            }
        },
        {
            "$project": {
                "_id": {"$toString": "$_id"},
                "user_id": 1,
                "license_number": 1,
                "license_expiry": 1,
                "status": 1,
                "created_at": 1,
                "user_name": "$user_info.name",
                "user_phone": "$user_info.phone",
                "user_email": "$user_info.email",
                "vehicles": {
                    "$map": {
                        "input": "$vehicles",
                        "as": "v",
                        "in": {
                            "vehicle_id": {"$toString": "$$v._id"},
                            "vehicle_type": "$$v.vehicle_type",
                            "make": "$$v.make",
                            "model": "$$v.model",
                            "registration_number": "$$v.registration_number",
                        },
                    }
                },
            }
        },
    ]
    return await db[DRIVERS_COLLECTION].aggregate(pipeline).to_list(length=100)


# ── User Search ────────────────────────────────────────────────────────────


async def search_users(
    query: str,
    skip: int,
    limit: int,
    db: Any,
    role: Optional[UserRole] = None,
) -> dict:
    """Search users by name or phone (case-insensitive), optionally filter by role."""
    search_filter: dict = {
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"phone": {"$regex": query, "$options": "i"}},
        ]
    }
    if role:
        search_filter["role"] = role.value

    total = await db[USERS_COLLECTION].count_documents(search_filter)
    cursor = (
        db[USERS_COLLECTION]
        .find(search_filter)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    users = []
    async for doc in cursor:
        users.append(
            {
                "_id": str(doc["_id"]),
                "name": doc.get("name"),
                "phone": doc.get("phone"),
                "email": doc.get("email"),
                "role": doc.get("role"),
                "is_active": doc.get("is_active"),
                "created_at": doc.get("created_at"),
            }
        )
    return {"data": users, "total": total, "skip": skip, "limit": limit}

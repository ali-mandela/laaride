"""Route service — all business logic for the routes module."""

import re
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId, errors
from fastapi import HTTPException, UploadFile, status

from app.core.database import BOOKINGS_COLLECTION, ROUTES_COLLECTION
from app.schemas.route import RouteCreate, RouteResponse, RouteSearchParams, RouteUpdate
from app.services.osrm_service import get_route_info
from app.services.storage_service import get_storage_service


def _to_object_id(value: str, label: str = "ID") -> ObjectId:
    try:
        return ObjectId(value)
    except errors.InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label} format",
        )


def _generate_slug(origin_name: str, destination_name: str) -> str:
    """Generate a URL-friendly slug from origin and destination names."""
    raw = f"{origin_name}-{destination_name}".lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug


async def _ensure_unique_slug(slug: str, db: Any, exclude_id: Optional[ObjectId] = None) -> str:
    """If slug already exists, append a numeric suffix to make it unique."""
    query: dict = {"slug": slug}
    if exclude_id:
        query["_id"] = {"$ne": exclude_id}
    existing = await db[ROUTES_COLLECTION].find_one(query)
    if not existing:
        return slug

    counter = 2
    while True:
        candidate = f"{slug}-{counter}"
        query["slug"] = candidate
        if not await db[ROUTES_COLLECTION].find_one(query):
            return candidate
        counter += 1


# ── CRUD ───────────────────────────────────────────────────────────────────


async def create_route(data: RouteCreate, db: Any) -> RouteResponse:
    """Create a new route with auto-generated slug."""
    origin_name = data.origin.get("name", "")
    dest_name = data.destination.get("name", "")
    base_slug = _generate_slug(origin_name, dest_name)
    slug = await _ensure_unique_slug(base_slug, db)

    # Sort waypoints by order if provided
    waypoints = sorted(data.waypoints, key=lambda w: w.get("order", 0)) if data.waypoints else []

    # Auto-calculate distance and duration via OSRM if coords are available
    distance_km = data.distance_km
    duration_mins = data.estimated_duration_mins
    origin = data.origin
    destination = data.destination
    if (
        origin.get("lat") and origin.get("lng")
        and destination.get("lat") and destination.get("lng")
    ):
        osrm = get_route_info(
            origin_lat=origin["lat"], origin_lng=origin["lng"],
            dest_lat=destination["lat"], dest_lng=destination["lng"],
        )
        if osrm:
            # Only override if not explicitly provided by the admin
            if distance_km is None:
                distance_km = osrm.distance_km
            if duration_mins is None:
                duration_mins = osrm.duration_minutes

    now = datetime.utcnow()
    route_doc = {
        "name": data.name,
        "slug": slug,
        "origin": origin,
        "destination": destination,
        "distance_km": distance_km,
        "estimated_duration_mins": duration_mins,
        "base_fare": data.base_fare,
        "is_active": True,
        "waypoints": waypoints,
        "tags": data.tags,
        "is_seasonal": data.is_seasonal,
        "season_start_month": data.season_start_month,
        "season_end_month": data.season_end_month,
        "thumbnail_url": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await db[ROUTES_COLLECTION].insert_one(route_doc)
    route_doc["_id"] = result.inserted_id
    return RouteResponse(**route_doc)


async def get_route_by_id(route_id: str, db: Any) -> RouteResponse:
    """Fetch a route by its document _id."""
    obj_id = _to_object_id(route_id, "Route ID")
    route = await db[ROUTES_COLLECTION].find_one({"_id": obj_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Route not found"
        )
    return RouteResponse(**route)


async def get_route_by_slug(slug: str, db: Any) -> RouteResponse:
    """Fetch a route by its slug."""
    route = await db[ROUTES_COLLECTION].find_one({"slug": slug})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Route not found"
        )
    return RouteResponse(**route)


async def list_routes(
    params: RouteSearchParams,
    skip: int,
    limit: int,
    db: Any,
    admin: bool = False,
) -> dict:
    """List routes with search/filter, paginated."""
    query: dict = {}

    # Non-admins only see active routes
    if not admin:
        query["is_active"] = True
    elif params.is_active is not None:
        query["is_active"] = params.is_active

    if params.origin_name:
        query["origin.name"] = {"$regex": params.origin_name, "$options": "i"}

    if params.destination_name:
        query["destination.name"] = {"$regex": params.destination_name, "$options": "i"}

    if params.max_fare is not None:
        query["base_fare"] = {"$lte": params.max_fare}

    if params.tag:
        query["tags"] = params.tag

    total = await db[ROUTES_COLLECTION].count_documents(query)
    cursor = (
        db[ROUTES_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    routes = [RouteResponse(**doc) async for doc in cursor]

    return {
        "data": routes,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


async def update_route(
    route_id: str, data: RouteUpdate, db: Any
) -> RouteResponse:
    """Partially update a route. Regenerate slug if origin/destination name changes."""
    obj_id = _to_object_id(route_id, "Route ID")

    route = await db[ROUTES_COLLECTION].find_one({"_id": obj_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Route not found"
        )

    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    # Sort waypoints if being updated
    if "waypoints" in update_fields and update_fields["waypoints"]:
        update_fields["waypoints"] = sorted(
            update_fields["waypoints"], key=lambda w: w.get("order", 0)
        )

    # Regenerate slug if origin or destination name changed
    new_origin = update_fields.get("origin", route.get("origin", {}))
    new_dest = update_fields.get("destination", route.get("destination", {}))
    origin_name = new_origin.get("name", "") if isinstance(new_origin, dict) else ""
    dest_name = new_dest.get("name", "") if isinstance(new_dest, dict) else ""

    if "origin" in update_fields or "destination" in update_fields:
        base_slug = _generate_slug(origin_name, dest_name)
        update_fields["slug"] = await _ensure_unique_slug(base_slug, db, exclude_id=obj_id)

    update_fields["updated_at"] = datetime.utcnow()

    await db[ROUTES_COLLECTION].update_one({"_id": obj_id}, {"$set": update_fields})
    updated = await db[ROUTES_COLLECTION].find_one({"_id": obj_id})
    return RouteResponse(**updated)


async def delete_route(route_id: str, db: Any) -> dict:
    """Soft-delete a route. Hard-delete only if no bookings reference it."""
    obj_id = _to_object_id(route_id, "Route ID")

    route = await db[ROUTES_COLLECTION].find_one({"_id": obj_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Route not found"
        )

    # Check if any bookings reference this route
    booking_count = await db[BOOKINGS_COLLECTION].count_documents({"route_id": route_id})
    if booking_count > 0:
        # Soft delete — deactivate
        await db[ROUTES_COLLECTION].update_one(
            {"_id": obj_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        return {
            "message": f"Route deactivated (soft-deleted). {booking_count} booking(s) reference this route.",
            "hard_deleted": False,
        }

    # Hard delete — no bookings reference it
    await db[ROUTES_COLLECTION].delete_one({"_id": obj_id})
    return {"message": "Route permanently deleted.", "hard_deleted": True}


# ── Thumbnail upload ───────────────────────────────────────────────────────


async def upload_route_thumbnail(
    route_id: str, file: UploadFile, db: Any
) -> RouteResponse:
    """Upload a thumbnail image and update thumbnail_url on the route."""
    obj_id = _to_object_id(route_id, "Route ID")

    route = await db[ROUTES_COLLECTION].find_one({"_id": obj_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Route not found"
        )

    storage = get_storage_service()
    thumbnail_url = await storage.upload_file(file, "routes", file.filename or "thumbnail")

    await db[ROUTES_COLLECTION].update_one(
        {"_id": obj_id},
        {"$set": {"thumbnail_url": thumbnail_url, "updated_at": datetime.utcnow()}},
    )

    updated = await db[ROUTES_COLLECTION].find_one({"_id": obj_id})
    return RouteResponse(**updated)


# ── Popular routes ─────────────────────────────────────────────────────────


async def get_popular_routes(limit: int, db: Any) -> list[RouteResponse]:
    """Return routes with the most bookings, or most recently created if no bookings."""
    # Aggregate bookings by route_id, count them, sort desc
    pipeline = [
        {"$match": {"route_id": {"$ne": None}}},
        {"$group": {"_id": "$route_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    booking_agg = await db[BOOKINGS_COLLECTION].aggregate(pipeline).to_list(length=limit)

    if booking_agg:
        route_ids = [item["_id"] for item in booking_agg]
        # Try to convert to ObjectId for lookup, but route_id might be stored as string
        routes = []
        for rid in route_ids:
            try:
                oid = ObjectId(rid)
                route = await db[ROUTES_COLLECTION].find_one({"_id": oid, "is_active": True})
            except errors.InvalidId:
                route = None
            if route:
                routes.append(RouteResponse(**route))
        if routes:
            return routes

    # Fallback: most recently created active routes
    cursor = (
        db[ROUTES_COLLECTION]
        .find({"is_active": True})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [RouteResponse(**doc) async for doc in cursor]


# ── Seed default routes ───────────────────────────────────────────────────


async def seed_default_routes(db: Any) -> dict:
    """Create default Ladakh/Himachal routes if they don't already exist (idempotent)."""
    defaults = [
        {
            "name": "Leh to Kargil",
            "origin": {"name": "Leh", "lat": 34.1526, "lng": 77.5771},
            "destination": {"name": "Kargil", "lat": 34.5539, "lng": 76.1349},
            "distance_km": 234,
            "estimated_duration_mins": 300,
            "base_fare": 800,
            "tags": ["scenic"],
            "is_seasonal": False,
        },
        {
            "name": "Leh to Nubra Valley",
            "origin": {"name": "Leh", "lat": 34.1526, "lng": 77.5771},
            "destination": {"name": "Nubra Valley", "lat": 34.6833, "lng": 77.5667},
            "distance_km": 150,
            "estimated_duration_mins": 180,
            "base_fare": 600,
            "tags": ["scenic", "high-altitude"],
            "is_seasonal": False,
        },
        {
            "name": "Leh to Pangong Lake",
            "origin": {"name": "Leh", "lat": 34.1526, "lng": 77.5771},
            "destination": {"name": "Pangong Lake", "lat": 33.7595, "lng": 78.6625},
            "distance_km": 160,
            "estimated_duration_mins": 200,
            "base_fare": 700,
            "tags": ["scenic", "high-altitude"],
            "is_seasonal": False,
        },
        {
            "name": "Manali to Leh",
            "origin": {"name": "Manali", "lat": 32.2396, "lng": 77.1887},
            "destination": {"name": "Leh", "lat": 34.1526, "lng": 77.5771},
            "distance_km": 479,
            "estimated_duration_mins": 720,
            "base_fare": 2500,
            "tags": ["high-altitude", "seasonal"],
            "is_seasonal": True,
            "season_start_month": 6,
            "season_end_month": 10,
        },
        {
            "name": "Manali to Spiti",
            "origin": {"name": "Manali", "lat": 32.2396, "lng": 77.1887},
            "destination": {"name": "Spiti", "lat": 32.5983, "lng": 78.0367},
            "distance_km": 200,
            "estimated_duration_mins": 360,
            "base_fare": 1200,
            "tags": ["scenic", "high-altitude", "seasonal"],
            "is_seasonal": True,
            "season_start_month": 5,
            "season_end_month": 10,
        },
        {
            "name": "Srinagar to Leh",
            "origin": {"name": "Srinagar", "lat": 34.0837, "lng": 74.7973},
            "destination": {"name": "Leh", "lat": 34.1526, "lng": 77.5771},
            "distance_km": 434,
            "estimated_duration_mins": 600,
            "base_fare": 2000,
            "tags": ["scenic", "high-altitude", "seasonal"],
            "is_seasonal": True,
            "season_start_month": 5,
            "season_end_month": 10,
        },
        {
            "name": "Leh to Tso Moriri",
            "origin": {"name": "Leh", "lat": 34.1526, "lng": 77.5771},
            "destination": {"name": "Tso Moriri", "lat": 32.9900, "lng": 78.3119},
            "distance_km": 240,
            "estimated_duration_mins": 300,
            "base_fare": 900,
            "tags": ["scenic", "high-altitude"],
            "is_seasonal": False,
        },
        {
            "name": "Dharamshala to Dalhousie",
            "origin": {"name": "Dharamshala", "lat": 32.2190, "lng": 76.3234},
            "destination": {"name": "Dalhousie", "lat": 32.5373, "lng": 75.9710},
            "distance_km": 120,
            "estimated_duration_mins": 180,
            "base_fare": 500,
            "tags": ["scenic"],
            "is_seasonal": False,
        },
    ]

    created = 0
    skipped = 0
    now = datetime.utcnow()

    for route_data in defaults:
        origin_name = route_data["origin"]["name"]
        dest_name = route_data["destination"]["name"]
        base_slug = _generate_slug(origin_name, dest_name)

        # Check if a route with this slug already exists
        existing = await db[ROUTES_COLLECTION].find_one({"slug": base_slug})
        if existing:
            skipped += 1
            continue

        doc = {
            **route_data,
            "slug": base_slug,
            "waypoints": [],
            "is_active": True,
            "season_start_month": route_data.get("season_start_month"),
            "season_end_month": route_data.get("season_end_month"),
            "thumbnail_url": None,
            "created_at": now,
            "updated_at": now,
        }
        await db[ROUTES_COLLECTION].insert_one(doc)
        created += 1

    return {
        "message": f"Seeding complete. Created: {created}, Skipped (already exist): {skipped}",
        "created": created,
        "skipped": skipped,
    }

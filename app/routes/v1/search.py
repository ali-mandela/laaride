"""Search & Discovery endpoints — public route/driver search and trip planning."""

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from app.core.database import get_database
from app.enums.common import VehicleType
from app.services import search_service

router = APIRouter(tags=["Search & Discovery"])


@router.get("/routes", summary="Search routes")
async def search_routes(
    q: str = Query(..., min_length=1, description="Search query"),
    db: Any = Depends(get_database),
):
    """Full-text + partial search on routes (name, origin, destination)."""
    return await search_service.search_routes(q, db)


@router.get("/routes/suggestions", summary="Route autocomplete")
async def route_suggestions(
    q: str = Query(..., min_length=1, description="Partial query for autocomplete"),
    db: Any = Depends(get_database),
):
    """Fast autocomplete suggestions for the search bar. Max 10 results."""
    return await search_service.get_route_suggestions(q, db)


@router.get("/routes/from/{origin_name}", summary="Routes from origin")
async def routes_from_origin(
    origin_name: str,
    db: Any = Depends(get_database),
):
    """Find all active routes departing from a given origin city."""
    return await search_service.get_routes_from_origin(origin_name, db)


@router.get("/drivers", summary="Search available drivers")
async def search_drivers(
    origin: Optional[str] = Query(default=None),
    destination: Optional[str] = Query(default=None),
    trip_date: Optional[date] = Query(default=None),
    vehicle_type: Optional[VehicleType] = Query(default=None),
    min_seats: Optional[int] = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Any = Depends(get_database),
):
    """Unified driver search with optional route, date, vehicle type, and seat filters."""
    return await search_service.search_drivers(
        db,
        origin=origin,
        destination=destination,
        trip_date=trip_date,
        vehicle_type=vehicle_type,
        min_seats=min_seats,
        limit=limit,
    )


@router.get("/trip-summary", summary="Trip summary")
async def trip_summary(
    route_id: str = Query(...),
    trip_date: date = Query(...),
    db: Any = Depends(get_database),
):
    """Full pre-booking summary: route, drivers, seats, fares, weather advisory."""
    return await search_service.get_trip_summary(route_id, trip_date, db)


@router.get("/popular-origins", summary="Popular origin cities")
async def popular_origins(
    db: Any = Depends(get_database),
):
    """Top origin cities ranked by booking count."""
    return await search_service.get_popular_origins(db)

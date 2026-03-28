"""Trip endpoints — public seat map and search."""

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from app.core.database import get_database
from app.schemas.trip import SeatMapResponse, TripResponse
from app.services import trip_service

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    summary="Get trip details",
)
async def get_trip(
    trip_id: str,
    db: Any = Depends(get_database),
):
    """Return full trip details including driver and vehicle info."""
    return await trip_service.get_trip_by_id(trip_id, db)


@router.get(
    "/{trip_id}/seats",
    response_model=SeatMapResponse,
    summary="Get seat map for a trip",
)
async def get_trip_seats(
    trip_id: str,
    db: Any = Depends(get_database),
):
    """Return seat availability and layout for a trip."""
    return await trip_service.get_trip_seat_map(trip_id, db)

"""WebSocket and REST endpoints for real-time driver GPS tracking."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.core.security import get_current_user, require_role
from app.enums.common import UserRole
from app.services import tracking_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["Tracking"])


class LocationPayload(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    heading: Optional[float] = Field(None, ge=0, lt=360)


# ---------------------------------------------------------------------------
# REST — driver pushes location updates
# ---------------------------------------------------------------------------

@router.post("/location")
async def update_my_location(
    payload: LocationPayload,
    current_user=Depends(require_role(UserRole.DRIVER)),
):
    """Driver pushes their current GPS coordinates (REST fallback)."""
    location = tracking_service.update_driver_location(
        str(current_user.id), payload.lat, payload.lng, payload.heading
    )
    await tracking_service.broadcast_location(str(current_user.id), location)
    return {"status": "ok", "location": location}


@router.get("/drivers/{driver_id}")
async def get_driver_location(
    driver_id: str,
    current_user=Depends(get_current_user),
):
    """Get the last known GPS location for a driver."""
    location = tracking_service.get_driver_location(driver_id)
    if not location:
        raise HTTPException(status_code=404, detail="No location data available for this driver")
    return location


# ---------------------------------------------------------------------------
# WebSocket — passenger subscribes to live location updates
# ---------------------------------------------------------------------------

@router.websocket("/ws/booking/{booking_id}")
async def booking_location_ws(booking_id: str, websocket: WebSocket):
    """WebSocket endpoint for passengers to receive live driver location.

    Protocol:
    - Client connects with JWT token as query param: ?token=<jwt>
    - Server streams JSON location updates as the driver moves.
    - Connection closes when booking completes or driver goes offline.

    TODO:
    - Validate JWT token from query params.
    - Verify passenger is a participant in this booking.
    - Integrate with booking status to auto-close on COMPLETED.
    """
    await websocket.accept()
    await tracking_service.subscribe_to_booking(booking_id, websocket)
    logger.info("Passenger connected to live tracking", extra={"booking_id": booking_id})
    try:
        while True:
            # Keep connection alive; location updates are pushed via broadcast
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Passenger disconnected from tracking", extra={"booking_id": booking_id})
    finally:
        await tracking_service.unsubscribe_from_booking(booking_id, websocket)


@router.websocket("/ws/driver")
async def driver_location_ws(websocket: WebSocket):
    """WebSocket endpoint for drivers to stream GPS updates.

    Protocol:
    - Driver sends JSON: {\"lat\": 34.1, \"lng\": 77.5, \"heading\": 90}
    - Server broadcasts to all subscribers of driver's active bookings.

    TODO:
    - Validate JWT token from query params before accepting.
    - Map driver to their active booking for targeted broadcasts.
    """
    await websocket.accept()
    driver_id = "unknown"  # TODO: extract from JWT
    logger.info("Driver connected to GPS stream")
    try:
        while True:
            data = await websocket.receive_json()
            lat, lng = data.get("lat"), data.get("lng")
            heading = data.get("heading")
            if lat is not None and lng is not None:
                location = tracking_service.update_driver_location(driver_id, lat, lng, heading)
                await tracking_service.broadcast_location(driver_id, location)
    except WebSocketDisconnect:
        logger.info("Driver disconnected from GPS stream")

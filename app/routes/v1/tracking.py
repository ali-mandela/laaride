"""WebSocket and REST endpoints for real-time driver GPS tracking."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import get_database, BOOKINGS_COLLECTION, DRIVERS_COLLECTION
from app.core.security import get_current_user, require_role, verify_token
from app.enums.common import UserRole
from app.services import tracking_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["Tracking"])


class LocationPayload(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    heading: Optional[float] = Field(None, ge=0, lt=360)


async def _ws_authenticate(websocket: WebSocket, token: str) -> dict:
    """Validate a JWT token from a WebSocket query param.

    Returns the decoded payload or closes the connection with 1008.
    """
    try:
        payload = verify_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=1008, reason="Invalid token type")
            return {}
        return payload
    except (JWTError, HTTPException):
        await websocket.close(code=1008, reason="Unauthorized")
        return {}


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
async def booking_location_ws(
    booking_id: str,
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db=Depends(get_database),
):
    """Passenger receives live driver location for an active booking.

    Connect with: ws://.../tracking/ws/booking/{id}?token=<jwt>
    Receives: {"driver_id", "lat", "lng", "heading", "timestamp"}
    """
    await websocket.accept()

    # Authenticate
    payload = await _ws_authenticate(websocket, token)
    if not payload:
        return
    user_id = payload.get("sub")

    # Verify this passenger is a participant in the booking
    booking = await db[BOOKINGS_COLLECTION].find_one({"_id": booking_id})
    if not booking:
        booking = await db[BOOKINGS_COLLECTION].find_one({"_id": booking_id})
    if not booking or booking.get("passenger_id") != user_id:
        await websocket.close(code=1008, reason="Booking not found or access denied")
        return

    await tracking_service.subscribe_to_booking(booking_id, websocket)
    logger.info("Passenger connected to live tracking", extra={"booking_id": booking_id, "user_id": user_id})
    try:
        while True:
            # Keep-alive: client can send pings, we don't process them
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Passenger disconnected from tracking", extra={"booking_id": booking_id})
    finally:
        await tracking_service.unsubscribe_from_booking(booking_id, websocket)


# ---------------------------------------------------------------------------
# WebSocket — driver streams GPS updates
# ---------------------------------------------------------------------------

@router.websocket("/ws/driver")
async def driver_location_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db=Depends(get_database),
):
    """Driver streams GPS location updates in real time.

    Connect with: ws://.../tracking/ws/driver?token=<jwt>
    Send: {"lat": 34.1, "lng": 77.5, "heading": 90}  (heading optional)
    """
    await websocket.accept()

    # Authenticate
    payload = await _ws_authenticate(websocket, token)
    if not payload:
        return
    user_id = payload.get("sub")

    # Verify the user is a driver
    driver = await db[DRIVERS_COLLECTION].find_one({"user_id": user_id})
    if not driver:
        await websocket.close(code=1008, reason="Driver profile not found")
        return

    driver_id = str(driver.get("_id"))
    logger.info("Driver connected to GPS stream", extra={"driver_id": driver_id})

    try:
        while True:
            data = await websocket.receive_json()
            lat, lng = data.get("lat"), data.get("lng")
            heading = data.get("heading")
            if lat is not None and lng is not None:
                location = tracking_service.update_driver_location(driver_id, lat, lng, heading)
                await tracking_service.broadcast_location(driver_id, location)
    except WebSocketDisconnect:
        logger.info("Driver disconnected from GPS stream", extra={"driver_id": driver_id})

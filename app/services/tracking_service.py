"""Real-time driver GPS tracking service.

Uses an in-memory store (dict) for current driver locations.
For production, swap the store with Redis pub/sub for multi-instance support.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory location cache: {driver_id: LocationUpdate}
# TODO: Replace with Redis hash/pub-sub for multi-instance deployments.
_driver_locations: dict[str, dict] = {}

# Active WebSocket connections per booking: {booking_id: set[WebSocket]}
_booking_subscribers: dict[str, set] = {}


class LocationUpdate:
    """Represents a single GPS update from a driver."""

    def __init__(self, driver_id: str, lat: float, lng: float, heading: Optional[float] = None):
        self.driver_id = driver_id
        self.lat = lat
        self.lng = lng
        self.heading = heading
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "driver_id": self.driver_id,
            "lat": self.lat,
            "lng": self.lng,
            "heading": self.heading,
            "timestamp": self.timestamp,
        }


def update_driver_location(driver_id: str, lat: float, lng: float, heading: Optional[float] = None) -> dict:
    """Update a driver's current GPS position and broadcast to subscribers."""
    update = LocationUpdate(driver_id, lat, lng, heading)
    _driver_locations[driver_id] = update.to_dict()
    logger.debug("Driver location updated", extra={"driver_id": driver_id, "lat": lat, "lng": lng})
    return update.to_dict()


def get_driver_location(driver_id: str) -> Optional[dict]:
    """Get the last known GPS location of a driver."""
    return _driver_locations.get(driver_id)


async def subscribe_to_booking(booking_id: str, websocket) -> None:
    """Register a WebSocket connection to receive location updates for a booking."""
    if booking_id not in _booking_subscribers:
        _booking_subscribers[booking_id] = set()
    _booking_subscribers[booking_id].add(websocket)
    logger.info("WebSocket subscribed to booking", extra={"booking_id": booking_id})


async def unsubscribe_from_booking(booking_id: str, websocket) -> None:
    """Remove a WebSocket connection from a booking's subscriber set."""
    if booking_id in _booking_subscribers:
        _booking_subscribers[booking_id].discard(websocket)


async def broadcast_location(driver_id: str, location: dict) -> None:
    """Broadcast a location update to all subscribers watching this driver.

    TODO: Currently O(n) over all bookings — optimise with a driver→bookings
    reverse index.
    """
    dead_connections: list = []
    for booking_id, subscribers in _booking_subscribers.items():
        for ws in list(subscribers):
            try:
                await ws.send_json(location)
            except Exception:  # noqa: BLE001
                dead_connections.append((booking_id, ws))
    for booking_id, ws in dead_connections:
        _booking_subscribers.get(booking_id, set()).discard(ws)

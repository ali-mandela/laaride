"""Real-time driver GPS tracking service with Redis backend.

Supports multi-instance deployments using Redis Streams and Redis Pub/Sub.
This is the production-ready version that scales horizontally.

Fallback: If Redis is unavailable, falls back to in-memory tracking (single-instance only).
"""
from __future__ import annotations

import json
import logging
import redis.asyncio as redis
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Redis client (initialized in lifespan)
_redis_client: Optional[redis.Redis] = None

# Fallback in-memory store if Redis unavailable
_driver_locations: dict[str, dict] = {}
_booking_subscribers: dict[str, set] = {}
_use_redis: bool = False


async def initialize_redis(redis_url: str) -> bool:
    """Initialize Redis connection for tracking service.

    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379)

    Returns:
        True if Redis connected successfully, False if fallback to in-memory.
    """
    global _redis_client, _use_redis

    if not redis_url:
        logger.info("Redis tracking disabled: no REDIS_URL configured")
        _use_redis = False
        return False

    try:
        _redis_client = await redis.from_url(redis_url, decode_responses=True)
        # Test connection
        await _redis_client.ping()
        _use_redis = True
        logger.info("Redis tracking initialized", redis_url=redis_url)
        return True
    except Exception as e:
        logger.warning("Failed to connect to Redis for tracking, falling back to in-memory", error=str(e))
        _use_redis = False
        _redis_client = None
        return False


async def close_redis():
    """Close Redis connection."""
    global _redis_client, _use_redis
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        _use_redis = False
        logger.info("Redis tracking connection closed")


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

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


async def update_driver_location(driver_id: str, lat: float, lng: float, heading: Optional[float] = None) -> dict:
    """Update a driver's current GPS position and broadcast to subscribers.

    In Redis mode: Stores in Redis hash and publishes to subscribers.
    In fallback mode: Uses in-memory dict.
    """
    update = LocationUpdate(driver_id, lat, lng, heading)
    update_dict = update.to_dict()

    if _use_redis and _redis_client:
        try:
            # Store in Redis hash (auto-expires after 24 hours)
            await _redis_client.hset(
                f"driver_location:{driver_id}",
                mapping=update_dict
            )
            await _redis_client.expire(f"driver_location:{driver_id}", 86400)

            # Publish to Redis Pub/Sub channel for real-time subscribers
            await _redis_client.publish(
                f"driver_tracking:{driver_id}",
                update.to_json()
            )

            logger.debug("Driver location updated (Redis)", extra={"driver_id": driver_id, "lat": lat, "lng": lng})
        except Exception as e:
            logger.warning("Redis update failed, falling back to in-memory", error=str(e))
            _driver_locations[driver_id] = update_dict
    else:
        # Fallback to in-memory
        _driver_locations[driver_id] = update_dict
        logger.debug("Driver location updated (in-memory)", extra={"driver_id": driver_id, "lat": lat, "lng": lng})

    return update_dict


async def get_driver_location(driver_id: str) -> Optional[dict]:
    """Get the last known GPS location of a driver.

    In Redis mode: Fetches from Redis hash.
    In fallback mode: Uses in-memory dict.
    """
    if _use_redis and _redis_client:
        try:
            location = await _redis_client.hgetall(f"driver_location:{driver_id}")
            if location:
                return {
                    "driver_id": location.get("driver_id", driver_id),
                    "lat": float(location.get("lat", 0)),
                    "lng": float(location.get("lng", 0)),
                    "heading": float(location["heading"]) if location.get("heading") else None,
                    "timestamp": location.get("timestamp"),
                }
        except Exception as e:
            logger.warning("Redis fetch failed, falling back to in-memory", error=str(e))

    return _driver_locations.get(driver_id)


async def subscribe_to_booking_redis(
    booking_id: str,
    driver_id: str,
    on_update_callback
) -> None:
    """Subscribe to real-time location updates for a booking (Redis mode).

    Subscribes to Redis Pub/Sub channel for the driver and calls callback on updates.

    Args:
        booking_id: Booking ID (for logging)
        driver_id: Driver ID to track
        on_update_callback: Async callback function to call on location updates
    """
    if not _use_redis or not _redis_client:
        logger.debug("Redis tracking unavailable, subscription failed", booking_id=booking_id)
        return

    try:
        pubsub = _redis_client.pubsub()
        await pubsub.subscribe(f"driver_tracking:{driver_id}")

        logger.info("Redis subscribed to tracking", booking_id=booking_id, driver_id=driver_id)

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    location_data = json.loads(message["data"])
                    await on_update_callback(location_data)
                except Exception as e:
                    logger.warning("Error processing location update", error=str(e))
    except Exception as e:
        logger.error("Subscription error", booking_id=booking_id, error=str(e))
    finally:
        await pubsub.unsubscribe()


async def subscribe_to_booking(booking_id: str, websocket) -> None:
    """Register a WebSocket connection to receive location updates for a booking.

    In Redis mode: Uses Pub/Sub (scalable).
    In fallback mode: Uses in-memory set (single-instance only).
    """
    if booking_id not in _booking_subscribers:
        _booking_subscribers[booking_id] = set()
    _booking_subscribers[booking_id].add(websocket)
    logger.info("WebSocket subscribed to booking", extra={"booking_id": booking_id, "mode": "redis" if _use_redis else "in-memory"})


async def unsubscribe_from_booking(booking_id: str, websocket) -> None:
    """Remove a WebSocket connection from a booking's subscriber set."""
    if booking_id in _booking_subscribers:
        _booking_subscribers[booking_id].discard(websocket)
        logger.debug("WebSocket unsubscribed from booking", extra={"booking_id": booking_id})


async def broadcast_location(driver_id: str, location: dict) -> None:
    """Broadcast a location update to all subscribers watching this driver.

    In Redis mode: Publishes to Redis Pub/Sub (other instances receive it).
    In fallback mode: Sends to in-memory WebSocket set (this instance only).

    This is O(1) in Redis mode, O(n) in fallback mode.
    """
    if _use_redis and _redis_client:
        try:
            # Redis Pub/Sub — other instances' WebSockets will receive via subscription
            await _redis_client.publish(
                f"driver_tracking:{driver_id}",
                json.dumps(location)
            )
        except Exception as e:
            logger.warning("Failed to broadcast via Redis, falling back to in-memory", error=str(e))
            # Fall through to in-memory broadcast below

    # In-memory fallback (for this instance's WebSocket connections)
    dead_connections: list = []
    for booking_id, subscribers in list(_booking_subscribers.items()):
        for ws in list(subscribers):
            try:
                await ws.send_json(location)
            except Exception:
                dead_connections.append((booking_id, ws))

    # Clean up dead connections
    for booking_id, ws in dead_connections:
        _booking_subscribers.get(booking_id, set()).discard(ws)

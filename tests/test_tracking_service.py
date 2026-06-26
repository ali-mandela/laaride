"""Tests for Redis-backed tracking service with fallback."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import tracking_service_redis


@pytest.mark.asyncio
async def test_tracking_initialization_redis_success():
    """Test successful Redis initialization."""
    with patch("app.services.tracking_service_redis.redis.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_redis.return_value = mock_client

        result = await tracking_service_redis.initialize_redis("redis://localhost:6379")

        assert result is True
        assert mock_client.ping.called


@pytest.mark.asyncio
async def test_tracking_initialization_redis_failure():
    """Test fallback to in-memory when Redis unavailable."""
    with patch("app.services.tracking_service_redis.redis.from_url") as mock_redis:
        mock_redis.side_effect = Exception("Connection refused")

        result = await tracking_service_redis.initialize_redis("redis://localhost:6379")

        assert result is False


@pytest.mark.asyncio
async def test_update_driver_location_redis():
    """Test updating driver location via Redis."""
    with patch("app.services.tracking_service_redis._redis_client") as mock_client:
        with patch("app.services.tracking_service_redis._use_redis", True):
            mock_client.hset = AsyncMock()
            mock_client.expire = AsyncMock()
            mock_client.publish = AsyncMock()

            tracking_service_redis._redis_client = mock_client
            tracking_service_redis._use_redis = True

            location = await tracking_service_redis.update_driver_location(
                driver_id="driver_123",
                lat=34.5,
                lng=77.5,
                heading=90,
            )

            assert location["driver_id"] == "driver_123"
            assert location["lat"] == 34.5
            assert location["lng"] == 77.5
            assert mock_client.hset.called
            assert mock_client.publish.called


@pytest.mark.asyncio
async def test_get_driver_location():
    """Test retrieving driver location."""
    with patch("app.services.tracking_service_redis._driver_locations") as mock_locs:
        mock_locs.get.return_value = {
            "driver_id": "driver_123",
            "lat": 34.5,
            "lng": 77.5,
            "heading": 90,
            "timestamp": "2024-01-01T00:00:00",
        }

        tracking_service_redis._use_redis = False
        location = await tracking_service_redis.get_driver_location("driver_123")

        assert location is not None
        assert location["driver_id"] == "driver_123"


@pytest.mark.asyncio
async def test_broadcast_location():
    """Test broadcasting location to subscribers."""
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    tracking_service_redis._booking_subscribers = {
        "booking_1": {ws1, ws2},
    }
    tracking_service_redis._use_redis = False

    location = {
        "driver_id": "driver_123",
        "lat": 34.5,
        "lng": 77.5,
        "timestamp": "2024-01-01T00:00:00",
    }

    await tracking_service_redis.broadcast_location("driver_123", location)

    # Both websockets should receive the location
    assert ws1.send_json.called
    assert ws2.send_json.called


@pytest.mark.asyncio
async def test_websocket_subscription():
    """Test WebSocket subscription to booking."""
    ws = AsyncMock()

    await tracking_service_redis.subscribe_to_booking("booking_123", ws)

    assert "booking_123" in tracking_service_redis._booking_subscribers
    assert ws in tracking_service_redis._booking_subscribers["booking_123"]


@pytest.mark.asyncio
async def test_websocket_unsubscription():
    """Test WebSocket unsubscription from booking."""
    ws = AsyncMock()
    tracking_service_redis._booking_subscribers = {
        "booking_123": {ws},
    }

    await tracking_service_redis.unsubscribe_from_booking("booking_123", ws)

    assert ws not in tracking_service_redis._booking_subscribers["booking_123"]

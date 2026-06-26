"""Tests for OSRM routing service with retry logic."""

import pytest
from unittest.mock import patch, MagicMock
import requests

from app.services.osrm_service import get_route_info


def test_osrm_successful_route_fetch():
    """Test successful OSRM route fetching."""
    mock_response = {
        "code": "Ok",
        "routes": [
            {
                "distance": 50000,  # 50 km in metres
                "duration": 3600,  # 1 hour in seconds
            }
        ],
    }

    with patch("app.services.osrm_service.requests.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: mock_response)

        result = get_route_info(
            origin_lat=34.5,
            origin_lng=77.5,
            dest_lat=35.5,
            dest_lng=78.5,
        )

        assert result is not None
        assert result.distance_km == 50.0
        assert result.duration_minutes == 60


def test_osrm_timeout_with_retry():
    """Test that OSRM retries on timeout."""
    with patch("app.services.osrm_service.requests.get") as mock_get:
        # First two calls timeout, third succeeds
        mock_response = {
            "code": "Ok",
            "routes": [{"distance": 30000, "duration": 1800}],
        }
        mock_get.side_effect = [
            requests.Timeout("Connection timeout"),
            requests.Timeout("Connection timeout"),
            MagicMock(json=lambda: mock_response),
        ]

        result = get_route_info(
            origin_lat=34.5,
            origin_lng=77.5,
            dest_lat=35.5,
            dest_lng=78.5,
        )

        # Should succeed after retries
        assert result is not None
        assert result.distance_km == 30.0
        # Should have retried 3 times
        assert mock_get.call_count == 3


def test_osrm_all_retries_fail():
    """Test that all retries fail and return None."""
    with patch("app.services.osrm_service.requests.get") as mock_get:
        mock_get.side_effect = requests.Timeout("Connection timeout")

        result = get_route_info(
            origin_lat=34.5,
            origin_lng=77.5,
            dest_lat=35.5,
            dest_lng=78.5,
        )

        # Should return None after all retries fail
        assert result is None
        # Should have retried 3 times (MAX_RETRIES)
        assert mock_get.call_count == 3


def test_osrm_no_route_found():
    """Test when OSRM returns no route."""
    mock_response = {
        "code": "NoRoute",
        "message": "No route found",
        "routes": [],
    }

    with patch("app.services.osrm_service.requests.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: mock_response)

        result = get_route_info(
            origin_lat=34.5,
            origin_lng=77.5,
            dest_lat=35.5,
            dest_lng=78.5,
        )

        # Should return None
        assert result is None


def test_osrm_request_exception_handling():
    """Test handling of various request exceptions."""
    with patch("app.services.osrm_service.requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("Network error")

        result = get_route_info(
            origin_lat=34.5,
            origin_lng=77.5,
            dest_lat=35.5,
            dest_lng=78.5,
        )

        # Should return None after retries
        assert result is None

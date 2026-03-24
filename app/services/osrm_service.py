"""OpenStreetMap routing via the public OSRM demo server.

No API key required. For production, self-host OSRM or use the Stadia Maps
OSRM endpoint with a free API key.

OSRM Route API docs: http://project-osrm.org/docs/v5.22.0/api/#route-service
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_OSRM_BASE = "http://router.project-osrm.org/route/v1/driving"
_TIMEOUT = 8  # seconds


class RouteInfo:
    """Routing result from OSRM."""

    def __init__(self, distance_km: float, duration_minutes: int):
        self.distance_km = round(distance_km, 1)
        self.duration_minutes = duration_minutes

    def __repr__(self) -> str:
        return f"RouteInfo(distance_km={self.distance_km}, duration_minutes={self.duration_minutes})"


def get_route_info(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> Optional[RouteInfo]:
    """Fetch driving distance and duration from OSRM.

    Returns None on failure — callers should fall back to user-supplied values.

    Args:
        origin_lat / origin_lng: Starting point coordinates.
        dest_lat / dest_lng: Ending point coordinates.
    """
    # OSRM coordinate format: lng,lat (note: longitude first)
    coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    url = f"{_OSRM_BASE}/{coords}"

    try:
        resp = requests.get(
            url,
            params={"overview": "false", "steps": "false"},
            timeout=_TIMEOUT,
            headers={"User-Agent": "LaaRide/1.0 (laaride.app)"},
        )
        data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning("osrm_no_route", code=data.get("code"), coords=coords)
            return None

        route = data["routes"][0]
        distance_km = route["distance"] / 1000  # metres → km
        duration_minutes = int(route["duration"] / 60)  # seconds → minutes

        logger.info(
            "osrm_route_fetched",
            distance_km=round(distance_km, 1),
            duration_minutes=duration_minutes,
        )
        return RouteInfo(distance_km=distance_km, duration_minutes=duration_minutes)

    except requests.Timeout:
        logger.warning("osrm_timeout", coords=coords)
        return None
    except Exception as exc:
        logger.error("osrm_error", error=str(exc))
        return None


def estimate_fare(distance_km: float, base_fare_per_km: float = 4.0, min_fare: float = 50.0) -> float:
    """Estimate a fare based on distance.

    Default: ₹4/km with a ₹50 minimum — adjust as needed.
    """
    return max(round(distance_km * base_fare_per_km, 0), min_fare)

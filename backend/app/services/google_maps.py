"""Google Maps Platform proxy with daily quota tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx
from fastapi import HTTPException

from app.config import settings

GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
GOOGLE_PLACES_TEXT_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass
class QuotaTracker:
    directions_count: int = 0
    places_count: int = 0
    day_start: float = field(default_factory=time.time)

    def _maybe_reset(self) -> None:
        if time.time() - self.day_start > 86400:
            self.directions_count = 0
            self.places_count = 0
            self.day_start = time.time()

    def check_directions(self) -> None:
        self._maybe_reset()
        if self.directions_count >= settings.directions_daily_quota:
            raise HTTPException(status_code=429, detail="Directions API daily quota exceeded")

    def check_places(self) -> None:
        self._maybe_reset()
        if self.places_count >= settings.places_daily_quota:
            raise HTTPException(status_code=429, detail="Places API daily quota exceeded")

    def record_directions(self) -> None:
        self.directions_count += 1

    def record_places(self) -> None:
        self.places_count += 1


quota = QuotaTracker()


def require_api_key() -> str:
    if not settings.google_maps_api_key:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_MAPS_API_KEY is not configured on the server",
        )
    return settings.google_maps_api_key


async def fetch_directions(waypoints: list[tuple[float, float]]) -> dict:
    """waypoints: list of (lat, lng). Returns parsed Directions API response."""
    if len(waypoints) < 2:
        raise HTTPException(status_code=400, detail="At least two waypoints required")

    api_key = require_api_key()
    quota.check_directions()

    origin = f"{waypoints[0][0]},{waypoints[0][1]}"
    destination = f"{waypoints[-1][0]},{waypoints[-1][1]}"
    params: dict[str, str] = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "key": api_key,
    }
    if len(waypoints) > 2:
        mid = "|".join(f"{lat},{lng}" for lat, lng in waypoints[1:-1])
        params["waypoints"] = mid

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(GOOGLE_DIRECTIONS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    quota.record_directions()

    if data.get("status") != "OK":
        raise HTTPException(
            status_code=502,
            detail=f"Directions API error: {data.get('status')} — {data.get('error_message', '')}",
        )
    return data


def decode_polyline(encoded: str) -> list[list[float]]:
    """Decode Google encoded polyline to [[lat, lng], ...]."""
    points: list[list[float]] = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        shift = result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat

        shift = result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng

        points.append([lat / 1e5, lng / 1e5])

    return points


def extract_route_from_directions(data: dict) -> tuple[list[list[float]], float, int]:
    route = data["routes"][0]
    leg_total_distance = 0.0
    leg_total_duration = 0
    all_points: list[list[float]] = []

    for leg in route["legs"]:
        leg_total_distance += leg["distance"]["value"]
        leg_total_duration += leg["duration"]["value"]
        for step in leg["steps"]:
            all_points.extend(decode_polyline(step["polyline"]["points"]))

    if not all_points and route.get("overview_polyline"):
        all_points = decode_polyline(route["overview_polyline"]["points"])

    return all_points, leg_total_distance, leg_total_duration


async def search_places(query: str, lat: float | None = None, lng: float | None = None) -> dict:
    api_key = require_api_key()
    quota.check_places()

    params: dict[str, str] = {"query": query, "key": api_key}
    if lat is not None and lng is not None:
        params["location"] = f"{lat},{lng}"
        params["radius"] = "50000"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(GOOGLE_PLACES_TEXT_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    quota.record_places()

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise HTTPException(
            status_code=502,
            detail=f"Places API error: {data.get('status')} — {data.get('error_message', '')}",
        )
    return data


async def geocode_address(address: str) -> dict:
    api_key = require_api_key()
    quota.check_places()

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            GOOGLE_GEOCODE_URL,
            params={"address": address, "key": api_key},
        )
        resp.raise_for_status()
        data = resp.json()

    quota.record_places()

    if data.get("status") != "OK":
        raise HTTPException(
            status_code=502,
            detail=f"Geocoding API error: {data.get('status')}",
        )
    return data

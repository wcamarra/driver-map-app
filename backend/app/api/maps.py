from fastapi import APIRouter, Query

from app.config import settings
from app.services import google_maps

router = APIRouter(prefix="/maps", tags=["maps"])


@router.get("/config")
async def maps_config():
    return {
        "configured": bool(settings.google_maps_api_key),
        "directions_quota_remaining": max(
            0,
            settings.directions_daily_quota - google_maps.quota.directions_count,
        ),
        "places_quota_remaining": max(
            0,
            settings.places_daily_quota - google_maps.quota.places_count,
        ),
    }


@router.get("/places")
async def places_search(
    q: str = Query(min_length=1),
    lat: float | None = None,
    lng: float | None = None,
):
    data = await google_maps.search_places(q, lat, lng)
    results = []
    for place in data.get("results", [])[:10]:
        loc = place.get("geometry", {}).get("location", {})
        results.append(
            {
                "name": place.get("name"),
                "place_id": place.get("place_id"),
                "address": place.get("formatted_address"),
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
                "types": place.get("types", []),
            }
        )
    return {"results": results}


@router.get("/geocode")
async def geocode(address: str = Query(min_length=1)):
    data = await google_maps.geocode_address(address)
    results = []
    for item in data.get("results", [])[:5]:
        loc = item["geometry"]["location"]
        results.append(
            {
                "formatted_address": item.get("formatted_address"),
                "lat": loc["lat"],
                "lng": loc["lng"],
            }
        )
    return {"results": results}

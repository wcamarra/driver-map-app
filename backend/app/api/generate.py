import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.route import Route, RouteSource, RouteStop, RouteVisibility
from app.models.user import User
from app.api.deps import route_to_detail
from app.schemas.generate import GenerateRouteRequest
from app.schemas.route import RouteDetail
from app.services.route_builder import coords_to_linestring
from app.workers.route_generator import GenerateRequest, generate_route, sample_stops

router = APIRouter(prefix="/routes", tags=["generate"])

# ~35 mph average on backroads
METERS_PER_MINUTE = 940.0

PROFILE_TAGS = {
    "scenic": ["scenic", "generated"],
    "twisty": ["twisty", "generated"],
    "relaxed": ["cruise", "generated"],
}

PROFILE_TITLES = {
    "scenic": "Scenic drive",
    "twisty": "Twisty backroads",
    "relaxed": "Relaxed cruise",
}


def _target_distance_m(body: GenerateRouteRequest) -> float:
    if body.target_distance_m is not None:
        return body.target_distance_m
    if body.duration_minutes is not None:
        return body.duration_minutes * METERS_PER_MINUTE
    return 25000.0


@router.post("/generate", response_model=RouteDetail, status_code=201)
async def generate_driving_route(
    body: GenerateRouteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_m = _target_distance_m(body)
    req = GenerateRequest(
        center_lat=body.center_lat,
        center_lng=body.center_lng,
        profile=body.profile,
        target_distance_m=target_m,
        radius_m=0,  # 0 → auto-scale from target in generate_route
        near_lat=body.near_lat,
        near_lng=body.near_lng,
    )

    try:
        result = await asyncio.to_thread(generate_route, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Route generation failed: {exc}",
        ) from exc

    if len(result.polyline) < 2:
        raise HTTPException(status_code=400, detail="Could not build a route in this area")

    title = body.title or PROFILE_TITLES.get(body.profile, "Generated route")
    tags = PROFILE_TAGS.get(body.profile, ["generated"])

    actual_mi = result.distance_m / 1609.34
    target_mi = result.target_distance_m / 1609.34
    if actual_mi < target_mi * 0.5:
        reach_note = (
            f"Generated ~{actual_mi:.0f} mi of your ~{target_mi:.0f} mi target — "
            "the road network in this area may be limited. Try a rural region, shorter duration, "
            "or scenic/relaxed profile. "
        )
    else:
        reach_note = f"Generated ~{actual_mi:.0f} mi (target ~{target_mi:.0f} mi). "

    route = Route(
        owner_id=user.id,
        title=title,
        description=f"Auto-generated {body.profile} route. {reach_note}"
        "Tap Build route to snap to drivable roads, then tweak stops.",
        region=body.region,
        tags=tags,
        visibility=RouteVisibility.DRAFT.value,
        source=RouteSource.GENERATED.value,
        geometry=coords_to_linestring(result.polyline),
        distance_meters=result.distance_m,
        duration_seconds=int(result.distance_m / METERS_PER_MINUTE * 60),
    )
    db.add(route)
    await db.flush()

    for i, (lat, lng, name) in enumerate(sample_stops(result.polyline, count=6)):
        db.add(RouteStop(route_id=route.id, sequence=i, lat=lat, lng=lng, name=name))

    await db.commit()

    loaded = await db.execute(
        select(Route)
        .options(selectinload(Route.stops), selectinload(Route.owner))
        .where(Route.id == route.id)
    )
    route = loaded.scalar_one()
    return await route_to_detail(route, db, user.id)

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_optional_user
from app.database import get_db
from app.models.route import Route, RouteSource, RouteStop, RouteVisibility
from app.models.user import User
from app.api.deps import can_view_route, route_to_detail, route_to_feed_item
from app.schemas.route import (
    RouteBuildResult,
    RouteCreate,
    RouteDetail,
    RouteFeedItem,
    RouteUpdate,
)
from app.services.route_builder import build_route_geometry, linestring_to_coords

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("", response_model=RouteDetail, status_code=status.HTTP_201_CREATED)
async def create_route(
    body: RouteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    route = Route(
        owner_id=user.id,
        title=body.title,
        description=body.description,
        region=body.region,
        tags=body.tags,
        visibility=RouteVisibility.DRAFT.value,
        source=RouteSource.CREATED.value,
    )
    db.add(route)
    await db.commit()

    result = await db.execute(
        select(Route)
        .options(selectinload(Route.stops), selectinload(Route.owner))
        .where(Route.id == route.id)
    )
    route = result.scalar_one()
    return await route_to_detail(route, db, user.id)


@router.get("/feed", response_model=list[RouteFeedItem])
async def feed(
    tag: str | None = None,
    region: str | None = None,
    q: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Route)
        .options(selectinload(Route.owner))
        .where(Route.visibility == RouteVisibility.PUBLIC.value)
        .order_by(Route.published_at.desc().nullslast(), Route.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if tag:
        stmt = stmt.where(Route.tags.contains([tag]))
    if region:
        stmt = stmt.where(Route.region.ilike(f"%{region}%"))
    if q:
        stmt = stmt.where(
            or_(Route.title.ilike(f"%{q}%"), Route.description.ilike(f"%{q}%"))
        )

    result = await db.execute(stmt)
    routes = result.scalars().all()
    return [await route_to_feed_item(r, db) for r in routes]


@router.get("/mine", response_model=list[RouteFeedItem])
async def my_routes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Route)
        .options(selectinload(Route.owner))
        .where(Route.owner_id == user.id)
        .order_by(Route.updated_at.desc())
    )
    routes = result.scalars().all()
    return [await route_to_feed_item(r, db) for r in routes]


@router.get("/{route_id}", response_model=RouteDetail)
async def get_route(
    route_id: int,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Route)
        .options(selectinload(Route.stops), selectinload(Route.owner))
        .where(Route.id == route_id)
    )
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    if not can_view_route(route, user.id if user else None):
        raise HTTPException(status_code=404, detail="Route not found")

    return await route_to_detail(route, db, user.id if user else None)


@router.patch("/{route_id}", response_model=RouteDetail)
async def update_route(
    route_id: int,
    body: RouteUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Route)
        .options(selectinload(Route.stops), selectinload(Route.owner))
        .where(Route.id == route_id, Route.owner_id == user.id)
    )
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    if body.title is not None:
        route.title = body.title
    if body.description is not None:
        route.description = body.description
    if body.region is not None:
        route.region = body.region
    if body.tags is not None:
        route.tags = body.tags
    if body.visibility is not None:
        if body.visibility not in {v.value for v in RouteVisibility}:
            raise HTTPException(status_code=400, detail="Invalid visibility")
        route.visibility = body.visibility

    if body.stops is not None:
        for stop in list(route.stops):
            await db.delete(stop)
        await db.flush()
        for i, s in enumerate(body.stops):
            db.add(
                RouteStop(
                    route_id=route.id,
                    sequence=s.sequence if s.sequence is not None else i,
                    lat=s.lat,
                    lng=s.lng,
                    name=s.name,
                    note=s.note,
                )
            )

    await db.commit()
    await db.refresh(route)
    result = await db.execute(
        select(Route)
        .options(selectinload(Route.stops), selectinload(Route.owner))
        .where(Route.id == route.id)
    )
    route = result.scalar_one()
    return await route_to_detail(route, db, user.id)


@router.post("/{route_id}/build", response_model=RouteBuildResult)
async def build_route(
    route_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Route)
        .options(selectinload(Route.stops))
        .where(Route.id == route_id, Route.owner_id == user.id)
    )
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    try:
        polyline, distance_m, duration_s = await build_route_geometry(route, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.commit()
    return RouteBuildResult(
        distance_meters=distance_m,
        duration_seconds=duration_s,
        polyline=polyline,
    )


@router.post("/{route_id}/publish", response_model=RouteDetail)
async def publish_route(
    route_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Route)
        .options(selectinload(Route.stops), selectinload(Route.owner))
        .where(Route.id == route_id, Route.owner_id == user.id)
    )
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    if len(route.stops) < 2:
        raise HTTPException(status_code=400, detail="Add at least two stops before publishing")
    if route.geometry is None:
        raise HTTPException(status_code=400, detail="Build the route before publishing")

    route.visibility = RouteVisibility.PUBLIC.value
    route.published_at = datetime.now(UTC)
    route.version += 1
    await db.commit()

    result = await db.execute(
        select(Route)
        .options(selectinload(Route.stops), selectinload(Route.owner))
        .where(Route.id == route.id)
    )
    route = result.scalar_one()
    return await route_to_detail(route, db, user.id)


@router.post("/{route_id}/fork", response_model=RouteDetail, status_code=status.HTTP_201_CREATED)
async def fork_route(
    route_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Route)
        .options(selectinload(Route.stops))
        .where(Route.id == route_id)
    )
    source = result.scalar_one_or_none()
    if source is None or not can_view_route(source, user.id):
        raise HTTPException(status_code=404, detail="Route not found")
    if source.visibility != RouteVisibility.PUBLIC.value:
        raise HTTPException(status_code=400, detail="Can only fork public routes")

    new_route = Route(
        owner_id=user.id,
        title=f"{source.title} (copy)",
        description=source.description,
        region=source.region,
        tags=list(source.tags or []),
        visibility=RouteVisibility.DRAFT.value,
        source=RouteSource.CREATED.value,
        geometry=source.geometry,
        distance_meters=source.distance_meters,
        duration_seconds=source.duration_seconds,
    )
    db.add(new_route)
    await db.flush()

    for stop in sorted(source.stops, key=lambda s: s.sequence):
        db.add(
            RouteStop(
                route_id=new_route.id,
                sequence=stop.sequence,
                lat=stop.lat,
                lng=stop.lng,
                name=stop.name,
                note=stop.note,
            )
        )

    await db.commit()
    result = await db.execute(
        select(Route)
        .options(selectinload(Route.stops), selectinload(Route.owner))
        .where(Route.id == new_route.id)
    )
    new_route = result.scalar_one()
    return await route_to_detail(new_route, db, user.id)

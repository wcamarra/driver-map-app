from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.route import Route, RouteVisibility
from app.models.social import Comment, Rating, SavedRoute
from app.models.user import User
from app.schemas.route import RouteDetail, RouteFeedItem, RouteStopOut
from app.services.route_builder import linestring_to_coords


async def route_stats(db: AsyncSession, route_id: int) -> tuple[float | None, int, int, int]:
    avg_result = await db.execute(
        select(func.avg(Rating.stars), func.count(Rating.id)).where(Rating.route_id == route_id)
    )
    avg_rating, rating_count = avg_result.one()
    comment_count = await db.scalar(
        select(func.count(Comment.id)).where(Comment.route_id == route_id)
    )
    save_count = await db.scalar(
        select(func.count(SavedRoute.id)).where(SavedRoute.route_id == route_id)
    )
    return (
        float(avg_rating) if avg_rating is not None else None,
        rating_count or 0,
        comment_count or 0,
        save_count or 0,
    )


async def route_to_detail(
    route: Route,
    db: AsyncSession,
    current_user_id: int | None = None,
) -> RouteDetail:
    avg_rating, rating_count, comment_count, save_count = await route_stats(db, route.id)

    user_rating = None
    user_saved = False
    if current_user_id:
        r = await db.execute(
            select(Rating.stars).where(
                Rating.route_id == route.id, Rating.user_id == current_user_id
            )
        )
        user_rating = r.scalar_one_or_none()
        s = await db.execute(
            select(SavedRoute.id).where(
                SavedRoute.route_id == route.id, SavedRoute.user_id == current_user_id
            )
        )
        user_saved = s.scalar_one_or_none() is not None

    owner = route.owner
    if owner is None:
        owner_result = await db.execute(select(User).where(User.id == route.owner_id))
        owner = owner_result.scalar_one()

    return RouteDetail(
        id=route.id,
        title=route.title,
        description=route.description,
        region=route.region,
        tags=route.tags or [],
        visibility=route.visibility,
        source=route.source,
        version=route.version,
        distance_meters=route.distance_meters,
        duration_seconds=route.duration_seconds,
        owner_id=route.owner_id,
        owner_username=owner.username,
        stops=[RouteStopOut.model_validate(s) for s in sorted(route.stops, key=lambda x: x.sequence)],
        polyline=linestring_to_coords(route.geometry),
        avg_rating=avg_rating,
        rating_count=rating_count,
        comment_count=comment_count,
        save_count=save_count,
        user_rating=user_rating,
        user_saved=user_saved,
        published_at=route.published_at,
        created_at=route.created_at,
        updated_at=route.updated_at,
    )


async def route_to_feed_item(route: Route, db: AsyncSession) -> RouteFeedItem:
    avg_rating, rating_count, comment_count, save_count = await route_stats(db, route.id)
    owner = route.owner
    if owner is None:
        owner_result = await db.execute(select(User).where(User.id == route.owner_id))
        owner = owner_result.scalar_one()

    polyline = linestring_to_coords(route.geometry)
    preview = polyline[:: max(1, len(polyline) // 50)] if polyline else None

    return RouteFeedItem(
        id=route.id,
        title=route.title,
        description=route.description,
        region=route.region,
        tags=route.tags or [],
        visibility=route.visibility,
        source=route.source,
        distance_meters=route.distance_meters,
        duration_seconds=route.duration_seconds,
        owner_username=owner.username,
        avg_rating=avg_rating,
        rating_count=rating_count,
        comment_count=comment_count,
        save_count=save_count,
        published_at=route.published_at,
        preview_polyline=preview,
    )


def can_view_route(route: Route, user_id: int | None) -> bool:
    if route.visibility == RouteVisibility.PUBLIC.value:
        return True
    if user_id and route.owner_id == user_id:
        return True
    if route.visibility == RouteVisibility.UNLISTED.value and user_id:
        return route.owner_id == user_id
    return False

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_optional_user
from app.database import get_db
from app.models.route import Route, RouteVisibility
from app.models.social import Comment, Rating, SavedRoute
from app.models.user import User
from app.api.deps import can_view_route
from app.schemas.social import CommentCreate, CommentOut, RatingCreate, RatingOut

router = APIRouter(tags=["social"])


@router.post("/routes/{route_id}/ratings", response_model=RatingOut)
async def rate_route(
    route_id: int,
    body: RatingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    route = await db.get(Route, route_id)
    if route is None or route.visibility != RouteVisibility.PUBLIC.value:
        raise HTTPException(status_code=404, detail="Route not found")

    existing = await db.execute(
        select(Rating).where(Rating.route_id == route_id, Rating.user_id == user.id)
    )
    rating = existing.scalar_one_or_none()
    if rating:
        rating.stars = body.stars
        rating.fun = body.fun
        rating.scenery = body.scenery
        rating.road_quality = body.road_quality
    else:
        rating = Rating(
            route_id=route_id,
            user_id=user.id,
            stars=body.stars,
            fun=body.fun,
            scenery=body.scenery,
            road_quality=body.road_quality,
        )
        db.add(rating)

    await db.commit()
    await db.refresh(rating)
    return RatingOut(
        id=rating.id,
        route_id=rating.route_id,
        user_id=rating.user_id,
        username=user.username,
        stars=rating.stars,
        fun=rating.fun,
        scenery=rating.scenery,
        road_quality=rating.road_quality,
        created_at=rating.created_at,
    )


@router.get("/routes/{route_id}/ratings", response_model=list[RatingOut])
async def list_ratings(route_id: int, db: AsyncSession = Depends(get_db)):
    route = await db.get(Route, route_id)
    if route is None or route.visibility != RouteVisibility.PUBLIC.value:
        raise HTTPException(status_code=404, detail="Route not found")

    result = await db.execute(
        select(Rating, User.username)
        .join(User, Rating.user_id == User.id)
        .where(Rating.route_id == route_id)
        .order_by(Rating.created_at.desc())
    )
    return [
        RatingOut(
            id=r.id,
            route_id=r.route_id,
            user_id=r.user_id,
            username=username,
            stars=r.stars,
            fun=r.fun,
            scenery=r.scenery,
            road_quality=r.road_quality,
            created_at=r.created_at,
        )
        for r, username in result.all()
    ]


@router.post("/routes/{route_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def add_comment(
    route_id: int,
    body: CommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    route = await db.get(Route, route_id)
    if route is None or route.visibility != RouteVisibility.PUBLIC.value:
        raise HTTPException(status_code=404, detail="Route not found")

    comment = Comment(route_id=route_id, user_id=user.id, body=body.body)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentOut(
        id=comment.id,
        route_id=comment.route_id,
        user_id=comment.user_id,
        username=user.username,
        body=comment.body,
        created_at=comment.created_at,
    )


@router.get("/routes/{route_id}/comments", response_model=list[CommentOut])
async def list_comments(route_id: int, db: AsyncSession = Depends(get_db)):
    route = await db.get(Route, route_id)
    if route is None or route.visibility != RouteVisibility.PUBLIC.value:
        raise HTTPException(status_code=404, detail="Route not found")

    result = await db.execute(
        select(Comment, User.username)
        .join(User, Comment.user_id == User.id)
        .where(Comment.route_id == route_id)
        .order_by(Comment.created_at.desc())
    )
    return [
        CommentOut(
            id=c.id,
            route_id=c.route_id,
            user_id=c.user_id,
            username=username,
            body=c.body,
            created_at=c.created_at,
        )
        for c, username in result.all()
    ]


@router.post("/routes/{route_id}/save", status_code=status.HTTP_201_CREATED)
async def save_route(
    route_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    route = await db.get(Route, route_id)
    if route is None or not can_view_route(route, user.id):
        raise HTTPException(status_code=404, detail="Route not found")
    if route.visibility != RouteVisibility.PUBLIC.value:
        raise HTTPException(status_code=400, detail="Can only save public routes")

    existing = await db.execute(
        select(SavedRoute).where(SavedRoute.route_id == route_id, SavedRoute.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        return {"saved": True, "message": "Already saved"}

    db.add(SavedRoute(route_id=route_id, user_id=user.id))
    await db.commit()
    return {"saved": True}


@router.delete("/routes/{route_id}/save", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_route(
    route_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedRoute).where(SavedRoute.route_id == route_id, SavedRoute.user_id == user.id)
    )
    saved = result.scalar_one_or_none()
    if saved:
        await db.delete(saved)
        await db.commit()


@router.get("/me/saved", response_model=list[int])
async def my_saved_route_ids(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SavedRoute.route_id).where(SavedRoute.user_id == user.id))
    return list(result.scalars().all())

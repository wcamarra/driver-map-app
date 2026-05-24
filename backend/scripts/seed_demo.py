"""Seed a demo user and public route. Run: python -m scripts.seed_demo"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import hash_password
from app.config import settings
from app.database import Base
from app.models.route import Route, RouteStop, RouteSource, RouteVisibility
from app.models.user import User
from app.services.route_builder import coords_to_linestring


async def seed() -> None:
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as db:
        result = await db.execute(select(User).where(User.email == "demo@drivermap.app"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email="demo@drivermap.app",
                username="demo_driver",
                password_hash=hash_password("demo12345"),
                display_name="Demo Driver",
            )
            db.add(user)
            await db.flush()

        result = await db.execute(select(Route).where(Route.owner_id == user.id, Route.title == "Blue Ridge sampler"))
        if result.scalar_one_or_none():
            print("Demo route already exists")
            await db.commit()
            return

        polyline = [
            [35.5951, -82.5515],
            [35.62, -82.48],
            [35.65, -82.42],
            [35.68, -82.38],
        ]
        route = Route(
            owner_id=user.id,
            title="Blue Ridge sampler",
            description="A short demo scenic loop — replace with your own favorite roads.",
            region="Asheville, NC",
            tags=["scenic", "demo"],
            visibility=RouteVisibility.PUBLIC.value,
            source=RouteSource.CREATED.value,
            geometry=coords_to_linestring(polyline),
            distance_meters=42000,
            duration_seconds=3600,
        )
        db.add(route)
        await db.flush()

        stops = [
            (35.5951, -82.5515, "Asheville"),
            (35.62, -82.48, "Scenic overlook"),
            (35.65, -82.42, "Mountain pass"),
            (35.68, -82.38, "Loop end"),
        ]
        for i, (lat, lng, name) in enumerate(stops):
            db.add(RouteStop(route_id=route.id, sequence=i, lat=lat, lng=lng, name=name))

        route.published_at = datetime.now(UTC)
        await db.commit()
        print("Seeded demo user demo@drivermap.app / demo12345 and route 'Blue Ridge sampler'")


if __name__ == "__main__":
    asyncio.run(seed())

from datetime import datetime
from enum import Enum

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RouteVisibility(str, Enum):
    DRAFT = "draft"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class RouteSource(str, Enum):
    CREATED = "created"
    GENERATED = "generated"
    RECORDED = "recorded"


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="Untitled route")
    description: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(120))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    visibility: Mapped[str] = mapped_column(String(20), default=RouteVisibility.DRAFT.value)
    source: Mapped[str] = mapped_column(String(20), default=RouteSource.CREATED.value)
    version: Mapped[int] = mapped_column(Integer, default=1)
    distance_meters: Mapped[float | None] = mapped_column(Float)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    geometry = mapped_column(Geometry("LINESTRING", srid=4326), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner = relationship("User", back_populates="routes")
    stops = relationship(
        "RouteStop",
        back_populates="route",
        order_by="RouteStop.sequence",
        cascade="all, delete-orphan",
    )
    ratings = relationship("Rating", back_populates="route", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="route", cascade="all, delete-orphan")
    saves = relationship("SavedRoute", back_populates="route", cascade="all, delete-orphan")


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)

    route = relationship("Route", back_populates="stops")

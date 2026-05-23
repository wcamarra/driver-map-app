from datetime import datetime

from pydantic import BaseModel, Field


class RouteStopIn(BaseModel):
    lat: float
    lng: float
    name: str | None = None
    note: str | None = None
    sequence: int | None = None


class RouteStopOut(BaseModel):
    id: int
    sequence: int
    lat: float
    lng: float
    name: str | None
    note: str | None

    model_config = {"from_attributes": True}


class RouteCreate(BaseModel):
    title: str = "Untitled route"
    description: str | None = None
    region: str | None = None
    tags: list[str] = Field(default_factory=list)


class RouteUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    region: str | None = None
    tags: list[str] | None = None
    visibility: str | None = None
    stops: list[RouteStopIn] | None = None


class RouteBuildResult(BaseModel):
    distance_meters: float
    duration_seconds: int
    polyline: list[list[float]]


class RouteFeedItem(BaseModel):
    id: int
    title: str
    description: str | None
    region: str | None
    tags: list[str]
    visibility: str
    source: str
    distance_meters: float | None
    duration_seconds: int | None
    owner_username: str
    avg_rating: float | None
    rating_count: int
    comment_count: int
    save_count: int
    published_at: datetime | None
    preview_polyline: list[list[float]] | None = None


class RouteDetail(BaseModel):
    id: int
    title: str
    description: str | None
    region: str | None
    tags: list[str]
    visibility: str
    source: str
    version: int
    distance_meters: float | None
    duration_seconds: int | None
    owner_id: int
    owner_username: str
    stops: list[RouteStopOut]
    polyline: list[list[float]] | None
    avg_rating: float | None
    rating_count: int
    comment_count: int
    save_count: int
    user_rating: int | None = None
    user_saved: bool = False
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

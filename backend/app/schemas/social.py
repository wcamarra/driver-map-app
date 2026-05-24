from datetime import datetime

from pydantic import BaseModel, Field


class RatingCreate(BaseModel):
    stars: int = Field(ge=1, le=5)
    fun: int | None = Field(default=None, ge=1, le=5)
    scenery: int | None = Field(default=None, ge=1, le=5)
    road_quality: int | None = Field(default=None, ge=1, le=5)


class RatingOut(BaseModel):
    id: int
    route_id: int
    user_id: int
    username: str
    stars: int
    fun: int | None
    scenery: int | None
    road_quality: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    route_id: int
    user_id: int
    username: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}

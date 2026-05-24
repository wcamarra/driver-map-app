from typing import Literal

from pydantic import BaseModel, Field


class GenerateRouteRequest(BaseModel):
    center_lat: float = Field(ge=-90, le=90)
    center_lng: float = Field(ge=-180, le=180)
    profile: Literal["scenic", "twisty", "relaxed"] = "scenic"
    target_distance_m: float | None = Field(default=None, ge=5000, le=200000)
    duration_minutes: int | None = Field(default=None, ge=15, le=480)
    near_lat: float | None = Field(default=None, ge=-90, le=90)
    near_lng: float | None = Field(default=None, ge=-180, le=180)
    region: str | None = None
    title: str | None = None

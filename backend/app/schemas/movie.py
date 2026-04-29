"""Movie and recommendation schemas."""

from pydantic import BaseModel, Field
from datetime import datetime


class MovieBrief(BaseModel):
    id: str
    title: str
    poster: str | None = None
    genres: list[str] = []
    rating: float = 0.0

    model_config = {"from_attributes": True}


class MovieRecommendation(BaseModel):
    id: str
    title: str
    poster: str | None = None
    genres: list[str] = []
    rating: float = 0.0
    similarity: float
    overview: str | None = None


class RecommendRequest(BaseModel):
    limit: int = Field(default=20, le=50, ge=1)
    genre_filter: list[str] | None = None
    min_year: int | None = None
    min_rating: float | None = Field(default=None, ge=0, le=10)


class RecommendResponse(BaseModel):
    recommendations: list[MovieRecommendation]
    profile_version: int
    generated_at: datetime

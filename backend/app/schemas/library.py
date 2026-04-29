"""Library system schemas."""

from pydantic import BaseModel, Field
from datetime import datetime

from app.schemas.movie import MovieBrief


class LibraryPromptRequest(BaseModel):
    prompt: str = Field(
        min_length=3,
        max_length=5000,
        examples=["Add Inception and Interstellar to watched, loved both"],
    )


class MovieMatchResult(BaseModel):
    input_title: str
    movie_id: str | None = None
    matched_title: str | None = None
    confidence: float = 0.0
    action_applied: str | None = None
    ambiguous: bool = False
    candidates: list[dict] | None = None


class LibraryPromptResponse(BaseModel):
    parsed_action: str
    results: list[MovieMatchResult]
    ambiguous_items: list[MovieMatchResult]
    taste_updated: bool


class LibraryItemOut(BaseModel):
    id: str
    movie: MovieBrief
    status: str
    sentiment: str | None = None
    added_at: datetime
    watched_at: datetime | None = None

    model_config = {"from_attributes": True}


class LibraryResponse(BaseModel):
    items: list[LibraryItemOut]
    total: int
    page: int
    per_page: int


class LibraryUpdateRequest(BaseModel):
    status: str | None = None
    sentiment: str | None = None


class ImportResponse(BaseModel):
    matched: int
    failed: int
    duplicates: int
    ambiguous: list[dict]


class ResolveItem(BaseModel):
    input_title: str
    movie_id: str
    action: str


class ResolveRequest(BaseModel):
    resolutions: list[ResolveItem]

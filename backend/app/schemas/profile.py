"""Profile request/response schemas."""

from pydantic import BaseModel, Field
from datetime import datetime


class GenerateProfileRequest(BaseModel):
    prompt: str = Field(
        min_length=10,
        max_length=2000,
        examples=["I love slow-burn psychological thrillers with unreliable narrators"],
    )


class TasteProfileResponse(BaseModel):
    id: str
    prompt: str
    tags: list[str]
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}

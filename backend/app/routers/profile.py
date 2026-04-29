"""Profile router — generate and retrieve taste profiles."""

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.taste_profile import TasteProfile
from app.schemas.profile import GenerateProfileRequest, TasteProfileResponse
from app.services.embedding import embedding_service

router = APIRouter()

# Genre/theme keywords for tag extraction
GENRE_KEYWORDS = {
    "action", "adventure", "animation", "comedy", "crime", "documentary",
    "drama", "family", "fantasy", "history", "horror", "music", "mystery",
    "romance", "sci-fi", "science fiction", "thriller", "war", "western",
}
THEME_KEYWORDS = {
    "slow-burn", "psychological", "dark", "indie", "cerebral", "mind-bending",
    "dystopian", "noir", "coming-of-age", "surreal", "atmospheric",
    "emotional", "epic", "gritty", "heartwarming", "intense", "suspenseful",
    "thought-provoking", "visually stunning", "witty", "satirical",
}


def extract_tags(prompt: str) -> list[str]:
    """Extract genre and theme tags from a prompt using keyword matching."""
    prompt_lower = prompt.lower()
    tags = []
    for keyword in GENRE_KEYWORDS | THEME_KEYWORDS:
        if re.search(r"\b" + re.escape(keyword) + r"\b", prompt_lower):
            tags.append(keyword)
    return sorted(set(tags))


@router.post("/generate", response_model=TasteProfileResponse)
async def generate_profile(
    req: GenerateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new taste profile from a natural language prompt."""
    # Get current max version for this user
    result = await db.execute(
        select(func.coalesce(func.max(TasteProfile.version), 0))
        .where(TasteProfile.user_id == user.id)
    )
    max_version = result.scalar()

    # Generate embedding
    vector = embedding_service.embed_text(req.prompt)

    # Extract tags
    tags = extract_tags(req.prompt)

    profile = TasteProfile(
        user_id=user.id,
        raw_prompt=req.prompt,
        embedding=vector,
        tags=tags,
        version=max_version + 1,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return TasteProfileResponse(
        id=str(profile.id),
        prompt=profile.raw_prompt,
        tags=profile.tags,
        version=profile.version,
        created_at=profile.created_at,
    )


@router.get("/me", response_model=TasteProfileResponse)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's latest taste profile."""
    result = await db.execute(
        select(TasteProfile)
        .where(TasteProfile.user_id == user.id)
        .order_by(TasteProfile.version.desc())
        .limit(1)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(404, "No taste profile found. Generate one first.")

    return TasteProfileResponse(
        id=str(profile.id),
        prompt=profile.raw_prompt,
        tags=profile.tags,
        version=profile.version,
        created_at=profile.created_at,
    )


@router.get("/history", response_model=list[TasteProfileResponse])
async def get_profile_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all versions of the user's taste profile."""
    result = await db.execute(
        select(TasteProfile)
        .where(TasteProfile.user_id == user.id)
        .order_by(TasteProfile.version.desc())
    )
    profiles = result.scalars().all()

    return [
        TasteProfileResponse(
            id=str(p.id),
            prompt=p.raw_prompt,
            tags=p.tags,
            version=p.version,
            created_at=p.created_at,
        )
        for p in profiles
    ]

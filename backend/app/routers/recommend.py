"""Recommendation router."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.movie import RecommendRequest, RecommendResponse, MovieRecommendation
from app.services.recommender import get_recommendations

router = APIRouter()


@router.post("", response_model=RecommendResponse)
async def recommend(
    req: RecommendRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get movie recommendations based on the user's taste profile."""
    recs, version = await get_recommendations(
        user_id=str(user.id),
        db=db,
        limit=req.limit,
        genre_filter=req.genre_filter,
        min_year=req.min_year,
        min_rating=req.min_rating,
    )

    if not recs and version == 0:
        raise HTTPException(404, "No taste profile found. Generate one first.")

    return RecommendResponse(
        recommendations=[MovieRecommendation(**r) for r in recs],
        profile_version=version,
        generated_at=datetime.now(timezone.utc),
    )

"""Taste vector updater — recomputes user taste embedding from prompt + library signals."""

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taste_profile import TasteProfile
from app.models.library import LibraryItem
from app.models.movie import Movie

# Signal weights for taste vector computation
SIGNAL_WEIGHTS = {
    "liked": 1.0,
    "disliked": -0.8,
    "watched": 0.3,
    "watchlist": 0.1,
}

# How much the prompt anchor vs library signals weigh
PROMPT_WEIGHT = 0.4
LIBRARY_WEIGHT = 0.6


async def get_latest_profile(user_id: str, db: AsyncSession) -> TasteProfile | None:
    """Get the user's latest taste profile by version."""
    result = await db.execute(
        select(TasteProfile)
        .where(TasteProfile.user_id == user_id)
        .order_by(TasteProfile.version.desc())
        .limit(1)
    )
    return result.scalars().first()


async def recompute_taste_vector(user_id: str, db: AsyncSession) -> list[float] | None:
    """
    Rebuild user taste vector from:
      1. Base prompt embedding (anchors the profile)
      2. Library signals (liked/disliked/watched movies)

    Formula: taste = normalize(0.4 * prompt_embedding + 0.6 * weighted_mean(library_embeddings))
    """
    profile = await get_latest_profile(user_id, db)
    if not profile:
        return None

    prompt_vec = np.array(profile.embedding)

    # Get all library items with their movie embeddings
    result = await db.execute(
        select(LibraryItem, Movie.embedding)
        .join(Movie, LibraryItem.movie_id == Movie.id)
        .where(LibraryItem.user_id == user_id)
        .where(Movie.embedding.isnot(None))
    )

    weighted_vecs = []
    total_weight = 0.0

    for item, movie_emb in result:
        if movie_emb is None:
            continue

        if item.sentiment == "liked":
            w = SIGNAL_WEIGHTS["liked"]
        elif item.sentiment == "disliked":
            w = SIGNAL_WEIGHTS["disliked"]
        elif item.status == "watched":
            w = SIGNAL_WEIGHTS["watched"]
        else:
            w = SIGNAL_WEIGHTS["watchlist"]

        vec = np.array(movie_emb)
        weighted_vecs.append(w * vec)
        total_weight += abs(w)

    # Combine prompt + library signals
    if weighted_vecs and total_weight > 0:
        library_vec = np.sum(weighted_vecs, axis=0) / total_weight
        combined = PROMPT_WEIGHT * prompt_vec + LIBRARY_WEIGHT * library_vec
    else:
        combined = prompt_vec

    # Normalize
    norm = np.linalg.norm(combined)
    if norm > 0:
        combined = combined / norm

    # Store updated embedding
    profile.embedding = combined.tolist()
    await db.commit()

    return combined.tolist()

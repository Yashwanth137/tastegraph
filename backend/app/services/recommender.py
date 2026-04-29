"""Recommendation engine — pgvector cosine similarity search with library integration."""

from datetime import date, datetime, timezone

from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.library import LibraryItem
from app.services.taste_updater import get_latest_profile


async def get_recommendations(
    user_id: str,
    db: AsyncSession,
    limit: int = 20,
    genre_filter: list[str] | None = None,
    min_year: int | None = None,
    min_rating: float | None = None,
) -> tuple[list[dict], int]:
    """
    Core recommendation query:
      1. Load user's taste vector
      2. Cosine similarity search via pgvector
      3. Exclude watched + disliked
      4. Boost watchlist items
      5. Apply filters
    Returns (recommendations, profile_version).
    """
    profile = await get_latest_profile(user_id, db)
    if not profile:
        return [], 0

    embedding_str = "[" + ",".join(str(x) for x in profile.embedding) + "]"

    # Build dynamic SQL for flexibility with pgvector operators
    base_query = """
        SELECT
            m.id, m.title, m.poster_path, m.genres, m.vote_average, m.overview,
            1 - (m.embedding <=> :embedding::vector) AS similarity,
            CASE WHEN wl.id IS NOT NULL THEN 0.05 ELSE 0 END AS watchlist_boost
        FROM movies m
        LEFT JOIN library_items wl
            ON wl.movie_id = m.id AND wl.user_id = :user_id AND wl.status = 'watchlist'
        WHERE m.embedding IS NOT NULL
          AND m.id NOT IN (
              SELECT movie_id FROM library_items
              WHERE user_id = :user_id AND status = 'watched'
          )
          AND m.id NOT IN (
              SELECT movie_id FROM library_items
              WHERE user_id = :user_id AND sentiment = 'disliked'
          )
    """

    params: dict = {"embedding": embedding_str, "user_id": user_id}

    # Optional filters
    if min_rating is not None:
        base_query += " AND m.vote_average >= :min_rating"
        params["min_rating"] = min_rating

    if min_year is not None:
        base_query += " AND m.release_date >= :min_date"
        params["min_date"] = date(min_year, 1, 1)

    if genre_filter:
        # JSONB array overlap check
        genre_array = "{" + ",".join(genre_filter) + "}"
        base_query += " AND m.genres ?| :genres"
        params["genres"] = genre_array

    base_query += """
        ORDER BY (1 - (m.embedding <=> :embedding::vector)) +
                 CASE WHEN wl.id IS NOT NULL THEN 0.05 ELSE 0 END DESC
        LIMIT :limit
    """
    params["limit"] = limit

    result = await db.execute(text(base_query), params)
    rows = result.fetchall()

    recommendations = []
    for r in rows:
        poster = f"https://image.tmdb.org/t/p/w500{r.poster_path}" if r.poster_path else None
        recommendations.append({
            "id": str(r.id),
            "title": r.title,
            "poster": poster,
            "genres": r.genres if r.genres else [],
            "rating": r.vote_average or 0.0,
            "similarity": round(float(r.similarity + r.watchlist_boost), 4),
            "overview": r.overview,
        })

    return recommendations, profile.version

"""Movie title matching — pg_trgm fuzzy search with exact fallback."""

from dataclasses import dataclass, field

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie

SIMILARITY_THRESHOLD = 0.3


@dataclass
class MatchResult:
    movie_id: str | None
    title: str
    confidence: float
    ambiguous: bool = False
    candidates: list[dict] = field(default_factory=list)


async def match_movie_title(raw_title: str, db: AsyncSession) -> MatchResult:
    """Map a user-typed movie title → movie_id using fuzzy matching."""
    clean = raw_title.strip()
    if not clean:
        return MatchResult(None, raw_title, 0.0)

    # 1. Exact match (case-insensitive, fast)
    result = await db.execute(
        select(Movie).where(func.lower(Movie.title) == clean.lower())
    )
    movie = result.scalars().first()
    if movie:
        return MatchResult(str(movie.id), movie.title, 1.0)

    # 2. Trigram similarity search
    rows = await db.execute(
        text("""
            SELECT id, title, similarity(LOWER(title), :q) AS sim
            FROM movies
            WHERE similarity(LOWER(title), :q) > :threshold
            ORDER BY sim DESC
            LIMIT 5
        """),
        {"q": clean.lower(), "threshold": SIMILARITY_THRESHOLD},
    )
    candidates = rows.fetchall()

    if not candidates:
        return MatchResult(None, raw_title, 0.0)

    top = candidates[0]

    # 3. Check ambiguity: top two scores are very close
    if len(candidates) >= 2 and (top.sim - candidates[1].sim) < 0.1:
        return MatchResult(
            movie_id=str(top.id),
            title=top.title,
            confidence=float(top.sim),
            ambiguous=True,
            candidates=[
                {"id": str(c.id), "title": c.title, "score": round(float(c.sim), 3)}
                for c in candidates[:3]
            ],
        )

    return MatchResult(str(top.id), top.title, float(top.sim))


async def match_movies_batch(
    titles: list[str], db: AsyncSession
) -> list[MatchResult]:
    """Match multiple titles. Returns results in same order as input."""
    return [await match_movie_title(t, db) for t in titles]

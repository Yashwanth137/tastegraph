"""TMDB movie ingestion script — fetches popular + top-rated movies and stores them."""

import asyncio
import sys
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add parent dir to path for imports
sys.path.insert(0, ".")

from app.config import settings
from app.models.movie import Movie
from app.database import Base


async def fetch_movies(endpoint: str, pages: int = 100) -> list[dict]:
    """Fetch movies from TMDB API."""
    all_movies = []
    async with httpx.AsyncClient() as client:
        for page in range(1, pages + 1):
            try:
                resp = await client.get(
                    f"{settings.TMDB_BASE_URL}/movie/{endpoint}",
                    params={"api_key": settings.TMDB_API_KEY, "page": page, "language": "en-US"},
                )
                resp.raise_for_status()
                data = resp.json()
                all_movies.extend(data.get("results", []))
                print(f"  [{endpoint}] Page {page}/{pages} — {len(data.get('results', []))} movies")

                if page >= data.get("total_pages", 1):
                    break
            except Exception as e:
                print(f"  [ERROR] Page {page}: {e}")
                break
    return all_movies


async def get_genre_map() -> dict[int, str]:
    """Fetch TMDB genre ID → name mapping."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.TMDB_BASE_URL}/genre/movie/list",
            params={"api_key": settings.TMDB_API_KEY, "language": "en-US"},
        )
        resp.raise_for_status()
        genres = resp.json().get("genres", [])
        return {g["id"]: g["name"] for g in genres}


async def seed_movies():
    """Main seeding function."""
    if not settings.TMDB_API_KEY:
        print("ERROR: TMDB_API_KEY not set. Set it in .env or environment.")
        return

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    genre_map = await get_genre_map()
    print(f"Loaded {len(genre_map)} genres from TMDB.")

    # Fetch from multiple endpoints for variety
    print("\nFetching popular movies...")
    popular = await fetch_movies("popular", pages=50)
    print(f"\nFetching top-rated movies...")
    top_rated = await fetch_movies("top_rated", pages=50)

    # Deduplicate by tmdb_id
    seen_ids = set()
    all_movies = []
    for m in popular + top_rated:
        if m["id"] not in seen_ids:
            seen_ids.add(m["id"])
            all_movies.append(m)

    print(f"\nTotal unique movies to ingest: {len(all_movies)}")

    async with session_factory() as db:
        inserted = 0
        skipped = 0

        for m in all_movies:
            # Check if already exists
            existing = await db.execute(
                select(Movie).where(Movie.tmdb_id == m["id"])
            )
            if existing.scalars().first():
                skipped += 1
                continue

            # Parse release date
            release = None
            if m.get("release_date"):
                try:
                    release = date.fromisoformat(m["release_date"])
                except ValueError:
                    pass

            # Map genre IDs to names
            genres = [genre_map.get(gid, "Unknown") for gid in m.get("genre_ids", [])]

            movie = Movie(
                tmdb_id=m["id"],
                title=m.get("title", "Unknown"),
                overview=m.get("overview", ""),
                genres=genres,
                release_date=release,
                poster_path=m.get("poster_path"),
                vote_average=m.get("vote_average", 0),
                popularity=m.get("popularity", 0),
            )
            db.add(movie)
            inserted += 1

            if inserted % 100 == 0:
                await db.commit()
                print(f"  Committed {inserted} movies...")

        await db.commit()
        print(f"\nDone! Inserted: {inserted}, Skipped (duplicates): {skipped}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_movies())

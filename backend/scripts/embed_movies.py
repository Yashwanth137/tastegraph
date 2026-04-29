"""Batch embedding script — embeds all un-embedded movies in the database."""

import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

sys.path.insert(0, ".")

from app.config import settings
from app.models.movie import Movie
from app.services.embedding import embedding_service


def build_movie_text(movie: Movie) -> str:
    """Compose rich text from movie data for embedding."""
    genres = ", ".join(movie.genres) if movie.genres else ""
    parts = [movie.title]
    if genres:
        parts.append(genres)
    if movie.overview:
        parts.append(movie.overview)
    return ". ".join(parts)


async def embed_movies():
    """Embed all movies that don't have embeddings yet."""
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        result = await db.execute(
            select(Movie).where(Movie.embedding.is_(None))
        )
        movies = result.scalars().all()
        print(f"Found {len(movies)} un-embedded movies.")

        if not movies:
            print("Nothing to embed.")
            await engine.dispose()
            return

        # Build texts
        texts = [build_movie_text(m) for m in movies]

        # Batch embed
        print("Generating embeddings (this may take a minute)...")
        vectors = embedding_service.embed_batch(texts, batch_size=64)
        print(f"Generated {len(vectors)} embeddings.")

        # Store
        for movie, vec in zip(movies, vectors):
            movie.embedding = vec
            movie.embedded_at = datetime.now(timezone.utc)

        await db.commit()
        print(f"Stored embeddings for {len(movies)} movies.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(embed_movies())

"""Movie model with pgvector embedding column."""

import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, Float, Date, DateTime, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import settings


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    genres: Mapped[dict] = mapped_column(JSONB, default=list)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    vote_average: Mapped[float] = mapped_column(Float, default=0.0)
    popularity: Mapped[float] = mapped_column(Float, default=0.0)
    embedding = mapped_column(Vector(settings.EMBEDDING_DIM), nullable=True)
    embedded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_movies_genres", "genres", postgresql_using="gin"),
        Index("idx_movies_release", "release_date"),
        Index(
            "idx_movies_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

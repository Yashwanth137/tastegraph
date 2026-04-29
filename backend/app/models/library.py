"""Library system models — unified library_items + interaction log."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, ForeignKey, UniqueConstraint, Index, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LibraryItem(Base):
    """Unified user↔movie state. Replaces the old watchlist + interactions tables."""
    __tablename__ = "library_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="watchlist"
    )
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    watched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="library_items")
    movie = relationship("Movie", lazy="joined")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_library_user_movie"),
        CheckConstraint("status IN ('watchlist', 'watched')", name="ck_library_status"),
        CheckConstraint(
            "sentiment IS NULL OR sentiment IN ('liked', 'disliked')",
            name="ck_library_sentiment",
        ),
        Index("idx_lib_user_status", "user_id", "status"),
        Index("idx_lib_user_sentiment", "user_id", "sentiment", postgresql_where="sentiment IS NOT NULL"),
        Index("idx_lib_movie", "movie_id"),
        Index("idx_lib_updated", "updated_at"),
    )


class Interaction(Base):
    """Append-only event log for all library mutations. Feeds the embedding pipeline."""
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_interactions_user", "user_id", "created_at"),
        Index("idx_interactions_user_movie", "user_id", "movie_id"),
    )

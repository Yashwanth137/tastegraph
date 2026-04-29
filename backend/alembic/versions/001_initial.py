"""Initial schema with all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # Movies
    op.create_table(
        "movies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tmdb_id", sa.Integer, unique=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("overview", sa.Text, nullable=True),
        sa.Column("genres", JSONB, server_default="'[]'"),
        sa.Column("release_date", sa.Date, nullable=True),
        sa.Column("poster_path", sa.String(500), nullable=True),
        sa.Column("vote_average", sa.Float, server_default="0"),
        sa.Column("popularity", sa.Float, server_default="0"),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    # Add vector column via raw SQL (Alembic doesn't natively handle vector type)
    op.execute("ALTER TABLE movies ADD COLUMN embedding vector(384)")
    op.create_index("idx_movies_tmdb", "movies", ["tmdb_id"])
    op.create_index("idx_movies_genres", "movies", ["genres"], postgresql_using="gin")
    op.create_index("idx_movies_release", "movies", ["release_date"])
    op.execute("CREATE INDEX idx_movies_embedding ON movies USING hnsw (embedding vector_cosine_ops)")
    op.execute("CREATE INDEX idx_movies_title_trgm ON movies USING gin (title gin_trgm_ops)")
    op.execute("CREATE INDEX idx_movies_title_lower ON movies (LOWER(title))")

    # Taste Profiles
    op.create_table(
        "taste_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_prompt", sa.Text, nullable=False),
        sa.Column("tags", JSONB, server_default="'[]'"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.execute("ALTER TABLE taste_profiles ADD COLUMN embedding vector(384) NOT NULL")
    op.create_index("idx_taste_user", "taste_profiles", ["user_id"])
    op.execute("CREATE INDEX idx_taste_embedding ON taste_profiles USING hnsw (embedding vector_cosine_ops)")

    # Library Items
    op.create_table(
        "library_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("movie_id", UUID(as_uuid=True), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="watchlist"),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("watched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "movie_id", name="uq_library_user_movie"),
        sa.CheckConstraint("status IN ('watchlist', 'watched')", name="ck_library_status"),
        sa.CheckConstraint("sentiment IS NULL OR sentiment IN ('liked', 'disliked')", name="ck_library_sentiment"),
    )
    op.create_index("idx_lib_user_status", "library_items", ["user_id", "status"])
    op.create_index("idx_lib_movie", "library_items", ["movie_id"])
    op.create_index("idx_lib_updated", "library_items", ["updated_at"])

    # Interactions
    op.create_table(
        "interactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("movie_id", UUID(as_uuid=True), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("weight", sa.Float, nullable=False),
        sa.Column("metadata", JSONB, server_default="'{}'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_interactions_user", "interactions", ["user_id", "created_at"])
    op.create_index("idx_interactions_user_movie", "interactions", ["user_id", "movie_id"])

    # Follows
    op.create_table(
        "follows",
        sa.Column("follower_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("followed_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.CheckConstraint("follower_id != followed_id", name="ck_no_self_follow"),
    )
    op.create_index("idx_follows_follower", "follows", ["follower_id"])
    op.create_index("idx_follows_followed", "follows", ["followed_id"])

    # User Similarity Cache
    op.create_table(
        "user_similarity_cache",
        sa.Column("user_a", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_b", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("similarity", sa.Float, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_similarity_a", "user_similarity_cache", ["user_a", "similarity"])


def downgrade() -> None:
    op.drop_table("user_similarity_cache")
    op.drop_table("follows")
    op.drop_table("interactions")
    op.drop_table("library_items")
    op.drop_table("taste_profiles")
    op.drop_table("movies")
    op.drop_table("users")
    op.execute('DROP EXTENSION IF EXISTS "pg_trgm"')
    op.execute('DROP EXTENSION IF EXISTS "vector"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')

"""Social router — similar users, follow/unfollow."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.follow import Follow
from app.models.taste_profile import TasteProfile
from app.schemas.social import SimilarUser, FollowResponse, UserListResponse

router = APIRouter()


@router.get("/similar-users", response_model=UserListResponse)
async def get_similar_users(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Find users with similar taste profiles using pgvector cosine similarity."""
    # Get current user's latest profile
    my_profile = await db.execute(
        select(TasteProfile)
        .where(TasteProfile.user_id == user.id)
        .order_by(TasteProfile.version.desc())
        .limit(1)
    )
    profile = my_profile.scalars().first()
    if not profile:
        raise HTTPException(404, "No taste profile found. Generate one first.")

    embedding_str = "[" + ",".join(str(x) for x in profile.embedding) + "]"

    # Find similar users via their latest profiles
    result = await db.execute(
        text("""
            SELECT DISTINCT ON (tp.user_id)
                u.id, u.username, tp.tags,
                1 - (tp.embedding <=> :embedding::vector) AS similarity
            FROM taste_profiles tp
            JOIN users u ON u.id = tp.user_id
            WHERE tp.user_id != :user_id
            ORDER BY tp.user_id, tp.version DESC, similarity DESC
        """),
        {"embedding": embedding_str, "user_id": str(user.id)},
    )
    rows = result.fetchall()

    # Sort by similarity and limit
    rows = sorted(rows, key=lambda r: r.similarity, reverse=True)[:limit]

    my_tags = set(profile.tags) if profile.tags else set()

    return UserListResponse(
        users=[
            SimilarUser(
                id=str(r.id),
                username=r.username,
                similarity=round(float(r.similarity), 4),
                shared_tags=sorted(list(my_tags & set(r.tags))) if r.tags else [],
            )
            for r in rows
        ],
        total=len(rows),
    )


@router.post("/follow/{target_id}", response_model=FollowResponse)
async def follow_user(
    target_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Follow another user."""
    if str(user.id) == target_id:
        raise HTTPException(400, "Cannot follow yourself")

    # Check target exists
    target = await db.get(User, target_id)
    if not target:
        raise HTTPException(404, "User not found")

    # Check not already following
    existing = await db.execute(
        select(Follow).where(
            Follow.follower_id == user.id,
            Follow.followed_id == target_id,
        )
    )
    if existing.scalars().first():
        raise HTTPException(409, "Already following this user")

    follow = Follow(follower_id=user.id, followed_id=target_id)
    db.add(follow)
    await db.commit()

    return FollowResponse(
        followed=True,
        follower_id=str(user.id),
        followed_id=target_id,
    )


@router.delete("/follow/{target_id}", response_model=FollowResponse)
async def unfollow_user(
    target_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unfollow a user."""
    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == user.id,
            Follow.followed_id == target_id,
        )
    )
    follow = result.scalars().first()
    if not follow:
        raise HTTPException(404, "Not following this user")

    await db.delete(follow)
    await db.commit()

    return FollowResponse(
        followed=False,
        follower_id=str(user.id),
        followed_id=target_id,
    )

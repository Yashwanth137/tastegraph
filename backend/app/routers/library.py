"""Library router — prompt-driven library management, CRUD, and bulk import."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.library import LibraryItem, Interaction
from app.models.movie import Movie
from app.schemas.library import (
    LibraryPromptRequest, LibraryPromptResponse, MovieMatchResult,
    LibraryItemOut, LibraryResponse, LibraryUpdateRequest,
)
from app.schemas.movie import MovieBrief
from app.services.prompt_parser import parse_library_prompt
from app.services.movie_matcher import match_movies_batch
from app.services.taste_updater import recompute_taste_vector

router = APIRouter()

# Interaction weights for the event log
ACTION_WEIGHTS = {
    "add_watchlist": 0.3,
    "mark_watched": 0.5,
    "like": 1.0,
    "dislike": -1.0,
    "remove": -0.2,
}


async def _apply_library_action(
    user_id: str,
    movie_id: str,
    action: str,
    sentiment: str | None,
    db: AsyncSession,
):
    """Apply a library action (add, watch, like, dislike, remove) to a movie."""
    # Get existing item
    result = await db.execute(
        select(LibraryItem).where(
            LibraryItem.user_id == user_id,
            LibraryItem.movie_id == movie_id,
        )
    )
    existing = result.scalars().first()

    if action == "remove":
        if existing:
            await db.delete(existing)
    elif action == "like":
        if existing:
            existing.status = "watched"
            existing.sentiment = "liked"
            existing.watched_at = existing.watched_at or datetime.now(timezone.utc)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            item = LibraryItem(
                user_id=user_id, movie_id=movie_id,
                status="watched", sentiment="liked",
                watched_at=datetime.now(timezone.utc),
            )
            db.add(item)
    elif action == "dislike":
        if existing:
            existing.status = "watched"
            existing.sentiment = "disliked"
            existing.watched_at = existing.watched_at or datetime.now(timezone.utc)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            item = LibraryItem(
                user_id=user_id, movie_id=movie_id,
                status="watched", sentiment="disliked",
                watched_at=datetime.now(timezone.utc),
            )
            db.add(item)
    elif action == "mark_watched":
        if existing:
            existing.status = "watched"
            existing.watched_at = datetime.now(timezone.utc)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            item = LibraryItem(
                user_id=user_id, movie_id=movie_id,
                status="watched",
                watched_at=datetime.now(timezone.utc),
            )
            db.add(item)
    else:  # add_watchlist
        if not existing:
            item = LibraryItem(
                user_id=user_id, movie_id=movie_id,
                status="watchlist",
            )
            db.add(item)

    # Log interaction
    weight = ACTION_WEIGHTS.get(action, 0.0)
    interaction = Interaction(
        user_id=user_id,
        movie_id=movie_id,
        action=action,
        weight=weight,
        metadata_={"source": "prompt", "sentiment": sentiment},
    )
    db.add(interaction)


@router.post("/prompt", response_model=LibraryPromptResponse)
async def library_prompt(
    req: LibraryPromptRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Parse a natural language prompt and apply library actions."""
    parsed = parse_library_prompt(req.prompt)
    matches = await match_movies_batch(parsed.movies, db)

    results = []
    ambiguous = []

    for title, match in zip(parsed.movies, matches):
        if match.ambiguous:
            item = MovieMatchResult(
                input_title=title, movie_id=None,
                matched_title=None, confidence=match.confidence,
                ambiguous=True, candidates=match.candidates,
            )
            ambiguous.append(item)
            results.append(item)
            continue

        if match.movie_id is None:
            results.append(MovieMatchResult(
                input_title=title, confidence=0.0,
            ))
            continue

        await _apply_library_action(
            user_id=str(user.id),
            movie_id=match.movie_id,
            action=parsed.action,
            sentiment=parsed.metadata.get("sentiment"),
            db=db,
        )

        results.append(MovieMatchResult(
            input_title=title,
            movie_id=match.movie_id,
            matched_title=match.title,
            confidence=match.confidence,
            action_applied=parsed.action,
        ))

    await db.commit()

    # Trigger taste update
    is_bulk = len(parsed.movies) > 3
    has_actions = any(r.action_applied for r in results)
    if has_actions:
        if is_bulk:
            background_tasks.add_task(recompute_taste_vector, str(user.id), db)
        else:
            await recompute_taste_vector(str(user.id), db)

    return LibraryPromptResponse(
        parsed_action=parsed.action,
        results=results,
        ambiguous_items=ambiguous,
        taste_updated=has_actions and not is_bulk,
    )


@router.get("", response_model=LibraryResponse)
async def get_library(
    status: str | None = Query(None, pattern="^(watchlist|watched)$"),
    sentiment: str | None = Query(None, pattern="^(liked|disliked)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's library with optional filters."""
    query = select(LibraryItem).where(LibraryItem.user_id == user.id)
    count_query = select(func.count(LibraryItem.id)).where(LibraryItem.user_id == user.id)

    if status:
        query = query.where(LibraryItem.status == status)
        count_query = count_query.where(LibraryItem.status == status)
    if sentiment:
        query = query.where(LibraryItem.sentiment == sentiment)
        count_query = count_query.where(LibraryItem.sentiment == sentiment)

    total = (await db.execute(count_query)).scalar() or 0

    query = (
        query.order_by(LibraryItem.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = (await db.execute(query)).scalars().all()

    return LibraryResponse(
        items=[
            LibraryItemOut(
                id=str(item.id),
                movie=MovieBrief(
                    id=str(item.movie.id),
                    title=item.movie.title,
                    poster=f"https://image.tmdb.org/t/p/w500{item.movie.poster_path}" if item.movie.poster_path else None,
                    genres=item.movie.genres or [],
                    rating=item.movie.vote_average or 0.0,
                ),
                status=item.status,
                sentiment=item.sentiment,
                added_at=item.added_at,
                watched_at=item.watched_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.patch("/{movie_id}")
async def update_library_item(
    movie_id: str,
    req: LibraryUpdateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a library item's status or sentiment."""
    result = await db.execute(
        select(LibraryItem).where(
            LibraryItem.user_id == user.id,
            LibraryItem.movie_id == movie_id,
        )
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(404, "Movie not in library")

    if req.status:
        item.status = req.status
        if req.status == "watched":
            item.watched_at = datetime.now(timezone.utc)
    if req.sentiment is not None:
        item.sentiment = req.sentiment if req.sentiment else None
    item.updated_at = datetime.now(timezone.utc)

    # Log interaction
    action = req.sentiment or req.status or "update"
    interaction = Interaction(
        user_id=str(user.id), movie_id=movie_id,
        action=action, weight=ACTION_WEIGHTS.get(action, 0.0),
        metadata_={"source": "manual"},
    )
    db.add(interaction)
    await db.commit()

    background_tasks.add_task(recompute_taste_vector, str(user.id), db)
    return {"status": "updated"}


@router.delete("/{movie_id}", status_code=204)
async def remove_from_library(
    movie_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a movie from the user's library."""
    result = await db.execute(
        select(LibraryItem).where(
            LibraryItem.user_id == user.id,
            LibraryItem.movie_id == movie_id,
        )
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(404, "Movie not in library")

    # Log removal
    interaction = Interaction(
        user_id=str(user.id), movie_id=movie_id,
        action="remove", weight=ACTION_WEIGHTS["remove"],
        metadata_={"source": "manual"},
    )
    db.add(interaction)
    await db.commit()

    background_tasks.add_task(recompute_taste_vector, str(user.id), db)

from fastapi import UploadFile, File, Form
from app.services.bulk_import import process_csv_import
from app.schemas.library import ImportResponse, ResolveRequest

@router.post("/import", response_model=ImportResponse)
async def import_library(
    background_tasks: BackgroundTasks,
    source: str = Form(pattern="^(letterboxd|imdb)$"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import library from a CSV file (Letterboxd or IMDb)."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported")

    content = await file.read()
    results = await process_csv_import(str(user.id), content, source, db)

    if results["matched"] > 0:
        background_tasks.add_task(recompute_taste_vector, str(user.id), db)

    return results


@router.post("/resolve", response_model=LibraryPromptResponse)
async def resolve_ambiguous_matches(
    req: ResolveRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve ambiguous movie matches from a previous prompt or import."""
    results = []

    for resolution in req.resolutions:
        # We assume the movie_id passed here is confirmed by the user
        await _apply_library_action(
            user_id=str(user.id),
            movie_id=resolution.movie_id,
            action=resolution.action,
            sentiment=None,  # Or pass it if needed
            db=db,
        )

        results.append(MovieMatchResult(
            input_title=resolution.input_title,
            movie_id=resolution.movie_id,
            matched_title="Resolved via ID", # Ideally fetch title, but keeping it simple
            confidence=1.0,
            action_applied=resolution.action,
            ambiguous=False,
        ))

    await db.commit()

    if results:
        background_tasks.add_task(recompute_taste_vector, str(user.id), db)

    return LibraryPromptResponse(
        parsed_action="resolved",
        results=results,
        ambiguous_items=[],
        taste_updated=True,
    )


"""Bulk CSV import service for Letterboxd and IMDb exports."""

import csv
from io import StringIO
from typing import BinaryIO

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import LibraryItem, Interaction
from app.services.movie_matcher import match_movie_title
from app.routers.library import ACTION_WEIGHTS


async def process_csv_import(
    user_id: str,
    file_content: bytes,
    source: str,
    db: AsyncSession,
) -> dict:
    """
    Process an uploaded CSV file from Letterboxd or IMDb.
    Letterboxd requires 'Name', 'Year', 'Rating'.
    IMDb requires 'Title', 'Year', 'Your Rating'.
    """
    content_str = file_content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(StringIO(content_str))

    results = {
        "matched": 0,
        "failed": 0,
        "duplicates": 0,
        "ambiguous": [],
    }

    for row in reader:
        # 1. Extract and normalize fields based on source
        title = ""
        rating_val = 0.0

        if source == "letterboxd":
            title = row.get("Name", "").strip()
            # Letterboxd ratings are 0.5 to 5.0
            rating_str = row.get("Rating", "0")
            rating_val = float(rating_str) if rating_str else 0.0
        elif source == "imdb":
            title = row.get("Title", "").strip()
            # IMDb ratings are 1 to 10. Normalize to 5-star scale.
            rating_str = row.get("Your Rating", "0")
            rating_val = float(rating_str) / 2.0 if rating_str else 0.0

        if not title:
            continue

        # 2. Match movie title
        match = await match_movie_title(title, db)

        if match.movie_id is None:
            results["failed"] += 1
            continue

        if match.ambiguous:
            results["ambiguous"].append({
                "input": title,
                "candidates": match.candidates,
            })
            continue

        # 3. Check for duplicates
        existing = await db.execute(
            select(LibraryItem).where(
                LibraryItem.user_id == user_id,
                LibraryItem.movie_id == match.movie_id,
            )
        )
        if existing.scalars().first():
            results["duplicates"] += 1
            continue

        # 4. Determine sentiment from rating
        sentiment = None
        if rating_val >= 4.0:
            sentiment = "liked"
        elif 0.0 < rating_val <= 2.5:
            # We treat <= 2.5 as disliked in a 5-star system for stronger signals
            sentiment = "disliked"

        # 5. Insert library item
        item = LibraryItem(
            user_id=user_id,
            movie_id=match.movie_id,
            status="watched",
            sentiment=sentiment,
            watched_at=func.now(),
        )
        db.add(item)

        # 6. Log interaction
        action = sentiment if sentiment else "mark_watched"
        weight = ACTION_WEIGHTS.get(action, 0.5)
        interaction = Interaction(
            user_id=user_id,
            movie_id=match.movie_id,
            action=action,
            weight=weight,
            metadata_={"source": "bulk_import", "original_rating": rating_val},
        )
        db.add(interaction)

        results["matched"] += 1

    await db.commit()
    return results

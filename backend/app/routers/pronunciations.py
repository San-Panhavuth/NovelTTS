"""REST API router for pronunciation dictionary management."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.deps.auth import get_current_user_id
from app.deps.db import get_db
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.pronunciation_entry import PronunciationEntry
from app.models.segment import Segment
from app.providers.llm import get_llm_provider
from app.services.phonetics_inference import infer_pronunciations

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pronunciations"])


# ────────────────────────────────────────────────────────────────────────────────
# Schemas
# ────────────────────────────────────────────────────────────────────────────────


class PronunciationEntrySchema:
    """Schema for pronunciation entry responses."""

    def __init__(self, entry: PronunciationEntry):
        self.id = entry.id
        self.term = entry.term
        self.phoneme = entry.phoneme
        self.language_code = entry.language_code
        self.created_at = entry.created_at
        self.updated_at = entry.updated_at

    def dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "term": self.term,
            "phoneme": self.phoneme,
            "language_code": self.language_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PronunciationCreateRequest:
    """Request to manually add a pronunciation entry."""

    def __init__(self, term: str, phoneme: str, language_code: str | None = None):
        self.term = term
        self.phoneme = phoneme
        self.language_code = language_code


class PronunciationUpdateRequest:
    """Request to edit a pronunciation entry."""

    def __init__(
        self, term: str | None = None, phoneme: str | None = None, language_code: str | None = None
    ):
        self.term = term
        self.phoneme = phoneme
        self.language_code = language_code


# ────────────────────────────────────────────────────────────────────────────────
# Helper: Check book ownership
# ────────────────────────────────────────────────────────────────────────────────


async def _check_book_ownership(
    book_id: str, user_id: str, db: AsyncSession
) -> Book:
    """Verify that the given user owns the given book. Raise 403 if not."""
    stmt = select(Book).where((Book.id == book_id) & (Book.user_id == user_id))
    result = await db.execute(stmt)
    book = result.scalars().first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this book.",
        )
    return book


# ────────────────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────────────────


@router.post("/books/{book_id}/pronunciations/infer")
async def infer_pronunciations_for_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Trigger Gemini inference on all segments for a book and store pronunciation entries.

    Returns:
        {
            "entries": [...],
            "inference_metadata": {
                "total_segments": 5,
                "segments_processed": 5,
                "unique_terms": 12
            }
        }
    """
    # Verify ownership
    await _check_book_ownership(book_id, user_id, db)

    llm_provider = get_llm_provider()

    stmt = (
        select(Chapter)
        .where(Chapter.book_id == book_id)
        .options(selectinload(Chapter.segments).selectinload(Segment.character))
        .order_by(Chapter.chapter_idx)
    )
    chapters = (await db.execute(stmt)).scalars().all()

    segments = [segment for chapter in chapters for segment in chapter.segments]

    if not segments:
        logger.warning("infer_pronunciations_for_book: no segments found for book_id=%s", book_id)
        return {
            "entries": [],
            "inference_metadata": {
                "total_segments": 0,
                "segments_processed": 0,
                "unique_terms": 0,
            },
        }

    # Collect character names from segments
    character_names = set()
    for segment in segments:
        if segment.character:
            character_names.add(segment.character.name)

    logger.info(
        "infer_pronunciations_for_book_started",
        extra={
            "book_id": book_id,
            "num_segments": len(segments),
            "num_characters": len(character_names),
        },
    )

    # Infer pronunciations for each segment and deduplicate by term
    inferred_terms: dict[str, str | None] = {}  # term -> language_code

    for idx, segment in enumerate(segments):
        inferred_entries = await infer_pronunciations(
            segment.text,
            characters=list(character_names),
            origin_language=None,  # Could be set per-book if available
            llm_provider=llm_provider,
        )

        for entry in inferred_entries:
            term = entry.get("term", "").strip()
            if term and term not in inferred_terms:
                inferred_terms[term] = entry.get("language_code")

    logger.debug(
        "infer_pronunciations_for_book_inferred",
        extra={"unique_terms": len(inferred_terms)},
    )

    # Upsert all terms into the database
    stored_entries = []
    for term, language_code in inferred_terms.items():
        # For now, use term as a simple phoneme placeholder (the LLM already inferred it)
        # In production, we'd store the actual phoneme from the LLM response.
        # For this endpoint, we'll store empty phoneme and let the user review/edit.
        result = await db.execute(
            select(PronunciationEntry).where(
                (PronunciationEntry.book_id == book_id) & (PronunciationEntry.term == term)
            )
        )
        existing = result.scalars().first()

        if not existing:
            entry = PronunciationEntry(
                id=str(uuid.uuid4()),
                book_id=book_id,
                term=term,
                phoneme="",  # User must review and set phoneme
                language_code=language_code,
            )
            db.add(entry)
            stored_entries.append(entry)
        else:
            stored_entries.append(existing)

    await db.commit()

    logger.info(
        "infer_pronunciations_for_book_complete",
        extra={"stored_entries": len(stored_entries)},
    )

    return {
        "entries": [PronunciationEntrySchema(e).dict() for e in stored_entries],
        "inference_metadata": {
            "total_segments": len(segments),
            "segments_processed": len(segments),
            "unique_terms": len(inferred_terms),
        },
    }


@router.get("/books/{book_id}/pronunciations")
async def list_pronunciations_for_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all pronunciation entries for a book."""
    # Verify ownership
    await _check_book_ownership(book_id, user_id, db)

    stmt = select(PronunciationEntry).where(PronunciationEntry.book_id == book_id)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    return {
        "entries": [PronunciationEntrySchema(e).dict() for e in entries],
        "total": len(entries),
    }


@router.post("/books/{book_id}/pronunciations")
async def add_pronunciation(
    book_id: str,
    request_data: dict[str, Any],
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Manually add a pronunciation entry.

    Request body:
        {
            "term": "魔法",
            "phoneme": "mɔː.fɑː",
            "language_code": "zh"
        }
    """
    # Verify ownership
    await _check_book_ownership(book_id, user_id, db)

    term = request_data.get("term", "").strip()
    phoneme = request_data.get("phoneme", "").strip()
    language_code = request_data.get("language_code")

    if not term or not phoneme:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="term and phoneme are required.",
        )

    # Check if already exists (upsert behavior)
    result = await db.execute(
        select(PronunciationEntry).where(
            (PronunciationEntry.book_id == book_id) & (PronunciationEntry.term == term)
        )
    )
    existing = result.scalars().first()

    if existing:
        existing.phoneme = phoneme
        existing.language_code = language_code
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pronunciation entry with that term already exists for this book.",
            ) from None
        entry = existing
    else:
        entry = PronunciationEntry(
            id=str(uuid.uuid4()),
            book_id=book_id,
            term=term,
            phoneme=phoneme,
            language_code=language_code,
        )
        db.add(entry)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pronunciation entry with that term already exists for this book.",
            ) from None

    return PronunciationEntrySchema(entry).dict()


@router.put("/books/{book_id}/pronunciations/{entry_id}")
async def update_pronunciation(
    book_id: str,
    entry_id: str,
    request_data: dict[str, Any],
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Edit a pronunciation entry."""
    # Verify ownership
    await _check_book_ownership(book_id, user_id, db)

    result = await db.execute(
        select(PronunciationEntry).where(
            (PronunciationEntry.id == entry_id) & (PronunciationEntry.book_id == book_id)
        )
    )
    entry = result.scalars().first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pronunciation entry not found.",
        )

    # Update fields if provided
    if "term" in request_data and request_data["term"]:
        entry.term = request_data["term"].strip()
    if "phoneme" in request_data and request_data["phoneme"]:
        entry.phoneme = request_data["phoneme"].strip()
    if "language_code" in request_data:
        entry.language_code = request_data.get("language_code")

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pronunciation entry with that term already exists for this book.",
        ) from None
    return PronunciationEntrySchema(entry).dict()


@router.delete("/books/{book_id}/pronunciations/{entry_id}")
async def delete_pronunciation(
    book_id: str,
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a pronunciation entry."""
    # Verify ownership
    await _check_book_ownership(book_id, user_id, db)

    result = await db.execute(
        select(PronunciationEntry).where(
            (PronunciationEntry.id == entry_id) & (PronunciationEntry.book_id == book_id)
        )
    )
    entry = result.scalars().first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pronunciation entry not found.",
        )

    db.delete(entry)
    await db.commit()

    return {"success": True, "deleted_id": entry_id}

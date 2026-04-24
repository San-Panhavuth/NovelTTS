from __future__ import annotations

import re
from html import unescape
from io import BytesIO
from uuid import uuid4

from ebooklib import ITEM_DOCUMENT, epub
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import AuthUser, get_current_user
from app.deps.db import get_db_session
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.enums import SegmentType
from app.models.segment import Segment
from app.models.user import User
from app.providers.llm import get_llm_provider
from app.services.attribution import AttributedSegment, attribute_chunk
from app.services.text_chunker import chunk_text

router = APIRouter(prefix="/books", tags=["books"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
EPUB_MIME_TYPES = {
    "application/epub+zip",
    "application/octet-stream",
}
LOW_CONFIDENCE_THRESHOLD = 0.65


class ChapterResponse(BaseModel):
    id: str
    chapter_idx: int
    title: str | None
    status: str


class ChapterDetailResponse(ChapterResponse):
    raw_text: str


class BookSummaryResponse(BaseModel):
    id: str
    title: str
    author: str | None
    chapter_count: int
    created_at: str


class BookDetailResponse(BaseModel):
    id: str
    title: str
    author: str | None
    origin_language: str | None
    chapters: list[ChapterResponse]


class ProcessChapterResponse(BaseModel):
    chapter_id: str
    chapter_idx: int
    status: str
    segment_count: int


class SegmentResponse(BaseModel):
    id: str
    segment_idx: int
    text: str
    type: SegmentType
    character_id: str | None
    character_name: str | None
    confidence: float | None
    low_confidence: bool


class CharacterSummaryResponse(BaseModel):
    id: str
    name: str
    role: str | None


class SegmentCorrectionRequest(BaseModel):
    type: SegmentType
    character_name: str | None = None


def _normalize_text(raw_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_low_confidence(confidence: float | None) -> bool:
    if confidence is None:
        return True
    return confidence < LOW_CONFIDENCE_THRESHOLD


def _normalize_character_name(value: str | None) -> str | None:
    if not value:
        return None

    normalized = re.sub(r"\s+", " ", value).strip().strip('"').strip("'")
    if not normalized:
        return None

    # DB column is VARCHAR(255).
    return normalized[:255]


async def _ensure_user_exists(session: AsyncSession, auth_user: AuthUser) -> None:
    existing_user = await session.get(User, auth_user.id)
    if existing_user:
        if auth_user.email and existing_user.email != auth_user.email:
            existing_user.email = auth_user.email
        return

    session.add(User(id=auth_user.id, email=auth_user.email))


@router.post("/upload", response_model=BookDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_epub(
    file: UploadFile = File(...),
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> BookDetailResponse:
    try:
        if file.content_type not in EPUB_MIME_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only EPUB uploads are allowed")

        payload = await file.read()
        if len(payload) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 50MB")

        try:
            parsed_book = epub.read_epub(BytesIO(payload))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed EPUB file") from exc

        chapter_items = [item for item in parsed_book.get_items_of_type(ITEM_DOCUMENT)]
        if not chapter_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No chapters found in EPUB")

        await _ensure_user_exists(session, auth_user)

        db_book = Book(
            id=str(uuid4()),
            user_id=auth_user.id,
            title=(parsed_book.get_metadata("DC", "title") or [[file.filename or "Untitled", {}]])[0][0],
            author=(parsed_book.get_metadata("DC", "creator") or [[None, {}]])[0][0],
            origin_language=(parsed_book.get_metadata("DC", "language") or [[None, {}]])[0][0],
        )
        session.add(db_book)

        db_chapters: list[Chapter] = []
        for index, item in enumerate(chapter_items):
            chapter_text = _normalize_text(item.get_body_content().decode("utf-8", errors="ignore"))
            if not chapter_text:
                continue

            db_chapter = Chapter(
                id=str(uuid4()),
                book_id=db_book.id,
                chapter_idx=index,
                title=item.get_name(),
                raw_text=chapter_text,
                status="uploaded",
            )
            db_chapters.append(db_chapter)
            session.add(db_chapter)

        if not db_chapters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No readable chapter text found in EPUB",
            )

        await session.commit()

        return BookDetailResponse(
            id=db_book.id,
            title=db_book.title,
            author=db_book.author,
            origin_language=db_book.origin_language,
            chapters=[
                ChapterResponse(
                    id=chapter.id,
                    chapter_idx=chapter.chapter_idx,
                    title=chapter.title,
                    status=chapter.status,
                )
                for chapter in db_chapters
            ],
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload processing failed: {exc}",
        ) from exc


@router.get("", response_model=list[BookSummaryResponse])
async def list_books(
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[BookSummaryResponse]:
    stmt: Select[tuple[Book]] = select(Book).where(Book.user_id == auth_user.id).order_by(Book.created_at.desc())
    books = (await session.execute(stmt)).scalars().all()

    result: list[BookSummaryResponse] = []
    for book in books:
        chapter_count_stmt = select(Chapter).where(Chapter.book_id == book.id)
        chapters = (await session.execute(chapter_count_stmt)).scalars().all()
        result.append(
            BookSummaryResponse(
                id=book.id,
                title=book.title,
                author=book.author,
                chapter_count=len(chapters),
                created_at=book.created_at.isoformat(),
            )
        )
    return result


@router.get("/{book_id}", response_model=BookDetailResponse)
async def get_book(
    book_id: str,
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> BookDetailResponse:
    book = await session.get(Book, book_id)
    if not book or book.user_id != auth_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    chapter_stmt = select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.chapter_idx.asc())
    chapters = (await session.execute(chapter_stmt)).scalars().all()

    return BookDetailResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        origin_language=book.origin_language,
        chapters=[
            ChapterResponse(
                id=chapter.id,
                chapter_idx=chapter.chapter_idx,
                title=chapter.title,
                status=chapter.status,
            )
            for chapter in chapters
        ],
    )


@router.get("/{book_id}/chapters/{index}", response_model=ChapterDetailResponse)
async def get_book_chapter(
    book_id: str,
    index: int,
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChapterDetailResponse:
    book = await session.get(Book, book_id)
    if not book or book.user_id != auth_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    stmt = select(Chapter).where(Chapter.book_id == book.id, Chapter.chapter_idx == index)
    chapter = (await session.execute(stmt)).scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    return ChapterDetailResponse(
        id=chapter.id,
        chapter_idx=chapter.chapter_idx,
        title=chapter.title,
        status=chapter.status,
        raw_text=chapter.raw_text,
    )


@router.post("/{book_id}/chapters/{index}/process", response_model=ProcessChapterResponse)
async def process_book_chapter(
    book_id: str,
    index: int,
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProcessChapterResponse:
    try:
        book = await session.get(Book, book_id)
        if not book or book.user_id != auth_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        chapter_stmt = (
            select(Chapter)
            .where(Chapter.book_id == book.id, Chapter.chapter_idx == index)
            .with_for_update()
        )
        chapter = (await session.execute(chapter_stmt)).scalar_one_or_none()
        if chapter is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

        chapter_chunks = chunk_text(chapter.raw_text)
        if not chapter_chunks:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chapter has no processable text")

        llm_provider = get_llm_provider()

        existing_characters_stmt = select(Character).where(Character.book_id == book.id)
        existing_characters = (await session.execute(existing_characters_stmt)).scalars().all()
        characters_by_name: dict[str, Character] = {
            character.name.lower(): character for character in existing_characters
        }
        characters_by_id: dict[str, Character] = {character.id: character for character in existing_characters}

        await session.execute(delete(Segment).where(Segment.chapter_id == chapter.id))
        await session.flush()

        created_segments: list[Segment] = []
        segment_idx = 0
        known_character_names = [character.name for character in existing_characters]
        last_known_speaker: str | None = None

        # Seed speaker memory from previously processed chapters in this book.
        previous_named_dialogue_stmt = (
            select(Segment, Chapter)
            .join(Chapter, Segment.chapter_id == Chapter.id)
            .where(
                Chapter.book_id == book.id,
                Chapter.chapter_idx < chapter.chapter_idx,
                Segment.type == SegmentType.DIALOGUE,
                Segment.character_id.is_not(None),
            )
            .order_by(Chapter.chapter_idx.desc(), Segment.segment_idx.desc())
            .limit(1)
        )
        previous_named_dialogue = (await session.execute(previous_named_dialogue_stmt)).first()
        if previous_named_dialogue is not None:
            previous_segment = previous_named_dialogue[0]
            previous_character = characters_by_id.get(previous_segment.character_id or "")
            if previous_character is not None:
                last_known_speaker = previous_character.name
        for chunk in chapter_chunks:
            attributed_segments: list[AttributedSegment] = await attribute_chunk(
                chunk,
                llm_provider,
                known_characters=known_character_names,
                last_speaker=last_known_speaker,
            )
            for attributed in attributed_segments:
                character_id: str | None = None
                character_name = _normalize_character_name(attributed.character)
                if character_name:
                    key = character_name.lower()
                    character = characters_by_name.get(key)
                    if character is None:
                        character = Character(
                            id=str(uuid4()),
                            book_id=book.id,
                            name=character_name,
                            role=None,
                            voice_id=None,
                        )
                        session.add(character)
                        characters_by_name[key] = character
                    character_id = character.id
                    if character.name not in known_character_names:
                        known_character_names.append(character.name)
                        characters_by_id[character.id] = character
                    if attributed.type == SegmentType.DIALOGUE:
                        last_known_speaker = character.name

                segment = Segment(
                    id=str(uuid4()),
                    chapter_id=chapter.id,
                    segment_idx=segment_idx,
                    text=attributed.text,
                    type=attributed.type,
                    character_id=character_id,
                    confidence=attributed.confidence,
                )
                created_segments.append(segment)
                session.add(segment)
                segment_idx += 1

        chapter.status = "processed"
        await session.commit()

        return ProcessChapterResponse(
            chapter_id=chapter.id,
            chapter_idx=chapter.chapter_idx,
            status=chapter.status,
            segment_count=len(created_segments),
        )
    except HTTPException:
        await session.rollback()
        raise
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chapter processing failed: {exc}",
        ) from exc


@router.get("/{book_id}/chapters/{index}/segments", response_model=list[SegmentResponse])
async def list_chapter_segments(
    book_id: str,
    index: int,
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SegmentResponse]:
    book = await session.get(Book, book_id)
    if not book or book.user_id != auth_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    chapter_stmt = select(Chapter).where(Chapter.book_id == book.id, Chapter.chapter_idx == index)
    chapter = (await session.execute(chapter_stmt)).scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    segments_stmt = select(Segment).where(Segment.chapter_id == chapter.id).order_by(Segment.segment_idx.asc())
    segments = (await session.execute(segments_stmt)).scalars().all()
    characters_stmt = select(Character).where(Character.book_id == book.id)
    characters = (await session.execute(characters_stmt)).scalars().all()
    character_name_by_id = {character.id: character.name for character in characters}

    return [
        SegmentResponse(
            id=segment.id,
            segment_idx=segment.segment_idx,
            text=segment.text,
            type=segment.type,
            character_id=segment.character_id,
            character_name=character_name_by_id.get(segment.character_id) if segment.character_id else None,
            confidence=segment.confidence,
            low_confidence=_is_low_confidence(segment.confidence),
        )
        for segment in segments
    ]


@router.get("/{book_id}/characters", response_model=list[CharacterSummaryResponse])
async def list_book_characters(
    book_id: str,
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[CharacterSummaryResponse]:
    book = await session.get(Book, book_id)
    if not book or book.user_id != auth_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    characters_stmt = select(Character).where(Character.book_id == book.id).order_by(Character.name.asc())
    characters = (await session.execute(characters_stmt)).scalars().all()

    return [
        CharacterSummaryResponse(id=character.id, name=character.name, role=character.role)
        for character in characters
    ]


@router.patch("/{book_id}/chapters/{index}/segments/{segment_id}", response_model=SegmentResponse)
async def update_chapter_segment(
    book_id: str,
    index: int,
    segment_id: str,
    payload: SegmentCorrectionRequest,
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SegmentResponse:
    book = await session.get(Book, book_id)
    if not book or book.user_id != auth_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    chapter_stmt = select(Chapter).where(Chapter.book_id == book.id, Chapter.chapter_idx == index)
    chapter = (await session.execute(chapter_stmt)).scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    segment_stmt = select(Segment).where(Segment.id == segment_id, Segment.chapter_id == chapter.id)
    segment = (await session.execute(segment_stmt)).scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")

    character_name = _normalize_character_name(payload.character_name)
    character_id: str | None = None
    resolved_character_name: str | None = None

    if character_name:
        existing_character_stmt = select(Character).where(Character.book_id == book.id)
        existing_characters = (await session.execute(existing_character_stmt)).scalars().all()
        by_name = {character.name.lower(): character for character in existing_characters}

        character = by_name.get(character_name.lower())
        if character is None:
            character = Character(
                id=str(uuid4()),
                book_id=book.id,
                name=character_name,
                role=None,
                voice_id=None,
            )
            session.add(character)
        character_id = character.id
        resolved_character_name = character.name

    segment.type = payload.type
    segment.character_id = character_id
    # Manual correction is treated as high confidence.
    segment.confidence = 1.0

    await session.commit()

    return SegmentResponse(
        id=segment.id,
        segment_idx=segment.segment_idx,
        text=segment.text,
        type=segment.type,
        character_id=segment.character_id,
        character_name=resolved_character_name,
        confidence=segment.confidence,
        low_confidence=_is_low_confidence(segment.confidence),
    )

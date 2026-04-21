from __future__ import annotations

import re
from html import unescape
from io import BytesIO
from uuid import uuid4

from ebooklib import ITEM_DOCUMENT, epub
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import AuthUser, get_current_user
from app.deps.db import get_db_session
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.user import User

router = APIRouter(prefix="/books", tags=["books"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
EPUB_MIME_TYPES = {
    "application/epub+zip",
    "application/octet-stream",
}


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


def _normalize_text(raw_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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

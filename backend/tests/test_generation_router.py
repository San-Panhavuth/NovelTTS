from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.deps.auth import AuthUser
from app.models.audio_job import AudioJob
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.enums import JobStatus
from app.routers.generation import generate_chapter_audio, get_job_status


class _FakeScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSession:
    def __init__(self, *, chapter: Chapter, book: Book, latest_job: AudioJob | None = None) -> None:
        self._chapter = chapter
        self._book = book
        self._latest_job = latest_job
        self.added: list[object] = []
        self.committed = False

    async def get(self, model: type, id_value: str) -> object | None:
        if model is Book and id_value == self._book.id:
            return self._book
        if model is AudioJob and self._latest_job and id_value == self._latest_job.id:
            return self._latest_job
        if model is Chapter and id_value == self._chapter.id:
            return self._chapter
        return None

    async def execute(self, statement: object) -> _FakeScalarResult:  # noqa: ARG002
        # Generation router issues select(Chapter...) first, then select(AudioJob...)
        if self._chapter is not None:
            chapter = self._chapter
            self._chapter = None  # type: ignore[assignment]
            return _FakeScalarResult(chapter)
        return _FakeScalarResult(self._latest_job)

    def add(self, item: object) -> None:
        self.added.append(item)
        if isinstance(item, AudioJob):
            self._latest_job = item

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_generate_chapter_audio_queues_job() -> None:
    book = Book(
        id="book-1",
        user_id="user-1",
        title="Test",
        author=None,
        origin_language=None,
    )
    chapter = Chapter(
        id="chapter-1",
        book_id=book.id,
        chapter_idx=1,
        title="Ch",
        raw_text="x",
        status="processed",
    )
    session = _FakeSession(chapter=chapter, book=book, latest_job=None)
    auth_user = AuthUser(id="user-1", email="u@example.com")
    tasks = BackgroundTasks()

    result = await generate_chapter_audio(
        book_id=book.id,
        chapter_idx=1,
        background_tasks=tasks,
        auth_user=auth_user,
        session=session,  # type: ignore[arg-type]
    )

    assert result.status == JobStatus.QUEUED
    assert result.job_id
    assert chapter.status == "generating"
    assert session.committed
    assert len(tasks.tasks) == 1


@pytest.mark.asyncio
async def test_generate_chapter_audio_rejects_when_job_running() -> None:
    book = Book(
        id="book-1",
        user_id="user-1",
        title="Test",
        author=None,
        origin_language=None,
    )
    chapter = Chapter(
        id="chapter-1",
        book_id=book.id,
        chapter_idx=1,
        title="Ch",
        raw_text="x",
        status="processed",
    )
    running_job = AudioJob(
        id="job-1",
        chapter_id=chapter.id,
        status=JobStatus.PROCESSING,
        provider="edge_tts",
        progress=50,
        error=None,
        output_url=None,
    )
    running_job.created_at = datetime.utcnow()
    session = _FakeSession(chapter=chapter, book=book, latest_job=running_job)
    auth_user = AuthUser(id="user-1", email="u@example.com")

    with pytest.raises(HTTPException, match="already running"):
        await generate_chapter_audio(
            book_id=book.id,
            chapter_idx=1,
            background_tasks=BackgroundTasks(),
            auth_user=auth_user,
            session=session,  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_get_job_status_returns_job_payload() -> None:
    book = Book(
        id="book-1",
        user_id="user-1",
        title="Test",
        author=None,
        origin_language=None,
    )
    chapter = Chapter(
        id="chapter-1",
        book_id=book.id,
        chapter_idx=1,
        title="Ch",
        raw_text="x",
        status="processed",
    )
    job = AudioJob(
        id="job-1",
        chapter_id=chapter.id,
        status=JobStatus.COMPLETED,
        provider="edge_tts",
        progress=100,
        error=None,
        output_url="https://example/audio.mp3",
    )
    session = _FakeSession(chapter=chapter, book=book, latest_job=job)
    auth_user = AuthUser(id="user-1", email="u@example.com")

    payload = await get_job_status(
        job_id=job.id,
        auth_user=auth_user,
        session=session,  # type: ignore[arg-type]
    )

    assert payload.job_id == "job-1"
    assert payload.status == JobStatus.COMPLETED
    assert payload.progress == 100

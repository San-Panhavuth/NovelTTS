from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps.auth import AuthUser, get_current_user
from app.deps.db import get_db_session
from app.models.audio_job import AudioJob
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.enums import JobStatus
from app.services.audio_generation import run_generation
from app.services.job_queue import enqueue_audio_generation_job

logger = logging.getLogger(__name__)
router = APIRouter(tags=["generation"])


class GenerateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    error: str | None
    output_url: str | None


async def _load_chapter(
    session: AsyncSession, auth_user: AuthUser, book_id: str, chapter_idx: int
) -> Chapter:
    book = await session.get(Book, book_id)
    if not book or book.user_id != auth_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    chapter = (
        await session.execute(
            select(Chapter).where(
                Chapter.book_id == book_id,
                Chapter.chapter_idx == chapter_idx,
            )
        )
    ).scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    return chapter


@router.post(
    "/books/{book_id}/chapters/{chapter_idx}/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_chapter_audio(
    book_id: str,
    chapter_idx: int,
    auth_user: AuthUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> GenerateResponse:
    chapter = await _load_chapter(session, auth_user, book_id, chapter_idx)

    # Cancel any running job for this chapter first
    existing = (
        await session.execute(
            select(AudioJob)
            .where(AudioJob.chapter_id == chapter.id)
            .order_by(AudioJob.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if existing and existing.status in (JobStatus.QUEUED, JobStatus.PROCESSING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A generation job is already running for this chapter",
        )

    job = AudioJob(
        id=str(uuid4()),
        chapter_id=chapter.id,
        status=JobStatus.QUEUED,
        provider="edge_tts",
        progress=0,
    )
    session.add(job)
    chapter.status = "generating"
    await session.commit()

    logger.info("generation: enqueued job=%s chapter=%s", job.id, chapter.id)
    await enqueue_audio_generation_job(job.id, auth_user.id)

    return GenerateResponse(job_id=job.id, status=JobStatus.QUEUED)


class WorkerGenerateRequest(BaseModel):
    job_id: str
    user_id: str


@router.post("/internal/worker/audio-generate", status_code=status.HTTP_202_ACCEPTED)
async def internal_worker_audio_generate(
    body: WorkerGenerateRequest,
    x_worker_secret: str | None = Header(default=None),
) -> dict[str, str]:
    if x_worker_secret != settings.worker_shared_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized worker")

    await run_generation(body.job_id, body.user_id)
    return {"status": "accepted"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    auth_user: AuthUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> JobStatusResponse:
    job = await session.get(AudioJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Verify ownership via chapter → book
    chapter = await session.get(Chapter, job.chapter_id)
    if chapter:
        book = await session.get(Book, chapter.book_id)
        if not book or book.user_id != auth_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        error=job.error,
        output_url=job.output_url,
    )


@router.get("/audio/{book_id}/{chapter_id}.mp3")
async def stream_chapter_audio(
    book_id: str,
    chapter_id: str,
    auth_user: AuthUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> Response:
    book = await session.get(Book, book_id)
    if not book or book.user_id != auth_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

    chapter = await session.get(Chapter, chapter_id)
    if chapter is None or chapter.book_id != book_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

    from app.providers.storage.r2 import get_storage_provider

    storage = get_storage_provider()
    key = f"audio/{book_id}/{chapter_id}.mp3"
    try:
        payload = await storage.get(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("generation: failed to fetch audio key=%s error=%s", key, exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found") from exc

    return Response(content=payload, media_type="audio/mpeg")

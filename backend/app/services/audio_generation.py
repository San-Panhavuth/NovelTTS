"""Audio generation pipeline: segments → TTS → FFmpeg stitch → R2 upload."""
from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.audio_job import AudioJob
from app.models.chapter import Chapter
from app.models.enums import JobStatus, SegmentType
from app.models.segment import Segment
from app.models.voice import Voice
from app.models.voice_assignment import VoiceAssignment
from app.providers.tts.edge import EdgeTTSProvider

logger = logging.getLogger(__name__)
SEGMENT_SYNTH_MAX_RETRIES = 3
DEFAULT_EDGE_VOICE = "en-US-AriaNeural"


def _resolve_ffmpeg_binary() -> str:
    resolved = shutil.which("ffmpeg")
    if resolved:
        return resolved

    windows_candidates = [
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/FFmpeg/bin/ffmpeg.exe"),
        Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"),
    ]
    for candidate in windows_candidates:
        if candidate.exists():
            return str(candidate)
    return "ffmpeg"


def _to_asyncpg_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


def _content_hash(text: str, voice_id: str) -> str:
    return hashlib.sha256(f"{voice_id}:{text}".encode()).hexdigest()[:16]


def _is_valid_edge_voice_id(voice_id: str | None) -> bool:
    # Edge voices are identifiers like en-US-AriaNeural.
    if not voice_id:
        return False
    if "Neural" not in voice_id:
        return False
    return voice_id.count("-") >= 2


async def _set_job_status(
    session: AsyncSession,
    job: AudioJob,
    status: JobStatus,
    progress: int = 0,
    error: str | None = None,
    output_url: str | None = None,
) -> None:
    job.status = status
    job.progress = progress
    if error is not None:
        job.error = error
    if output_url is not None:
        job.output_url = output_url
    await session.commit()


async def _synthesize_with_retries(
    tts: EdgeTTSProvider,
    seg_type: SegmentType,
    text: str,
    dialogue_voice: str,
    narration_voice: str,
    thought_pitch: float,
    max_retries: int = SEGMENT_SYNTH_MAX_RETRIES,
) -> bytes:
    last_error: Exception | None = None
    active_dialogue_voice = dialogue_voice if _is_valid_edge_voice_id(dialogue_voice) else DEFAULT_EDGE_VOICE
    active_narration_voice = narration_voice if _is_valid_edge_voice_id(narration_voice) else DEFAULT_EDGE_VOICE
    for attempt in range(1, max_retries + 1):
        try:
            if seg_type == SegmentType.NARRATION:
                return await tts.synthesize(text, active_narration_voice)
            if seg_type == SegmentType.THOUGHT:
                return await tts.synthesize_with_pitch(text, active_dialogue_voice, thought_pitch)
            return await tts.synthesize(text, active_dialogue_voice)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if "Invalid voice" in str(exc):
                active_dialogue_voice = DEFAULT_EDGE_VOICE
                active_narration_voice = DEFAULT_EDGE_VOICE
            logger.warning(
                "generation: segment synth attempt %d/%d failed: %s",
                attempt,
                max_retries,
                exc,
            )
    raise RuntimeError(f"Segment synthesis failed after {max_retries} attempts: {last_error}")


def _run_ffmpeg_concat(concat_list: Path, output_mp3: Path) -> None:
    ffmpeg_cmd = [
        _resolve_ffmpeg_binary(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-af",
        "aresample=async=1:first_pts=0",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "4",
        str(output_mp3),
    ]
    try:
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            timeout=300,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "FFmpeg executable was not found. Install FFmpeg and ensure it is in PATH."
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="ignore").strip()
        raise RuntimeError(stderr or "FFmpeg failed without stderr output")


async def _resolve_voices(
    session: AsyncSession, user_id: str, book_id: str
) -> tuple[str | None, str | None, float]:
    rows = (
        await session.execute(
            select(VoiceAssignment).where(
                VoiceAssignment.user_id == user_id,
                VoiceAssignment.book_id.in_([None, book_id]),
            )
        )
    ).scalars().all()

    default = next((r for r in rows if r.book_id is None), None)
    override = next((r for r in rows if r.book_id == book_id), None)

    narration = (override.narration_voice_id if override else None) or (
        default.narration_voice_id if default else None
    )
    dialogue = (override.dialogue_voice_id if override else None) or (
        default.dialogue_voice_id if default else None
    )
    pitch = (
        override.thought_pitch_semitones
        if override is not None and override.thought_pitch_semitones != -2.0
        else (default.thought_pitch_semitones if default is not None else -2.0)
    )
    voice_uuid_values = [voice_id for voice_id in (narration, dialogue) if voice_id]
    if not voice_uuid_values:
        return narration, dialogue, pitch

    voice_rows = (
        await session.execute(select(Voice).where(Voice.id.in_(voice_uuid_values)))
    ).scalars().all()
    provider_by_uuid = {voice.id: voice.provider_id for voice in voice_rows}

    narration_provider = provider_by_uuid.get(narration, narration) if narration else None
    dialogue_provider = provider_by_uuid.get(dialogue, dialogue) if dialogue else None
    return narration_provider, dialogue_provider, pitch


async def run_generation(job_id: str, user_id: str) -> None:
    """Entry point for background task. Owns its own DB session."""
    engine = create_async_engine(_to_asyncpg_url(settings.database_url), echo=False)
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with Session() as session:
            job = await session.get(AudioJob, job_id)
            if job is None:
                logger.error("generation: job %s not found", job_id)
                return

            # Avoid async lazy-loading on relationship access, which can fail and leave
            # a job stuck at queued if the task crashes before status transition.
            chapter_id = job.chapter_id
            chapter = await session.get(Chapter, chapter_id)
            if chapter is None:
                await _set_job_status(
                    session,
                    job,
                    JobStatus.FAILED,
                    error="Chapter not found for generation job",
                )
                return
            book_id = chapter.book_id

            logger.info("generation: job=%s chapter=%s starting", job_id, chapter.id)
            await _set_job_status(session, job, JobStatus.PROCESSING, progress=0)

            segments = (
                await session.execute(
                    select(Segment)
                    .where(Segment.chapter_id == chapter.id)
                    .order_by(Segment.segment_idx.asc())
                )
            ).scalars().all()

            if not segments:
                await _set_job_status(
                    session, job, JobStatus.FAILED, error="No segments to synthesize"
                )
                return

            narration_voice, dialogue_voice, thought_pitch = await _resolve_voices(
                session, user_id, book_id
            )

            # Fall back to a default Edge TTS voice if nothing is configured
            narration_voice = narration_voice or DEFAULT_EDGE_VOICE
            dialogue_voice = dialogue_voice or DEFAULT_EDGE_VOICE

            # Guard against stale/incorrect voice ids persisted in DB.
            if not _is_valid_edge_voice_id(narration_voice):
                logger.warning(
                    "generation: invalid narration voice '%s', using fallback '%s'",
                    narration_voice,
                    DEFAULT_EDGE_VOICE,
                )
                narration_voice = DEFAULT_EDGE_VOICE
            if not _is_valid_edge_voice_id(dialogue_voice):
                logger.warning(
                    "generation: invalid dialogue voice '%s', using fallback '%s'",
                    dialogue_voice,
                    DEFAULT_EDGE_VOICE,
                )
                dialogue_voice = DEFAULT_EDGE_VOICE

            tts = EdgeTTSProvider()
            chunk_paths: list[Path] = []
            total = len(segments)

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)

                for i, seg in enumerate(segments):
                    try:
                        audio = await _synthesize_with_retries(
                            tts=tts,
                            seg_type=seg.type,
                            text=seg.text,
                            dialogue_voice=dialogue_voice,
                            narration_voice=narration_voice,
                            thought_pitch=thought_pitch,
                        )

                        chunk_file = tmp / f"{i:05d}.mp3"
                        chunk_file.write_bytes(audio)
                        chunk_paths.append(chunk_file)
                        logger.info(
                            "generation: job=%s segment=%d/%d ok", job_id, i + 1, total
                        )
                    except Exception as exc:
                        logger.warning(
                            "generation: job=%s segment=%d failed: %s", job_id, i + 1, exc
                        )
                        # Write silence placeholder so stitching still works
                        chunk_paths.append(None)  # type: ignore[arg-type]

                    progress = int((i + 1) / total * 80)
                    await _set_job_status(session, job, JobStatus.PROCESSING, progress=progress)

                # Stitch with FFmpeg
                valid_chunks = [p for p in chunk_paths if p is not None]
                if not valid_chunks:
                    await _set_job_status(
                        session, job, JobStatus.FAILED, error="All segments failed synthesis"
                    )
                    return

                concat_list = tmp / "concat.txt"
                concat_list.write_text(
                    "\n".join(f"file '{p.as_posix()}'" for p in valid_chunks)
                )
                output_mp3 = tmp / "chapter.mp3"

                try:
                    _run_ffmpeg_concat(concat_list=concat_list, output_mp3=output_mp3)
                except Exception as exc:
                    logger.error("generation: ffmpeg failed: %s", exc)
                    await _set_job_status(session, job, JobStatus.FAILED, error=f"FFmpeg: {exc}")
                    return

                logger.info("generation: job=%s stitching done, uploading", job_id)
                await _set_job_status(session, job, JobStatus.PROCESSING, progress=90)

                # Upload to R2 (or save locally if R2 not configured)
                audio_bytes = output_mp3.read_bytes()
                output_url = await _upload_audio(audio_bytes, book_id, chapter.id)

                # Update chapter status
                chapter.status = "done"
                await _set_job_status(
                    session, job, JobStatus.COMPLETED, progress=100, output_url=output_url
                )
                logger.info("generation: job=%s complete url=%s", job_id, output_url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("generation: job=%s crashed before completion: %s", job_id, exc)
        async with Session() as rescue_session:
            rescue_job = await rescue_session.get(AudioJob, job_id)
            if rescue_job is not None and rescue_job.status in (
                JobStatus.QUEUED,
                JobStatus.PROCESSING,
            ):
                await _set_job_status(
                    rescue_session,
                    rescue_job,
                    JobStatus.FAILED,
                    error=f"Generation crashed: {exc}",
                )
    finally:
        await engine.dispose()


async def _upload_audio(audio_bytes: bytes, book_id: str, chapter_id: str) -> str:
    if not settings.r2_endpoint or not settings.r2_bucket:
        # No R2 configured — save to a local temp path and return a placeholder
        out = Path(tempfile.gettempdir()) / f"noveltts_{chapter_id}.mp3"
        out.write_bytes(audio_bytes)
        logger.warning("generation: R2 not configured, saved locally to %s", out)
        return f"local://{out}"

    from app.providers.storage.r2 import get_storage_provider
    storage = get_storage_provider()
    key = f"audio/{book_id}/{chapter_id}.mp3"
    return await storage.put(key, audio_bytes)

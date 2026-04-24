from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import AuthUser, get_current_user
from app.deps.db import get_db_session
from app.models.book import Book
from app.models.voice import Voice
from app.models.voice_assignment import VoiceAssignment
from app.services.voice_resolution import ResolvedAssignment, resolve_voice_assignment

router = APIRouter(tags=["voice-settings"])


# --- shared helpers ---

async def _load_owned_book(session: AsyncSession, auth_user: AuthUser, book_id: str) -> Book:
    book = await session.get(Book, book_id)
    if not book or book.user_id != auth_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


# --- schemas ---

class VoiceResponse(BaseModel):
    id: str
    provider: str
    provider_id: str
    name: str
    gender: str | None
    locale: str | None
    pitch: str | None
    age_group: str | None
    tone: str | None
    energy: str | None
    sample_url: str | None


class VoiceAssignmentBody(BaseModel):
    narration_voice_id: str | None = None
    dialogue_voice_id: str | None = None
    thought_pitch_semitones: float = Field(default=-2.0, ge=-12.0, le=0.0)


class VoiceAssignmentResponse(BaseModel):
    scope: str
    narration_voice_id: str | None
    dialogue_voice_id: str | None
    thought_pitch_semitones: float


class ResolvedAssignmentResponse(BaseModel):
    narration_voice_id: str | None
    dialogue_voice_id: str | None
    thought_pitch_semitones: float


# --- voice catalog ---

@router.get("/voices", response_model=list[VoiceResponse])
async def list_voices(
    auth_user: AuthUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[VoiceResponse]:
    _ = auth_user
    voices = (await session.execute(select(Voice).order_by(Voice.name.asc()))).scalars().all()
    return [
        VoiceResponse(
            id=v.id,
            provider=v.provider,
            provider_id=v.provider_id,
            name=v.name,
            gender=v.gender,
            locale=v.locale,
            pitch=v.pitch,
            age_group=v.age_group,
            tone=v.tone,
            energy=v.energy,
            sample_url=v.sample_url,
        )
        for v in voices
    ]


# --- user defaults ---

@router.get("/voice-settings/defaults", response_model=VoiceAssignmentResponse)
async def get_user_defaults(
    auth_user: AuthUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> VoiceAssignmentResponse:
    row = await _get_or_create_user_default(session, auth_user.id)
    await session.commit()
    return VoiceAssignmentResponse(
        scope="user",
        narration_voice_id=row.narration_voice_id,
        dialogue_voice_id=row.dialogue_voice_id,
        thought_pitch_semitones=row.thought_pitch_semitones,
    )


@router.put("/voice-settings/defaults", response_model=VoiceAssignmentResponse)
async def update_user_defaults(
    body: VoiceAssignmentBody,
    auth_user: AuthUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> VoiceAssignmentResponse:
    row = await _get_or_create_user_default(session, auth_user.id)
    row.narration_voice_id = body.narration_voice_id
    row.dialogue_voice_id = body.dialogue_voice_id
    row.thought_pitch_semitones = body.thought_pitch_semitones
    await session.commit()
    return VoiceAssignmentResponse(
        scope="user",
        narration_voice_id=row.narration_voice_id,
        dialogue_voice_id=row.dialogue_voice_id,
        thought_pitch_semitones=row.thought_pitch_semitones,
    )


# --- per-book settings ---

@router.get("/books/{book_id}/voice-settings", response_model=ResolvedAssignmentResponse)
async def get_book_voice_settings(
    book_id: str,
    auth_user: AuthUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ResolvedAssignmentResponse:
    await _load_owned_book(session, auth_user, book_id)
    resolved: ResolvedAssignment = await resolve_voice_assignment(session, auth_user.id, book_id)
    return ResolvedAssignmentResponse(
        narration_voice_id=resolved.narration_voice_id,
        dialogue_voice_id=resolved.dialogue_voice_id,
        thought_pitch_semitones=resolved.thought_pitch_semitones,
    )


@router.put("/books/{book_id}/voice-settings", response_model=VoiceAssignmentResponse)
async def update_book_voice_settings(
    book_id: str,
    body: VoiceAssignmentBody,
    auth_user: AuthUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> VoiceAssignmentResponse:
    await _load_owned_book(session, auth_user, book_id)
    row = await _get_or_create_book_override(session, auth_user.id, book_id)
    row.narration_voice_id = body.narration_voice_id
    row.dialogue_voice_id = body.dialogue_voice_id
    row.thought_pitch_semitones = body.thought_pitch_semitones
    await session.commit()
    return VoiceAssignmentResponse(
        scope="book",
        narration_voice_id=row.narration_voice_id,
        dialogue_voice_id=row.dialogue_voice_id,
        thought_pitch_semitones=row.thought_pitch_semitones,
    )


# --- private helpers ---

async def _get_or_create_user_default(session: AsyncSession, user_id: str) -> VoiceAssignment:
    row = (
        await session.execute(
            select(VoiceAssignment).where(
                VoiceAssignment.user_id == user_id,
                VoiceAssignment.book_id.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = VoiceAssignment(
            id=str(uuid4()),
            user_id=user_id,
            book_id=None,
            scope="user",
            narration_voice_id=None,
            dialogue_voice_id=None,
            thought_pitch_semitones=-2.0,
        )
        session.add(row)
    return row


async def _get_or_create_book_override(
    session: AsyncSession, user_id: str, book_id: str
) -> VoiceAssignment:
    row = (
        await session.execute(
            select(VoiceAssignment).where(
                VoiceAssignment.user_id == user_id,
                VoiceAssignment.book_id == book_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = VoiceAssignment(
            id=str(uuid4()),
            user_id=user_id,
            book_id=book_id,
            scope="book",
            narration_voice_id=None,
            dialogue_voice_id=None,
            thought_pitch_semitones=-2.0,
        )
        session.add(row)
    return row

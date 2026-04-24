from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice_assignment import VoiceAssignment


@dataclass(frozen=True)
class ResolvedAssignment:
    narration_voice_id: str | None
    dialogue_voice_id: str | None
    thought_pitch_semitones: float


async def resolve_voice_assignment(
    session: AsyncSession,
    user_id: str,
    book_id: str,
) -> ResolvedAssignment:
    """Return effective voice assignment for (user, book), merging default + book override."""
    rows = (
        await session.execute(
            select(VoiceAssignment).where(
                VoiceAssignment.user_id == user_id,
                VoiceAssignment.book_id.in_([None, book_id]),
            )
        )
    ).scalars().all()

    default: VoiceAssignment | None = None
    override: VoiceAssignment | None = None
    for row in rows:
        if row.book_id is None:
            default = row
        elif row.book_id == book_id:
            override = row

    narration = (
        (override.narration_voice_id if override else None)
        or (default.narration_voice_id if default else None)
    )
    dialogue = (
        (override.dialogue_voice_id if override else None)
        or (default.dialogue_voice_id if default else None)
    )
    pitch = (
        override.thought_pitch_semitones
        if override is not None and override.thought_pitch_semitones != -2.0
        else (default.thought_pitch_semitones if default is not None else -2.0)
    )
    return ResolvedAssignment(
        narration_voice_id=narration,
        dialogue_voice_id=dialogue,
        thought_pitch_semitones=pitch,
    )

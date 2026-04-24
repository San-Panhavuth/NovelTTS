"""Tests for voice resolution service (user default + book override merging)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.voice_assignment import VoiceAssignment
from app.services.voice_resolution import ResolvedAssignment, resolve_voice_assignment

NARRATION_ID = "nar-voice-id"
DIALOGUE_ID = "dia-voice-id"
OVERRIDE_NARRATION_ID = "nar-override-id"
USER_ID = "user-1"
BOOK_ID = "book-1"


def _make_row(
    book_id: str | None,
    narration: str | None = None,
    dialogue: str | None = None,
    pitch: float = -2.0,
) -> VoiceAssignment:
    row = MagicMock(spec=VoiceAssignment)
    row.book_id = book_id
    row.narration_voice_id = narration
    row.dialogue_voice_id = dialogue
    row.thought_pitch_semitones = pitch
    return row


def _make_session(rows: list[VoiceAssignment]) -> AsyncMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_user_default_only():
    default = _make_row(None, narration=NARRATION_ID, dialogue=DIALOGUE_ID, pitch=-2.0)
    session = _make_session([default])
    resolved = await resolve_voice_assignment(session, USER_ID, BOOK_ID)
    assert resolved == ResolvedAssignment(
        narration_voice_id=NARRATION_ID,
        dialogue_voice_id=DIALOGUE_ID,
        thought_pitch_semitones=-2.0,
    )


@pytest.mark.asyncio
async def test_book_override_wins():
    default = _make_row(None, narration=NARRATION_ID, dialogue=DIALOGUE_ID, pitch=-2.0)
    override = _make_row(BOOK_ID, narration=OVERRIDE_NARRATION_ID, dialogue=None, pitch=-4.0)
    session = _make_session([default, override])
    resolved = await resolve_voice_assignment(session, USER_ID, BOOK_ID)
    assert resolved.narration_voice_id == OVERRIDE_NARRATION_ID
    assert resolved.thought_pitch_semitones == -4.0


@pytest.mark.asyncio
async def test_partial_override_falls_back_for_missing_fields():
    default = _make_row(None, narration=NARRATION_ID, dialogue=DIALOGUE_ID, pitch=-2.0)
    override = _make_row(BOOK_ID, narration=OVERRIDE_NARRATION_ID, dialogue=None, pitch=-2.0)
    session = _make_session([default, override])
    resolved = await resolve_voice_assignment(session, USER_ID, BOOK_ID)
    assert resolved.narration_voice_id == OVERRIDE_NARRATION_ID
    assert resolved.dialogue_voice_id == DIALOGUE_ID


@pytest.mark.asyncio
async def test_no_rows_returns_defaults():
    session = _make_session([])
    resolved = await resolve_voice_assignment(session, USER_ID, BOOK_ID)
    assert resolved == ResolvedAssignment(
        narration_voice_id=None,
        dialogue_voice_id=None,
        thought_pitch_semitones=-2.0,
    )


@pytest.mark.asyncio
async def test_thought_pitch_default_is_minus_two():
    session = _make_session([])
    resolved = await resolve_voice_assignment(session, USER_ID, BOOK_ID)
    assert resolved.thought_pitch_semitones == -2.0

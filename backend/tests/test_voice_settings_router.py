from __future__ import annotations

import pytest

from app.routers.voice_settings import _resolve_voice_uuid_from_input


class _FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class _FakeVoice:
    def __init__(self, voice_id: str) -> None:
        self.id = voice_id


class _FakeSession:
    def __init__(self, voice: _FakeVoice | None = None) -> None:
        self.voice = voice
        self.get_calls = 0

    async def get(self, model: type, id_value: str) -> object | None:  # noqa: ARG002
        self.get_calls += 1
        return None

    async def execute(self, statement: object) -> _FakeScalarResult:  # noqa: ARG002
        return _FakeScalarResult(self.voice)


@pytest.mark.asyncio
async def test_resolve_voice_uuid_skips_pk_lookup_for_provider_ids() -> None:
    session = _FakeSession(voice=_FakeVoice("uuid-voice-id"))

    resolved = await _resolve_voice_uuid_from_input(session, "en-US-AndrewNeural")

    assert resolved == "uuid-voice-id"
    # Critical regression check: provider ids must not be sent to session.get(UUID pk)
    assert session.get_calls == 0


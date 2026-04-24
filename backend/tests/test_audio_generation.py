from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from app.models.enums import SegmentType
from app.services.audio_generation import _run_ffmpeg_concat, _synthesize_with_retries


class _FlakyTTS:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    async def synthesize(self, text: str, voice_id: str) -> bytes:  # noqa: ARG002
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("temporary failure")
        return b"audio"

    async def synthesize_with_pitch(self, text: str, voice_id: str, pitch_semitones: float) -> bytes:  # noqa: ARG002
        return await self.synthesize(text, voice_id)


@pytest.mark.asyncio
async def test_synthesize_with_retries_recovers_after_transient_failure() -> None:
    tts = _FlakyTTS(failures=2)
    audio = await _synthesize_with_retries(
        tts=tts,
        seg_type=SegmentType.DIALOGUE,
        text="hello",
        dialogue_voice="edge-voice",
        narration_voice="edge-voice",
        thought_pitch=-2.0,
        max_retries=3,
    )

    assert audio == b"audio"
    assert tts.calls == 3


@pytest.mark.asyncio
async def test_synthesize_with_retries_raises_after_max_attempts() -> None:
    tts = _FlakyTTS(failures=5)
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        await _synthesize_with_retries(
            tts=tts,
            seg_type=SegmentType.NARRATION,
            text="hello",
            dialogue_voice="edge-voice",
            narration_voice="edge-voice",
            thought_pitch=-2.0,
            max_retries=3,
        )


def test_run_ffmpeg_concat_reports_missing_binary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    concat_file = tmp_path / "concat.txt"
    output_file = tmp_path / "out.mp3"
    concat_file.write_text("file 'a.mp3'\n", encoding="utf-8")

    def _raise_not_found(*args: object, **kwargs: object) -> object:  # noqa: ARG001
        raise FileNotFoundError("ffmpeg missing")

    monkeypatch.setattr(subprocess, "run", _raise_not_found)

    with pytest.raises(RuntimeError, match="FFmpeg executable was not found"):
        _run_ffmpeg_concat(concat_list=concat_file, output_mp3=output_file)

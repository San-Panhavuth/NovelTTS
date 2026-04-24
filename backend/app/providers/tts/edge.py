from __future__ import annotations

import io

import edge_tts


class EdgeTTSProvider:
    async def synthesize(self, text: str, voice_id: str, ssml: bool = False) -> bytes:
        communicate = edge_tts.Communicate(text, voice_id)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    async def synthesize_with_pitch(
        self, text: str, voice_id: str, pitch_semitones: float
    ) -> bytes:
        """Synthesize with SSML prosody pitch offset (edge-tts supports pitch as Hz string)."""
        # Edge TTS pitch is expressed as relative Hz: "+0Hz" default, "-20Hz" lower
        # Approximate: 1 semitone ≈ 6% frequency ≈ ~7Hz at 120Hz fundamental
        hz_offset = int(pitch_semitones * 7)
        pitch_str = f"{hz_offset:+d}Hz"
        communicate = edge_tts.Communicate(text, voice_id, pitch=pitch_str)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

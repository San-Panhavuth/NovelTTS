# ruff: noqa: I001
"""Generate a short preview MP3 for every voice and upload to R2.

Requires:
  - edge-tts installed (for edge_tts provider voices)
  - Kokoro installed + CUDA available (for kokoro provider voices)
  - R2 credentials in .env: R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET

Usage (from backend/):
    python scripts/generate_voice_previews.py --provider edge_tts
    python scripts/generate_voice_previews.py --provider kokoro
    python scripts/generate_voice_previews.py              # all providers
    python scripts/generate_voice_previews.py --dry-run    # skip upload, print only
"""
from __future__ import annotations

import argparse
import asyncio
import io
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.config import settings  # noqa: E402
from app.models.voice import Voice  # noqa: E402

PREVIEW_TEXT = (
    "The ancient sect loomed in the distance as the cultivator stepped forward, "
    "his golden core thrumming with restrained power."
)
R2_PREFIX = "previews"


def _to_asyncpg_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


def _make_r2_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


async def _synthesize_edge(voice_id: str) -> bytes:
    import edge_tts

    communicate = edge_tts.Communicate(PREVIEW_TEXT, voice_id)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


async def _synthesize_kokoro(voice_id: str) -> bytes:
    # Import lazily — Kokoro requires CUDA and is not installed in all envs.
    from kokoro import KPipeline  # type: ignore[import]
    import soundfile as sf  # type: ignore[import]

    pipeline = KPipeline(lang_code="a")
    buf = io.BytesIO()
    audio_chunks = []
    for _, _, audio in pipeline(PREVIEW_TEXT, voice=voice_id):
        audio_chunks.append(audio)

    import numpy as np

    combined = np.concatenate(audio_chunks)
    sf.write(buf, combined, 24000, format="mp3")
    return buf.getvalue()


async def run(provider_filter: str | None, dry_run: bool) -> None:
    engine = create_async_engine(_to_asyncpg_url(settings.database_url), echo=False)
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        query = select(Voice)
        if provider_filter:
            query = query.where(Voice.provider == provider_filter)
        voices = (await session.execute(query)).scalars().all()

        print(f"Found {len(voices)} voice(s) to process")

        if dry_run:
            for v in voices:
                print(f"  [{v.provider}] {v.provider_id} — {v.name}")
            print("(dry run — no synthesis or upload)")
            await engine.dispose()
            return

        r2 = _make_r2_client()
        bucket = os.environ["R2_BUCKET"]
        public_base = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")

        for voice in voices:
            if voice.sample_url:
                print(f"  SKIP {voice.provider_id} (already has sample_url)")
                continue

            print(f"  Synthesizing {voice.provider_id} ...", end=" ", flush=True)
            try:
                if voice.provider == "edge_tts":
                    audio_bytes = await _synthesize_edge(voice.provider_id)
                elif voice.provider == "kokoro":
                    audio_bytes = await _synthesize_kokoro(voice.provider_id)
                else:
                    print(f"SKIP (unknown provider {voice.provider})")
                    continue

                key = f"{R2_PREFIX}/{voice.provider}/{voice.provider_id}.mp3"
                r2.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=audio_bytes,
                    ContentType="audio/mpeg",
                )
                url = f"{public_base}/{key}" if public_base else f"r2://{bucket}/{key}"
                voice.sample_url = url
                print(f"OK → {url}")
            except Exception as exc:
                print(f"ERROR — {exc}")

        await session.commit()

    await engine.dispose()
    print("Done")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate voice preview samples and upload to R2")
    parser.add_argument("--provider", default=None, choices=["edge_tts", "kokoro"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.provider, args.dry_run))


if __name__ == "__main__":
    main()

# ruff: noqa: I001, E501
"""Seed the ~10 Kokoro v0.19 voices into the voices table.

Usage (from backend/):
    python scripts/seed_kokoro_voices.py
    python scripts/seed_kokoro_voices.py --dry-run

Kokoro voices are local CUDA-based models; they have no network API, so their
metadata is hardcoded here based on the published voice card.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.config import settings  # noqa: E402
from app.models.voice import Voice  # noqa: E402

# fmt: off
KOKORO_VOICES: list[dict] = [
    # American English — Female
    {"provider_id": "af_bella",   "name": "Bella (American Female)",   "gender": "Female", "locale": "en-US", "pitch": "medium", "age_group": "adult",  "tone": "warm",        "energy": "medium"},
    {"provider_id": "af_sarah",   "name": "Sarah (American Female)",   "gender": "Female", "locale": "en-US", "pitch": "medium", "age_group": "adult",  "tone": "neutral",     "energy": "medium"},
    {"provider_id": "af_sky",     "name": "Sky (American Female)",     "gender": "Female", "locale": "en-US", "pitch": "high",   "age_group": "young",  "tone": "cheerful",    "energy": "high"},
    {"provider_id": "af_nicole",  "name": "Nicole (American Female)",  "gender": "Female", "locale": "en-US", "pitch": "medium", "age_group": "adult",  "tone": "gentle",      "energy": "low"},
    # American English — Male
    {"provider_id": "am_adam",    "name": "Adam (American Male)",      "gender": "Male",   "locale": "en-US", "pitch": "low",    "age_group": "adult",  "tone": "neutral",     "energy": "medium"},
    {"provider_id": "am_michael", "name": "Michael (American Male)",   "gender": "Male",   "locale": "en-US", "pitch": "low",    "age_group": "adult",  "tone": "storytelling","energy": "medium"},
    # British English — Female
    {"provider_id": "bf_emma",    "name": "Emma (British Female)",     "gender": "Female", "locale": "en-GB", "pitch": "medium", "age_group": "adult",  "tone": "formal",      "energy": "medium"},
    {"provider_id": "bf_isabella","name": "Isabella (British Female)", "gender": "Female", "locale": "en-GB", "pitch": "medium", "age_group": "adult",  "tone": "warm",        "energy": "medium"},
    # British English — Male
    {"provider_id": "bm_george",  "name": "George (British Male)",     "gender": "Male",   "locale": "en-GB", "pitch": "low",    "age_group": "adult",  "tone": "formal",      "energy": "medium"},
    {"provider_id": "bm_lewis",   "name": "Lewis (British Male)",      "gender": "Male",   "locale": "en-GB", "pitch": "low",    "age_group": "adult",  "tone": "storytelling","energy": "medium"},
]
# fmt: on


def _to_asyncpg_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


async def run(dry_run: bool) -> None:
    if dry_run:
        for v in KOKORO_VOICES:
            print(v)
        print(f"(dry run — {len(KOKORO_VOICES)} voices, not writing to DB)")
        return

    engine = create_async_engine(_to_asyncpg_url(settings.database_url), echo=False)
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    inserted = 0
    updated = 0
    async with Session() as session:
        for v in KOKORO_VOICES:
            existing = (
                await session.execute(
                    select(Voice).where(
                        Voice.provider == "kokoro",
                        Voice.provider_id == v["provider_id"],
                    )
                )
            ).scalar_one_or_none()

            row_data = {**v, "provider": "kokoro", "sample_url": None}
            if existing is None:
                session.add(Voice(id=str(uuid4()), **row_data))
                inserted += 1
            else:
                for k, val in row_data.items():
                    if k != "sample_url" or existing.sample_url is None:
                        setattr(existing, k, val)
                updated += 1

        await session.commit()

    await engine.dispose()
    print(f"Done — inserted {inserted}, updated {updated}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Kokoro voices into DB")
    parser.add_argument("--dry-run", action="store_true", help="Print voices, no DB write")
    args = parser.parse_args()
    asyncio.run(run(args.dry_run))


if __name__ == "__main__":
    main()

# ruff: noqa: I001
"""Ingest Edge TTS voice catalog into the voices table.

Usage (from backend/):
    python scripts/ingest_edge_tts_voices.py
    python scripts/ingest_edge_tts_voices.py --locale en-US   # filter by locale prefix
    python scripts/ingest_edge_tts_voices.py --dry-run        # print without writing

Requires: edge-tts (pip install edge-tts)
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

import edge_tts  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.config import settings  # noqa: E402
from app.models.voice import Voice  # noqa: E402


def _to_asyncpg_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


def _tag_pitch(gender: str) -> str:
    return "high" if gender.lower() == "female" else "low"


def _tag_age_group(short_name: str, friendly_name: str) -> str:
    combined = (short_name + " " + friendly_name).lower()
    if any(k in combined for k in ("child", "kid", "junior", "young")):
        return "young"
    if any(k in combined for k in ("senior", "old", "elder")):
        return "senior"
    return "adult"


def _tag_tone(personalities: list[str]) -> str:
    mapping = {
        "cheerful": "cheerful",
        "empathetic": "warm",
        "newscast": "formal",
        "assistant": "neutral",
        "customerservice": "friendly",
        "narrative": "storytelling",
        "poetry": "expressive",
        "gentle": "gentle",
        "calm": "calm",
        "serious": "serious",
    }
    for p in personalities:
        key = p.lower().replace("-", "").replace(" ", "")
        if key in mapping:
            return mapping[key]
    return "neutral"


def _tag_energy(personalities: list[str]) -> str:
    high_energy = {"lively", "cheerful", "excited", "energetic", "positive"}
    low_energy = {"gentle", "soft", "calm", "soothing", "whispering"}
    pl = {p.lower() for p in personalities}
    if pl & high_energy:
        return "high"
    if pl & low_energy:
        return "low"
    return "medium"


def _build_voice(v: dict) -> dict:
    personalities: list[str] = (v.get("VoiceTag") or {}).get("VoicePersonalities") or []
    gender = v.get("Gender", "")
    return {
        "provider": "edge_tts",
        "provider_id": v["ShortName"],
        "name": v.get("FriendlyName") or v["ShortName"],
        "gender": gender or None,
        "locale": v.get("Locale"),
        "pitch": _tag_pitch(gender),
        "age_group": _tag_age_group(v["ShortName"], v.get("FriendlyName", "")),
        "tone": _tag_tone(personalities),
        "energy": _tag_energy(personalities),
        "sample_url": None,
    }


async def run(locale_prefix: str | None, dry_run: bool) -> None:
    all_voices = await edge_tts.list_voices()

    if locale_prefix:
        all_voices = [v for v in all_voices if v.get("Locale", "").startswith(locale_prefix)]

    print(f"Fetched {len(all_voices)} Edge TTS voices (locale filter: {locale_prefix or 'none'})")

    if dry_run:
        for v in all_voices[:5]:
            built = _build_voice(v)
            print(built)
        print(f"... (dry run — {len(all_voices)} total, not writing to DB)")
        return

    engine = create_async_engine(_to_asyncpg_url(settings.database_url), echo=False)
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    inserted = 0
    updated = 0
    async with Session() as session:
        for raw in all_voices:
            built = _build_voice(raw)
            existing = (
                await session.execute(
                    select(Voice).where(
                        Voice.provider == "edge_tts",
                        Voice.provider_id == built["provider_id"],
                    )
                )
            ).scalar_one_or_none()

            if existing is None:
                session.add(Voice(id=str(uuid4()), **built))
                inserted += 1
            else:
                for k, val in built.items():
                    if k != "sample_url" or existing.sample_url is None:
                        setattr(existing, k, val)
                updated += 1

        await session.commit()

    await engine.dispose()
    print(f"Done — inserted {inserted}, updated {updated}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Edge TTS voices into DB")
    parser.add_argument("--locale", default=None, help="Filter by locale prefix, e.g. en-US")
    parser.add_argument("--dry-run", action="store_true", help="Print first 5 voices, no DB write")
    args = parser.parse_args()
    asyncio.run(run(args.locale, args.dry_run))


if __name__ == "__main__":
    main()

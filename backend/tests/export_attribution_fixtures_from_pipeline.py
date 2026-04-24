from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import re
import sys

from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.deps.db import SessionLocal
from app.models.book import Book
from app.models.chapter import Chapter
from app.providers.llm import get_llm_provider
from app.services.attribution import attribute_chunk


def _default_output_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "attribution" / "bootstrap"


def _is_gold_dir(path: Path) -> bool:
    normalized = [part.lower() for part in path.resolve().parts]
    return "gold" in normalized


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return cleaned.lower() or "book"


def _parse_chapter_spec(spec: str) -> tuple[int, str]:
    try:
        raw_index, raw_genre = spec.split(":", maxsplit=1)
    except ValueError as exc:
        raise ValueError(
            f"Invalid --chapter value '{spec}'. Expected format: <chapter_idx>:<genre>"
        ) from exc

    chapter_idx = int(raw_index)
    genre = raw_genre.strip().lower()
    if not genre:
        raise ValueError(f"Genre is required in chapter spec: {spec}")
    return chapter_idx, genre


async def _export_fixtures(
    book_id: str,
    chapter_specs: list[tuple[int, str]],
    out_dir: Path,
    overwrite: bool,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written_files: list[Path] = []

    async with SessionLocal() as session:
        book = await session.get(Book, book_id)
        if book is None:
            raise ValueError(f"Book not found: {book_id}")

        provider = get_llm_provider()

        for chapter_idx, genre in chapter_specs:
            chapter_stmt = select(Chapter).where(Chapter.book_id == book.id, Chapter.chapter_idx == chapter_idx)
            chapter = (await session.execute(chapter_stmt)).scalar_one_or_none()
            if chapter is None:
                raise ValueError(f"Chapter not found for book {book_id}: index={chapter_idx}")

            predicted_segments = await attribute_chunk(chapter.raw_text, provider)
            if not predicted_segments:
                raise ValueError(
                    f"Chapter {chapter_idx} produced no attributed segments from the current pipeline."
                )

            expected = [
                {
                    "text": segment.text,
                    "type": segment.type.value,
                    "character": segment.character,
                }
                for segment in predicted_segments
            ]

            case = {
                "id": f"{genre}-{_slugify(book.title)}-chapter-{chapter_idx:03d}",
                "genre": genre,
                "text": chapter.raw_text,
                "expected": expected,
            }

            file_path = out_dir / f"{genre}_chapter_{chapter_idx:03d}.json"
            if file_path.exists() and not overwrite:
                raise ValueError(
                    f"Fixture already exists: {file_path}. Use --overwrite to replace existing files."
                )

            file_path.write_text(json.dumps([case], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            written_files.append(file_path)

    return written_files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export bootstrap attribution fixtures from the current attribution pipeline"
    )
    parser.add_argument("--book-id", required=True, help="Book ID from database")
    parser.add_argument(
        "--chapter",
        action="append",
        required=True,
        help="Chapter spec format: <chapter_idx>:<genre>. Repeat this arg for multiple chapters.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=_default_output_dir(),
        help="Output directory for fixture json files",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing fixture files with the same names",
    )
    args = parser.parse_args()

    if _is_gold_dir(args.out_dir):
        raise ValueError(
            "Pipeline exporter cannot write into gold fixtures. "
            "Use backend/tests/export_attribution_fixtures_from_db.py for independent gold fixture curation."
        )

    chapter_specs = [_parse_chapter_spec(spec) for spec in args.chapter]
    written_files = asyncio.run(
        _export_fixtures(
            book_id=args.book_id,
            chapter_specs=chapter_specs,
            out_dir=args.out_dir,
            overwrite=args.overwrite,
        )
    )

    print(f"Exported {len(written_files)} fixture file(s):")
    for path in written_files:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

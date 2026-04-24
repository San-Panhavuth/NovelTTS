from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models.enums import SegmentType
from app.providers.llm import get_llm_provider
from app.providers.llm.base import LLMProvider
from app.services.attribution import AttributedSegment, attribute_chunk

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "attribution"
GOLD_ROOT = FIXTURES_ROOT / "gold"
GOLD_LOCK_PATH = GOLD_ROOT / "test.lock.json"


@dataclass(frozen=True)
class ExpectedSegment:
    text: str
    type: SegmentType
    character: str | None


@dataclass(frozen=True)
class AttributionCase:
    case_id: str
    genre: str
    text: str
    expected: list[ExpectedSegment]


@dataclass(frozen=True)
class BenchmarkResult:
    total_cases: int
    total_expected_segments: int
    matched_segments: int
    type_correct: int
    character_correct: int
    strict_correct: int
    token_total: int
    token_correct: int

    @property
    def span_recall(self) -> float:
        if self.total_expected_segments == 0:
            return 0.0
        return self.matched_segments / self.total_expected_segments

    @property
    def type_accuracy(self) -> float:
        if self.matched_segments == 0:
            return 0.0
        return self.type_correct / self.matched_segments

    @property
    def character_accuracy(self) -> float:
        if self.matched_segments == 0:
            return 0.0
        return self.character_correct / self.matched_segments

    @property
    def strict_accuracy(self) -> float:
        if self.token_total == 0:
            return 0.0
        return self.token_correct / self.token_total

    @property
    def segment_strict_accuracy(self) -> float:
        if self.total_expected_segments == 0:
            return 0.0
        return self.strict_correct / self.total_expected_segments


@dataclass(frozen=True)
class MismatchTopItem:
    count: int
    example: str


@dataclass(frozen=True)
class BenchmarkErrorReport:
    span_mismatch_count: int
    type_mismatch_count: int
    character_mismatch_count: int
    top_span_mismatches: list[MismatchTopItem]
    top_type_mismatches: list[MismatchTopItem]
    top_character_mismatches: list[MismatchTopItem]


def resolve_fixture_dir(mode: str, split: str | None = None) -> Path:
    mode_value = mode.strip().lower()
    split_value = split.strip().lower() if split else None

    if mode_value == "bootstrap":
        if split_value is not None:
            raise ValueError("split is not supported for bootstrap mode")
        return FIXTURES_ROOT / "bootstrap"

    if mode_value == "gold":
        resolved_split = split_value or "dev"
        if resolved_split not in {"dev", "test"}:
            raise ValueError(f"Unsupported gold split: {resolved_split}")
        return GOLD_ROOT / resolved_split

    raise ValueError(f"Unsupported benchmark mode: {mode}")


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def build_fixture_hashes(fixtures_dir: Path) -> dict[str, str]:
    return {
        fixture.name: _sha256_file(fixture)
        for fixture in sorted(fixtures_dir.glob("*.json"))
    }


def verify_fixture_lock(fixtures_dir: Path, lockfile_path: Path = GOLD_LOCK_PATH) -> None:
    if not fixtures_dir.exists():
        raise ValueError(f"Fixture directory does not exist: {fixtures_dir}")

    if not lockfile_path.exists():
        raise ValueError(
            f"Fixture lockfile is missing: {lockfile_path}. "
            "Run backend/tests/update_attribution_fixture_lock.py"
        )

    payload = json.loads(lockfile_path.read_text(encoding="utf-8"))
    expected_files = payload.get("files")
    if not isinstance(expected_files, dict):
        raise ValueError(f"Invalid lockfile format: {lockfile_path}")

    actual_files = build_fixture_hashes(fixtures_dir)
    if actual_files != expected_files:
        missing = sorted(set(expected_files) - set(actual_files))
        extra = sorted(set(actual_files) - set(expected_files))
        changed = sorted(
            name
            for name in set(actual_files).intersection(expected_files)
            if actual_files[name] != expected_files[name]
        )
        mismatch_summary = {
            "missing": missing,
            "extra": extra,
            "changed": changed,
        }
        raise ValueError(
            "Gold test fixtures differ from lockfile. "
            f"Mismatch={json.dumps(mismatch_summary)}. "
            "If this was intentional, regenerate lock with "
            "backend/tests/update_attribution_fixture_lock.py"
        )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _normalize_character(character: str | None) -> str | None:
    if character is None:
        return None
    normalized = character.strip().lower()
    if not normalized:
        return None
    return normalized


def _clip_excerpt(text: str, max_chars: int = 120) -> str:
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) <= max_chars:
        return compact
    return f"{compact[: max_chars - 3]}..."


def _top_items(counter: Counter[str], limit: int) -> list[MismatchTopItem]:
    return [
        MismatchTopItem(count=count, example=example)
        for example, count in counter.most_common(limit)
    ]


def _parse_type(value: str) -> SegmentType:
    return SegmentType(value.strip().lower())


def load_attribution_cases(fixtures_dir: Path) -> list[AttributionCase]:
    cases: list[AttributionCase] = []

    for fixture_path in sorted(fixtures_dir.glob("*.json")):
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Fixture file must contain a list: {fixture_path}")

        for item in payload:
            if not isinstance(item, dict):
                raise ValueError(f"Fixture case must be an object: {fixture_path}")

            raw_expected = item.get("expected")
            if not isinstance(raw_expected, list):
                raise ValueError(f"Case expected must be a list: {fixture_path}")

            expected = [
                ExpectedSegment(
                    text=str(segment["text"]),
                    type=_parse_type(str(segment["type"])),
                    character=segment.get("character"),
                )
                for segment in raw_expected
            ]

            cases.append(
                AttributionCase(
                    case_id=str(item["id"]),
                    genre=str(item.get("genre", "other")),
                    text=str(item["text"]),
                    expected=expected,
                )
            )

    return cases


def _index_predictions(predicted: list[AttributedSegment]) -> dict[str, AttributedSegment]:
    indexed: dict[str, AttributedSegment] = {}
    for segment in predicted:
        key = _normalize_text(segment.text)
        if key and key not in indexed:
            indexed[key] = segment
    return indexed


def _find_span(raw_text: str, segment_text: str, start_at: int = 0) -> tuple[int, int] | None:
    cleaned = segment_text.strip()
    if not cleaned:
        return None

    parts = [re.escape(part) for part in re.split(r"\s+", cleaned) if part]
    if not parts:
        return None

    pattern = r"\s+".join(parts)
    match = re.search(pattern, raw_text[start_at:], flags=re.DOTALL)
    if match is None:
        # Fallback to punctuation-tolerant canonical matching.
        raw_canon, raw_map = _canonicalize_for_search(raw_text)
        seg_canon, _ = _canonicalize_for_search(cleaned)
        canon_start = _canonical_cursor_from_raw(raw_map, start_at)
        canon_match = re.search(re.escape(seg_canon), raw_canon[canon_start:])
        if canon_match is None:
            return None

        canon_begin = canon_start + canon_match.start()
        canon_end = canon_start + canon_match.end()
        raw_begin = raw_map[canon_begin]
        raw_end = raw_map[min(canon_end - 1, len(raw_map) - 1)] + 1
        return raw_begin, raw_end

    return start_at + match.start(), start_at + match.end()


def _canonicalize_for_search(text: str) -> tuple[str, list[int]]:
    canonical_chars: list[str] = []
    index_map: list[int] = []
    previous_space = False

    for index, char in enumerate(text):
        if char.isalnum():
            canonical_chars.append(char.lower())
            index_map.append(index)
            previous_space = False
            continue

        if char.isspace():
            if not previous_space:
                canonical_chars.append(" ")
                index_map.append(index)
                previous_space = True
            continue

    canonical = "".join(canonical_chars).strip()
    if not canonical:
        return "", [0]
    return canonical, index_map


def _canonical_cursor_from_raw(raw_map: list[int], raw_cursor: int) -> int:
    for index, raw_index in enumerate(raw_map):
        if raw_index >= raw_cursor:
            return index
    return len(raw_map)


def _build_token_spans(raw_text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in re.finditer(r"\S+", raw_text)]


def _build_token_labels(
    raw_text: str,
    segments: list[AttributedSegment],
) -> list[tuple[SegmentType | None, str | None]]:
    token_spans = _build_token_spans(raw_text)
    labels: list[tuple[SegmentType | None, str | None]] = [(None, None) for _ in token_spans]

    segment_index = 0
    for segment in segments:
        span = _find_span(raw_text, segment.text, start_at=segment_index)
        if span is None:
            continue

        start, end = span
        segment_index = end
        for token_index, (token_start, token_end) in enumerate(token_spans):
            if token_start >= start and token_end <= end:
                labels[token_index] = (segment.type, segment.character)

    return labels


async def run_attribution_benchmark(
    cases: list[AttributionCase],
    provider: LLMProvider,
) -> BenchmarkResult:
    result, _ = await _run_attribution_benchmark_core(
        cases=cases,
        provider=provider,
        collect_error_report=False,
    )
    return result


async def run_attribution_benchmark_with_report(
    cases: list[AttributionCase],
    provider: LLMProvider,
    top_limit: int = 10,
) -> tuple[BenchmarkResult, BenchmarkErrorReport]:
    return await _run_attribution_benchmark_core(
        cases=cases,
        provider=provider,
        collect_error_report=True,
        top_limit=top_limit,
    )


async def _run_attribution_benchmark_core(
    cases: list[AttributionCase],
    provider: LLMProvider,
    collect_error_report: bool,
    top_limit: int = 10,
) -> tuple[BenchmarkResult, BenchmarkErrorReport | None]:
    total_expected_segments = 0
    matched_segments = 0
    type_correct = 0
    character_correct = 0
    strict_correct = 0
    token_total = 0
    token_correct = 0
    span_mismatch_counter: Counter[str] = Counter()
    type_mismatch_counter: Counter[str] = Counter()
    character_mismatch_counter: Counter[str] = Counter()

    for case in cases:
        predicted = await attribute_chunk(case.text, provider)
        by_text = _index_predictions(predicted)

        expected_token_labels = _build_token_labels(
            case.text,
            [
                AttributedSegment(
                    text=expected.text,
                    type=expected.type,
                    character=expected.character,
                    confidence=1.0,
                )
                for expected in case.expected
            ],
        )
        predicted_token_labels = _build_token_labels(case.text, predicted)

        for expected_label, predicted_label in zip(
            expected_token_labels,
            predicted_token_labels,
            strict=False,
        ):
            if expected_label[0] is None:
                continue
            token_total += 1
            if expected_label == predicted_label:
                token_correct += 1

        for expected in case.expected:
            total_expected_segments += 1
            expected_key = _normalize_text(expected.text)
            prediction = by_text.get(expected_key)
            if prediction is None:
                if collect_error_report:
                    mismatch = f"{case.case_id}: {_clip_excerpt(expected.text)}"
                    span_mismatch_counter.update([mismatch])
                continue

            matched_segments += 1

            type_ok = prediction.type == expected.type
            if type_ok:
                type_correct += 1
            elif collect_error_report:
                type_mismatch_counter.update(
                    [
                        (
                            f"{case.case_id}: expected={expected.type.value}, "
                            "predicted="
                            f"{prediction.type.value}, text={_clip_excerpt(expected.text)}"
                        )
                    ]
                )

            expected_character = _normalize_character(expected.character)
            predicted_character = _normalize_character(prediction.character)
            character_ok = expected_character == predicted_character
            if character_ok:
                character_correct += 1
            elif collect_error_report:
                character_mismatch_counter.update(
                    [
                        (
                            f"{case.case_id}: expected={expected_character or 'null'}, "
                            "predicted="
                            f"{predicted_character or 'null'}, text={_clip_excerpt(expected.text)}"
                        )
                    ]
                )

            if type_ok and character_ok:
                strict_correct += 1

    result = BenchmarkResult(
        total_cases=len(cases),
        total_expected_segments=total_expected_segments,
        matched_segments=matched_segments,
        type_correct=type_correct,
        character_correct=character_correct,
        strict_correct=strict_correct,
        token_total=token_total,
        token_correct=token_correct,
    )
    if not collect_error_report:
        return result, None

    report = BenchmarkErrorReport(
        span_mismatch_count=sum(span_mismatch_counter.values()),
        type_mismatch_count=sum(type_mismatch_counter.values()),
        character_mismatch_count=sum(character_mismatch_counter.values()),
        top_span_mismatches=_top_items(span_mismatch_counter, limit=max(0, top_limit)),
        top_type_mismatches=_top_items(type_mismatch_counter, limit=max(0, top_limit)),
        top_character_mismatches=_top_items(
            character_mismatch_counter,
            limit=max(0, top_limit),
        ),
    )
    return result, report


def result_to_dict(result: BenchmarkResult) -> dict[str, Any]:
    return {
        "total_cases": result.total_cases,
        "total_expected_segments": result.total_expected_segments,
        "matched_segments": result.matched_segments,
        "span_recall": round(result.span_recall, 4),
        "type_accuracy": round(result.type_accuracy, 4),
        "character_accuracy": round(result.character_accuracy, 4),
        "strict_accuracy": round(result.strict_accuracy, 4),
        "segment_strict_accuracy": round(result.segment_strict_accuracy, 4),
        "token_total": result.token_total,
        "token_correct": result.token_correct,
    }


def error_report_to_dict(report: BenchmarkErrorReport) -> dict[str, Any]:
    return {
        "span_mismatch_count": report.span_mismatch_count,
        "type_mismatch_count": report.type_mismatch_count,
        "character_mismatch_count": report.character_mismatch_count,
        "top_span_mismatches": [
            {"count": item.count, "example": item.example} for item in report.top_span_mismatches
        ],
        "top_type_mismatches": [
            {"count": item.count, "example": item.example} for item in report.top_type_mismatches
        ],
        "top_character_mismatches": [
            {"count": item.count, "example": item.example}
            for item in report.top_character_mismatches
        ],
    }


async def benchmark_from_fixture_dir(fixtures_dir: Path) -> BenchmarkResult:
    cases = load_attribution_cases(fixtures_dir)
    provider = get_llm_provider()
    return await run_attribution_benchmark(cases=cases, provider=provider)


async def benchmark_from_fixture_dir_with_report(
    fixtures_dir: Path,
    top_limit: int = 10,
) -> tuple[BenchmarkResult, BenchmarkErrorReport]:
    cases = load_attribution_cases(fixtures_dir)
    provider = get_llm_provider()
    return await run_attribution_benchmark_with_report(
        cases=cases,
        provider=provider,
        top_limit=top_limit,
    )


async def benchmark_from_mode(mode: str, split: str | None = None) -> BenchmarkResult:
    fixtures_dir = resolve_fixture_dir(mode=mode, split=split)
    if mode.strip().lower() == "gold" and (split or "dev").strip().lower() == "test":
        verify_fixture_lock(fixtures_dir)
    return await benchmark_from_fixture_dir(fixtures_dir)


def run_benchmark_sync(fixtures_dir: Path) -> BenchmarkResult:
    return asyncio.run(benchmark_from_fixture_dir(fixtures_dir))


def run_benchmark_with_report_sync(
    fixtures_dir: Path,
    top_limit: int = 10,
) -> tuple[BenchmarkResult, BenchmarkErrorReport]:
    return asyncio.run(benchmark_from_fixture_dir_with_report(fixtures_dir, top_limit=top_limit))


def run_benchmark_by_mode_sync(mode: str, split: str | None = None) -> BenchmarkResult:
    return asyncio.run(benchmark_from_mode(mode=mode, split=split))

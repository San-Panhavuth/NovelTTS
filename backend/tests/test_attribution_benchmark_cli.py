from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.attribution_benchmark import (
    build_fixture_hashes,
    error_report_to_dict,
    load_attribution_cases,
    resolve_fixture_dir,
    run_attribution_benchmark_with_report,
    verify_fixture_lock,
)
from tests.run_attribution_benchmark import _resolve_target


def test_resolve_fixture_dir_modes() -> None:
    bootstrap_dir = resolve_fixture_dir(mode="bootstrap")
    assert bootstrap_dir.as_posix().endswith("fixtures/attribution/bootstrap")

    gold_dev_dir = resolve_fixture_dir(mode="gold", split="dev")
    assert gold_dev_dir.as_posix().endswith("fixtures/attribution/gold/dev")

    gold_test_dir = resolve_fixture_dir(mode="gold", split="test")
    assert gold_test_dir.as_posix().endswith("fixtures/attribution/gold/test")


def test_resolve_fixture_dir_rejects_bootstrap_split() -> None:
    with pytest.raises(ValueError):
        resolve_fixture_dir(mode="bootstrap", split="test")


def test_resolve_target_independent_gate_flags() -> None:
    bootstrap_target = _resolve_target(fixtures_dir=None, mode="bootstrap", split="dev")
    assert not bootstrap_target.independent_gate

    gold_dev_target = _resolve_target(fixtures_dir=None, mode="gold", split="dev")
    assert not gold_dev_target.independent_gate

    gold_test_target = _resolve_target(fixtures_dir=None, mode="gold", split="test")
    assert gold_test_target.independent_gate

    custom_target = _resolve_target(
        fixtures_dir=Path("backend/tests/fixtures/attribution/bootstrap"),
        mode="gold",
        split="test",
    )
    assert not custom_target.independent_gate


def test_verify_fixture_lock_detects_changed_file(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(parents=True)

    fixture_file = fixtures_dir / "case.json"
    fixture_file.write_text(
        '[{"id":"case-1","genre":"other","text":"x","expected":[]}]\n',
        encoding="utf-8",
    )

    lockfile = tmp_path / "test.lock.json"
    lockfile.write_text(
        json.dumps(
            {
                "algorithm": "sha256",
                "files": build_fixture_hashes(fixtures_dir),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    verify_fixture_lock(fixtures_dir, lockfile)

    fixture_file.write_text(
        '[{"id":"case-1","genre":"other","text":"changed","expected":[]}]\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="differ from lockfile"):
        verify_fixture_lock(fixtures_dir, lockfile)


@pytest.mark.asyncio
async def test_run_attribution_benchmark_with_report_collects_mismatches(
    tmp_path: Path,
) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(parents=True)
    fixture_file = fixtures_dir / "case.json"
    fixture_file.write_text(
        json.dumps(
            [
                {
                    "id": "case-1",
                    "genre": "other",
                    "text": '"Hello there." Mina said quietly.',
                    "expected": [
                        {"text": '"Hello there."', "type": "dialogue", "character": "Mina"},
                        {"text": "Mina said quietly.", "type": "narration", "character": None},
                    ],
                },
                {
                    "id": "case-2",
                    "genre": "other",
                    "text": "The hallway was empty.",
                    "expected": [
                        {
                            "text": "The hallway was empty.",
                            "type": "dialogue",
                            "character": None,
                        }
                    ],
                },
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    class _FakeProvider:
        async def complete_json(self, prompt: str) -> dict:  # noqa: ARG002
            return {
                "items": [
                    {
                        "text": '"Hello there."',
                        "type": "dialogue",
                        "character": "Lina",
                        "confidence": 0.9,
                    },
                    {
                        "text": "Mina said quietly.",
                        "type": "dialogue",
                        "character": None,
                        "confidence": 0.8,
                    },
                ]
            }

    cases = load_attribution_cases(fixtures_dir)
    result, report = await run_attribution_benchmark_with_report(
        cases=cases,
        provider=_FakeProvider(),
        top_limit=2,
    )

    assert result.total_cases == 2
    assert report.character_mismatch_count >= 1
    assert report.type_mismatch_count >= 1
    assert report.span_mismatch_count >= 0

    report_payload = error_report_to_dict(report)
    assert "top_span_mismatches" in report_payload
    assert len(report_payload["top_span_mismatches"]) <= 2

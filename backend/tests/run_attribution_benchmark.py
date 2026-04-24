from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tests.attribution_benchmark import (  # noqa: E402
    error_report_to_dict,
    resolve_fixture_dir,
    result_to_dict,
    run_benchmark_sync,
    run_benchmark_with_report_sync,
    verify_fixture_lock,
)


class BenchmarkTarget(NamedTuple):
    fixtures_dir: Path
    description: str
    independent_gate: bool


def _resolve_target(fixtures_dir: Path | None, mode: str, split: str) -> BenchmarkTarget:
    if fixtures_dir is not None:
        return BenchmarkTarget(
            fixtures_dir=fixtures_dir,
            description=f"custom fixtures ({fixtures_dir})",
            independent_gate=False,
        )

    resolved = resolve_fixture_dir(mode=mode, split=split if mode == "gold" else None)
    if mode == "bootstrap":
        return BenchmarkTarget(
            fixtures_dir=resolved,
            description="bootstrap self-consistency",
            independent_gate=False,
        )

    return BenchmarkTarget(
        fixtures_dir=resolved,
        description=f"gold {split}",
        independent_gate=(split == "test"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run attribution benchmark against fixture cases")
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=None,
        help=(
            "Custom directory containing attribution fixture JSON files "
            "(disables independent-gate enforcement)"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["bootstrap", "gold"],
        default="bootstrap",
        help="Benchmark mode. bootstrap is self-consistency; gold uses independent fixtures",
    )
    parser.add_argument(
        "--split",
        choices=["dev", "test"],
        default="dev",
        help="Gold split to benchmark when --mode gold",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Strict accuracy threshold used with --enforce-threshold",
    )
    parser.add_argument(
        "--enforce-threshold",
        action="store_true",
        help="Exit with code 1 when strict_accuracy is below threshold",
    )
    parser.add_argument(
        "--error-report-limit",
        type=int,
        default=10,
        help="Maximum number of top mismatch examples per category in gold/dev runs",
    )
    args = parser.parse_args()

    target = _resolve_target(
        fixtures_dir=args.fixtures_dir,
        mode=args.mode,
        split=args.split,
    )

    if args.enforce_threshold and not target.independent_gate:
        print(
            "--enforce-threshold is only allowed for independent gold test runs. "
            "Use --mode gold --split test without --fixtures-dir.",
        )
        return 2

    if target.independent_gate:
        verify_fixture_lock(target.fixtures_dir)

    emit_error_report = args.fixtures_dir is None and args.mode == "gold" and args.split == "dev"
    if emit_error_report:
        result, error_report = run_benchmark_with_report_sync(
            target.fixtures_dir,
            top_limit=max(0, args.error_report_limit),
        )
    else:
        result = run_benchmark_sync(target.fixtures_dir)
        error_report = None

    payload = result_to_dict(result)
    payload["benchmark_target"] = target.description
    payload["fixtures_dir"] = str(target.fixtures_dir)
    if error_report is not None:
        payload["error_report"] = error_report_to_dict(error_report)
    print(json.dumps(payload, indent=2))

    if args.enforce_threshold and result.strict_accuracy < args.threshold:
        print(
            f"strict_accuracy={result.strict_accuracy:.4f} is below threshold={args.threshold:.4f}",
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tests.attribution_benchmark import run_benchmark_by_mode_sync, run_benchmark_sync


@dataclass(frozen=True)
class VariantResult:
    variant: str
    strict_accuracy: float
    span_recall: float
    type_accuracy: float
    character_accuracy: float
    token_total: int
    token_correct: int


VARIANTS: tuple[str, ...] = (
    "legacy_freeform",
    "preseg_label_v1",
    "preseg_label_v2",
    "hybrid_v1",
)


def _run_variant(variant: str, mode: str, split: str, fixtures_dir: Path | None) -> VariantResult:
    previous = os.getenv("ATTRIBUTION_EXPERIMENT")
    os.environ["ATTRIBUTION_EXPERIMENT"] = variant
    try:
        result = run_benchmark_sync(fixtures_dir) if fixtures_dir else run_benchmark_by_mode_sync(mode=mode, split=split)
    finally:
        if previous is None:
            os.environ.pop("ATTRIBUTION_EXPERIMENT", None)
        else:
            os.environ["ATTRIBUTION_EXPERIMENT"] = previous

    return VariantResult(
        variant=variant,
        strict_accuracy=round(result.strict_accuracy, 4),
        span_recall=round(result.span_recall, 4),
        type_accuracy=round(result.type_accuracy, 4),
        character_accuracy=round(result.character_accuracy, 4),
        token_total=result.token_total,
        token_correct=result.token_correct,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run attribution experiment matrix across strategy variants")
    parser.add_argument("--mode", choices=["bootstrap", "gold"], default="gold")
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=None,
        help="Optional custom fixture directory (overrides mode/split target)",
    )
    args = parser.parse_args()

    results = [_run_variant(variant, args.mode, args.split, args.fixtures_dir) for variant in VARIANTS]
    best = max(results, key=lambda item: item.strict_accuracy)
    payload = {
        "benchmark_target": f"custom:{args.fixtures_dir}" if args.fixtures_dir else f"{args.mode}/{args.split}",
        "variants": [asdict(item) for item in results],
        "best_variant": asdict(best),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tests.attribution_benchmark import GOLD_LOCK_PATH, build_fixture_hashes, resolve_fixture_dir


def main() -> int:
    fixtures_dir = resolve_fixture_dir(mode="gold", split="test")
    if not fixtures_dir.exists():
        raise ValueError(f"Gold test fixture directory does not exist: {fixtures_dir}")

    payload = {
        "algorithm": "sha256",
        "fixtures_dir": str(fixtures_dir),
        "files": build_fixture_hashes(fixtures_dir),
    }

    GOLD_LOCK_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Updated fixture lockfile: {GOLD_LOCK_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

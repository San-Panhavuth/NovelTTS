# Attribution Benchmark Report (Phase 2)

## Current benchmark status

- Benchmark command (dev diagnostics):  
  `c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_attribution_benchmark.py --mode gold --split dev`
- Benchmark command (locked acceptance gate):  
  `c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_attribution_benchmark.py --mode gold --split test --threshold 0.70 --enforce-threshold`
- Latest metrics (gold/dev and gold/test both currently match):
  - `strict_accuracy`: `0.7408`
  - `span_recall`: `0.5983`
  - `type_accuracy`: `0.9381`
  - `character_accuracy`: `0.9905`

Acceptance target is `strict_accuracy >= 0.70` on locked `gold/test` (current `0.7408`, target met).

## How we test attribution accuracy

1. Use independent fixtures in `backend/tests/fixtures/attribution/gold/dev` for iteration.
2. Run benchmark runner in gold/dev mode to get aggregate metrics plus `error_report`.
3. Analyze top repeated mismatches:
   - `top_span_mismatches`
   - `top_type_mismatches`
   - `top_character_mismatches`
4. Apply targeted prompt/fallback/post-processing changes.
5. Re-run gold/dev until improvement is stable.
6. Run locked `gold/test` only for acceptance verification.

### Experiment matrix command

Use this when you need prompt/contract A-B results in one shot:

`c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_attribution_experiment_matrix.py --mode gold --split dev`

Matrix variants currently include:
- `legacy_freeform`
- `preseg_label_v1`
- `preseg_label_v2`
- `hybrid_v1`

## Main constraints identified

- Strict span matching is boundary-sensitive (small punctuation/quote boundary drift is penalized as full miss).
- Long, dense chunks are under-constrained for free-form model segmentation.
- Classification quality is already strong (`type` and `character`), while span alignment/coverage is weak.
- Many misses are global segmentation shape mismatches, not isolated quote-edge bugs.

## Solutions tried and results

### Baseline controls
- Added gold split workflow (`gold/dev` for tuning, locked `gold/test` for acceptance).
- Added lockfile checks for `gold/test`.
- Added automatic mismatch diagnostics in benchmark output.
- Result: visibility improved, no metric lift by itself.

### Prompt and fallback tuning
- Enforced JSON-only schema and stricter excerpt preservation guidance.
- Added quote-preservation and speaker-tag instructions.
- Result: no measurable strict accuracy lift on independent set.

### Post-processing fixes
- Quote run coalescing and fragmented quote merge.
- Apostrophe-safe stitching (`'` / `’` boundary repair).
- Coverage repair by filling uncovered source gaps with exact substrings.
- Result: edge-case robustness improved in unit tests, benchmark metrics unchanged.

### Two additional attempts (latest)
- Attempt 1: deterministic pre-segmentation + label-only prompt path (idx-based labeling), with legacy fallback compatibility retained.
- Attempt 2: adjacent same-label merge calibration on labeled spans.
- Result: unit tests passed, gold/dev metrics unchanged (`strict_accuracy 0.7408`, `span_recall 0.5983`).

## Practical interpretation

- Current bottleneck is still span contract mismatch against strict fixture boundaries.
- Provider capability may contribute, but evidence so far points more to segmentation contract and evaluation brittleness than pure type/character reasoning quality.
- Further gains likely require changing segmentation contract strategy (for example, fully deterministic segmentation and benchmark alignment against that contract) rather than incremental local heuristics.

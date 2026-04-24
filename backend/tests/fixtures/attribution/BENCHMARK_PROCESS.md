# Attribution Benchmark Process

This document describes how attribution quality is measured for Phase 2.

## What this test is for

This benchmark checks whether the chapter-processing NLP can:
- split chapter text into the right segment boundaries
- label each segment as `narration`, `dialogue`, or `thought`
- assign the right character when one is known

It is used to measure whether the chapter processing pipeline is good enough to review and correct, before moving on to voice and TTS work.

It does not measure:
- TTS audio quality
- speaker voice selection
- FFmpeg stitching
- frontend rendering

## Scope

The benchmark evaluates the full attribution pipeline output against labeled fixtures:
- text span matching
- segment type classification (`narration`, `dialogue`, `thought`)
- character assignment

It does not evaluate TTS quality.

## Data source

Fixtures are stored under:
- `backend/tests/fixtures/attribution/bootstrap/`
- `backend/tests/fixtures/attribution/gold/dev/`
- `backend/tests/fixtures/attribution/gold/test/`
- `backend/tests/fixtures/attribution/gold/test.lock.json`

Benchmark modes:
- `bootstrap`: self-consistency only.
- `gold dev`: independent iteration set.
- `gold test`: locked independent acceptance set.

The acceptance gate must run on `gold test` only.

Each case contains:
- `text`: chapter chunk input
- `expected[]`: labeled segments with `text`, `type`, and `character`

The `expected[]` entries are the ground truth. The benchmark compares the model output to these labels.

## Runner and implementation

- CLI runner: `backend/tests/run_attribution_benchmark.py`
- Benchmark logic: `backend/tests/attribution_benchmark.py`

The benchmark uses the active LLM provider from app settings:
- If `gemini_api_key` is present, provider is Gemini (`gemini_model`, default `gemini-2.5-flash`)
- Otherwise fallback provider behavior may apply

## How to run

From repo root:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_attribution_benchmark.py --mode bootstrap
```

Independent development set:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_attribution_benchmark.py --mode gold --split dev
```

Locked independent acceptance gate:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_attribution_benchmark.py --mode gold --split test --threshold 0.85 --enforce-threshold
```

If `gold/test` fixtures are changed, regenerate lock hashes intentionally:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/update_attribution_fixture_lock.py
```

## Metrics

- `span_recall`: matched expected segment texts / total expected segment texts
- `type_accuracy`: correct type among matched spans
- `character_accuracy`: correct character among matched spans
- `strict_accuracy`: expected segments where both type and character are correct, divided by total expected segments

How the comparison works:
- The benchmark first tries to match predicted segments to expected segments by text span.
- If a predicted span does not exactly match an expected span, it is counted as a miss for span recall.
- For matched spans, the benchmark checks type and character separately.
- `strict_accuracy` is the most important score because it requires both the split and the labels to be correct.

Phase 2 completion target uses `strict_accuracy >= 0.85` on the locked independent `gold/test` fixture set.

## Current baseline snapshot

Latest local run output:

### Gold independent 5-chapter set (current snapshot)

- `total_cases`: 5
- `total_expected_segments`: 351
- `matched_segments`: 210
- `span_recall`: 0.5983
- `type_accuracy`: 0.9381
- `character_accuracy`: 0.9905
- `strict_accuracy`: 0.7408

### Bootstrap 5-chapter set from current pipeline output

- `total_cases`: 5
- `total_expected_segments`: 598
- `matched_segments`: 598
- `span_recall`: 1.0
- `type_accuracy`: 1.0
- `character_accuracy`: 1.0
- `strict_accuracy`: 1.0

Bootstrap currently passes 0.85, but this does not satisfy the independent acceptance gate.

## What 100% means

A score of 100% means that, on the specific fixture set being tested:
- every expected segment had a matching predicted text span
- every matched span had the correct segment type
- every matched span had the correct character label

So 100% means perfect performance on that benchmark input, not perfect performance on all novels or all chapters.

If the fixture set was bootstrapped from the current pipeline output, 100% also means the current code reproduces that exported label set exactly.

## Interpretation notes

- Final acceptance requires `--mode gold --split test --enforce-threshold` to pass.
- Strict accuracy is intentionally harsh and includes both segmentation and labeling correctness.

## Recommended iteration loop

1. Export or label fixture chapters.
2. Run benchmark and record metrics.
3. Improve prompt and fallback parsing.
4. Re-run benchmark.
5. Repeat until strict accuracy reaches 0.85 or higher.

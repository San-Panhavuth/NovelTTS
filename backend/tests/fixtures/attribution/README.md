# Attribution Fixture Format

This folder contains attribution fixtures for Phase 2 benchmarking.

## Fixture sets

- `bootstrap/`: exported from current pipeline output. Use for self-consistency regression checks only.
- `gold/dev/`: independent fixtures used for iteration and debugging.
- `gold/test/`: locked independent acceptance fixtures.
- `gold/test.lock.json`: hash lock for `gold/test/*.json`.

## File format

Each JSON file stores an array of cases:

```json
[
  {
    "id": "unique-case-id",
    "genre": "cultivation|romance|action|other",
    "text": "raw input chunk",
    "expected": [
      {
        "text": "exact excerpt",
        "type": "narration|dialogue|thought",
        "character": "optional character name or null"
      }
    ]
  }
]
```

## Labeling notes

- Keep `expected[].text` as an exact excerpt from `text`.
- Keep segmentation human-consistent and stable across edits.
- Use `character: null` when speaker attribution is unknown.
- Keep acceptance fixtures independent from the current model output.
- Label in `gold/dev` first, review, then intentionally promote to `gold/test`.

## Export independent fixtures from DB-reviewed data

You can export fixtures from already uploaded and reviewed chapters into `gold/dev`:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/export_attribution_fixtures_from_db.py --book-id <BOOK_ID> --chapter 1:cultivation --chapter 2:cultivation --chapter 3:romance --chapter 4:romance --chapter 5:action
```

Notes:

- `--chapter` uses format `<chapter_idx>:<genre>` and can be repeated.
- Default output is `gold/dev`.
- Writing directly to `gold/test` is blocked unless `--allow-locked-test-write` is provided.

## Export bootstrap fixtures from current pipeline

Use bootstrap exporter for self-consistency snapshots:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/export_attribution_fixtures_from_pipeline.py --book-id <BOOK_ID> --chapter 1:cultivation --out-dir backend/tests/fixtures/attribution/bootstrap --overwrite
```

This exporter refuses to write into any `gold/` directory.

## Update locked test hash

After intentional updates to `gold/test` fixtures:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/update_attribution_fixture_lock.py
```

## Running benchmark

From repo root:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_attribution_benchmark.py --mode bootstrap
```

Run independent development set:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_attribution_benchmark.py --mode gold --split dev
```

This run now includes an automatic `error_report` section in JSON output with:

- mismatch totals for span/type/character
- top repeated span mismatches
- top repeated type mismatches
- top repeated character mismatches

Tune attribution prompt and fallback logic against this `gold/dev` report only.

Enforce Phase 2 acceptance target on locked independent set:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_attribution_benchmark.py --mode gold --split test --threshold 0.85 --enforce-threshold
```

Use `gold/test` only as locked acceptance verification (no tuning on this split).

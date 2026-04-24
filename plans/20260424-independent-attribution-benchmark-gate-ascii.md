# Plan: Independent Attribution Benchmark Gate for Phase 2

## Why
Phase 2 currently mixes self-consistency and independent accuracy signals, which makes the >=85% gate ambiguous. This plan formalizes benchmark modes and fixture governance so Phase 2 completion is measured only on an independent, locked gold test split, while still preserving a bootstrap mode for fast regression checks during prompt iteration.

## Phase + Step
Phase 2, step "Build accuracy fixture set: 5 hand-labeled chapters covering cultivation, romance, action" of docs/DEV_PLAN.md

## Files Touched
- backend/tests/run_attribution_benchmark.py (MODIFY) - add CLI mode/split selection and threshold enforcement that only gates independent gold test runs
- backend/tests/attribution_benchmark.py (MODIFY) - add fixture mode/split loading entrypoints, lock/hash validation hook, and benchmark metadata in result payload
- backend/tests/export_attribution_fixtures_from_db.py (MODIFY) - support exporting directly into gold/dev so independent fixtures are prepared separately from locked test fixtures
- backend/tests/export_attribution_fixtures_from_pipeline.py (MODIFY) - keep bootstrap-only export semantics explicit and prevent accidental writes into gold fixtures
- backend/tests/fixtures/attribution/README.md (MODIFY) - document bootstrap vs gold responsibilities, gold dev/test workflow, and lockfile policy
- backend/tests/fixtures/attribution/BENCHMARK_PROCESS.md (MODIFY) - document acceptance gate as independent locked gold test only and define allowed benchmark modes
- docs/DEV_PLAN.md (MODIFY) - clarify that >=85% means strict accuracy on independent locked gold test split
- backend/tests/fixtures/attribution/gold/dev/ (NEW) - add editable gold development fixture directory
- backend/tests/fixtures/attribution/gold/test/ (NEW) - add locked independent gold test fixture directory used by acceptance gate
- backend/tests/fixtures/attribution/gold/test.lock.json (NEW) - store per-file hashes for locked gold test fixtures
- backend/tests/update_attribution_fixture_lock.py (NEW) - utility to regenerate lockfile intentionally when test fixtures are explicitly updated

## Tasks
1. Edit backend/tests/attribution_benchmark.py to introduce fixture-set resolution helpers for bootstrap, gold/dev, and gold/test so loading logic no longer relies on a single flat directory.
2. Edit backend/tests/attribution_benchmark.py to add lockfile verification (gold/test.lock.json) before running any benchmark on gold/test, failing fast when fixture content hashes do not match.
3. Create backend/tests/update_attribution_fixture_lock.py to compute deterministic sha256 hashes for gold/test/*.json and write a sorted lockfile payload.
4. Create backend/tests/fixtures/attribution/gold/dev/ and move current editable independent fixtures from full/ into this split during implementation, preserving file names for traceability.
5. Create backend/tests/fixtures/attribution/gold/test/ and populate the locked acceptance subset from reviewed gold fixtures; create backend/tests/fixtures/attribution/gold/test.lock.json from those files.
6. Edit backend/tests/run_attribution_benchmark.py to add --mode {bootstrap,gold} and --split {dev,test} flags, defaulting to non-gating local iteration behavior (bootstrap or gold/dev).
7. Edit backend/tests/run_attribution_benchmark.py to enforce threshold only when mode/split is gold/test; reject invalid combinations (for example, --enforce-threshold with bootstrap) with clear CLI errors.
8. Edit backend/tests/export_attribution_fixtures_from_db.py to support an explicit output target under gold/dev so fixture curation for independent sets is isolated from locked acceptance fixtures.
9. Edit backend/tests/export_attribution_fixtures_from_pipeline.py to hard-scope output to bootstrap fixtures and add guardrails that prevent writing into gold/* directories.
10. Edit backend/tests/fixtures/attribution/README.md and backend/tests/fixtures/attribution/BENCHMARK_PROCESS.md to define the new split workflow, lock/update procedure, and exact acceptance command for independent locked gold test.
11. Edit docs/DEV_PLAN.md to change the Phase 2 done-when text so >=85% explicitly refers to strict accuracy on the independent locked gold test split.
12. Add or update benchmark tests in backend/tests/test_attribution.py (or a new backend/tests/test_attribution_benchmark_cli.py) to cover mode/split routing, lockfile mismatch failure, and threshold gating behavior.
13. Record provider impact as none to protocol surfaces: benchmark still uses existing LLMProvider reads only; no changes to TTSProvider, StorageProvider, or AuthProvider interfaces.

## Risks
- LLM JSON parsing instability can produce noisy benchmark variance; lock validation protects fixture integrity but does not eliminate model nondeterminism.
- Free-tier LLM rate limits can cause flaky benchmark runs, especially for full gold test passes; document retry/backoff expectations in benchmark process docs.
- Voice tagging gaps are out of scope for this gate and must not be conflated with attribution strict-accuracy failures.
- TTS job logging is not directly involved in this benchmark flow; keep this work isolated so no assumptions are made about audio pipeline observability.

## Done When
- Benchmark CLI supports explicit mode/split selection and errors on unsupported gating combinations.
- gold/test benchmark runs fail when any locked fixture hash differs from gold/test.lock.json.
- Threshold enforcement is wired to independent locked gold test runs and blocked for bootstrap/self-consistency runs.
- Fixture docs describe bootstrap vs gold purpose, gold dev/test workflow, and lockfile update steps.
- Phase 2 done-when wording in docs/DEV_PLAN.md explicitly states >=85% on independent locked gold test strict accuracy.
- Minimal run commands are documented:
  - python backend/tests/run_attribution_benchmark.py --mode bootstrap
  - python backend/tests/run_attribution_benchmark.py --mode gold --split dev
  - python backend/tests/run_attribution_benchmark.py --mode gold --split test --enforce-threshold --threshold 0.85
  - python backend/tests/update_attribution_fixture_lock.py

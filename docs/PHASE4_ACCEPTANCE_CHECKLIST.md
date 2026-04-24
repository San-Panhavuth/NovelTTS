# Phase 4 Acceptance Checklist

Use this checklist to mark Phase 4 as truly done for production quality.

## Scope

Phase 4 covers chapter audio generation:

- queue generation job
- synthesize per segment
- stitch with FFmpeg
- store output URL
- expose job status and frontend polling/retry UX

## Prerequisites

- Backend API reachable (default `http://127.0.0.1:8010`)
- Frontend reachable (default `http://localhost:3000`)
- FFmpeg installed and available in PATH
- Valid Supabase JWT for authenticated API calls
- At least one processed book with chapters and segments

## Automated runtime validation (recommended)

Run:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe backend/tests/run_phase4_runtime_validation.py --book-id <BOOK_ID> --chapters 1-10 --bearer-token <JWT> --check-conflict
```

Pass criteria:

- `summary.failed == 0`
- `summary.timeout == 0`
- most/all chapters return `terminal_status=completed`
- conflict probe returns `passed=true` (2nd concurrent generate gets 409)

## Manual quality checks (must-do)

For at least 3 different chapters:

1. Open chapter page and click **Generate Audio**
2. Observe progress updates and completion state
3. Play output and check:
   - no abrupt early cut-off
   - no obvious pops/clicks between joins
   - no long silence from failed chunks
4. Confirm retry UX:
   - simulate/observe failed generation
   - click **Retry generation**
   - verify new job starts and recovers

## Failure-path checks

- Missing FFmpeg should surface explicit error:
  - `"FFmpeg executable was not found. Install FFmpeg and ensure it is in PATH."`
- Concurrent generate should return HTTP 409 with running-job message
- Polling interruption should fail cleanly with retry option in UI

## Test suite gate

Run and require pass:

```powershell
c:/Users/Vuth/Desktop/NovelTTS/backend/.venv/Scripts/python.exe -m pytest backend/tests
```

## Done definition

Mark Phase 4 done only when:

- automated runtime validation passes for target chapters
- manual audio quality checks pass on multiple chapters
- failure/retry behavior validated in live flow
- backend test suite remains green

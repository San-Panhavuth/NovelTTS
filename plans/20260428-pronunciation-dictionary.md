# Plan: Pronunciation Dictionary (Phase 3 remaining task)

## Why
Phase 3 voice assignment system assigns three global voices (narration, dialogue, thought) per book but does not handle proper pronunciation of non-English names, cultivation terms, and place names common in translated CN/KR/JP web novels. Without phoneme tagging via SSML `<phoneme>` overlays, TTS engines default to English phonetics—producing mispronunciations like "魔法 (magic)" as "maw-fah" instead of the correct Mandarin. This phase builds the infrastructure to infer correct pronunciations via Gemini, store per-book pronunciation entries, and inject SSML into segments before TTS synthesis.

## Phase + Step
Phase 3, remaining task (after voice assignment ✅)  
Reference: `docs/DEV_PLAN.md` Phase 3 — Pronunciation Dictionary (lines ~140–143)

## Files Touched

### Backend — Phonetics Inference Service (NEW)
- `backend/app/services/phonetics_inference.py` (NEW) — LLM pipeline to extract and infer phonetics for terms

### Backend — SSML Injection Service (NEW)
- `backend/app/services/ssml_injector.py` (NEW) — applies PronunciationEntry phonemes to segment text via SSML `<phoneme>` tags

### Backend — Pronunciation API Router (NEW)
- `backend/app/routers/pronunciations.py` (NEW) — CRUD endpoints for per-book pronunciation dictionary

### Backend — Database & Schema (MODIFY)
- `backend/app/models/pronunciation_entry.py` (already exists, no change needed)
- `alembic/versions/` (no new migration; model already in schema from Phase 0)

### Backend — Audio Generation Integration (MODIFY)
- `backend/app/services/audio_generation.py` — inject SSML before calling `TTSProvider.synthesize(text, voice_id, ssml=True)`

### Backend — Tests (NEW)
- `backend/tests/test_phonetics_inference.py` (NEW) — unit tests for LLM prompt, JSON parsing, term extraction
- `backend/tests/test_ssml_injector.py` (NEW) — unit tests for SSML tag injection logic
- `backend/tests/test_pronunciation_api.py` (NEW) — integration tests for `/pronunciations/*` endpoints

### Frontend — API Client (MODIFY)
- `frontend/src/lib/backend.ts` — add client functions for GET/POST/PUT pronunciation endpoints

### Frontend — Pronunciation Dictionary UI (NEW)
- `frontend/src/app/books/[id]/pronunciations/page.tsx` (NEW) — read-only list of inferred pronunciations with inline edit mode
- `frontend/src/app/books/[id]/pronunciations/AddDialog.tsx` (NEW) — modal to manually add/override pronunciation entry

### Frontend — Integration in Generate Flow (MODIFY)
- `frontend/src/app/books/[id]/chapters/[idx]/page.tsx` — link to pronunciation dictionary before generating audio

## Tasks

### 1. Define Phonetics Inference Prompt + Schema
**File**: `backend/app/services/phonetics_inference.py`  
**Why**: Establish the LLM contract for extracting and inferring phonetics.  
**Steps**:
- Define a Pydantic schema `PhoneticsInferenceRequest` with segment text + character names + origin language
- Define schema `PhoneticsInferenceResponse` with list of `{ term, phoneme, language_code, confidence }`
- Write the inference prompt (in English, targeting Gemini 2.5 Flash):
  - Receives a segment of novel text
  - Task: identify non-English names, cultivation terms, place names that will be mispronounced
  - Return JSON-only `{ entries: [{ term, phoneme, language_code, confidence }] }` where `phoneme` is IPA or SSML format
  - Include exemplars for common CN cultivation terms (e.g., "丹" = "dan" in Mandarin)
  - Mark confidence 0.0–1.0 based on term commonality and inference certainty
- **Acceptance**: prompt passes linting; schema matches response format

### 2. Implement Phonetics Inference Service
**File**: `backend/app/services/phonetics_inference.py`  
**Why**: Wire LLM inference into the backend with error handling and fallback logic.  
**Steps**:
- Implement `async def infer_pronunciations(text: str, characters: list[str], origin_language: str | None, llm_provider: LLMProvider) -> list[dict]`
- Call `llm_provider.complete_json(prompt)` with the inference prompt
- Parse response inside `try/except` — on failure, return empty list (no phonetics inferred)
- Filter entries by confidence ≥ 0.5
- Log every step: "inference_started", "inference_prompt_sent", "inference_response_parsed", "entries_filtered"
- **Acceptance**: service returns list of inference dicts; logs appear in stdout when called

### 3. Add SSML Phoneme Injection Service
**File**: `backend/app/services/ssml_injector.py`  
**Why**: Transform plain text + pronunciation entries → SSML with `<phoneme>` tags.  
**Steps**:
- Implement `def inject_ssml(text: str, entries: list[PronunciationEntry]) -> str`
  - Build a dict mapping term (exact match, case-insensitive) → phoneme
  - Iterate through text, find term matches (word boundary aware)
  - Wrap each match in `<phoneme alphabet="ipa" ph="...">term</phoneme>` or `<phoneme alphabet="x-sampa" ph="...">term</phoneme>`
  - Return modified text (still valid for TTS `ssml=True` parameter)
- Handle edge case: overlapping matches (prefer longest match)
- Handle edge case: term appears within another term (skip inner matches)
- **Acceptance**: injection produces valid SSML; test with real Edge TTS + Kokoro voice IDs

### 4. Create Pronunciation API Router
**File**: `backend/app/routers/pronunciations.py`  
**Why**: Expose CRUD endpoints for pronunciation dictionaries.  
**Steps**:
- `POST /books/{book_id}/pronunciations/infer` — trigger Gemini inference on all segments for a book
  - Collect all segments for the book
  - For each segment, call `infer_pronunciations(segment.text, ...)`
  - Deduplicate terms across all segments
  - Store `PronunciationEntry` rows (upsert on book_id + term)
  - Return list of stored entries + inference metadata
- `GET /books/{book_id}/pronunciations` — list all stored entries for a book
- `POST /books/{book_id}/pronunciations` — manually add a single entry (term + phoneme + language_code)
- `PUT /books/{book_id}/pronunciations/{entry_id}` — edit an entry (term, phoneme, or confidence)
- `DELETE /books/{book_id}/pronunciations/{entry_id}` — remove an entry
- Require auth (JWT from FastAPI middleware)
- **Acceptance**: all 5 endpoints respond with correct HTTP status; entries are stored/retrieved from DB

### 5. Integrate SSML Injection into Audio Generation
**File**: `backend/app/services/audio_generation.py`  
**Why**: Ensure TTS synthesis applies pronunciation overrides.  
**Steps**:
- In `_synthesize_with_retries` or the segment loop, before calling `tts_provider.synthesize(text, voice_id)`:
  - Query all `PronunciationEntry` rows for the book (cache this per job)
  - Call `inject_ssml(segment_text, entries)` → ssml_text
  - Call `tts_provider.synthesize(ssml_text, voice_id, ssml=True)` instead
- Add logging: "ssml_injected_for_segment_idx={idx}, num_replacements={N}"
- Edge case: if no pronunciation entries exist, skip injection and pass `ssml=False` to TTS
- **Acceptance**: audio generation still works with/without pronunciations; logs show SSML injection steps

### 6. Write Backend Unit Tests — Phonetics Inference
**File**: `backend/tests/test_phonetics_inference.py`  
**Why**: Validate LLM prompt and inference logic.  
**Steps**:
- Mock `LLMProvider` (via dependency injection)
- Test 1: valid Gemini response → entries parsed correctly
- Test 2: malformed JSON in response → empty list returned (graceful fallback)
- Test 3: filtering by confidence ≥ 0.5 works
- Test 4: logging captures all steps
- Test 5: edge case — text with no detectable terms → empty response
- Run: `pytest backend/tests/test_phonetics_inference.py -v`
- **Acceptance**: all 5 tests pass; coverage ≥ 90%

### 7. Write Backend Unit Tests — SSML Injector
**File**: `backend/tests/test_ssml_injector.py`  
**Why**: Validate SSML tag injection logic.  
**Steps**:
- Test 1: single term replaced with `<phoneme>` tag
- Test 2: multiple non-overlapping terms in same text
- Test 3: case-insensitive matching (term "Ye Qing" matches "ye qing" in text)
- Test 4: longest-match preference (if "魔法" and "法" both in dict, "魔法" gets priority)
- Test 5: term with special regex chars (e.g., "Li'l") doesn't break regex
- Test 6: empty entries list → text unchanged
- Test 7: invalid SSML alphabet parameter → defaults to "ipa"
- Run: `pytest backend/tests/test_ssml_injector.py -v`
- **Acceptance**: all 7 tests pass; coverage ≥ 95%; output is valid SSML

### 8. Write Backend Integration Tests — Pronunciation API
**File**: `backend/tests/test_pronunciation_api.py`  
**Why**: Validate REST endpoints against a real test DB.  
**Steps**:
- Setup: create test book + segments
- Test 1: POST infer → returns entries + stores in DB
- Test 2: GET list → returns all entries for book
- Test 3: POST manual entry → stored in DB
- Test 4: PUT edit entry → updated in DB
- Test 5: DELETE removes entry → not in DB
- Test 6: auth required — unauthenticated request → 401
- Test 7: book isolation — user A cannot access user B's pronunciation entries
- Run: `pytest backend/tests/test_pronunciation_api.py -v`
- **Acceptance**: all 7 tests pass; coverage ≥ 85%

### 9. Update Audio Generation Tests
**File**: `backend/tests/` (modify existing audio generation test)  
**Why**: Ensure SSML injection doesn't break existing TTS job flow.  
**Steps**:
- Add a test case: generate audio for a segment with pronunciation entries
  - Mock `TTSProvider.synthesize` to verify it receives `ssml=True` and injected text
  - Verify job completes successfully
- Run: `pytest backend/tests/test_audio_generation.py -v`
- **Acceptance**: new test passes; existing tests still pass

### 10. Update Backend API Docs + Main Router
**File**: `backend/app/main.py`  
**Why**: Register the pronunciation router with FastAPI.  
**Steps**:
- Import `backend/app/routers/pronunciations.py`
- Register router: `app.include_router(pronunciations.router, prefix="/books", tags=["pronunciations"])`
- Verify schema registration if using auto-docs

### 11. Add Frontend API Client Functions
**File**: `frontend/src/lib/backend.ts`  
**Why**: Provide TypeScript wrappers for pronunciation endpoints.  
**Steps**:
- Add: `getpronunciations(bookId: string) -> Promise<PronunciationEntry[]>`
- Add: `addPronunciation(bookId: string, term: string, phoneme: string, language_code?: string) -> Promise<PronunciationEntry>`
- Add: `updatePronunciation(bookId: string, entryId: string, updates: Partial<PronunciationEntry>) -> Promise<PronunciationEntry>`
- Add: `deletePronunciation(bookId: string, entryId: string) -> Promise<void>`
- Add: `inferPronunciations(bookId: string) -> Promise<{ entries: PronunciationEntry[], summary: string }>`
- All require auth header (JWT from Supabase)
- **Acceptance**: functions have correct signatures; TypeScript strict mode passes

### 12. Create Frontend Pronunciations Page UI
**File**: `frontend/src/app/books/[id]/pronunciations/page.tsx`  
**Why**: Display and manage pronunciation dictionary per book.  
**Steps**:
- Layout:
  - Header: "Pronunciation Dictionary" + book title
  - Button: "Infer from Segments" (calls `inferPronunciations`, shows spinner + toast on complete)
  - Button: "Add Manual Entry" (opens modal)
  - Table with columns: term | phoneme | language_code | confidence | actions (edit, delete)
  - Empty state: "No pronunciations yet. Tap Infer to start."
- Interactions:
  - Click table row → inline edit mode (term, phoneme read-only; can edit confidence)
  - Click delete → confirmation modal → call `deletePronunciation`
  - Click "Add Manual" → modal with form
- Data fetching: `useQuery({ queryKey: ['pronunciations', bookId], queryFn: () => getpronunciations(bookId) })`
- Loading + error states per React Query patterns
- **Acceptance**: page loads, displays entries, can add/edit/delete; no console errors

### 13. Create Frontend Add/Edit Pronunciation Modal
**File**: `frontend/src/app/books/[id]/pronunciations/AddDialog.tsx`  
**Why**: Allow manual pronunciation entry addition.  
**Steps**:
- Form fields:
  - term (text input, required)
  - phoneme (text input, required; hint: "IPA or SSML format")
  - language_code (select: "zh-CN", "ko-KR", "ja-JP", or custom text)
  - confidence (slider 0.0–1.0, optional, default 1.0)
- Validate: term + phoneme non-empty
- On submit: call `addPronunciation`, toast success, close modal, refetch pronunciations
- On error: show toast + keep modal open
- **Acceptance**: modal renders; form validation works; can submit and see entry in list

### 14. Add Pronunciation Dictionary Link to Chapter Audio Page
**File**: `frontend/src/app/books/[id]/chapters/[idx]/page.tsx`  
**Why**: Make pronunciation editing discoverable before TTS generation.  
**Steps**:
- Add link/button in the chapter header or sidebar: "Pronunciations" → navigate to `/books/[id]/pronunciations`
- Or: in the Generate Audio section, add a small info pill: "❓ Pronunciations defined: N" with link
- **Acceptance**: link visible; clicking navigates to pronunciation page

### 15. Add End-to-End Test — Full Pronunciation Pipeline
**File**: `backend/tests/test_e2e_pronunciation.py` (NEW)  
**Why**: Validate entire flow: infer → store → inject → generate audio.  
**Steps**:
- Setup: create book + segments with non-English terms
- Step 1: call `POST /books/{id}/pronunciations/infer` with mock Gemini response
- Step 2: verify entries stored in DB
- Step 3: trigger audio generation for one segment
- Step 4: verify TTS was called with SSML (mock the TTSProvider)
- Step 5: verify audio job completes successfully
- Run: `pytest backend/tests/test_e2e_pronunciation.py -v`
- **Acceptance**: test passes end-to-end

## Risks

- **LLM JSON parsing failures**: Gemini may return malformed JSON or low-confidence entries. *Mitigation*: wrap in try/except, return empty list, log error; frontend shows "No pronunciations inferred" (graceful fallback).
- **SSML injection breaking TTS**: malformed SSML tags or special characters in phonemes may cause TTS to fail. *Mitigation*: validate SSML syntax in tests; run real TTS calls (not just mocks) in integration tests; log SSML before sending to provider.
- **Regex overlaps in SSML injector**: overlapping term matches in text could produce nested or duplicate tags. *Mitigation*: implement longest-match and non-overlapping logic; test exhaustively with fixture data.
- **Performance on large books**: inferring pronunciations for 1000+ segments sequentially is slow. *Mitigation*: batch LLM calls (5–10 segments per prompt); run as background job via BullMQ (defer to Phase 4 if needed).
- **Pronunciation data explosion**: each book accumulates many entries over time (manual + inferred). *Mitigation*: add frontend pagination/search; enforce unique constraint on (book_id, term) in schema (already present).
- **Auth boundary**: unauthenticated users could infer pronunciations if endpoint not guarded. *Mitigation*: all endpoints require FastAPI JWT auth middleware (already in place); test 401 cases.

## Done When

- ✅ `backend/app/services/phonetics_inference.py` exists with `infer_pronunciations()` function, passes unit tests
- ✅ `backend/app/services/ssml_injector.py` exists with `inject_ssml()` function, produces valid SSML, passes unit tests
- ✅ `backend/app/routers/pronunciations.py` implements all 5 endpoints (infer, list, add, edit, delete) + auth + integration tests pass
- ✅ Audio generation service calls `inject_ssml()` before TTS synthesis; logs show SSML injection steps
- ✅ `backend/tests/test_phonetics_inference.py` passes with ≥ 90% coverage
- ✅ `backend/tests/test_ssml_injector.py` passes with ≥ 95% coverage
- ✅ `backend/tests/test_pronunciation_api.py` passes with ≥ 85% coverage + 7 test cases
- ✅ `backend/tests/test_e2e_pronunciation.py` passes end-to-end (infer → store → inject → generate)
- ✅ Frontend `/books/[id]/pronunciations` page renders and allows add/edit/delete operations
- ✅ `frontend/src/app/books/[id]/chapters/[idx]/page.tsx` links to pronunciation page
- ✅ `ruff check` passes on all backend files; `prettier --check` passes on all frontend files
- ✅ All pronunciation features work without breaking existing Phase 1–3 functionality

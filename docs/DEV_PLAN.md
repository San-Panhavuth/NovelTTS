# Development Plan: NovelTTS

Status legend: ✅ done · 🔄 in progress · ⬜ todo · ⏭ deferred (post-MVP)

---

## Phase 0 — Setup & Foundations
**Goal**: monorepo + local dev stack runs end to end with no errors.

- ✅ Initialize monorepo: `frontend/` (latest Next.js), `backend/` (FastAPI), `worker/` (BullMQ)
- ⬜ Provision Supabase project (DB + Auth) — local + cloud instances *(requires user cloud account setup)*
- ⬜ Provision Upstash Redis (free tier) *(requires user cloud account setup)*
- ⬜ Provision Cloudflare R2 bucket + CORS policy *(requires user cloud account setup)*
- ✅ Initialize Prisma + SQLAlchemy schemas with shared model defs: Book, Chapter, Segment, Character, CharacterProfile, VoiceRequirement, Voice, AudioJob, PronunciationEntry
- ✅ First DB migration
- ✅ Configure ESLint + Prettier (frontend), Ruff + Black (backend)
- ✅ `.env.example` files for both apps
- ✅ GitHub Actions: lint + type-check on every PR
- ✅ `docker-compose.yml` for local Postgres + Redis + backend + worker

**Done when**: `docker-compose up` boots full local stack with no errors. ✅ Met locally.

---

## Phase 1 — Auth & Upload Flow
**Goal**: logged-in user uploads an EPUB and sees its chapter list.

- ⬜ Wire Supabase Auth on Next.js (email + Google OAuth)
- ⬜ FastAPI JWT middleware that validates Supabase JWT
- ⬜ EPUB upload endpoint: receive file → ebooklib parse → store chapters in DB
- ⬜ Handle malformed EPUB HTML: strip tags, decode entities, normalize whitespace
- ⬜ 50MB file size limit + MIME type validation
- ⬜ REST endpoints: `GET /books`, `GET /books/{id}`, `GET /books/{id}/chapters/{index}`
- ⬜ Frontend: auth pages (sign up, log in, forgot password)
- ⬜ Frontend: library page (user's uploaded books)
- ⬜ Frontend: upload page with drag-and-drop zone
- ⬜ Frontend: book detail page (chapter list + "Process" button)

**Done when**: logged-in user uploads an EPUB and sees its chapter list.

---

## Phase 2 — Text Processing & Dialog Attribution
**Goal**: any chapter produces a correctable, tagged segment list.

- ⬜ Text chunker: split chapter into ~500-word segments at paragraph boundaries
- ⬜ Wire Gemini 2.5 Flash via `google-generativeai` SDK
- ⬜ Design + iterate attribution prompt → JSON `[{ text, type, character, confidence }]`
- ⬜ Pipeline: chunk → LLM → JSON parse (try/except) → store Segments
- ⬜ Character registry endpoint: extract unique character names per book
- ⬜ Confidence flagging: mark low-confidence attributions for review
- ⬜ REST endpoints:
  - `POST /books/{id}/chapters/{index}/process`
  - `GET /books/{id}/characters`
  - `GET /books/{id}/chapters/{index}/segments`
- ⬜ Frontend: segment review UI — tagged lines, allow correcting type / character
- ⬜ Build accuracy fixture set: 5 hand-labeled chapters covering cultivation, romance, action

**Done when**: chapter produces tagged segments with ≥ 85% accuracy on the fixture set.

---

## Phase 3 — Character Intelligence & Voice System
**Goal**: AI profiles + recommended voices per character; user manages everything from one dashboard.

### Character Profile Pipeline (LLM-only — no wiki)
- ⬜ Pipeline: collect first 5 chapters per character + every dialogue line they speak → Gemini → `CharacterProfile`
- ⬜ Store `CharacterProfile` (age, gender, personality[], speechStyle[], role, voiceNotes, confidence)
- ⬜ LLM prompt: `CharacterProfile` → `VoiceRequirement` (pitch, age_group, tone, pacing, energy, avoid[], rationale)
- ⬜ Store `VoiceRequirement` per character

### Voice Library & Scoring
- ⬜ Build Edge TTS voice catalog ingestion script (auto-tag pitch / age / gender / locale from voice metadata)
- ⬜ Manually tag all ~10 Kokoro voices: pitch, ageGroup, tone, gender, energy
- ⬜ Generate preview audio samples for every voice → upload to R2
- ⬜ Voice scoring function: hard-reject voices in `avoid` list, score positive matches, return top 3
- ⬜ Voice conflict detector: flag if two main characters share a voice

### Pronunciation Dictionary
- ⬜ LLM infers phonetics for character names (Korean / Chinese), cultivation terms, place names
- ⬜ Store `PronunciationEntry` per book
- ⬜ SSML `<phoneme>` injector before TTS call

### Dashboard
- ⬜ Per-novel `/dashboard/[bookId]/voices` page
- ⬜ Character cards: name, role, age badge, personality summary, "avoid" chips
- ⬜ Top 3 recommended voices with one-click preview
- ⬜ "Change Voice" full browser, disqualified voices greyed out + tooltip
- ⬜ "Re-research" button to re-run profile extraction
- ⬜ Manual override: edit AI personality notes

**Done when**: dashboard shows all characters with profiles + recommended voices + working assignment.

---

## Phase 4 — TTS Audio Generation
**Goal**: clicking "Generate" produces a playable MP3 per chapter.

- ⬜ Set up BullMQ job queue (Redis) with TTS worker
- ⬜ TTS worker: dequeue segment → call provider (Kokoro CUDA or Edge TTS) → save chunk to R2
- ⬜ Audio stitcher: FFmpeg concatenates chunks → final chapter MP3
- ⬜ Upload final MP3 to R2, store URL in DB
- ⬜ REST endpoints:
  - `POST /books/{id}/chapters/{index}/generate`
  - `GET /jobs/{jobId}/status`
- ⬜ WebSocket endpoint for real-time progress
- ⬜ Audio caching: skip regeneration when `(voice_id, text_hash)` matches
- ⬜ Retry logic: max 3 retries per failed segment
- ⬜ Frontend: "Generate Audio" button + progress bar + plain `<audio>` player

**Done when**: clicking Generate produces a playable MP3.

---

## Phase 5 — Audio Player & Playback UX (post-MVP)
- ⏭ Wavesurfer.js waveform player
- ⏭ Speed control (0.75x – 2x)
- ⏭ Chapter navigation (prev / next)
- ⏭ Sync segment text highlight with audio position
- ⏭ Resume playback per book per user

---

## Phase 6 — PDF / TXT Support (post-MVP)
- ⏭ PDF upload via PyMuPDF + cleanup heuristics (headers, footers, hyphenation)
- ⏭ TXT upload + chapter heading detection

---

## Phase 7 — Polish & Reliability (post-MVP)
- ⏭ Error boundaries + toast notifications
- ⏭ DB indexes on `bookId`, `chapterId`, `status`, `userId`
- ⏭ Rate limiting on Gemini / Edge TTS calls (free tier protection)
- ⏭ Admin panel: books, job queue, error logs
- ⏭ Unit + integration tests for: chunker, JSON parser, stitcher, voice scorer, character extractor, SSML injector
- ⏭ Load test: 10 concurrent chapter generations

---

## Phase 8 — Production Launch (post-MVP)
- ⏭ Deploy frontend to Vercel
- ⏭ Deploy backend + worker to Render
- ⏭ Sentry error monitoring
- ⏭ Better Uptime / UptimeRobot
- ⏭ Custom domain + SSL

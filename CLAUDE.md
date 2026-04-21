# Project: NovelTTS

## What this is
A web app that turns uploaded English-translated CN/KR/JP web novels (EPUB) into multi-voice audiobooks. An LLM tags each line as narration / dialogue / inner thought, infers per-character personality, and recommends matching TTS voices that the user can override. Users assign voices, the backend generates per-segment audio with Kokoro + Edge TTS, FFmpeg stitches it into chapter MP3s, and a streaming player handles playback.

## Tech Stack
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, React Query, Wavesurfer.js (Phase 5)
- **Backend**: Python 3.11 + FastAPI, Pydantic v2
- **Database**: PostgreSQL (Supabase) with Prisma (frontend) + SQLAlchemy 2 (backend)
- **Auth**: Supabase Auth (email + Google OAuth) — JWT validated by FastAPI
- **Job queue**: BullMQ + Redis (Upstash) — Node orchestrator + Python TTS/LLM workers
- **AI**: Gemini 2.5 Flash for dialog attribution + character profiling
- **TTS**: Kokoro (CUDA, lead voices) + Microsoft Edge TTS (variety) behind one `TTSProvider` interface
- **Audio**: FFmpeg for stitching; Cloudflare R2 for storage
- **File parsing**: ebooklib (EPUB only for MVP)
- **Hosting**: Vercel (frontend) + Render (backend + worker) + Supabase (DB/Auth) + Upstash (Redis) + R2 (audio)

## Code Standards
- **Python**: Ruff (lint + format) + Black, type hints everywhere, Pydantic models for I/O. snake_case files/functions, PascalCase classes.
- **TypeScript**: ESLint + Prettier, `strict: true`. PascalCase components, `useX` hooks, server actions in `actions/`.
- **Folder layout**:
  - `frontend/` — Next.js app
  - `backend/` — FastAPI service + Python workers
  - `worker/` — Node BullMQ orchestrator (if separated)
  - `shared/` — JSON schemas for cross-stack types
- **Provider interfaces**: TTS, LLM, Storage, Auth each abstracted behind a `Protocol` class so they're swappable.
- **No runtime scraping** — upload-only.
- **All LLM prompts request JSON-only output**, parsed inside `try/except` with a fallback.
- **The `avoid` list in voice scoring is a HARD disqualifier** — never recommend a voice in it, even if it scores well otherwise.
- **Log every step in TTS jobs** — async audio is impossible to debug without logs.

## Sub-Agent Routing Rules
- **Parallel dispatch**: 3+ unrelated tasks, no shared files (e.g. write a FastAPI endpoint + a Next.js page + a Prisma migration at the same time).
- **Sequential dispatch**: tasks depend on each other or share files (e.g. attribution prompt → tests using the prompt).
- **Background dispatch**: research / analysis tasks not blocking work (e.g. compile Edge TTS voice catalog).

## Active Sub-Agents
- `planner` — breaks a feature into ordered, file-level tasks; writes `/plans/YYYYMMDD-{slug}.md`
- `code-reviewer` — reviews diffs for security, correctness, and standards; flags missing TTS-job logging
- `tester` — writes pytest / Vitest tests, runs them, reports failures only
- `tts-debugger` — investigates audio artifacts, voice tagging mismatches, FFmpeg stitching issues
- `attribution-tuner` — iterates the LLM dialog-attribution prompt; runs accuracy benchmarks against fixture chapters

## Session Handoff
At the end of every session, update `/docs/SESSION_LOG.md` with: Completed · Next · Decisions · Blockers.

When starting a new session, read in this order:
1. `CLAUDE.md` (this file — auto-loaded)
2. `/docs/SESSION_LOG.md` (most recent entry)
3. `/docs/DEV_PLAN.md` (find current phase status)
4. `/docs/CODEBASE.md` (architecture refresher only if needed)

## Hard Rules
- Work strictly phase by phase — do not skip ahead.
- Never run actual TTS jobs in tests (mock the `TTSProvider`).
- Never commit `.env` files; ship `.env.example`.
- Integration tests hit a real Supabase test instance — do not mock the DB.
- Do not introduce a third TTS provider without updating the `TTSProvider` Protocol first.

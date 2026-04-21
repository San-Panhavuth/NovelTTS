# Session Log

Most recent on top. Each session ends with: **Completed · Next · Decisions · Blockers**.

---

## Session 2026-04-21 — Cloud provisioning completed, ready for Phase 1
### Completed
- Provisioned Supabase project and captured project URL, anon key, and service role key
- Provisioned Upstash Redis and configured secure `rediss://` connection URL
- Provisioned Cloudflare R2 bucket, generated access credentials, and configured bucket CORS for local frontend origin
- Added Gemini API key for backend usage
- Updated `docs/DEV_PLAN.md` to mark all remaining Phase 0 provisioning items as complete
- Updated `README.md` progress language to reflect current status

### Next
- Begin Phase 1, Step 1: wire Supabase Auth in Next.js (email + Google OAuth)
- Implement FastAPI JWT middleware to validate Supabase JWTs
- Start EPUB upload + parsing pipeline and persist chapter records

### Decisions Made
- Treat Phase 0 as fully complete (local foundations + cloud provisioning)
- Keep local development database on docker-compose Postgres for now; Supabase remains provisioned for auth and future DB cutover
- Keep Redis configured via Upstash `rediss://` URL in backend and worker envs

### Blockers
- none

---

## Session 2026-04-21 — Phase 0 implementation complete (local)
### Completed
- Re-scaffolded `frontend/` with latest Next.js and normalized monorepo layout
- Re-scaffolded `backend/` with FastAPI + uv + Ruff + Black + mypy + pytest
- Scaffolded `worker/` BullMQ orchestrator with TypeScript + ESLint + typecheck
- Added Prisma MVP schema with all core models and generated initial Prisma migration
- Added SQLAlchemy MVP model set and Alembic setup with initial revision file
- Added app-specific `.env.example` files (`frontend/`, `backend/`, `worker/`)
- Added `docker-compose.yml` for Postgres + Redis + backend + worker and validated stack boot
- Added GitHub Actions CI workflow for lint + type-check (JS + Python lanes)
- Validation passes: `pnpm lint`, `pnpm typecheck`, backend Ruff/Black/mypy/pytest

### Next
- User to provision Supabase, Upstash, and Cloudflare R2 accounts/credentials
- Fill `.env` values from provisioned cloud services and continue Phase 1

### Decisions Made
- Treat Phase 0 as complete for local engineering baseline
- Keep external cloud provisioning as explicit user-owned setup tasks
- Keep latest stable Next.js frontend baseline

### Blockers
- External account provisioning not automatable from repo:
	- Supabase project URL + keys
	- Upstash Redis URL
	- Cloudflare R2 endpoint + credentials

## Session 2026-04-21 — Phase 0 reset
### Completed
- Cancelled prior Phase 0 execution progress and restarted planning baseline
- Reconfirmed restart point at Phase 0, Step 1
- Updated project docs to target latest Next.js for frontend scaffolding

### Next
- Phase 0, Step 1: re-initialize monorepo (`frontend/` + `backend/` + `worker/`) from scratch workflow
- Continue Phase 0 tasks in order, without skipping

### Decisions Made
- Treat previous Phase 0 implementation progress as discarded for tracking purposes
- Use latest stable Next.js instead of pinning to Next.js 14

### Blockers
- none

## Session 2026-04-21 — Project bootstrap
### Completed
- Read original brief (`Upload.md`)
- Refined idea via 3 rounds of clarifying questions
- Locked stack: Next.js + FastAPI + Supabase + R2, Gemini 2.5 Flash, Kokoro + Edge TTS, EPUB-only upload, English audio, multi-user cloud deploy
- Created project doc structure (`CLAUDE.md`, `PRODUCT_PRD.md`, `DEV_PLAN.md`, `CODEBASE.md`, `SKILLS.md`, this log)
- Defined 5 sub-agents (`planner`, `code-reviewer`, `tester`, `tts-debugger`, `attribution-tuner`)
- Defined 5 slash commands (`/start-session`, `/end-session`, `/plan-feature`, `/review`, `/new-phase`)

### Next
- Phase 0, Step 1: initialize monorepo (`frontend/` + `backend/` + `worker/`)
- Provision Supabase project, Upstash Redis, Cloudflare R2 bucket
- Verify CUDA + PyTorch GPU installation locally before Phase 4

### Decisions Made
- **Architecture**: Next.js + FastAPI two-service split (not full-stack Next.js)
- **Source**: Upload-only EPUB; no scraping; no default catalog
- **Char research**: LLM-only from novel text (wiki dropped — won't help arbitrary uploads)
- **LLM**: Gemini 2.5 Flash (free tier first; Claude Haiku as paid fallback)
- **TTS**: Kokoro on CUDA + Edge TTS for variety, behind one `TTSProvider` interface
- **Auth**: Supabase Auth (email + Google OAuth)
- **Deploy target**: Vercel + Render + Supabase + Upstash + R2 from day 1
- **Language**: English only

### Blockers
- Need user-supplied: Gemini API key, Supabase project URL + service-role key, R2 bucket creds, Upstash Redis URL
- Confirm CUDA + GPU drivers are working before Phase 4 begins

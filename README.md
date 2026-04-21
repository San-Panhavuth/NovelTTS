# NovelTTS

NovelTTS turns uploaded EPUB novels into multi-voice audiobooks.

Status: Phase 0 is complete (foundations + cloud provisioning). Next focus is Phase 1 (Auth + EPUB upload flow). See `docs/DEV_PLAN.md` for detailed progress.

Multi-voice audiobook generator from EPUB uploads. Upload an English-translated CN/KR/JP web novel, get back chapter MP3s where each character speaks in a distinct voice.

## Repository Layout

```text
NovelTTS/
├── frontend/        Next.js app (latest, Vercel)
├── backend/         FastAPI + workers (Render)
├── worker/          Node BullMQ orchestrator
├── shared/          (future) cross-stack JSON schemas
├── docs/            PRD, dev plan, session log, codebase doc
├── plans/           Planner-agent output
├── .claude/         Sub-agents + slash commands
└── docker-compose.yml
```

See `docs/CODEBASE.md` for full architecture.

## How To Run (Windows + PowerShell)

This project has two run modes:
- Mode A: run everything with Docker Compose (fastest to start)
- Mode B: run apps locally and keep only Postgres/Redis in Docker (best for coding)

## Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.11
- uv (Python package manager)
- Docker Desktop
- FFmpeg (included in backend Docker image; install locally only if running backend outside Docker)

Install quick commands:

```powershell
npm i -g pnpm
pip install uv
```

## 1) First-Time Setup

From the repo root:

```powershell
pnpm install
Set-Location backend
uv sync
Set-Location ..
```

Create env files:

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item backend/.env.example backend/.env
Copy-Item worker/.env.example worker/.env
```

## 2) Run Mode A (All Services In Docker)

From repo root:

```powershell
docker compose up -d
docker compose ps
```

Expected services:
- `noveltts-postgres` on `localhost:5432`
- `noveltts-redis` on `localhost:6379`
- `noveltts-backend` on `localhost:8000`
- `noveltts-worker`

Stop all services:

```powershell
docker compose down
```

## 3) Run Mode B (Frontend/Backend/Worker Local + Infra In Docker)

Terminal 1 (infra):

```powershell
docker compose up -d postgres redis
```

Terminal 2 (frontend):

```powershell
pnpm dev:frontend
```

Terminal 3 (backend):

```powershell
pnpm dev:backend
```

Terminal 4 (worker):

```powershell
pnpm dev:worker
```

## 4) Database Migration (Prisma)

After Postgres is running:

```powershell
pnpm -F frontend prisma:migrate --name init
pnpm -F frontend prisma:generate
```

## 5) Useful Commands

```powershell
pnpm lint
pnpm typecheck
pnpm build
pnpm stack:up
pnpm stack:down
pnpm stack:logs
```

Backend checks:

```powershell
Set-Location backend
uv run ruff check app tests
uv run black --check app tests
uv run mypy app
uv run pytest -q
Set-Location ..
```

## 6) Troubleshooting

- If backend `uv run` fails with `.venv/lib64` access errors on Windows:

```powershell
Set-Location backend
Remove-Item .venv -Recurse -Force
uv sync
Set-Location ..
```

- If Docker DB auth fails unexpectedly, recreate local DB volume:

```powershell
docker compose down -v
docker compose up -d postgres redis
```

## Next Step For Phase 1

Phase 0 prerequisites are complete and environment values are configured.

Start implementing Phase 1 items in order:
- Supabase Auth wiring in Next.js (email + Google OAuth)
- FastAPI JWT middleware for Supabase token validation
- EPUB upload + parsing flow and chapter persistence
- Initial book/chapter REST endpoints and frontend library/upload/detail pages

Track implementation checklist in `docs/DEV_PLAN.md`.

## Cloud Services Reference

Provisioning status: completed for current development setup.

| Service | Used for | Env vars to set |
|---|---|---|
| Supabase | Postgres + Auth | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` |
| Upstash Redis | BullMQ job queue | `REDIS_URL` |
| Cloudflare R2 | Audio file storage | `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_ENDPOINT` |
| Google AI Studio | Gemini 2.5 Flash | `GEMINI_API_KEY` |

For local development, docker-compose Postgres + Redis covers local infra; cloud credentials are now provisioned for Supabase, Upstash, R2, and Gemini.

## Working With Claude Code

This repo has a structured workflow defined in `CLAUDE.md`:

- `/start-session` — load context at session start
- `/end-session` — log progress at session end
- `/plan-feature <description>` — dispatch planner agent
- `/review` — dispatch code-reviewer on uncommitted diff
- `/new-phase <N>` — transition to next dev phase

Sub-agents live in `.claude/agents/`. Hard rules and conventions are in `CLAUDE.md`.

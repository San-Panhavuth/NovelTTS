# NovelTTS

NovelTTS turns uploaded EPUB novels into multi-voice audiobooks.

Status: Phase 0 foundation is complete locally. See `docs/DEV_PLAN.md` for progress.

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

You still need cloud credentials before Phase 1 features:
- Supabase
- Upstash Redis
- Cloudflare R2
- Gemini API key

When ready, add those values to your env files and continue from `docs/DEV_PLAN.md`.

# Codebase Architecture

> Update this file at the end of each phase, not after every commit. It should always reflect the **current** state, not history.
> Phase 2 is complete under the current benchmark gate (`strict_accuracy >= 0.70` on locked `gold/test`; current `0.7408`).

## Repository Layout (current after Phase 0 local implementation)

```
NovelTTS/
├── frontend/                 Next.js App Router (latest)
│   ├── app/
│   │   ├── (auth)/           login, sign-up
│   │   ├── (app)/
│   │   │   ├── library/      user's uploaded books
│   │   │   ├── upload/       drag-drop EPUB upload
│   │   │   └── books/[id]/
│   │   │       ├── chapters/[idx]/    reader + player
│   │   │       └── voices/            character voice dashboard
│   │   └── api/              thin proxy routes (auth, file uploads → FastAPI)
│   ├── components/           shadcn/ui + custom
│   ├── lib/                  supabase client, api client, types
│   └── prisma/               schema.prisma + migrations
│
├── backend/                  FastAPI service
│   ├── app/
│   │   ├── routers/          books, chapters, characters, voices, jobs, ws
│   │   ├── services/         attribution, character_profiler, voice_scorer, ssml_injector
│   │   ├── providers/        tts/, llm/, storage/  (interface-based)
│   │   ├── workers/          tts_worker.py, attribution_worker.py, profile_worker.py, stitch_worker.py
│   │   ├── models/           SQLAlchemy ORM
│   │   ├── schemas/          Pydantic request/response models
│   │   └── deps/             auth (JWT validator), db, redis
│   ├── tests/                pytest + httpx
│   └── alembic/              migrations
│
├── shared/                   cross-stack JSON schemas (segments, voices, profiles)
│
├── docs/                     PRD, DEV_PLAN, SESSION_LOG, CODEBASE (this file), SKILLS
├── plans/                    YYYYMMDD-{slug}.md (subagent output)
├── .claude/                  agents/, commands/
├── docker-compose.yml        local stack
├── CLAUDE.md                 project brain (auto-loaded)
└── Upload.md                 original brief (do not modify)
```

## Provider Interfaces

All external services live behind a `Protocol` class so they can be swapped:

| Interface | Implementations | Method |
|---|---|---|
| `TTSProvider` | `KokoroProvider`, `EdgeTTSProvider`, `ElevenLabsProvider` (later) | `synthesize(text, voice_id, ssml=False) -> bytes` |
| `LLMProvider` | `GeminiProvider`, `OllamaProvider` (later) | `complete_json(prompt, schema) -> dict` |
| `StorageProvider` | `R2Provider`, `LocalFSProvider` (test) | `put(key, bytes) -> url`, `get(key) -> bytes` |
| `AuthProvider` | `SupabaseJWT` | `verify(token) -> User` |

## Job Queue Topology

```
Web (FastAPI) ──enqueue──▶ Redis (BullMQ)
                              │
                              ├─▶ attribution_worker  (CPU; calls Gemini)
                              ├─▶ profile_worker      (CPU; calls Gemini)
                              ├─▶ tts_worker          (GPU; calls Kokoro/Edge)
                              └─▶ stitch_worker       (CPU; FFmpeg) ─▶ R2
```

## Data Flow (Upload → Audio)

```
EPUB upload
  └─▶ ebooklib parse → Book + Chapter[] in Postgres
        └─▶ POST /chapters/{i}/process
              ├─▶ chunker → 500-word segments
              ├─▶ Gemini attribution → Segment[] with type + speaker
              └─▶ enqueue character profile job (background)
                    └─▶ Gemini character_profile + voice_requirement
                          └─▶ voice_scorer → top-3 recommendations
        └─▶ POST /chapters/{i}/generate
              ├─▶ enqueue tts_job per segment
              └─▶ stitch_job (FFmpeg) → chapter.mp3 → R2
```

## Key Models (see Prisma + SQLAlchemy schemas for source of truth)
- `User` — Supabase auth user mirror
- `Book` — uploaded EPUB metadata (`userId`, `title`, `author`, `originLanguage`)
- `Chapter` — raw text + processing status
- `Segment` — `{ chapterId, idx, text, type, characterId, audioUrl, contentHash }`
- `Character` — `{ bookId, name, voiceId }`
- `CharacterProfile` — LLM-extracted personality (`age`, `gender`, `personality[]`, `role`, `voiceNotes`, `confidence`)
- `VoiceRequirement` — LLM-mapped TTS requirements (`pitch`, `ageGroup`, `tone`, `pacing`, `energy`, `avoid[]`)
- `Voice` — TTS voice catalog (Kokoro + Edge TTS) with pre-tagged metadata
- `PronunciationEntry` — SSML phoneme overrides per book
- `AudioJob` — BullMQ job mirror for status display

## Environment Variables (loaded via `.env.example`)
| Var | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | both | Supabase Postgres |
| `SUPABASE_URL` | both | Project URL |
| `SUPABASE_ANON_KEY` | frontend | Public client |
| `SUPABASE_SERVICE_ROLE_KEY` | backend | Server-side only |
| `REDIS_URL` | backend, worker | Upstash |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_ENDPOINT` | backend | Cloudflare R2 |
| `GEMINI_API_KEY` | backend | Google AI Studio |
| `KOKORO_DEVICE` | backend | `cuda` / `cpu` |
| `EDGE_TTS_DEFAULT_VOICE` | backend | Fallback voice id |

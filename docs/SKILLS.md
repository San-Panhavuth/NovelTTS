# Skills

Project-specific workflows Claude should reach for when relevant. These are conventions for *this* project — not Claude Code platform skills.

---

## When to invoke each sub-agent

| Trigger | Agent |
|---|---|
| User says "plan X" or starts a non-trivial feature | `planner` |
| Before merging / committing a multi-file change | `code-reviewer` |
| Need test coverage for a new module | `tester` |
| TTS audio sounds wrong, voice mismatch, FFmpeg artifact | `tts-debugger` |
| Attribution accuracy regresses or new genre fails | `attribution-tuner` |

## When to invoke each slash command

| Command | Use |
|---|---|
| `/start-session` | First message of a new session — loads context from `SESSION_LOG.md` and `DEV_PLAN.md` |
| `/end-session` | Last message of a session — writes a new entry to `SESSION_LOG.md` |
| `/plan-feature <feature>` | Dispatch `planner` to write a plan to `/plans/` |
| `/review` | Dispatch `code-reviewer` on the current diff |
| `/new-phase <N>` | Mark previous phase ✅ in `DEV_PLAN.md`, set new phase 🔄, update `CODEBASE.md` |

## Coding workflows

### Adding a new TTS provider
1. Implement `TTSProvider` Protocol in `backend/app/providers/tts/`
2. Add provider name to `TTSProviderType` enum
3. Register in `tts_factory.py`
4. Pre-tag any new voices it exposes with pitch/age/gender/tone/energy
5. Add a recorded preview MP3 for each voice to R2
6. Update `CODEBASE.md` provider table

### Adding a new LLM prompt
1. Define output schema as a Pydantic model in `backend/app/schemas/llm/`
2. Write the prompt as a constant in `backend/app/services/prompts/`
3. Wrap call in `try/except` with fallback (return `None` or default)
4. Add a unit test with a fixture LLM response
5. If accuracy-critical (attribution, profiling), add to the benchmark fixture set

### Adding a Phase 1–4 user-facing feature
1. Confirm it appears in `DEV_PLAN.md` for the current phase — refuse if it skips ahead
2. Run `/plan-feature` to produce a plan in `/plans/`
3. Build sequentially per the plan
4. Run `/review` before committing
5. Update DEV_PLAN status and CODEBASE if architecture changed

## Avoid
- Building Phase 5+ features while Phase 4 is incomplete
- Hard-coding any voice ID, character name, or model name — use config or DB
- Skipping logging in TTS/LLM workers (they will be impossible to debug later)
- Using mock DB in integration tests (use Supabase test instance)
- Committing without running `/review` on multi-file changes

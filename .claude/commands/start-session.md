Start a new NovelTTS work session.

1. Read `docs/SESSION_LOG.md` and report the most recent entry's **Next**, **Decisions Made**, and **Blockers**.
2. Read `docs/DEV_PLAN.md` and identify the current phase (look for 🔄) and the next ⬜ task in that phase.
3. Read `CLAUDE.md`'s Hard Rules section as a refresher.
4. Print a 5-line briefing in this exact format:

```
📍 Phase: {N — name}, current task: {next ⬜ item}
✅ Last session: {1-line summary of what was completed}
⏭️ Next up: {1-line summary of what to do this session}
🚧 Blockers: {list any from last session, or "none"}
🧠 Active rules: phase-by-phase only, mock TTSProvider in tests, log every TTS step
```

5. Wait for the user to confirm or redirect before starting work.

End the current NovelTTS work session.

1. Review what was done this session (recent file edits, completed tasks, new decisions).
2. Ask the user to confirm:
   - **Completed**: bullet list of what shipped this session
   - **Next**: bullet list of what to pick up next session
   - **Decisions Made**: any architectural / scope choices that should outlive this session
   - **Blockers**: open questions, missing credentials, external dependencies
3. Prepend a new entry to `docs/SESSION_LOG.md` using this exact format (most recent on top):

```
## Session YYYY-MM-DD — {short title}
### Completed
- ...

### Next
- ...

### Decisions Made
- ...

### Blockers
- ... (or "none")
```

4. If any phase task in `docs/DEV_PLAN.md` was completed, mark it ✅. If a new task is now in progress, mark it 🔄.
5. If architecture changed (new provider, new service, new env var), update `docs/CODEBASE.md`.
6. Confirm to the user what was logged.

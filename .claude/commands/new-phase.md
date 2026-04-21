Transition to a new phase in `docs/DEV_PLAN.md`.

New phase number: $ARGUMENTS

1. Open `docs/DEV_PLAN.md`. Confirm the **previous** phase has all its tasks marked ✅. If any are still ⬜ or 🔄, refuse and list what remains.
2. Mark the previous phase header with a ✅ done timestamp.
3. Mark the new phase header with 🔄 in progress and today's date.
4. Update `docs/CODEBASE.md` if the new phase introduces:
   - A new directory in the repo layout
   - A new provider implementation
   - A new env var
   - A new worker process
   - A new API endpoint group
5. Append a `Decisions Made` line to today's `docs/SESSION_LOG.md` entry (or create today's entry) noting the phase transition.
6. Print the first ⬜ task of the new phase as the suggested next step.

If `$ARGUMENTS` is empty, list the current phase status and ask the user which phase to transition into.

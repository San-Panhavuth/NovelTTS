Dispatch the `code-reviewer` sub-agent on the current uncommitted diff.

Use the Agent tool with `subagent_type: code-reviewer`. Tell it to:
- Run `git diff HEAD` for uncommitted changes (or `git diff $ARGUMENTS` if a ref was provided)
- Apply the NovelTTS-specific checklist from `.claude/agents/code-reviewer.md`
- Report findings grouped as 🚫 Blocker / ⚠️ Warning / 💡 Suggestion / ✅ Looks good

Show the review verbatim to the user. Do not auto-fix issues — let the user decide which to address.

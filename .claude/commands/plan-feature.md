Dispatch the `planner` sub-agent to plan a NovelTTS feature.

Feature description: $ARGUMENTS

Use the Agent tool with `subagent_type: planner`. Pass the feature description above plus a reminder to:
- Validate the feature belongs to the current phase in `docs/DEV_PLAN.md`
- Write the plan to `plans/{YYYYMMDD}-{slug}.md`
- Return the plan path + a 3-bullet summary

Do NOT start implementing after the plan is returned. Show the plan summary to the user and wait for approval.

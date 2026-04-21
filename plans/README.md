# Plans

Implementation plans written by the `planner` sub-agent.

## Naming
`YYYYMMDD-{kebab-feature-slug}.md` — e.g. `20260421-epub-upload-pipeline.md`

## Plan template
Each plan file should contain:

```
# Plan: {feature name}

## Why
{1-paragraph motivation tied to PRD or DEV_PLAN}

## Phase + Step
Phase X, step Y of docs/DEV_PLAN.md

## Files Touched
- path/to/file.ts (NEW | MODIFY) — what changes

## Tasks
1. ...

## Risks
- ...

## Done When
- bullet list of acceptance criteria
```

## Lifecycle
- Created by `/plan-feature <description>` → `planner` agent
- Reviewed by user before implementation begins
- Marked complete (filename prefix `DONE-`) once shipped, kept for history
- Plans for skipped or abandoned features get prefix `ABANDONED-`

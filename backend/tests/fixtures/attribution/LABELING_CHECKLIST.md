# Attribution Labeling Checklist

Use this checklist while creating the 5 chapter fixtures required by Phase 2.

## Target coverage

- 2 cultivation chapters
- 2 romance chapters
- 1 action chapter

## Per-chapter checklist

- Confirm chapter text is English-translated source text (no editor notes or credits).
- Keep one fixture file per chapter with one JSON array of cases.
- Use stable case IDs with chapter prefix (example: `cultivation-title-chapter-003`).
- Prefer exporting from DB first, then manually cleaning fixture labels.
- Ensure each expected segment text is an exact excerpt from case text.
- Ensure each expected segment type is one of: `narration`, `dialogue`, `thought`.
- Set character name only when reasonably certain; otherwise set `null`.
- Keep apostrophes and quote style exactly as source text.
- Avoid over-splitting very short fragments unless they are semantically distinct.

## Consistency rules

- Quoted spoken lines are `dialogue`.
- Inner monologue quoted with single quotes is usually `thought`.
- Speaker tags such as `she said` are `narration` unless clearly internal thought.
- If uncertain between narration and thought, mark as narration and note for review.

## Quality pass before benchmark

- Re-read each case after labeling and verify segment order.
- Check for duplicate expected segments inside one case.
- Check that all expected texts can be found by simple string match.
- Run benchmark once and inspect strict accuracy result.

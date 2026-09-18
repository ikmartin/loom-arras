# Mode: draft

## Before you begin
- Write only under `$LOOM_RUN`. Never edit source. Never run
  paste it; the author decides, with an id from `loom id --next`.
- Read `ai/modes/blocks.md` once this session.

## Purpose
Write a complete node from a plan the author supplies. The plan states the
intended statement, its role, and a proof plan with the estimates,
computations, case division, and conclusion. You complete the local
argument. You do not change the plan's strategy; where the plan is wrong,
say so in the notes and stop at that step with `\incomplete`.

## Input
- The plan: `plan-ID.md` in the run, or the author's message; if absent,
  ask for it and stop.
- `loom new TAXON "Title" --print` for the skeleton in the quilt's
  environment names, or the id of a skeleton file the author created.
- `loom source DEP --closure --run $LOOM_RUN` for each intended dependency, so the
  statements you rely on are in front of you.

## Procedure
Write the statement first and check it against the plan. Then the proof:
cite each fact used by `\ref{ID}` and list all dependencies in `\uses`;
mark every step you could not complete with `\incomplete{...}`. Then
`loom compile --draft draft-ID.tex --run $LOOM_RUN` compiles it against
the quilt's preamble; fix compile errors; record the result.

## Output
1. `draft-ID.tex`: one complete node obeying the source contract
   (`% !LOOM author:` and `created:` lines; one environment with the title
   and `\label{ID}` if an id was given; adjacent proof; `\uses`).
2. `draft-ID.notes.md`: [summary]; what the plan asked; what you did; what
   you could not do and why; every trial.
3. An entry in `thread.md`.

## Checklist
- [ ] The statement matches the plan.
- [ ] Every fact used is a `\ref` or `\uses` to an existing id or a
      digest node.
- [ ] Every incomplete step is marked `\incomplete`.
- [ ] The draft compiles.
- [ ] Nothing was written outside `$LOOM_RUN`.

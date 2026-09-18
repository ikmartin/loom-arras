# Mode: simplify

## Before you begin
- Write only under your run directory. Never edit source. Never run `loom accept`.
- The revised text is a diff the author applies; you apply nothing.
- Read `ai/modes/blocks.md` once this session.

## Purpose
Revise the text of one key to be simpler and shorter while preserving mathematical content exactly. Assume the mathematics is correct; do not perform in-depth verification (that is referee). Citation verification is required for any argument you replace with a citation. If an error surfaces incidentally, flag it in [summary] and as an objection, and leave that passage unsimplified rather than propagating it.

## Input
- `loom source KEY --closure --run RUN`.
- If `audit-KEY.notes.md` exists in this run, its [patch-list] is your starting list.
- Digest nodes for candidate citations (standing rule 5).

## Procedure
For each candidate change: classify it; for a new-citation, verify against a digest node or record it under [rejected]; for an unnecessary hypothesis, confirm no step in the closure consumes it; make the change in a copy of the node's text; check meaning. Then produce the diff and compile it with the change applied.

## Output
1. `simplify-KEY.notes.md`: [summary], [simplifications], [rejected], [revised], [meaning-drift-check].
2. `proposal-KEY.diff`: a unified diff against the node's file (path from `loom search KEY --json`); the result of `loom compile KEY --with proposal-KEY.diff --run RUN` and `loom compile` recorded under [revised].
3. One suggestion annotation per simplification, anchored to the old text.
4. An entry in `thread.md`.

## Checklist
- [ ] Every new-citation names a digest node id and is marked verified.
- [ ] Every removed hypothesis has an absence-of-use demonstration.
- [ ] The diff applies cleanly and the result compiles.
- [ ] [meaning-drift-check] covers every modified passage.
- [ ] Nothing was written outside your run directory.

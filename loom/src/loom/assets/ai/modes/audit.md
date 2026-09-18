# Mode: audit

## Before you begin
- Write only under your run directory. Never edit source. Never run `loom accept`.
- Findings are `loom comment ... --run RUN` calls, quote-anchored.
- Read `ai/modes/blocks.md` once this session.

## Purpose
A load-bearing audit of one key. Assume the mathematics is correct; do not hunt for errors (that is referee). Hunt for mismatch between what is stated and what is used. If an error surfaces incidentally, flag it in [summary] and as an objection, and continue the audit; do not switch into referee mode.

## Input
- `loom source KEY --closure --run RUN`.
- `loom deps KEY --closure --json` for the closure and edge kinds.
- `loom status --json` for the states of the closure.
- Digest nodes for cited results are in the closure when the citation resolved; otherwise standing rule 5.

## Procedure
Read the closure once completely. Then build the six ledgers in order. Search digests before declaring anything unlocated; search the web only if no digest exists and say so. For the uses-ledger, read each proof sentence by sentence and ask what fact it invokes; if the fact is not named by a `\ref`, `\uses`, or matched citation, it is a finding.

## Output
1. `audit-KEY.notes.md`: [summary], [hypothesis-ledger], [citation-ledger], [uses-ledger], [self-containedness], [sharpenings], [patch-list].
2. Annotations for every item of [uses-ledger], [self-containedness], and [patch-list] (kind suggestion; kind objection for an incidental error; kind question where you could not decide), each anchored to the sentence it concerns; the notes list their ids.
3. An entry in `thread.md`.

## On a re-check
For each of your earlier annotations: resolve it with the reason if it is met; otherwise reply saying what remains. If nothing remains, record `--kind ok`.

## Checklist (copy into the notes and tick)
- [ ] Every hypothesis has a verdict.
- [ ] Every citation names a digest node id or "unlocated".
- [ ] Every uses-ledger, self-containedness, and patch-list item is an annotation with its id in the notes.
- [ ] [summary] states what the author must decide.
- [ ] Nothing was written outside your run directory.

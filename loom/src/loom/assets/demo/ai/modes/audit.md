# Mode: audit

## Before you begin
- Write only under your session's directory. Never edit source. Never run `loom accept`.
- Findings are `loom annotate ... --session SESSION` calls, quote-anchored.
- Read `ai/rules.md` once this session.

## Purpose
A load-bearing audit of one key. Assume the mathematics is correct; do not hunt for errors (that is referee). Hunt for mismatch between what is stated and what is used. If an error surfaces incidentally, flag it in [summary] and as an objection, and continue the audit; do not switch into referee mode.

## Input
- `loom source KEY --closure --session SESSION`.
- `loom deps KEY --closure --json` for the closure and edge kinds.
- `loom status --json` for the states of the closure.
- Digest nodes for cited results are in the closure when the citation resolved; otherwise standing rule 5.

## Procedure
Read the closure once completely. Then build the six blocks in order, beginning with the three ledgers. Search digests before declaring anything unlocated; search the web only if no digest exists and say so. For the uses-ledger, read each proof sentence by sentence and ask what fact it invokes; if the fact is not named by a `\ref`, `\uses`, or matched citation, it is a finding.

## Output
1. `audit-KEY.notes.md`: [summary], [hypothesis-ledger], [citation-ledger], [uses-ledger], [self-containedness], [sharpenings], [patch-list].
2. Annotations for every item of [uses-ledger], [self-containedness], and [patch-list] (kind suggestion; kind objection for an incidental error; kind question where you could not decide), each anchored to the sentence it concerns; the notes list their ids.
3. A message in the chat (`loom session say`) saying what you did and what remains.

## On a re-check
Per `rules.md` rule 7: resolve what is met, edit what still stands, discard what you should not have raised. Record a clean re-read with `--kind note` (any unambiguous prefix will do, so `--kind conf` is enough).

## Checklist (copy into the notes and tick)
- [ ] Every hypothesis has a verdict.
- [ ] Every citation names a digest node id or "unlocated".
- [ ] Every uses-ledger, self-containedness, and patch-list item is an annotation with its id in the notes.
- [ ] [summary] states what the author must decide.
- [ ] Nothing was written outside your session's directory.

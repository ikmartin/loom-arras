# Mode: review

## Before you begin
- Write only under your run directory. Never edit source. Never run `loom accept`.
- Findings are `loom comment ... --session SESSION` calls, quote-anchored, every one carrying `--severity`.
- Read `ai/rules.md` once this session.

## Purpose
A referee aiming to improve the source rather than to reject it. Where `referee` hunts for a reason the result is wrong, review reads for everything that would make the paper better and grades each finding by how bad the fault is. The author reaches for this most.

## Input
As audit. You can run code: save every trial per standing rule 7.

## Procedure
Read the closure. Work through the source in order, and look for each of these in turn:

- **new citations**: an argument that a citation could replace. Verify the source. If you are citing from memory, say so in the finding and mark the citation ledger entry `memory-grade`; propose it with `--kind citation` so the author can accept or reject it.
- **bad citations**: a citation that is wrong, or that does not cover the use made of it.
- **unnecessary hypotheses**: a hypothesis no step consumes.
- **merge-or-delete**: redundant lemmas, duplicated arguments, scaffolding.
- **sharpenings**: a proof that gives more than the statement claims, or a hypothesis that weakens without touching the argument.
- **self-containedness**: a theorem, lemma or definition that does not parse standalone.
- **mathematical errors**: a false statement or an incorrect claim. Always say *why* it is false, and attempt a fix.
- **grammar and wording**: grammar, punctuation, awkward phrasing.
- **clarity**: unclear writing, with a suggested fix.

Errors and prose both go in [referee-review], which already groups by severity and carries a location, a fix and an annotation id per item.

## Output
1. `review-KEY.notes.md`: [summary], [referee-review], [citation-ledger], [self-containedness], [sharpenings], [simplifications].
2. An annotation per item, every one with `--severity`, and a `--payload` wherever you are proposing text. Ids listed in the notes.
3. `review-KEY.check.py` with its output, for every trial.
4. An entry in `thread.md`.

There is no compiled LaTeX or PDF pair. The annotations carry the findings and the viewer renders them in place; exporting an annotated document for a reader who cannot open the viewer is a separate feature, and not this mode's job.

## On a re-check
Per `rules.md` rule 7: resolve what is met, edit what still stands, discard what you should not have raised. The fresh report goes in a new numbered notes file, `review-KEY.2.notes.md`, so each pass stays readable as what you thought at the time.

## Checklist
- [ ] Every one of the nine kinds above was looked for.
- [ ] Every finding is anchored, graded, and its id is in the notes.
- [ ] Every citation proposed from memory says so.
- [ ] Nothing was written outside your run directory.

# Mode: referee

## Before you begin
- Write only under `$LOOM_RUN`. Never edit source. Never run `loom accept`.
- Findings are `loom comment ... --run $LOOM_RUN` calls, quote-anchored.
- Read `ai/modes/blocks.md` once this session.

## Purpose
A hostile review of one key. You are a referee at a top-tier journal
looking for any possible opportunity to reject. Find gaps, test the
equations, look for counterexamples, and render a verdict. Do not soften:
a wrong step is an objection even if it is fixable.

## Input
As audit. You can run code: save every trial per standing rule 7.

## Procedure
Read the bundle. Produce the six blocks in order. Every gap, error, or
unjustified step is an objection anchored to the exact sentence; every
improvement a suggestion; every doubt a question. If an earlier audit
notes file exists in this run, read it first and do not repeat its
findings.

## Output
1. `referee-KEY.notes.md`: [summary], [gaps-and-ambiguities],
   [worked-examples], [counterexample], [referee-review],
   [referee-revised], [decision].
2. Annotations for every item of [gaps-and-ambiguities] and
   [referee-review], ids listed in the notes.
3. `proposal-KEY.diff` when [referee-revised] is nonempty, and the result
   of `loom bundle KEY --with proposal-KEY.diff --run $LOOM_RUN` followed
   by `loom compile` on it.
4. `referee-KEY.check.py` with its output, for every trial.
5. An entry in `thread.md`.

## On a re-check
For each earlier annotation: resolve with the reason if met; reply if not.
Then a fresh [decision] in a new notes file `referee-KEY.2.notes.md`, and
`--kind ok` if nothing remains.

## Checklist
- [ ] At least two worked examples with exact outputs.
- [ ] Every objection is anchored and its id is in the notes.
- [ ] [decision] cites the blocks above.
- [ ] The diff, if any, compiles in a bundle.
- [ ] Nothing was written outside `$LOOM_RUN`.

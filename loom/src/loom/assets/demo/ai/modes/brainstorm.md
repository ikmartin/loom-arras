# Mode: brainstorm

## Before you begin
- Write only under your run directory. Never edit source. Never run `loom accept` or paste it; the author decides.
- Read `ai/rules.md` once this session.

## Purpose
Help the author explore a topic before anything is proved. Your job is to make the author's ideas precise and testable quickly, not to supply strategy: restate what they want as a candidate statement with explicit hypotheses before evaluating it; compute the small cases before opining; search the digests before claiming anything is new or known; record what was tried and why it failed. If you have an idea of your own, offer it in one sentence under [open-questions] and do not pursue it unless asked.

## Input
- `loom status --json`; `loom search TOPIC --json` for the ids involved.
- `loom source ID --closure --run RUN` for each definition or result the topic touches.
- The overviews of the relevant digests (`loom refs overview CITEKEY`, each written to be read whole); `loom search --kind digest`.
- If the author has an outline master, `loom source drafting/outline.tex --run RUN` prints the plan as it stands, flattened.

## Procedure
1. Ask what the author is after and restate it precisely. Stop until they confirm.
2. For each candidate: write it as `draft-cand-SLUG.tex`, a complete node in the quilt's conventions (taxon `conjecture` or `question`, `\incomplete{Not yet attempted.}` in place of a proof, `\ref`s to the definitions it uses, `% !LOOM tags:` as the author prefers).
3. Compute: small cases, examples, degenerate cases; save every trial per standing rule 7.
4. Search: what the digests give, contradict, or give under other hypotheses; cite digest node ids.
5. Record every approach abandoned during the conversation under [dead-ends] with its reason at the time it is abandoned, not at the end.

## Output
1. `brainstorm-SLUG.notes.md`: [summary], [candidates], [dead-ends], [known-results], [open-questions].
2. `draft-cand-*.tex` per candidate.
3. `brainstorm-SLUG.check.py` with outputs.
4. An entry in `thread.md` after each significant exchange. No annotations unless an existing key was found wanting (then as audit would record it).

## Checklist
- [ ] Every candidate is a draft file with explicit hypotheses.
- [ ] Every dead end has a reason.
- [ ] Every "known" or "new" claim cites a digest node or says "no digest; memory-grade".
- [ ] Nothing was written outside your run directory.

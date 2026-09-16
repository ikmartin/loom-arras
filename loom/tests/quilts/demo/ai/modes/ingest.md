# Mode: ingest

## Before you begin
- Write only under `$LOOM_RUN`. Never edit `refs/`; the author promotes.
- Read `ai/modes/blocks.md` once this session and the digest rules below.

## Purpose
Produce or complete a digest of a cited paper: its results as external
nodes in the quilt's format, so that citations become edges and the paper
need not be reread. Read the paper thoroughly once. Focus on verbal
intuition in the overview; be exact in the statements.

## Digest rules (from the digests chapter)
- File header: `% !LOOM digest: CITEKEY`, `% !LOOM source: IDENT`,
  `% !LOOM method: ingest`, `% !LOOM created: DATE`,
  `% !LOOM requires: pkg, pkg`.
- `\section*{Overview}` in your words; then the paper's sections as
  `\section{Title}\label{CITEKEY-sec-N}` in the paper's order.
- Every numbered result is an external node: the quilt's environment for
  its taxon; title `{\cite[LOCATOR]{CITEKEY}}` with the paper's own number
  and page; `\label{CITEKEY-abbrev-number}` (`thm`, `lem`, `prop`, `cor`,
  `def`, `rem`, `ex`, `constr`, `conj`); the full statement with every
  hypothesis (verbatim where you have the source, faithful where only the
  PDF); `\uses{...}` listing the results its proof invokes; no proof.
- One `\label{CITEKEY-setup}` node for standing assumptions, conventions,
  and notation stated outside numbered results.
- Macro-free LaTeX: expand the paper's macros. What cannot be expanded goes
  in `% !LOOM begin macros` ... `% !LOOM end macros` at the top.
- Every `\label` and `\eqref` inside the digest is prefixed `CITEKEY-`.

## Case A: no digest exists
Input: `refs/pdf/CITEKEY.pdf` (or its extracted text) or fetched source
under `refs/src/CITEKEY/`. Output: `ingest-CITEKEY.tex`, a complete digest
whose overview contains [overview], [proof-basics], [dependencies],
[reconstruction-plan] as prose and a [notation] table.

## Case B: an extracted digest exists
Input: `refs/CITEKEY.tex` with `method: extract`, and the paper. Output:
`proposal-CITEKEY.diff` filling the `-setup` node, the overview and
[notation], missing `\uses` (a proof invokes lemmas it never `\ref`s), and
locators the extractor left as `\incomplete`.

## Output (both cases)
1. The file above.
2. `ingest-CITEKEY.notes.md`: [summary]; what you could not determine;
   any result whose statement you could not read exactly.
3. An entry in `thread.md`. The author promotes (case A) or applies the
   diff (case B).

## Checklist
- [ ] Every numbered result of the paper is a node with a locator.
- [ ] Hypotheses are complete in every statement.
- [ ] No proofs copied.
- [ ] `requires:` lists every package the statements need.
- [ ] [notation] maps the paper's symbols to the quilt's.
- [ ] Nothing was written outside `$LOOM_RUN`.

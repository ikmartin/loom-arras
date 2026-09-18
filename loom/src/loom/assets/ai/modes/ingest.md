# Mode: ingest

## Before you begin
- Write only under your run directory. Never edit source. Never run `loom accept`. Never edit `digests/`; the author promotes.
- Read `ai/rules.md` once this session and the digest rules below.

## Purpose
Produce or complete a digest of a cited paper: its results as external nodes in the quilt's format, so that citations become edges and the paper need not be reread. Read the paper thoroughly once. Focus on verbal intuition in the overview; be exact in the statements.

## Digest rules (from the digests chapter)
- File header: `% !LOOM digest: CITEKEY`, `% !LOOM extracted-from: IDENT` (the artifact you read: `arXiv:0805.2065v2`, `doi:10.1090/...`, `work:<hash>` or `local:<file>`), `% !LOOM published-as: IDENT` when the work a reader would open differs from it, `% !LOOM method: ingest`, `% !LOOM created: DATE`, `% !LOOM requires: pkg, pkg`. They are two facts, not two spellings of one: the statements and their numbers come from what you parsed, and the bibliography cites what a reader opens. `source:` is the pre-0.5 spelling of `extracted-from:` and is read but never written.
- `\section*{Overview}` in your words; then the paper's sections as `\section{Title}\label{CITEKEY-sec-N}` in the paper's order.
- Every numbered result is an external node: the quilt's environment for its taxon; title `{\cite[LOCATOR]{CITEKEY}}` with the paper's own number and page; `\label{SLUG-abbrev-number}` (`thm`, `lem`, `prop`, `cor`, `def`, `rem`, `ex`, `constr`, `conj`); the full statement with every hypothesis (verbatim where you have the source, faithful where only the PDF); `\uses{...}` listing the results its proof invokes; no proof.
- One `\label{SLUG-setup}` node for standing assumptions, conventions, and notation stated outside numbered results.
- Macro-free LaTeX: expand the paper's macros. What cannot be expanded goes in `% !LOOM begin macros` ... `% !LOOM end macros` at the top.
- Every `\label` and `\eqref` inside the digest is prefixed with the citekey's slug (its letters and digits only) and a hyphen, `SLUG-`, the same prefix the ids carry.

## Case A: no digest exists
Input: the PDF or unpacked source of the work, which `loom refs path CITEKEY` locates. Output: `ingest-CITEKEY.tex`, a complete digest whose overview contains [overview], [proof-basics], [dependencies], [reconstruction-plan] as prose and a [notation] table.

## Case B: an extracted digest exists
Input: `digests/CITEKEY.tex` with `method: extract`, and the paper. Output: `proposal-CITEKEY.diff` filling the `-setup` node, the overview and [notation], missing `\uses` (a proof invokes lemmas it never `\ref`s), and locators the extractor left as `\incomplete`.

## Output (both cases)
1. The file above.
2. `ingest-CITEKEY.notes.md`: [summary]; what you could not determine; any result whose statement you could not read exactly.
3. An entry in `thread.md`. The author promotes (case A) or applies the diff (case B).

## Checklist
- [ ] Every numbered result of the paper is a node with a locator.
- [ ] Hypotheses are complete in every statement.
- [ ] No proofs copied.
- [ ] `requires:` lists every package the statements need.
- [ ] [notation] maps the paper's symbols to the quilt's.
- [ ] Nothing was written outside your run directory.

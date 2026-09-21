# Mode: ingest

## Before you begin
- Write only under your run directory. Never edit source. Never run `loom accept`. **Never write `digests/`.** A digest is produced by `loom digest extract`, not typed.
- Read `ai/rules.md` once this session and the digest rules below.

## Purpose
Check a mechanically extracted digest of a cited paper against the paper itself, and say exactly where the two differ. You are the verifier of loom's copy, not its author: a typed transcription is unfalsifiable, an extracted one can be diffed against its source, and the whole value of a digest is that a reader can trust it without opening the paper.

## What loom already did
`loom digest extract CITEKEY SRC --to ingest-CITEKEY.tex` produces the digest from the paper's LaTeX source: every numbered result as an external node, proofs dropped, labels prefixed with the citekey's slug, numbering taken from the compiled reference. `loom refs fetch CITEKEY` gets that source from arXiv when `[refs] fetch = true`, and `loom refs build` does the whole mechanical pass -- resolve, fetch, extract -- over every cited work at once. Extraction is mechanical and therefore wrong in predictable ways, which is what you are looking for.

## When there is no source
Some cited works exist only as a PDF — a thesis, a journal-only paper, most of the classical literature. There is nothing to extract, and a digest you typed would be exactly the unverifiable artefact this mode exists to avoid (DR-173). What you do instead is read and propose: `loom refs page CITEKEY N` for the text, then `loom refs propose` for each result, main results first (`--level 1`). A proposal is not typed in DR-173's sense: its `--source-text` is checked against the page before anything is stored, and its `--statement` — your rendering, in the paper's words only — waits in a file nothing inputs until the author compares the two and verifies it. You never write `digests/` yourself, and a proposal that passed the check is **waiting for the author**, not verified.

For a work with no source the checks below apply to what you propose, and the outputs are `ingest-CITEKEY.notes.md` and the `thread.md` entry; there is no extractor output to keep and no diff to write.

## What to check, in this order
1. **Completeness.** Every numbered result in the paper is a node, and nothing that is not a result became one. Name what is missing by the paper's own number.
2. **Hypotheses.** A statement is worthless with a hypothesis dropped. Read each against the paper and say which are incomplete — this is the failure that makes a digest dangerous rather than merely thin.
3. **Standing assumptions.** The `-setup` node holds what the paper assumes outside numbered results: conventions, notation, blanket hypotheses. The extractor fills it from a conventions or notation heading, or else gathers the sentences that state an assumption and says it did; check each for its scope, and name what it missed — assumptions stated in passing are the ones a reader loses.
4. **`\uses` edges.** A proof invokes lemmas it never `\ref`s. The extractor sees only what the source cites, so the dependency graph is systematically thin.
5. **Locators.** Every node's title carries the paper's own number and page. The extractor leaves what it could not resolve as `\incomplete`. A digest extracted from a preprint carries the preprint's numbers, pages and statements; when the bibliography cites the published version `loom lint` says so (`loom:unverified-locators`), and then every number is checked against the cited PDF with `loom refs page` — versions renumber, and they change statements.
6. **Macros.** What could not be expanded sits in `% !LOOM begin macros`. Check the statements still say what the paper says with those definitions.

## Output
1. `ingest-CITEKEY.tex` — the extractor's output, unedited, so the author can see what it produced.
2. `proposal-CITEKEY.diff` — a unified diff against it carrying every correction you found: the `-setup` node, missing hypotheses, missing `\uses`, resolved locators. **The diff is a proposal; nothing applies it but the author.**
3. `ingest-CITEKEY.notes.md`: `## [summary]`; one section per check above, each naming the paper's own numbers; what you could not determine and why.
4. A finding per defect that matters, with `loom comment <node-id> --kind objection --severity ... --session SESSION`, so the author's to-do list carries them. A digest node is the cited paper's text: a finding on one says the **copy** is wrong, never that the paper is.
5. An entry in `thread.md`.

## Checklist
- [ ] For a work with a source: `loom digest extract` was run and its output is in the run directory, unedited.
- [ ] Every numbered result of the paper is accounted for, present or named as missing.
- [ ] Every statement checked for dropped hypotheses, by the paper's own numbers.
- [ ] Standing assumptions found in the prose and proposed for the `-setup` node.
- [ ] `\uses` edges the source does not state are proposed.
- [ ] Every locator either resolved or named as unresolved.
- [ ] Nothing was written outside your run directory. In particular nothing was written to `digests/`.

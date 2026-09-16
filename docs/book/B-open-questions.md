# Appendix B. Open questions

Everything the design could not settle and implementation did not, collected from the chapters and specifications with the marker each carries there. Questions settled during implementation were removed from the chapters with a pointer to the decision record or the demonstration record that settled them; Appendix A holds the records. Regenerated at the end of the implementation run (2026-09-16).

## From 1. Design philosophy (`book/01-design-philosophy.md`)

- None at the level of principles. Every open question in later chapters is about how to satisfy these principles, not whether to.

## From 2. Objectives (`book/02-objectives.md`)

- Whether success criterion 10 (the external user) should gate a release or only inform one. **[assumed]** It gates the claim "MVP done", not the first tagged release.
- Whether the library quilt should be demonstrated in the MVP with more than one paper. **[assumed]** Two digests, one extracted and one ingested, suffice.

## From 3. Vocabulary (`book/03-vocabulary.md`)

- Whether "thread" is too close to its withdrawn meaning to keep in the interface. **[assumed]** Kept; it is the ordinary word for a discussion and arras is the only place it appears.

## From 4. The quilt (`book/04-the-quilt.md`)

- Whether `loom init` should ask for the prefix interactively or require `--prefix`. **[assumed]** Ask once when a terminal is attached and `--yes` is absent; take the default `q` otherwise, so that scripts and agents never block.
- Whether the user config should support a default editor for a future `loom open`. Not in the MVP.
- Whether the default `\newtheorem` block in the minimal master should match the author's own conventions (e.g. `math-thms.sty`). **[assumed]** The minimal master is for new quilts; `--from` keeps the author's.

## From 5. The source contract (`book/05-source-contract.md`)

- Whether `\pageref` should create an edge (it references a location, not a result). **[assumed]** Yes, because omitting it would leave a dangling `\pageref` undetected.
- Nested theorem-like environments: settled by DR-41; a statement inside a proof is a node with a `nested` proof-edge from the enclosing proof, and no diagnostic is reported.
- The exact set of environments treated as labelled regions in 5.8.1. **[deferred]** Start with the amsmath display environments plus `figure`, `table`, and `enumerate` items; extend from fixtures.
- Whether `\declaretheorem` with a `sibling=` or `numberwithin=` key needs anything from the scanner. **[assumed]** No; numbering comes from the `.aux`.
- Whether `import` should also insert `\label`s on `\paragraph` and `\subparagraph` units. **[assumed]** No; sections through subsubsections only, by default; `--all-levels` to include them.

## From 6. Bringing a paper in (`book/06-bringing-a-paper-in.md`)

- Whether `import` should also copy files reached only by `\includeonly` or `\includegraphics` with unusual extensions. **[assumed]** Reported, not copied.
- Whether `atomize --sections` should default on: settled at M4, off; one-file-per-statement is the common wish, and section files can be made later.
- Whether the identity test should also compare bookmarks/hyperref anchors: settled at M4, no; text and label numbers are compared.
- The two fixtures' arXiv versions: settled at M4, pinned in `tests/fixtures/VERSIONS` (0805.2065 v2, 1709.09864 v4).

## From 7. Review (`book/07-review.md`)

- Whether the ledger should record the arras or loom version: settled at M3, `schema` only.
- Whether `--kind ok` should be allowed with a message ("read carefully; fine"): settled at M3, yes; the kind is what matters.
- Whether a person's comment sessions should be one file per day or one per session started explicitly: settled at M3, per day.
- Whether acceptance should be refused when the master does not compile: settled at M3, refused with `--force` to override.
- How arras displays a key with both an acceptance and many detached annotations. **[deferred]** to the arras chapter's badge rules.

## From 8. Digests (`book/08-digests.md`)

- Whether a library quilt should be a flag in config or recognized by having no masters. **[deferred]**; both are trivial; decide when the first library exists.
- The abbreviation map for extracted ids: settled in 8.5.3 (fixed map, unknown display names use the lowercased environment name, no author override).
- Whether extraction should keep proofs in a third form for ingest: settled in 8.6 (ingest reads the fetched source under `refs/src/` or the PDF directly).
- How the overview should be seeded when a paper has no introduction: settled in 8.5.4 (an `\incomplete` marker under `\section*{Overview}`).
- Locator normalization for non-English abbreviations. **[deferred]**; results numbered by letters (`Theorem A`, `thm-A.20`) and Roman numerals already match through the lowercase normalisation of 8.7.1; the matcher is a table and the table grows.

## From 10. Arras (`book/10-arras.md`)

- Whether the graph should be drawn client-side for a five-thousand-node quilt or precomputed by the publisher. **[deferred]**; measure on the ACGS fixture; the manifest may gain optional layout hints later.

## From 11. The AI layer (`book/11-ai-layer.md`)

- The form of a permission file for Codex, which has none at project level today (M6). **[deferred]**
- Whether runs should be nested (a run about a run). **[assumed]** No.
- Whether the mode templates should be per-quilt (in `ai/modes/`) or per-user (in `~/.config/loom/modes/`) with quilt overrides. **[assumed]** Per-quilt in the MVP; a user-level default set is a later addition.

## From 12. CLI reference (`book/12-cli-reference.md`)

- A `loom open KEY` that launches the user's editor at the node's file and line. Not in the MVP; would need a user-config editor key.

## From Dialect: the semantic HTML of fragments (`specs/dialect.md`)

- Whether footnotes should be `span.footnote` inline or collected at the end. **[assumed]** Inline; the viewer decides placement.
- Whether to permit a `nav.toc` block in master fragments. **[assumed]** No; the viewer builds a table of contents from headings.

## From Manifest: `build/manifest.json` (`specs/manifest.md`)

- Whether diffs should be inlined in the manifest or referenced by path. **[assumed]** By path, under `build/diffs/`, to keep the manifest small.
- Whether `search` should carry a full-text index. **[assumed]** Title, aliases, tags, excerpt only; full text is a later addition.
- Size limits. **[deferred]**; measure on the ACGS fixture; fragments are lazy, the manifest is not.

## From Runner contract (deferred) (`specs/runner.md`)

- Whether the runner should receive the prompt as a file path rather than stdin, for tools that cannot read stdin. **[assumed]** Both: stdin, plus `LOOM_PROMPT_FILE`.
- Whether responses should be streamed into the run directory for long runs. **[deferred]**

## From Write API (deferred) (`specs/write-api.md`)

- Whether `accept` should be exposed at all in version 1, given that a mis-click is an acceptance row forever. **[assumed]** Exposed behind a confirmation in the viewer.
- CSRF and origin checks for a localhost API. **[deferred]**

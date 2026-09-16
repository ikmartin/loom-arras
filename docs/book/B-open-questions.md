# Appendix B. Open questions

Everything the design could not settle and implementation did not, collected from the chapters and specifications with the marker each carries there. Questions settled during implementation were removed from the chapters with a pointer to the decision record or the demonstration record that settled them; Appendix A holds the records. Regenerated at the end of the 0.3 execution (2026-09-16).

## From 1. Design philosophy (`book/01-design-philosophy.md`)

- None at the level of principles. Every open question in later chapters is about how to satisfy these principles, not whether to.

## From 2. Objectives (`book/02-objectives.md`)

- Whether success criterion 10 (the external user) should gate a release or only inform one. **[assumed]** It gates the claim "MVP done", not the first tagged release.
- Whether the library quilt should be demonstrated in the MVP with more than one paper. **[assumed]** Two digests, one extracted and one ingested, suffice.

## From 3. Vocabulary (`book/03-vocabulary.md`)

- Whether "thread" is too close to its withdrawn meaning to keep in the interface. **[assumed]** Kept; it is the ordinary word for a discussion and arras is the only place it appears.

## From 4. The quilt (`book/04-the-quilt.md`)

- Whether `loom init` should ask for the prefix interactively or require `--prefix`. **[assumed]** Ask once when a terminal is attached and `--yes` is absent; take the default `q` otherwise, so that scripts and agents never block.
- Whether `.loom/snapshots/` should be committed. **[decided]** Yes; they are part of the acceptance record.
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

## From 9. Build and interface (`book/09-build-and-interface.md`)

Settled by implementation: the `data-src` encoding (character offsets, `FILE:START:END`, specs/dialect.md §1 and 9.3); PDF figures (converted to SVG at build, 9.4.1); the port (fixed default 8791, `--port` to change, fail if busy, 9.8); whether `loom build` compiles when no `.aux` exists (it never compiles; the panel says "not yet compiled", 9.6); the bundle id-beside-number mechanism (the `% id:` comment before each environment, 9.7).

## From 10. Arras (`book/10-arras.md`)

Settled by implementation: the route scheme (pretty paths under a server with the SPA fallback; `file://` unsupported, DR-57 and DR-78); the dark theme (yes, `src/lib/theme.css` follows `prefers-color-scheme` with a `data-theme` override, sitegen's tokens carried over); the "what you need to read first" list (yes, the node page's "Read first" line from the manifest's closure, 10.2.1).

- Whether the graph should be drawn client-side for a five-thousand-node quilt or precomputed by the publisher. **[deferred]**; measure on the ACGS fixture; the manifest may gain optional layout hints later.

## From 11. The AI layer (`book/11-ai-layer.md`)

Settled by implementation: the formats and locations of skill and command stubs (DR-71, 11.12); whether `loom ai start` refuses a command not on the path (yes, naming the command, the run having been created, 11.4); the form of the permission settings for Claude Code (DR-71, 11.8); whether `thread.md` has a required structure (no; `##` headings become dated messages and the rest is free, 11.4).

- The form of a permission file for Codex, which has none at project level today (M6). **[deferred]**
- Whether runs should be nested (a run about a run). **[assumed]** No.
- Whether the mode templates should be per-quilt (in `ai/modes/`) or per-user (in `~/.config/loom/modes/`) with quilt overrides. **[assumed]** Per-quilt in the MVP; a user-level default set is a later addition.

## From 12. CLI reference (`book/12-cli-reference.md`)

- `loom check` compiles bundles with `--bundles stale` by default, `all` or `none` on request. **[decided]** (settled at M2; a failed bundle is reported as `loom:bundle-failed`, M7).
- `loom search` accepts `--kind node|digest|master|thread`. **[decided]** (settled at M1).
- A `loom open KEY` that launches the user's editor at the node's file and line. Not in the MVP; would need a user-config editor key.

## From 13. The plan (`book/13-plan.md`)

- Whether M4 should precede M3, since importing the real paper early would surface scanner problems sooner. **[decided]** M3 first, as assumed; M1's scanner was additionally exercised on all three real papers through `loom lint` before M2 began, which is where the scanner problems surfaced (`docs/demonstrations/M1.md`, DR-40 to DR-53).
- Whether the ACGS stress test should gate M4 or only inform it. **[decided]** It gated M4, with `test_paper_acgs_import_with_documented_edits` carrying the hand-edit list; the list is empty (`docs/demonstrations/M4.md`).
- Whether to publish pre-1.0 releases to PyPI at all or install from git until M7. **[decided]** Install from git: the external user's install path is `pipx install git+https://github.com/ikmartin/loom` or a clone with `uv sync`, both exercised by the fresh-clone test at M7 (`docs/demonstrations/M7.md`), and no alpha was published because publishing is the author's step (`docs/demonstrations/M2.md`, `loom/docs/RELEASE.md`).

## From 14. Tests (`book/14-tests.md`)

- Whether the paper tier should run in a private CI with the sources stored as secrets. **[decided]** No; local only: `unit.yml` deselects `paper` and `network`, and the paper tier ran with `LOOM_PAPER_FIXTURES` on the implementing machine (`docs/demonstrations/M4.md`).
- Whether Playwright should also run against a live `loom serve` rather than the vendored fixture. **[decided]** Not as a test. `test_serve_static_routes` serves the vendored bundle without a browser, and criterion 8 of M7 visited every page kind of the served relloc quilt in a headless browser by hand (`docs/demonstrations/M7.md`); arras reaches loom as the vendored bundle, not through the pip package.

## From 15. Arras layout and visual design (`book/15-arras-layout.md`)

- The serif stack. **[decided]**, DR-90: the site generator's own stack.
- Whether the read view's right rail should push the text column or overlay it when comments appear. **[decided]** Push: the rail is a column of the shell's grid, so the text never moves under the cursor while reading.
- Whether shell B's breadcrumb should be the document picker on node pages too. **[decided]** No: the breadcrumb names the current document and the picker lives in the rail, in every view.
- Dark-mode values. **[decided]**, DR-90: derived from the light set in one file.
- Whether the graph inspector and the node page's right rail should be the same component. **[decided]** They share `RailList` and nothing else. The two hold different things — one a selection, the other a node's whole context — and a component that served both would be a switch with two branches.

## From 16. Editor clients (`book/16-editor-clients.md`)

- Whether the server should offer rename, which would have to rewrite every `\ref` and every ledger row and is therefore a loom command with an editor trigger rather than an LSP rename. **[deferred]**
- Whether an Emacs client is worth writing, given that `eglot` needs only the server and a root function. **[deferred]**
- Whether the code actions that write should become one `loom.run` command the clients share, rather than each client building the same argument vectors. **[assumed]** They should; the server already returns the vector, and only the confirmation differs.

## From `specs/dialect.md`

- Whether footnotes should be `span.footnote` inline or collected at the end. **[assumed]** Inline; the viewer decides placement.
- Whether `data-src` should include the master path for expanded inclusions in master fragments. **[decided]** Yes, `data-file` on `div.included` plus each element's own `data-src`.
- Whether to permit a `nav.toc` block in master fragments. **[assumed]** No; the viewer builds a table of contents from headings.

## From `specs/fixture.md`

- Timestamps are fixed by `LOOM_FIXED_TIME` during generation. **[decided]** (settled at M2).
- The fixture includes `talk.tex` in beamer. **[decided]** (settled at M2; the talk declares `proposition` because beamer predefines `lemma`, DR-58).

## From `specs/manifest.md`

- Whether diffs should be inlined in the manifest or referenced by path. **[assumed]** By path, under `build/diffs/`, to keep the manifest small.
- Whether `search` should carry a full-text index. **[assumed]** Title, aliases, tags, excerpt only; full text is a later addition.
- Size limits. **[deferred]**; measure on the ACGS fixture; fragments are lazy, the manifest is not.

## From `specs/runner.md`

- Whether the runner should receive the prompt as a file path rather than stdin, for tools that cannot read stdin. **[assumed]** Both: stdin, plus `LOOM_PROMPT_FILE`.
- Whether responses should be streamed into the run directory for long runs. **[deferred]**

## From `specs/write-api.md`

- Whether `accept` should be exposed at all in version 1, given that a mis-click is an acceptance row forever. **[assumed]** Exposed behind a confirmation in the viewer.
- CSRF and origin checks for a localhost API. **[deferred]**

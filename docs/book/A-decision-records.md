# Appendix A. Decision records

## Format

**[decided]** One record per decision, appended to this file, never edited afterwards (a reversal is a new record citing the old one). Fields: number, date, title, the principle(s) concerned, the decision in one or two sentences, the reason in one or two sentences, what it replaced if anything, and status (`active`, `superseded by N`). Records from the design conversations are dated by the day the conversation settled them; implementation-time records will be dated by merge.

## Records

DR-1 · 2026-09-15 · Adopt the block-based workflow of arXiv 2609.05669 §1.2 · P1, P5 · Decompose a paper into atomic units with tracked dependencies and review status, under a master recording order. · The source paper reports a threefold acceleration from exactly this. · active

DR-2 · 2026-09-15 · Source is LaTeX; no outer markup · P1 · Nodes are ordinary LaTeX; forester, Markdown, MyST, org, and Typst are rejected as source languages. · Mathematicians know LaTeX; the submitted `.tex` must be the written `.tex`; models are fluent in LaTeX. · active

DR-3 · 2026-09-15 · Forester as source considered and set aside · P1 · Forester's structure (addresses, transclusion, scoped macro modules) is better for a corpus; the per-paper tool is built first, in LaTeX. · No forester-to-LaTeX export exists; opam-only install; the corpus is deferred. · active

DR-4 · 2026-09-15 · The graph is defined by labels and environments, never by paths · P5 · One-file-per-node and regions-in-files are one specification. · Removes the need for a file format and lets the Stacks-style author keep one file. · active

DR-5 · 2026-09-15 · Transclusion is `\input`; no `\transclude` macro · P4 · The master compiles with plain `pdflatex`. · LaTeX already has transclusion. · superseded in part by DR-27 (`\nest` added for level shifting)

DR-6 · 2026-09-15 · Ids are `<prefix>-<local>`, prefix chosen by the author, sequential base-36 · P1 · Replaces random tags. · Forester and the Stacks project set the convention; the author chooses the prefix scheme. · active

DR-7 · 2026-09-15 · The ledger records acceptances only · P2, P3 · Reviews are files; states are computed; agents never write the ledger. · Prevents pollution by garbage runs; keeps decisions human. · active

DR-8 · 2026-09-15 · "Reviewed" is not a state · P3 · Reviews appear as facts and counts. · The word did two jobs and failed at both. · active

DR-9 · 2026-09-15 · Snapshots stored with acceptance rows · P2 · Content-addressed text of accepted keys and closures. · A stale acceptance must be explainable with a diff without git. · active

DR-10 · 2026-09-15 · One write path for annotations: `loom comment` · P4 · Agents and humans both use it; record files are never hand-written. · Loom owns the format end to end and computes anchors. · active

DR-11 · 2026-09-15 · Text-quote selectors relative to a region · P5 · Not file and line. · Anchors survive atomize, inline, and edits elsewhere. · active

DR-12 · 2026-09-15 · Runs are directories per chat thread, mode-free · P2 · Modes are applied inside runs; no run lifecycle. · A chat may cover several modes; restricting runs to one mode was prohibitive. · active

DR-13 · 2026-09-15 · Loom contains no model client; local models only · P8, P9 · Runner is an external local command; deferred. · No credentials, no hosted APIs. · active

DR-14 · 2026-09-15 · Digests in LaTeX as external nodes · P1, P4 · Replaces `map.toml` and `map.md`. · Reuses scanner, viewer, bundles; `\cite[postnote]` becomes an edge with no new syntax. · active

DR-15 · 2026-09-15 · Digest statements verbatim by default, macro-free or scoped · P1 · Expansion where mechanical, macro block otherwise; proofs never copied; sharing subject to licenses. · Verbatim is mathematically safer; paraphrase was solving licensing and notation, which are handled otherwise. · active

DR-16 · 2026-09-15 · `\uses` adopted from leanblueprint · P4 · No-op macro recording dependencies the text does not name; lint reconciles with `\ref`. · Some dependencies are only in prose; digests need internal trees. · active

DR-17 · 2026-09-15 · `\incomplete` rather than `\block` · P1 · Beamer defines `block`. · A talk in `drafts/` is a plausible master. · active

DR-18 · 2026-09-15 · Arras is a static Svelte bundle reading a build directory; loom is Python · P11 · No code shared; no server in the viewer; the write API is loom's. · Enforces separation by language and by artefact. · active

DR-19 · 2026-09-15 · Watching, not notification · P11 · Arras's only trigger is the manifest changing. · The viewer must not learn event kinds. · active

DR-20 · 2026-09-15 · Sections are nodes; nodes include nodes · P5 · Sectioning units are nodes; `sections/` is dropped; inclusion trees per master; own-text ownership. · Unifies masters, spines, sections; matches forester's model; the master view becomes "render expanded". · active

DR-21 · 2026-09-15 · Loom never modifies an author file · P7 · Destinations required; patches printed; `loom delete` refuses. · In-place rewriting destroys work. · active

DR-22 · 2026-09-15 · Directives use the `% !TEX` magic-comment family: `% !LOOM key: value` · P10 · Declarations only; never change output; regions as `begin`/`end`. · Established TeX convention; editors recognise it; `% !TEX program` and `root` honoured. · active

DR-23 · 2026-09-15 · Masters live in the masters directory; compile from the root · P12 · Every file with `\documentclass` there is a master; `config.toml` names the directory and the default. · Multiple masters without clutter; Overleaf-compatible. · active

DR-24 · 2026-09-15 · No loose-files directory · P5 · Loose is computed; `% !LOOM ignore` for archived drafts. · Naming the directory revealed it was a property. · active

DR-25 · 2026-09-15 · "id" for identity, "tag" for theme · vocabulary · Replaces "tag" as identifier. · Matches forester and sitegen; supports the zettelkasten use. · active

DR-26 · 2026-09-15 · Digest ids are `<citekey>-<paper's label>` · P1 · Distinct shape from author ids. · Cleanly separates provenance of nodes. · active

DR-27 · 2026-09-15 · `\nest{file}` for level shifting; no config flag · P4, P10 · Per inclusion site; `\input` or `\nest` as written. · A comment cannot change the PDF; a config default had nothing to decide. · active

DR-28 · 2026-09-16 · `loom.sty` vendored; `\usepackage{loom}` per master · P12 · Replaces preamble blocks. · Three macros in every master's preamble was duplication. · active

DR-29 · 2026-09-16 · Author name in user config, not quilt config · P2 · `~/.config/loom/config.toml`; fallback to git; refusal with instructions. · A committed config would attribute one person's acceptances to another. · active

DR-30 · 2026-09-16 · Diagnostics: reserved codes in the interface, publisher codes namespaced · P11 · Arras renders unknown codes generically. · Arras must not know what a proof is. · active

DR-31 · 2026-09-16 · Names: distribution `loomtex`, command `loom`, viewer `arras` · naming · `loom` on PyPI is abandoned; PEP 541 request in parallel. · active

DR-32 · 2026-09-16 · Licenses: GPL-3.0-or-later (loom), AGPL-3.0-or-later (arras), MIT (`loom.sty`, demo) · policy · Copyleft prevents proprietary appropriation without forbidding use; the package travels with papers. · active

DR-33 · 2026-09-16 · Command vocabulary consolidated · P4 · `deps`/`unravel` for the graph; `ai init|orient|start|discard|promote`; `digest extract|fetch|import`; `id` replaces `tag`; `delete` refuses. · Six graph commands were one question. · active

DR-34 · 2026-09-16 · Workspace repository tracks docs and specs; tool repositories separate; fixtures uncommitted · P11 · `loom-arras/` is a git repository ignoring `loom/`, `arras/`, `tests/fixtures/`. · The book and the interface need history; arXiv sources must not be redistributed. · active

DR-35 · 2026-09-16 · Overleaf compatibility is a contract · P12 · Portability rules; manual test per release; CI proxy. · The quilt is an ordinary LaTeX project. · active

DR-36 · 2026-09-16 · Vendor wrappers are generated pointer-only stubs · P4, 11.10 · Skill stubs and slash commands may be generated per mode but contain no mode content; the layer works with every stub deleted; `upgrade` never overwrites an edited mode file. · Two copies of a procedure drift; Codex has no stub mechanism. · active

DR-37 · 2026-09-16 · `bundle --with` and `bundle --draft` · P7, 11.5 · A bundle may be built with a proposed diff or a substitute file in place of a key's text, or for a not-yet-promoted node file, without touching the quilt. · Simplify, referee, and draft outputs must be compilable before a person promotes or applies them; otherwise verification happens after the only cheap moment for it. · active

DR-38 · 2026-09-16 · Mode files derived from the chat rules by an explicit mapping · 11.5 · `docs/source/global-rules.md` holds the chat rules verbatim and `global-rules-mapping.md` maps each part to its loom destination; the four environmental differences (inputs by command, outputs as files, findings as annotations, code and compilation available) drive every adaptation. · Provenance: an edit to a mode can be traced to the rule it came from. · active


DR-39 · 2026-09-15 · The 10.8 forbidden-word list exempts "digest" and "proof" · P11, 10.8 · Arras's source may use the manifest's own field names (`proofs`, `digest`, `kind: proof`) and the spec's route `/digest/`; the guard test forbids "quilt", "atomize", "unravel", and every "loom <command>" phrase, and generic rendering of unknown labels, codes, and taxa stays enforced by tests. · The manifest specification and the route list name those words, and the Web Crypto API has `digest()`, so the rule as written could not be satisfied. · active

DR-40 · 2026-09-15 · The scanner reads by character offset; line anchoring is enforced only where regions are moved · P1, 5.1.4, 5.2.3, 6.2 · Environments whose `\begin` or `\end` shares a line with body text are read correctly; `atomize` still refuses them and `import` gains `--fix-anchoring` to rewrite the copy it makes. · 43 % of the nodes in one fixture paper violate anchoring; refusing to read them would make lint useless on real papers (user decision). · active

DR-41 · 2026-09-15 · Proofs attach by enclosure; statements nested in proofs are nodes · 5.6.1, 5.7.1 · A proof directly inside a theorem-like node with no statement before it attaches to that node; a theorem-like environment inside a proof is a node in its own right, and the enclosing proof gets an implicit proof-edge to it (`via: nested`). · Five proofs inside `example` environments in Manolache and four lemma-plus-proof pairs inside one proof in ACGS. · active

DR-42 · 2026-09-15 · A `\cite` as the first token of the body marks an external node · 5.5.2 · External node = plain style, no proof, and a citation in the title or as the first body token. · Every real instance in the fixtures writes `\begin{definition}\cite[...]{...}` with no brackets. · active

DR-43 · 2026-09-15 · A heading's label is never taken from a line that opens an environment or another heading · 5.4.2 · The "same line or next non-blank line" rule stops at such a line. · Three label-theft cases in the fixtures. · active

DR-44 · 2026-09-15 · Inclusions resolve as TeX does · 5.9.1 · The path as written first, then with `.tex`; the braceless `\input name` form is accepted; a name kpsewhich finds is a system file and ignored; a non-.tex file is an opaque inclusion never scanned for nodes. · `\input{fig.pspdftex}` eleven times and `\input xy` in the fixtures. · active

DR-45 · 2026-09-15 · Digest id prefixes are citekey slugs; labels are whitespace-normalised · 5.3.1, 5.4 · The prefix is the citekey with everything but letters and digits removed; two citekeys with one slug are `loom:citekey-slug-collision`; the `digest:` directive keeps the verbatim key; runs of whitespace in any label collapse to one space. · Real citekeys contain hyphens, colons, and spaces, and real labels wrap across lines. · active

DR-46 · 2026-09-15 · The preamble closure is transitive through local style files; macro display names and unknown styles are resolved · 5.5.1, 5.5.3 · `\usepackage` lists, multi-line lists, and `\usepackage` inside a local `.sty` are followed; a display name that is a zero-argument macro is expanded, otherwise the environment name is capitalised with `loom:taxon-name-macro`; a `\theoremstyle` outside plain, definition, remark maps to plain with `loom:unknown-theoremstyle` unless `\newtheoremstyle` declared it. · All 26 declarations of the acceptance paper are two hops away in a local `.sty`. · active

DR-47 · 2026-09-15 · Non-UTF-8 sources are decoded with a warning · 5.1 · UTF-8 first, then Mac Roman, then Latin-1, with `loom:non-utf8-source`. · A 2011 arXiv source carries Mac Roman en dashes. · active

DR-48 · 2026-09-15 · Comments are blanked before every stage, not only before hashing · 5.13 · Comments are replaced by spaces of equal length so offsets are stable and no stage reads them; directives are parsed from the raw text. · A commented-out environment duplicated a live label. · active

DR-49 · 2026-09-15 · Ownership is per file; hierarchy is per master · 5.9.2, 5.9.3 · A section's own text runs from its heading to the next heading of equal or higher level in the same file (or the file's end), minus nested claimants; its parent and children come from the expanded master. Every character of a file belongs to exactly one claimant, the file (or master, which owns the preamble) being the outermost. · Hashes must not depend on which master reached a file. · active

DR-50 · 2026-09-15 · A master's preamble yields no edges or regions; a node never has an edge to itself; single-label reference commands are not split on commas · 5.7.1, 5.8 · Edges and region labels are read from `\begin{document}` on; `\ref` and `\eqref` take one label, `\cref`, `\Cref`, and `\uses` take lists. · Macro bodies in a preamble contain `\ref{#1;#2}`; labels contain commas. · active

DR-51 · 2026-09-15 · `unreachable` is emitted once per loose file and never for digest files · specs/diagnostics.md, 8.1.2 · One diagnostic per file no master reaches, listing its node keys; digests are loose by construction and are not reported. · Per-node reports would drown the problems page. · active

DR-52 · 2026-09-15 · Five diagnostic codes added · specs/diagnostics.md · `loom:non-utf8-source` (warning), `loom:unknown-theoremstyle` (warning), `loom:taxon-name-macro` (info), `loom:citekey-slug-collision` (error), `loom:main-not-found` (warning), plus the reserved `loom:foreign-annotations` and `loom:agent-wrote-outside-run` the book names in prose. · Each names a condition the fixtures produce. · active

DR-53 · 2026-09-15 · Unknown theorem-like environments are detected by a list of common names · 5.5.1 · An undeclared environment is reported as `loom:unknown-environment` only when its name is one of the usual theorem-like names (theorem, lemma, prop, defn, and so on); any other undeclared environment is prose. · Without a declaration nothing else says an environment is theorem-like. · active

DR-54 · 2026-09-15 · The static deployment is a shell prerender · 10.1.1, 10.7 · `arras build --prerender` writes one `index.html` per route named by the manifest plus the build directory, so pretty URLs work on any static host; pages are the single-page shell and content loads in the browser from `build/manifest.json`. · Server-rendered content needs a second data path (filesystem loads at build time) that the MVP does not need; crawlable pages are deferred. · active

DR-55 · 2026-09-15 · MathJax 3 with SVG output · 9.4.3, 10.1 · The viewer bundles MathJax's `tex-svg` component; no font files are shipped and a deployed site works offline. · The CommonHTML output needs a font directory the bundle would have to carry and reference. · active

DR-56 · 2026-09-15 · Per-fragment macro sets are applied inside the fragment · 8.3.5, 10.1 · A fragment naming a macro set gets `\renewcommand` lines for that set prepended to its first math element before typesetting; the default set is global. · MathJax's macro table is global; isolating a set per fragment would need a second MathJax instance. Node pages show one node at a time, so the approximation is invisible in practice. · active

DR-57 · 2026-09-15 · `file://` is unsupported; `loom serve` provides the SPA fallback · 10.1.2 · Routing is path-based; `loom serve` answers any extensionless path with `index.html`; opening the bundle from `file://` is not supported in the MVP (any static server, such as `python -m http.server`, works). · SvelteKit's router type is a build-time choice, so it cannot switch to hash routing when a page is opened from a file. · active

DR-58 · 2026-09-15 · The synthetic quilt compiles: missing include inside `\iffalse`, beamer talk declares `proposition` · specs/fixture.md §1, 14.3 · The `missing-include` case sits inside `\iffalse … \fi`, which LaTeX skips and the scanner does not interpret; the beamer master declares `proposition` in definition style for the taxon conflict instead of redeclaring `lemma`, which beamer predefines. · Both masters must compile for numbering, and a master with a missing `\input` cannot. · active

DR-59 · 2026-09-15 · Nodes that owe no proof are proved when their statement is accepted · 7.6.3 · `proved` requires a fresh accepted statement and, only for plain-style non-external nodes, a fresh accepted proof; definition- and remark-style nodes are proved by acceptance alone, so they can be settled and so can what depends on them. · The book's rule made every definition unprovable, hence nothing settled. · active

DR-60 · 2026-09-15 · Annotation ids are unique across the quilt · 7.4.2 · `a-<date>-<nnnn>` counts over every review record in the quilt rather than per file. · The book asked for quilt-wide uniqueness while assuming a per-file counter, which collides. · active

DR-61 · 2026-09-15 · `lint` and `check` include record-derived diagnostics · 5.14, 7.9, 7.10 · Detached annotations, retired ledger keys, positional-key matches, and foreign annotation files are reported by `loom lint` and `loom check`, not only in the manifest. · The book lists these codes under lint; they need the records, which the scanner does not read. · active

DR-62 · 2026-09-15 · Files no master reaches are sectioned per file · 5.9.2.3, 8.3.1 · A `.tex` file that no master reaches and that is not itself a master is sectioned on its own, the file path standing in for the master, so its headings are section nodes; a digest's headings are therefore the `<citekey>-sec-<n>` nodes of 8.3.1 and `loom id` labels headings in loose files. · The book stated the rule but the first implementation computed sections only on master expansions, which left digests without section nodes and `loom id` unable to label a heading in a file no master included.

DR-63 · 2026-09-15 · A proof naming only unknown labels attaches by position · 5.6.1 · When every label in a proof's optional argument is unknown, the proof attaches as it would without the argument (adjacency, then enclosure) and the unknown label is reported as a dangling link; `loom:unattached-proof` is reserved for proofs no rule places. · A deferred proof whose `\ref` has a typo still sits beside a statement; refusing to attach it lost information the position carried, and the dangling link already names the mistake.

DR-64 · 2026-09-15 · A heading's id label goes directly after the heading's arguments · 6.2.4 · `loom id` and `loom import` insert `\label{<id>}` immediately after the closing brace of a sectioning command, ahead of any label the author already placed there, so the id is the first label under the same rule that governs environments. · Appending the id after an existing label made the author's label the first one and the heading keyless.

DR-65 · 2026-09-15 · Identity through the reaching master for non-master files · 6.3, 6.4, 6.6 · When `atomize` or `inline` rewrites a file that is not a master, the identity test compiles the first master reaching it twice: as it is, and in a scratch copy of the quilt where DEST's text stands at SRC's path. With no reaching master the test is reported skipped rather than passed. · A section file has no PDF of its own, and the book specified the test only for masters.

DR-66 · 2026-09-16 · A digest's own locator citations are not postnote edges · 8.7 · A `\cite[LOCATOR]{citekey}` inside a node of the digest of that same citekey (every digest node's title is one) creates no edge and no `loom:unmatched-postnote`. · Matching the digest's own titles made the setup node depend on its section and flagged every title whose locator named only itself.

DR-67 · 2026-09-16 · Unnumbered results get star ids · 8.5.3 · A result of a `\newtheorem*` environment is extracted with id `<slug>-<abbrev>-star-<n>` (`n` counting unnumbered results in document order) and the locator `<Name> (unnumbered)`. · The book's id grammar assumed every result has a number.

DR-68 · 2026-09-16 · The counter emulator always runs · 8.5.2 · Results are numbered by the amsthm emulation in document order; whenever the paper's `.aux` numbers a labelled result, that number replaces the emulated one and resynchronises the counters, so unlabelled results between labelled ones are numbered correctly. `numbering: emulated` is written only when no `.aux` was produced. · An `.aux` file names only labelled results, so the emulator is needed even when the paper compiles.

DR-69 · 2026-09-16 · Display names map to the numbered environment · 8.1.7 · When the quilt declares a display name twice (`thm` and `thm*` both display `Theorem`), the extractor and `digest import` choose the numbered one, then the one whose environment name is the lowercased display name, then the first declared. · relloc's `math-env.sty` declares starred twins for every taxon.

DR-70 · 2026-09-16 · Run directories and fetched sources are not scanned · 5.1, 8.9, 11.2 · File discovery skips `ai/`, `refs/src/`, `refs/pdf/`, and `.claude/` in addition to `build/`; a bundle or draft copied into a run is never a master or a duplicate id. · Runs hold complete documents (`bundle-*.tex`) and drafts carrying ids that exist in the quilt; scanning them produced duplicate-id errors and phantom masters.

DR-71 · 2026-09-16 · Skills carry the target; commands are wrappers · 11.12 · `loom ai init --skills` writes a skill stub per mode under `.claude/skills/loom-<mode>/SKILL.md` whose body names the mode file and, for target-taking modes, `$ARGUMENTS`; it also writes `.claude/commands/<mode>.md` for those modes as one-line wrappers, since Claude Code documents commands as a legacy form of skills. `.claude/settings.json` denies Edit and Write per protected directory and the author-only loom commands, because deny rules take precedence over allow rules and an allow-only whitelist cannot be expressed. · Verified against Claude Code's current documentation at implementation time, as 11.12 deferred.

DR-72 · 2026-09-16 · The agent launch passes a pointer, not the orientation · 11.4.1 · `loom ai start` runs `[ai] agent` in the quilt root with `LOOM_RUN` set and a one-sentence prompt naming `loom ai orient --run RUN` and the run directory; the agent then reads the orientation and the live state through that command. `--no-launch` creates the run without launching. A run's `run.toml` records the agent's name when one is configured. · The orientation is a long document and `loom ai orient` is what keeps it current; passing it as an argument would freeze it at launch time.

# Implementation plan (approved 2026-09-15)

Copied verbatim from the plan approved in the implementing session. The live status of each milestone is in `docs/demonstrations/README.md`; deviations from the book are in `docs/deviations.md`.


## Context

The workspace `~/dev/loom-arras` holds a complete pre-implementation design book (`docs/book/`, 14 chapters plus appendices A–F) and an interface specification (`docs/specs/`) for two tools: **loom**, a Python CLI that turns a LaTeX paper into a "quilt" (nodes with permanent ids, a dependency graph read from `\ref`/`\uses`/`\cite[postnote]`, a hash-based acceptance ledger, quote-anchored review records, digests of cited papers, and an optional AI layer), and **arras**, a static Svelte viewer that renders the build directory loom publishes and knows nothing about LaTeX or loom. No code exists. `loom/` is an empty clone of `github.com/ikmartin/loom`; `arras/` is a clone of `github.com/ikmartin/arras` holding only an MIT LICENSE. The MVP acceptance test is the user's relative localization paper, copied to `tests/fixtures/relloc/`; the two conversion fixtures (Manolache 0805.2065, ACGS 1709.09864) are extracted, compile cleanly in an isolated TeX environment, and sit beside it, all gitignored.

The task: implement both tools following the book's milestones M0–M7 (`docs/book/13-plan.md`), recording every discovery and deviation as work proceeds, and finish by revising the book so it describes what was actually built.

## Decisions already made by the user

- **License holder**: `ikmartin` in every LICENSE file. loom GPL-3.0-or-later, arras AGPL-3.0-or-later (replacing the MIT file GitHub generated), `loom.sty` and the demo quilt MIT, workspace GPL-3.0-or-later.
- **Never edit anything under `~/notes/`.** Work only from copies under `tests/fixtures/`. Every test compile runs with `env -i`, an empty HOME/TEXMFHOME/TEXMFLOCAL/TEXMFVAR/TEXMFCONFIG, PATH limited to TeX Live plus system binaries, cwd = quilt root, so nothing outside the fixture directory can be read.
- **Deviations**: when implementation contradicts a `[decided]` statement, write a decision record and a deviations-log entry with my resolution, proceed, and flag it in the milestone's demonstration for review.
- **Commits**: commit at logical checkpoints inside a milestone in each repo; push to GitHub when the milestone's demonstration passes. The workspace repo (docs, demonstrations, deviations, specs tools and fixture) is committed and pushed the same way.
- **Line anchoring**: the scanner reads non-anchored environments by character offset; `loom import --fix-anchoring` rewrites only the copy it makes; `atomize` still requires anchoring; the identity test still gates.
- **Sitegen code**: the website repo has no license file. Ported files (`tikz.py`, the MathJax macro output shape and config template, the watch/serve skeleton, the shim pattern) go in with a `NOTICE` in loom stating they derive from the author's own site generator, relicensed by the copyright holder under GPL-3.0-or-later.
- **Node**: upgraded to 26.8.2 via Homebrew. Done.
- **Install from a clone, no registries**: at the end, an arbitrary person must be able to clone `github.com/ikmartin/loom` and `github.com/ikmartin/arras` and get everything running from the READMEs. Publishing to PyPI and npm stays gated by the user, so nothing in the install path may depend on a published package. Consequences: loom's repo carries the **built arras bundle** under `src/loom/assets/arras/` (plus a `VERSION` file naming the arras commit and interface version), refreshed by `loom/scripts/vendor_arras.py` from a local arras build at every milestone that changes arras and at every release; `loom serve` looks for the bundle in this order: `LOOM_ARRAS_BUNDLE` env var, the `arras` pip package if installed, the vendored copy. Lockfiles (`uv.lock`, `package-lock.json`) are committed. `pipx install git+https://github.com/ikmartin/loom` and `git clone … && uv sync` both work without any registry, and `loom doctor` names every missing system dependency with a per-platform install hint (Homebrew, apt, TeX Live installer).
- **Where quilts live**: `loom-arras/demos/` holds every runnable example quilt. Two are small, invented, and committed: `demos/demo/`, exactly what `loom init --demo` writes in the release (one master, five nodes, one digest, two accepted keys, one stale, its AI layer initialised, one finished run), and `demos/synthetic/`, the proof-of-concept quilt that exercises every construct in `specs/fixture.md` §1 and generates the conformance fixture. Both are refreshed from loom by `demos/refresh.sh` (runs `loom init demos/demo --demo` and copies `loom/tests/quilts/synthetic`), so loom's shipped assets stay the source of truth and the copies never drift. The quilts built from real papers (`demos/relloc/`, `demos/man12/`, `demos/acgs/`, `demos/scratch-*/`) are gitignored by pattern because they contain the paper sources. The fixture quilts also remain in `loom/tests/quilts/` (`demo`, `synthetic`, `edge/*`) because loom's CI needs them.

## Working method and record keeping

- **`docs/demonstrations/README.md`**: a status table, one row per milestone: `pending | in progress | demonstrated | blocked (reason)`, plus the date. This is the file a `/loop` wake-up reads first to find the next incomplete milestone.
- **`docs/demonstrations/M0.md` … `M7.md`**: one file per milestone with fixed sections: *Book says* (the "Demonstrates:" line from 13.2), *Commands run*, *Output* (actual, trimmed), *Tests* (counts per tier, command used), *Deviations recorded* (DR numbers), *Blocked on the user* (if any), *Status*.
- **`docs/deviations.md`**: running table: date · book section · what the book says · what was implemented · why · DR number · book updated (y/n). Every entry also becomes a decision record appended to `docs/book/A-decision-records.md` starting at DR-39, in the book's one-line format, never edited afterwards.
- **`docs/book/B-open-questions.md`** is not edited until the final book revision; closed questions are tracked via DRs.
- Prose in every file under `docs/` follows the repo CLAUDE.md: never hard-wrapped.
- Work order: M0 → M1 → M2 → M3, then M4 and M5 (M4 first, M5 second, sequentially since one agent), then M6, then M7, then the book revision. M1's scanner is additionally exercised on all three real papers via `loom lint` before M2 begins.
- **Monitoring from the phone**: the user runs `/remote-control` in this VS Code session (or starts a terminal session with `claude --remote-control` from the workspace directory); the session then appears under Code in the Claude mobile app, where progress is visible and messages and permission prompts can be answered. Each milestone's status line in `docs/demonstrations/README.md` is the one-glance summary.

## Technology choices

**loom** (`loomtex` on PyPI, command `loom`): Python ≥ 3.11 (tomllib), managed with `uv` (`uv init --lib`, hatchling backend), `src/loom/` layout, `click` for the CLI (nested groups `loom ai …`/`loom digest …`; `--help` and the generated CLI reference come from the same `click` command tree via `Context.to_info_dict()`), `markdown-it-py` for annotation bodies, everything else stdlib (`tomllib`, `json`, `hashlib`, `difflib`, `http.server`, `subprocess`, `importlib.resources`). Dev: `pytest`, `ruff`, `mypy`. No runtime dependency on the `arras` pip package: the built bundle is vendored in loom's repo (see the install-from-a-clone decision), so `pipx install git+…/loom` or `uv sync` gives a working `loom serve` with nothing from PyPI or npm; the `arras` pip package remains an optional override for the day the user publishes it. `loom serve` exits 2 only if no bundle can be found at all (12.5).

**arras**: SvelteKit 2 + Svelte 5 + TypeScript + Vite, `@sveltejs/adapter-static`. Bundled runtime libraries: `mathjax-full` with the **SVG output** (no font files to ship, works offline), `elkjs` for the layered graph with compound nodes for inclusion-as-grouping (decision confirmed at M2 by rendering the fixture; `@dagrejs/dagre` is the fallback if ELK's bundle or layout disappoints), `ninja-keys` for the search palette. Tests: `vitest`, `@playwright/test`. Pip wrapper `arras` under `arras/python/` vendoring the built bundle; loom locates it with `importlib.resources.files("arras") / "bundle"`.

**System dependencies an installer needs** (documented in both READMEs and checked by `loom doctor`): Python ≥ 3.11 and `uv` or `pipx`; a TeX distribution providing `latexmk`, `pdflatex` (and `lualatex`/`xelatex` if a paper needs them), `dvisvgm`, `bibtex`/`biber`; poppler's `pdftotext`/`pdfinfo` for the identity test; `git` optional. Node ≥ 20 and `npm` only for people building arras itself.

**Routing**: path-based routing everywhere; `loom serve` serves `index.html` as the SPA fallback for unknown paths; `arras build --prerender` prerenders every route listed in the manifest. `file://` is not supported in the MVP (deviation from 10.1.2's assumed automatic hash routing; documented workaround `python -m http.server`).

## Repository layout (concrete)

```
loom-arras/                      workspace repo (tracks docs/, CLAUDE.md, AGENTS.md, clone.sh, .gitignore, LICENSE)
  docs/book/  docs/specs/  docs/source/
  docs/specs/tools/validate-dialect.py   docs/specs/tools/refresh-fixture.sh   docs/specs/fixture/ (generated at M2)
  docs/demonstrations/  docs/deviations.md
  tests/fixtures/                gitignored: the paper sources only: relloc/ 0805.2065/ 1709.09864/ NOTES.md VERSIONS
  demos/                         README.md, refresh.sh, demo/ (= loom init --demo), synthetic/ (proof of concept) committed;
                                 relloc/ (acceptance), man12/, acgs/, scratch-*/ gitignored (paper sources)
  loom/  arras/                  separate clones, gitignored

loom/
  pyproject.toml  LICENSE (GPL)  NOTICE  README.md  CONTRIBUTING.md  .github/workflows/{unit,tex}.yml
  src/loom/
    __init__.py  __main__.py  version.py
    cli/          __init__.py (main group)  quilt.py  nodes.py  graph.py  build.py  review.py  digest.py  ai.py  _common.py (exit codes, --json, --run logging)
    scan/         model.py  quilt.py (discovery, config, user config, author)  source.py (files, encoding)  tokenize.py  macros.py  preamble.py (closure, taxa)  envtree.py  expand.py (span map)  sections.py  nodes.py  labels.py  edges.py  directives.py  hashing.py  lint.py  diagnostics.py  scan.py (orchestrator + per-file cache)
    records/      ledger.py  snapshots.py  annotations.py  selectors.py  states.py  diffs.py
    render/       convert.py (tokenizer-driven translator)  blocks.py  inline.py  fallback.py  tikz.py (ported)  marks.py  manifest.py  bib.py  publish.py  serve.py  watch.py
    tex/          runner.py (latexmk, isolation env, engine)  aux.py  bundle.py  assemble.py  identity.py  pdftotext.py
    digest/       extract.py  counters.py (amsthm emulation)  postnote.py  importer.py  fetch.py
    ai/           init.py  orient.py  runs.py  promote.py  check.py  discard.py  vendor.py (CLAUDE.md/AGENTS.md/skills/commands/permissions)
    assets/       LICENSE (MIT)  loom.sty  demo/  ai/{orientation.md,README.md,modes/*.md,vendor/…}  readme-contract.md
                  arras/ (vendored built bundle + VERSION; refreshed by scripts/vendor_arras.py, never edited by hand)
  scripts/      vendor_arras.py  gen_cli_reference.py
  uv.lock
  tests/
    conftest.py (fake bin dir on PATH, isolated tex env, quilt fixtures)  fake_latex/fake_tex.py
    quilts/demo/  quilts/synthetic/  quilts/edge/<case>/
    fixture/ (vendored snapshot + VERSION)
    unit/  tex/  papers/
  docs/  (README contract page source, generated cli-reference.md)

arras/
  package.json  LICENSE (AGPL)  README.md  svelte.config.js  vite.config.ts  playwright.config.ts
  src/app.html  src/routes/{+layout.ts,+layout.svelte,+page.svelte, node/[key]/, master/[stem]/, digest/[citekey]/, review/, problems/, blockers/, graph/, threads/, thread/[id]/, tags/, tag/[tag]/, taxa/, taxon/[slug]/, references/, loose/}
  src/lib/{manifest/ (types.ts, client.svelte.ts, loader.ts), fragments/ (fetch.ts, mount.ts, refs.ts), math/ (mathjax.ts), graph/ (layout.ts, Graph.svelte), search/ (Palette.svelte), components/ (Badge.svelte, AnnotationBox.svelte, Diagnostics.svelte, Toc.svelte, …), theme.css}
  static/  tests/unit/  tests/e2e/  tests/fixture/ (vendored + VERSION)
  python/ (pyproject.toml for the optional `arras` pip package, src/arras/{__init__.py, bundle/})
  scripts/build-prerender.mjs  package-lock.json  .github/workflows/ci.yml (build, tests, and a `bundle` artefact per commit so loom's vendoring script can also pull a build without Node)
```

## Core design

### Scanner (book ch. 5), the risk centre

Pipeline, each stage a pure function over dataclasses in `scan/model.py`:

1. **Files** (`source.py`): every `*.tex` under the root except `build/` and files with `% !LOOM ignore` in the first 20 lines. Decode UTF-8; on failure decode Mac Roman, then Latin-1, and emit `loom:non-utf8-source` (warning, new code). Keep `line_starts` for offset→line.
2. **Tokenizer** (`tokenize.py`): one pass over the whole text yielding tokens with character offsets: `command(name)`, `begin(env)`, `end(env)`, `group_open/close`, `bracket_open/close`, `math_inline_open/close` (`$`, `\(`), `math_display_open/close` (`$$`, `\[`), `comment` (skipped by consumers), `text`. Handles `\%`, `\\`, `\verb|…|`, `verbatim`/`lstlisting`/`comment` environments. Helper `read_group(tokens, i)` brace-matches across newlines (fixes multi-line `\cite{…}` and `\usepackage{a,\n b}`). Comments are stripped before every later stage, not only hashing (fixes the commented-out duplicate label).
3. **Macros** (`macros.py`): brace-matching parser for `\newcommand{\x}[n][default]{…}`, `\newcommand\x{…}`, `\renewcommand`, `\providecommand`, `\def\x#1#2{…}`, `\DeclareMathOperator[*]`, `\let`; output `{name, args, default, body}`; classify text-mode vs math-mode by whether the body parses as text or contains math-only commands. Replaces the three sitegen regexes; keeps its MathJax output shape.
4. **Preamble closure and taxa** (`preamble.py`): master text before `\begin{document}`; follow `\input{…}` there and `\usepackage{a,b,c}` (comma lists, multi-line) and `\documentclass` to local root files; **transitive** through `.sty` files; `\newtheorem`, `\newtheorem*`, `\declaretheorem`, `\theoremstyle`, `% !LOOM environment:`. Display names that are macros are expanded through the macro table when defined in the closure; otherwise the env name capitalised plus `loom:taxon-name-macro` (info, new). `\theoremstyle` values outside plain/definition/remark map to plain with `loom:unknown-theoremstyle` (warning, new). Lines inside `\newenvironment`/`\renewenvironment` bodies are skipped for `\begin`/`\end` pairing.
5. **Environment tree per file** (`envtree.py`): a tree of every environment with `[start,end)` offsets, optional argument, labels; theorem-like and `proof` flagged by the taxa table. Proof attachment, evaluated among siblings in the same container: adjacency (only whitespace/comments/directives between), `\ref`-family in the optional argument, else **enclosure** (a proof directly inside a theorem-like node with no preceding sibling statement attaches to the enclosing node), else `loom:unattached-proof`. Theorem-like nodes nested inside a proof are nodes; the enclosing proof gets an implicit proof-edge to each (`via: nested`).
6. **Master expansion** (`expand.py`): resolve `\input`, `\include`, `\nest` as TeX does: exact path first, then `.tex` appended; braceless `\input name` accepted; a name not found locally but found by `kpsewhich` is a system file and ignored; otherwise `missing-include`. Non-`.tex` inclusions (e.g. `.pspdftex`) are spliced as opaque text and never scanned for nodes. Span map = list of `(file, file_start, length)` in expanded order; `\nest` adds a level shift. Detects `double-inclusion` and `inclusion-cycle`.
7. **Sectioning** (`sections.py`): units on the expanded text with shifted levels; level skipping allowed. A section's label is the first `\label` on the same line or the next non-blank line **unless that line opens an environment or another sectioning command** (fixes label theft).
8. **Nodes, keys, ownership** (`nodes.py`, `labels.py`): ids by the 5.3.1 grammar; digest prefixes are **citekey slugs** (`[^A-Za-z0-9]` removed; `loom:citekey-slug-collision` error on collision), so `stacks-project` → `stacksproject-05QA`; the `digest:` directive keeps the verbatim citekey. Aliases, qualified keys, positional proof keys, own text = region minus children with a `%% loom:child KEY` placeholder line where a child was cut so structural changes hash differently. External node = `plain` style, no proof, and a `\cite` in the title **or as the first token of the body**.
9. **Edges** (`edges.py`): `\ref`/`\eqref`/`\cref`/`\Cref`/`\autoref`/`\pageref`, `\uses`, postnotes; edges found inside `\tag{}` count; classification statement/proof/prose; closure over statement-edges plus direct proof-edges.
10. **Lint** (`lint.py`, `diagnostics.py`): every code in `specs/diagnostics.md` plus the new ones above, each with locations and keys. `[lint] disable` honoured for publisher codes only.
11. **Hashing** (`hashing.py`): 5.13 normalisation, SHA-256, preamble-closure hash in inclusion order.
12. **Orchestrator** (`scan.py`): `scan(quilt) -> ScanResult`, per-file results cached by content hash so `serve` rescans only changed files.

### Records (book ch. 7)

- `ledger.py`: append-only writer emitting exactly the book's `[[accept]]` block text (header + `schema = 1` on first write, `[accept.closure]` sub-table); reader via `tomllib`. `snapshots.py`: content-addressed `.loom/snapshots/<hex>.tex`. `annotations.py`: `annotations.json` schema 1, id `a-<date>-<nnnn>` per file; only `status` is rewritten in place. `selectors.py`: 7.5.2 resolution with prefix/suffix scoring, whitespace-normalised retry, detached otherwise. `states.py`: pure functions for `incomplete/accepted/stale/draft`, the five causes, `proved`/`settled`, review facts. `diffs.py`: `difflib.unified_diff` snapshot vs current → `build/diffs/`.

### Publisher (book ch. 9)

- `render/convert.py`: tokenizer-driven translator over own text → dialect HTML. Blocks: paragraphs, headings, display math (`\[`, `$$`, equation family incl. starred and `\tag`), lists (itemize/enumerate/description and paralist variants), theorem envs, proofs (`details`), figures/tables, verbatim, fallback. Inline: emph/textbf/texttt/textsc/underline, inline math, `\ref` family → `a.ref`, `\cite` → `span.cite` with `data-postnote`/`data-target`, `\footnote` → `span.footnote`, `\url`/`\href`, `\uses` → nothing, `\incomplete` → `span.incomplete`, ligatures, text-mode macros expanded with argument substitution. Any block that fails to parse or contains an unknown command with arguments goes to `fallback.py`: the block's source compiled in `standalone` with the master's preamble closure (so author macros and `xy`/`tikz` work), `latex` + `dvisvgm --no-fonts --exact-bbox`, content-addressed cache, ids namespaced, width in em (ported `tikz.py`), emitted as `figure.fallback` with `data-src-text` and `loom:converter-fallback`. `tikzcd`/`tikzpicture` and `\xymatrix` displays go the same route as `figure.diagram`. `\includegraphics` PDF → SVG via dvisvgm, PNG/JPEG copied. Every block carries `data-src="FILE:START:END"`.
- `marks.py`: resolved selector span → blocks by `data-src` → quote located in rendered text → `<mark class="annotation">`, else block-level.
- `manifest.py`: every section of `specs/manifest.md`; `bib.py`: minimal `.bib` parser (author, title, year, eprint, version, doi, journal). `publish.py`: staging dir, move fragments/svg/diffs into place, `manifest.json.tmp` → rename. `serve.py` + `watch.py`: 1 s mtime polling of scanned files, config, ledger, snapshots, records; rebuild affected keys; publish; background `loom compile` of the default master; `ThreadingHTTPServer` with `translate_path` mapping `/build/…` to the build dir and everything else to the arras bundle with SPA fallback; ETag = manifest hash. Bundle lookup: `LOOM_ARRAS_BUNDLE`, then the installed `arras` package, then `importlib.resources.files("loom") / "assets/arras"`; `loom doctor` prints which one is in use and its VERSION.
- `tex/`: `runner.py` runs `latexmk -pdf|-lualatex|-xelatex -interaction=nonstopmode -outdir=build/<stem>` from the root with the isolation env (a `LOOM_TEX_ISOLATE=1` switch used by tests; production runs inherit the user's env); `aux.py` reads plain and hyperref `\newlabel` forms; `bundle.py` builds bundles, `--with FILE`, `--draft FILE`; `assemble.py`; `identity.py` compares `pdftotext -layout` outputs whitespace-collapsed and label numbers.

### Arras (book ch. 10)

- `src/lib/manifest/client.svelte.ts`: Svelte 5 rune store holding the manifest and its hash; loader polls `/build/manifest.json` every second with `If-None-Match`; interface version check → problems page with one diagnostic and nothing else.
- `src/lib/fragments/`: lazy fetch, cache keyed by manifest hash, injected via `{@html}` after a validation pass that strips anything outside the dialect (defence in depth); post-mount pass wires `a.ref[data-target]` to routes, `div.include[data-key]` to expandable child fragments, `mark.annotation` to boxes; MathJax typesets the injected subtree with `macros.default` plus the fragment's `data-macros` set.
- `src/lib/math/mathjax.ts`: `mathjax-full` TeX input + SVG output, macros configured at startup from the manifest, `texReset` + `typesetPromise` per fragment; re-typeset on live reload.
- Pages as in 10.2; `Badge.svelte` implements the 10.3 composition as a pure function in `badges.ts` with unit tests; generic rendering for unknown labels/codes/taxa; discarded records hidden behind a toggle.
- Prerender: `scripts/build-prerender.mjs` reads the manifest, writes `prerender-entries.json`, and `+layout.ts` exports `entries()` from it; `svelte.config.js` uses `adapter-static` with `fallback: 'index.html'` for the SPA build and `strict: true` for the prerender build.
- Guard test: `tests/unit/forbidden-words.test.ts` fails if `quilt`, `digest`, `proof`, or any loom command name appears in `src/`.

## Milestones

Each milestone ends with its demonstration recorded in `docs/demonstrations/Mn.md`, commits in each touched repo, and a push.

### M0. Skeleton

1. Workspace: `LICENSE` (GPL-3.0-or-later, ikmartin), `AGENTS.md` and an updated `CLAUDE.md` pointing agents at the book and specs, `clone.sh`, `.gitignore` gains `demos/relloc/`, `demos/man12/`, `demos/acgs/`, `demos/scratch-*/`, `demos/README.md` and `demos/refresh.sh` (a stub until M1), `docs/demonstrations/README.md` + `M0.md`, empty `docs/deviations.md`, `docs/specs/tools/validate-dialect.py` (stub that validates envelope and allowed elements), `docs/specs/fixture/.gitkeep`.
2. loom: `uv init --lib`, `pyproject.toml` (name `loomtex`, script `loom`, deps, ruff/mypy/pytest config, markers `tex`, `paper`, `network`), committed `uv.lock`, `LICENSE`, `NOTICE`, a README with the clone-and-install section (`pipx install git+https://github.com/ikmartin/loom` or `git clone` + `uv sync`, then `uv run loom doctor`), `scripts/vendor_arras.py` (copies a local `arras/build/` into `src/loom/assets/arras/` and writes `VERSION` with the arras commit hash and interface version; refuses if the interface versions differ), `src/loom/{__init__,__main__,version}.py`, `cli/__init__.py` with `loom --version` and `loom doctor` (reports Python, latexmk, engine, biber/bibtex, dvisvgm, pdftotext, git, arras bundle, author name and source, interface version; exit 2 if a required tool is missing), `tests/fake_latex/fake_tex.py` (argv-dispatching shim for latexmk/pdflatex/latex/lualatex/dvisvgm/bibtex/biber/pdftotext/pdfinfo: emits `.aux` with sequential per-section `\newlabel`s by scanning `\newtheorem`, sectioning, `\begin{ENV}` and `\label` through expanded `\input`s; placeholder PDF; fixed SVG; pdftotext = expanded source with commands stripped; invocation log via `FAKE_TEX_LOG`; failure via `FAKE_TEX_FAIL`), `tests/conftest.py` (fake bin dir prepended to PATH, isolated TeX env fixture, `tmp_quilt` builder), first tests (`test_cli_version`, `test_doctor_missing_tool_exit_2`, `test_fake_latex_emits_aux`), `.github/workflows/unit.yml` (uv + pytest on the shim, ruff, mypy, plus an `install-from-clone` job that does `pipx install .` on a clean runner and runs `loom --version` and `loom doctor`) and `tex.yml` (TeX Live container, `-m tex`).
3. arras: `npx sv create` (TS, vitest, playwright), `adapter-static`, committed `package-lock.json`, replace LICENSE with AGPL, a README with the developer install (`npm ci`, `npm run build`, `npm test`) and the note that end users never need Node, `src/lib/manifest/types.ts` from `specs/manifest.md`, home page reading a hand-written `static/build/manifest.json`, `python/` pip package skeleton with `bundle_path()`, `.github/workflows/ci.yml` (install, build, vitest, playwright smoke).
4. Demonstration: `uv run pytest`, `uv run ruff check`, `uv run mypy`, `npm run build && npm test` all green locally and on CI.

### M1. Read a quilt

1. `scan/quilt.py`: discovery walking up to `config.toml` with `[quilt]`, `--quilt`/`LOOM_QUILT`, config validation (unknown keys warn), user config at `~/.config/loom/config.toml`, author resolution order with the exact refusal message.
2. `assets/loom.sty` (three `\providecommand`s as in 4.5) and `assets/readme-contract.md`; `loom init [DIR] [--prefix] [--no-git] [--yes]` and `--demo`.
3. `scan/source.py`, `tokenize.py`, `macros.py`, `preamble.py`, `envtree.py`, `expand.py`, `sections.py`, `nodes.py`, `labels.py`, `edges.py`, `directives.py`, `hashing.py`, `lint.py`, `diagnostics.py`, `scan.py` in that order, each with unit tests from the chapter 5 list in `14-tests.md` (`test_env_*`, `test_id_*`, `test_taxa_*`, `test_proof_*`, `test_edge_*`, `test_region_*`, `test_inclusion_*`, `test_directive_*`, `test_normalize_*`, `test_example_single_file_paper`, `test_example_two_proofs`) plus new tests for each survey finding (`test_env_body_on_begin_line`, `test_proof_by_enclosure`, `test_statement_nested_in_proof`, `test_external_node_by_leading_cite`, `test_section_label_not_stolen`, `test_input_exact_extension_then_tex`, `test_input_braceless_system_file`, `test_taxa_transitive_sty_chain`, `test_taxa_display_name_macro`, `test_unknown_theoremstyle`, `test_non_utf8_source_decoded`, `test_cite_group_across_newline`, `test_digest_prefix_slug`).
4. Fixture quilts: `assets/demo/` (what `loom init --demo` writes: one master, five nodes, one digest; the ledger, annotation, and AI layer arrive at M3 and M6), `tests/quilts/demo/` (a copy asserted equal to `loom init --demo` output), `tests/quilts/synthetic/` (every construct in `specs/fixture.md` §1), `tests/quilts/edge/{spanning-env, begin-not-alone, cycle, double-inclusion, nested-nest, macro-collision, taxon-conflict, beamer-talk}`; each with an expected diagnostics list asserted by `test_lint_<quilt>_expected_codes`. `demos/refresh.sh` completed and run, so `demos/demo/` and `demos/synthetic/` exist in the workspace from M1 on and are re-run at the end of every later milestone that changes them (M2 numbering, M3 records, M6 AI layer).
5. Commands: `loom lint [--json]`, `loom search`, `loom deps [--closure] [--json]`, `loom unravel` (+ aliases, `--json`), `loom delete` (refusal), `loom new TAXON ["TITLE"] [--prefix] [--print]` with allocation per 5.3.2 (source, ledger, annotations, dangling refs, and `git log -S` history when git is present).
6. `test_never_modifies_author_files`: property test running every command against every fixture quilt and comparing author-file hashes.
7. Demonstration: `loom lint` on `demos/demo/` and `demos/synthetic/` reports exactly the fixture's expected codes; `loom deps`/`loom unravel` match hand-computed answers. Additionally: `loom lint` on scratch quilts made from `tests/fixtures/{relloc,0805.2065,1709.09864}` (copied into `demos/scratch-{relloc,man12,acgs}/` with a minimal `config.toml`) completes without crashing, and the diagnostic counts are recorded in `M1.md` with the deviations they triggered.

### M2. Publish and view

1. loom `render/`: `convert.py`, `blocks.py`, `inline.py`, `fallback.py`, ported `tikz.py`, `marks.py` (mark placement lands in M3 but the hook exists), `manifest.py`, `bib.py`, `publish.py`; `tex/runner.py`, `aux.py`, `bundle.py` (with `--with` and `--draft`), `assemble.py`; commands `loom build [--keys]`, `loom bundle`, `loom compile`, `loom assemble`, `loom check`, `loom serve`. Tests from the chapter 9 list (`test_build_*`, `test_fragment_*`, `test_convert_*`, `test_manifest_*`, `test_bundle_*`, `test_serve_*`).
2. `docs/specs/tools/validate-dialect.py` completed (envelope, allowed elements/classes/attributes, `data-src` on blocks, forbidden elements); `refresh-fixture.sh` (compile both synthetic masters, `LOOM_FIXED_TIME`, copy manifest/fragments/svg/diffs, write VERSION); fixture generated and vendored into `loom/tests/fixture/` and `arras/tests/fixture/`; `test_fixture_matches_vendored`.
3. arras: manifest client and loader, fragment mounting, MathJax, node page, master view, digest view (empty until M5), problems page, graph (ELK; decision recorded), tags/taxa/references/loose indexes, search palette, live reload, prerender script, pip wrapper build (`npm run build:pip` copies the bundle into `python/src/arras/bundle/`), vitest unit tests (`manifest_client_loads_and_hashes`, `unknown_state_renders_generic`, `unknown_code_renders_generic`, `version_mismatch_shows_only_diagnostic`), Playwright over the vendored fixture (every route renders, search finds by id/alias/title/tag, reload on manifest change only), prerender test, forbidden-words guard.
4. Vendoring: `npm run build` in arras, then `python scripts/vendor_arras.py ../arras/build` in loom, committed; from here on every arras change that reaches a milestone demonstration is re-vendored so a loom clone always carries a matching bundle.
5. Demonstration: `loom serve` on `demos/synthetic/` renders every page from a loom checkout with no `arras` package installed, and `loom serve` on `demos/demo/` shows the five-node demo; editing a node re-renders within two seconds (measured and recorded); `arras build --prerender` produces a static site of the fixture; the dialect validator passes on every fragment. Alpha release tags `loomtex 0.1.0a1` and `arras 0.1.0-alpha.1` are prepared; publishing to PyPI/npm is gated by the user and never run by me.

### M3. Review

1. `records/` modules; commands `loom accept` (all flags, refusals, `--force`), `loom comment` (all flags, `--batch`, exact error messages), `loom status` (all filters, `--explain`, `--json`, never nonzero), `loom ai discard` (record-level, `--before/--author/--target/--undo`).
2. States, causes with diffs, derived states, review facts, retired keys, positional-key recovery, `loom:detached-annotation`, `loom:retired-ledger-key`, `loom:previous-key-match`.
3. Marks in node and master fragments; manifest `keys`, `annotations`, `threads`, `states`; arras review panel, blockers page, badges, annotation boxes with kind/author filters and discarded toggle, threads pages (read-only).
4. Tests from the chapter 7 list, including `test_timeline_7_11` as one scenario and `test_selector_survives_atomize` (stubbed until M4, then real).
5. Demonstration: the 7.11 timeline executed on `demos/synthetic/`, with the review panel showing the day-9 definition diff; `demos/demo/` refreshed with its two accepted keys, one stale, and one annotation.

### M4. Bring a paper in

1. `loom id`, `loom import` (closure resolution incl. `.bib`, graphics, local styles; copy preserving layout; `\usepackage{loom}` insertion; label insertion in document order; diff shown and confirmed; `--fix-anchoring` rewriting the copy: moves body text after `\begin{ENV}[…]\label{…}` to the next line and text around `\end{ENV}` to its own line; identity test), `loom init --from`, `loom atomize` (all options, refusals, `--all --to-dir`), `loom inline`, `tex/identity.py`.
2. Tests from the chapter 6 list; paper tier tests `test_paper_manolache_*`, `test_paper_acgs_*` gated by `LOOM_PAPER_FIXTURES=/Users/isaac/dev/loom-arras/tests/fixtures`.
3. Demonstration: Manolache and ACGS import into `demos/man12/` and `demos/acgs/`, atomize, and inline with the identity test passing after a documented set of hand edits (expected: none beyond `--fix-anchoring` for Manolache); the relloc copy imports into `demos/relloc/`.

### M5. Digests

1. `digest/extract.py` (closure of the reference paper, compile for `.aux` or `counters.py` emulation, external nodes with slugged ids and locator titles, `\uses` from refs in dropped proofs, macro expansion and macro block, `requires:`), `postnote.py` (normalisation extended for ties, `\S`, `\href`, plurals, part selectors, page refs, Roman numerals, bare tags), `importer.py` (`--as` remapping), `fetch.py` (arXiv, gated by `[refs] fetch`); scanner support for digest files, macro-block groups in bundles and fragments, `loom:version-mismatch`, `status --undigested`; arras digest view and references index.
2. Tests from the chapter 8 list (`test_extract_from_source` on Manolache locally).
3. Demonstration: `loom digest extract Man12 tests/fixtures/0805.2065/virtual6.tex` in `demos/relloc/`; a relloc `\cite[Theorem 4.1]{Man12}`-style postnote resolves (the relloc paper cites other keys; the demonstration uses whichever relloc citation has a matching digest, or the demo quilt); a bundle of a relloc lemma compiles with a Manolache theorem in it.

### M6. The AI layer

1. `assets/ai/` (orientation.md and README.md from Appendix D, `modes/*.md` from Appendix C verbatim, `vendor/` templates), `loom ai init [--permissions] [--skills]` (writes `ai/`, `CLAUDE.md`, `AGENTS.md`, `.loom-modes-version`, `.gitignore` line, `.claude/settings.json`, `.claude/skills/loom-<mode>/SKILL.md`, `.claude/commands/<mode>.md` using the formats Claude Code documents), `loom ai orient [--run]`, `loom ai start [SLUG]` (run.toml, agent launch when configured), `--run` logging on every command that accepts it, `loom ai promote`, `loom ai check`, `loom upgrade` (refreshes shipped files; edited mode files left alone with `.md.new` beside them), threads in the manifest from `thread.md` and `run.log`.
2. Demo quilt gains its AI layer and one finished run; fixture regenerated; `demos/refresh.sh` re-run so `demos/demo/` matches the release's `loom init --demo`.
3. Tests from the chapter 11 list including `test_ai_init_skills_generated_pointer_only`, `test_upgrade_preserves_edited_modes`.
4. Demonstration: the 11.11 session performed with Claude Code on the demo quilt (I run it myself as the agent, in a run directory, via `loom comment --run`); findings appear as marks; a draft is promoted. The Codex half is recorded as blocked (Codex not installed).

### M7. Acceptance

1. relloc migration per 13.6 on `demos/relloc/`: init --from, identity, diagnostics triaged, atomize --sections, digests (one extracted, one ingested by me acting as the agent), `ai init`, a referee run per section, acceptances, an upstream edit made stale and re-accepted, arras served and every page checked.
2. READMEs (contract page generated from `assets/readme-contract.md`; a Quickstart that goes clone or pipx-from-git → `loom doctor` → `loom init demo --demo` → `loom serve`; a system-dependencies table per platform), CONTRIBUTING files, release checklist file (ends at "run `uv publish` / `npm publish`", which the user does), generated `docs/cli-reference.md` from the click tree with a test that it matches the checked-in copy.
3. **Fresh-clone test**, recorded in `M7.md` as the closest I can get to criterion 10 alone: in a temporary directory, `git clone` both repos from GitHub, follow the loom README literally (`pipx install git+…` in a throwaway pipx home, then the `uv sync` path as well), run `loom doctor`, `loom init demo --demo`, `loom check`, `loom serve`, and open every page; then follow the arras README (`npm ci && npm run build && npm test`) and re-vendor to confirm the two clones match. Any step that needed knowledge not in the README is a README bug fixed before the milestone closes.
4. Criteria 9 (Overleaf) and 10 (external user) and the Codex session are recorded as *Blocked on the user* with exact instructions.

### Book revision (final step)

1. Walk `docs/deviations.md` top to bottom; for each row edit the chapter text to describe the implemented behaviour, cite the DR number, and mark the row `book updated: y`.
2. Re-mark every `[assumed]` and `[deferred]` that implementation settled as `[decided]` with a DR reference where a decision changed; leave genuinely open items and move them to Appendix B.
3. Chapter 12 becomes the generated CLI reference (script `loom/docs/gen_cli_reference.py`); chapter 14's test lists are replaced by the actual test ids (script listing `pytest --collect-only`) and the coverage rule is checked mechanically.
4. `docs/specs/` updated for every additive interface change (new diagnostic codes such as `loom:non-utf8-source`, `loom:unknown-theoremstyle`, `loom:taxon-name-macro`, `loom:citekey-slug-collision`; any dialect additions such as a `span.color`); interface version stays 1 unless a breaking change was needed; fixture regenerated.
5. Front matter status line, 13.4 tree (`docs/book/` not `docs/books/`), colophon paragraph on implementation, Appendix B regenerated, Appendix A never edited (only appended).

## Deviations expected before starting (to be recorded as DR-39 onward when hit)

| book | says | plan | why |
|---|---|---|---|
| 5.1.4, 5.2.3, 6.2 | import/atomize refuse non-anchored environments; scanner recognises by surface form | tolerant character-offset scanner; `import --fix-anchoring`; atomize still refuses | 43 % of Manolache's nodes violate it (user decision) |
| 5.6.1 | proof attaches by adjacency or `\ref` only | plus attachment by enclosure; nested statements inside proofs are nodes; implicit `nested` proof-edges | 5 proofs inside examples (Manolache), 4 lemma+proof pairs inside one proof (ACGS) |
| 5.5.2 | external node = `\cite` in the title | or `\cite` as the first body token | all 5 real instances put it in the body |
| 5.4.2 | section label on same or next non-blank line | unless that line opens an environment or sectioning command | 3 label-theft cases |
| 5.9.1 | `\input{path}` with `.tex` appended if absent | exact path first, then `.tex`; braceless form; kpsewhich-resolvable names ignored; non-.tex opaque | `\input{fig.pspdftex}` ×11, `\input xy` |
| 5.3.1 | digest prefix is the citekey | citekey slug; collision error; `digest:` keeps the verbatim key | `stacks-project`, `Parker: gluing`, `FP:97` |
| 5.5.1 | closure = master preamble, `\input`s, `\usepackage` resolving to a local file | transitive through `.sty`, comma lists, multi-line; macro display names; unknown `\theoremstyle` → plain + warning | all 26 relloc taxa are two hops away in `math-env.sty` |
| 5.1 | scan `.tex` files | non-UTF-8 decoded with fallback + warning | Mac Roman arXiv source |
| 5.13 | comments removed for hashing | comments removed before every stage | commented-out duplicate label |
| 8.7 | postnote normalisation table | extended for `~`, `\S`, `\href`, plurals, part selectors, page refs, Roman numerals, bare tags | 104 real postnotes |
| 10.1.2 | hash routing under `file://` automatic | path routing + SPA fallback in `loom serve`; `file://` unsupported | SvelteKit router type is build-time |
| 9.4.3 (assumed) | MathJax 3 | MathJax 3 with SVG output | no font assets to ship offline |
| 10.1.3, 9.8, 12.5 | arras reaches loom users through the `arras` pip package | the built bundle is vendored in loom's repo; the pip package is an optional override; `pipx install git+…/loom` works with no registry | a clone of the two GitHub repos must be enough; publishing is gated by the user |
| 13.4 | `docs/books/` | `docs/book/` | actual directory name |

## Verification

- Unit tier: `cd loom && uv run pytest -m "not tex and not paper and not network"` on every change; `uv run ruff check src tests`; `uv run mypy src`.
- TeX tier: `uv run pytest -m tex` locally with the isolated env (TeX Live 2024 present) and in the CI container.
- Paper tier: `LOOM_PAPER_FIXTURES=/Users/isaac/dev/loom-arras/tests/fixtures uv run pytest -m paper`.
- arras: `npm run check && npm run test:unit && npm run build && npm run test:e2e`; prerender test; forbidden-words guard.
- Interface: `python docs/specs/tools/validate-dialect.py docs/specs/fixture/fragments` and `test_fixture_matches_vendored` in loom.
- Each milestone's "Demonstrates" line executed literally, output pasted into `docs/demonstrations/Mn.md`, status table updated, repos committed and pushed.
- Author-file invariance: `test_never_modifies_author_files` runs every command on every fixture quilt.
- `~/notes` is never touched: a pre-flight check in `conftest.py` asserts no test path resolves under `~/notes`, and every paper-derived quilt lives under `loom-arras/demos/`.

## Blocked on the user (known now)

- Publishing releases to PyPI and npm: gated by the user; the release checklist stops before the publish commands.
- Overleaf test, the external user's paper, and the Codex session at M6/M7.

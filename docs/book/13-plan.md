# 13. The plan

This chapter turns the specification into an order of work. It names the milestones, what each must demonstrate, what is cut from the MVP, how the repositories are laid out, how releases are made, and how the relative localization paper serves as the acceptance test. Estimates are absent by design: the milestones are gated by demonstrations, not dates. The plan was followed: the eight milestones were demonstrated on 2026-09-15 and 2026-09-16, the plan as approved is kept verbatim in `docs/plans/implementation-plan.md`, and each milestone below now ends with what its demonstration record holds.

## 13.1 Principles of construction

**[decided]**

1. The scanner before everything. Nothing else can be tested without it, and the source contract is the part most likely to be wrong on real papers. Build it against the demo quilt first, then the synthetic quilt, then Manolache, then ACGS.
2. Vertical slices. Each milestone runs end to end (source to arras page) for a growing subset of the contract, rather than completing one layer at a time.
3. The fixture is the contract's executable form. From milestone 2 onward, every change to loom's output regenerates the fixture and every change to the interface is a change to the fixture first.
4. Author files are sacred from the first commit. The tests that enforce P7 (4.8) are written before any command that touches a file.
5. Two repositories from the first commit, in two languages, sharing nothing but `specs/`.

## 13.2 Milestones

### M0. Skeleton (both repositories)

- `loom`: package layout, `pyproject.toml`, `loom --version`, `loom doctor`, the fake `latex` shim, CI running the unit suite on the shim.
- `arras`: SvelteKit project with `adapter-static`, a home page reading a hand-written `manifest.json`, CI building the bundle.
- workspace: `docs/`, `specs/`, `specs/fixture/` (empty), the clone script.

Demonstrates: both toolchains build and test on CI.

Demonstrated 2026-09-15; see `docs/work-queue/closed/M0.md`: 13 unit-tier tests on the shim and 2 TeX-tier tests in loom, 5 vitest and 1 Playwright test in arras, `loom doctor` exit 0 with every tool present and exit 2 naming the missing tool otherwise, the loom `unit` and `tex` workflows and the arras `ci` workflow green; DR-39.

### M1. Read a quilt

- `config.toml`, quilt discovery, user config, author resolution.
- The scanner: files, masters, theorem-like environments per file, ids and aliases, taxa from the preamble closure (including `\declaretheorem` and the `environment:` directive), proofs by adjacency and by reference, edges by `\ref` family and `\uses`, labelled regions, directives, `% !TEX program`.
- Sectioning on the expanded master with the source map, level shifts from `\nest`, ownership, uniqueness, cycles, reachability.
- Lint with every code in `specs/diagnostics.md` that concerns the source.
- `loom lint`, `loom search`, `loom deps`, `loom unravel`, `loom delete`.
- `loom.sty`, `loom init` (minimal and `--demo`), `loom new`.

Demonstrates: `loom lint` on the demo quilt and the synthetic quilt reports exactly the diagnostics the fixture description lists; `loom deps` and `loom unravel` match hand-computed answers.

Demonstrated 2026-09-15; see `docs/work-queue/closed/M1.md`: `loom lint` on the demo quilt (0 errors, 0 warnings, 2 infos) and the synthetic quilt (3 errors, 4 warnings, 13 infos) matches the frozen `EXPECTED-LINT.txt` files, `deps` and `unravel` match the hand-computed answers, and the scanner reads all three real papers without crashing (relloc in 0.14 s, Manolache in 0.21 s, ACGS in 0.15 s), which cost three scanner bugs and DR-40 to DR-53.

### M2. Publish and view

- The converter for the LaTeX contract (9.4) with the SVG fallback, the tikz route, macro extraction, `data-src` on blocks.
- The manifest, atomic publish, `loom build`.
- Numbering from the `.aux`; `loom compile`; `loom bundle`.
- arras: node page, master view, digest view (empty until M5), problems page, graph, tags, taxa, search, live reload, static prerender.
- `loom serve`.
- The fixture generated from the synthetic quilt and vendored into both repositories.

Demonstrates: the synthetic quilt served by `loom serve` renders every page in arras; editing a node re-renders within two seconds; `arras build --prerender` produces a static site of the fixture; the dialect validator passes on every fragment.

Demonstrated 2026-09-15; see `docs/work-queue/closed/M2.md`: every page kind renders in a 23-test Playwright suite over the fixture, an edit to a node produces a new manifest in 0.88 s, the prerender writes 50 routes, the validator reports 0 problems on the 26 fragments the fixture then had, the arras bundle is vendored into loom; 116 unit-tier and 6 TeX-tier tests; DR-54 to DR-58.

### M3. Review

- The ledger, snapshots, `loom accept`.
- Review records, selectors, `loom comment` (all flags, `--batch`), detached resolution.
- Computed states, causes with diffs, derived states, review facts.
- `loom status` with all filters and `--explain`; discard; retired keys; positional-key recovery.
- Marks in fragments; arras review panel, blockers page, badges, annotation boxes, threads (read-only).

Demonstrates: the worked timeline of 7.11 executed on the synthetic quilt, with the panel showing the diff of the definition on day 9.

Demonstrated 2026-09-15; see `docs/work-queue/closed/M3.md`: the timeline of 7.11 runs as the single test `test_timeline_7_11`, the shipped synthetic quilt reports 5 stale of 6 accepted with the definition's diff behind `status --explain` and in the review panel, and the fixture carries 7 annotations, 5 stale keys, and 3 diff files; 150 unit-tier tests, 25 Playwright tests; DR-59 to DR-61.

### M4. Bring a paper in

- `loom import`, `loom init --from`, `loom id`, `loom atomize` (all options), `loom inline`, `loom assemble`, the identity test.
- The Manolache fixture through 6.8; the ACGS stress test through 6.9.

Demonstrates: both papers import, atomize, and inline with the identity test passing, after at most a documented set of hand edits; the relative localization paper imports.

Demonstrated 2026-09-15; see `docs/work-queue/closed/M4.md`: Manolache imports after `--fix-anchoring` repairs its 51 line-anchoring violations, ACGS imports with no hand edits at all, both atomize and inline with the identity test passing, and relloc imports with identity passing; every compile ran through `demos/hermetic.sh`; 157 unit-tier, 10 TeX-tier, and 4 paper-tier tests; DR-62 to DR-65.

### M5. Digests

- Digest scanning (prefixed ids, external nodes, macro blocks at extraction sites, `requires`).
- Postnote matching, versioning, `status --undigested`.
- `loom digest extract` with counter emulation, `loom digest fetch`, `loom digest import --as`.
- Bundles including digest statements; arras digest view and references index.

Demonstrates: `loom digest extract Man12` on the Manolache source in the relloc quilt; `\cite[Theorem 4.1]{Man12}` resolves; a bundle of a relloc lemma compiles with Manolache's theorem in it.

Demonstrated 2026-09-16; see `docs/work-queue/closed/M5.md`: Manolache is extracted into the relloc quilt as 96 results and 13 sections with 33 `\uses` lines, every one of the six postnotes the paper uses resolves to a digest node, the bundles of the citing proofs compile with the cited results inside them, and a bundle that lacks the digest's packages fails with `loom:missing-package` named first; 166 unit-tier tests, 26 Playwright tests; DR-66 to DR-69.

### M6. The AI layer

- `loom ai init` (with `--permissions`), orientation document, `loom ai orient`, `loom ai start` with agent launch, runs, `run.log`, `thread.md`, `loom ai promote`, `loom ai check`, the mode templates.
- Threads in the manifest from runs.

Demonstrates: the example session of 11.11 performed with Claude Code and again with Codex on the demo quilt; findings appear as marks; a draft is promoted.

Demonstrated 2026-09-16 for the Claude Code half; see `docs/work-queue/closed/M6.md`: the session of 11.11 performed on the demo quilt, whose shipped run now leaves two marks on the main theorem and one thread in the manifest, a second live run on `demos/demo/`, and a drafted lemma promoted to `nodes/dm-0012.tex` with `loom ai check` passing; 180 unit-tier tests, 27 Playwright tests; DR-70 to DR-72. The Codex half stayed blocked on the user: Codex is not installed on the implementing machine, and `M6.md` gives the command to run it.

### M7. Acceptance

- The relative localization paper through every criterion of 2.3.
- The external user's paper through criterion 10.
- Overleaf manual test on the demo quilt.
- READMEs, CONTRIBUTING files, the release checklist.

Demonstrates: MVP done.

Demonstrated 2026-09-16 for criteria 1 to 8 of 2.3 on `demos/relloc`; see `docs/work-queue/closed/M7.md`: 57 accepted keys with 0 stale after the upstream edit was explained and re-accepted, three digests (Manolache and the virtual-localization paper extracted from source, Romagny ingested by the agent in a run) with every postnote resolving, a served manifest of 302 nodes, 257 keys, 236 edges, and 6 threads whose every page kind renders without a console error, both READMEs, both CONTRIBUTING files, the release checklist, the generated CLI reference (35 commands), and a fresh clone of both repositories installed and run from GitHub following the READMEs alone; 183 unit-tier, 10 TeX-tier, and 4 paper-tier tests, 10 vitest and 27 Playwright tests; DR-73 to DR-80. Criterion 9 (the Overleaf test) and criterion 10 (the external user's paper) stayed blocked on the user, as did publishing; `M7.md` lists the steps for each.

**[decided]** M1 through M3 are strictly ordered; M4 and M5 may proceed in parallel after M2; M6 after M3; M7 last. In the event one agent ran them in sequence, M0 to M7, M4 before M5, as `docs/plans/implementation-plan.md` set out.

## 13.3 What is cut from the MVP

**[decided]** Not built, with the specification kept so nothing forecloses them:

- The write API and the bridge; in-viewer comments and chat.
- The runner, `loom ai run --queued`, `--auto`.
- `atomize --relative`.
- Sitegen as a publisher.
- Cross-quilt references and the corpus.
- KaTeX as an alternative to MathJax.
- `loom open`, user-level mode templates, a user-level default prefix.
- Windows in CI.
- A `manifest.schema.json` derived from `specs/manifest.md`. **[decided]** Not built at M2 or later (`docs/work-queue/closed/M2.md`); loom checks the manifest structurally in `test_build_layout_and_manifest` and arras types it in `src/lib/manifest/types.ts`.
- Prerender optimisations for very large quilts, precomputed graph layouts.

None of these exists at the end of M7: the generated CLI reference (`loom/docs/cli-reference.md`) has no `open`, no `atomize --relative`, and no `ai run`, and both CI workflows run on Ubuntu only.

What became of them since is in `docs/work-queue/`, and three were not merely cut but **declined**, which is a different thing: the runner (WQ-15), `atomize --relative` (WQ-07), and `manifest.schema.json` (WQ-14). Each had a specification kept so as not to foreclose it, and each was examined later and found to be a decline rather than a deferral — a trigger nobody would ever observe. The rest are live queue items or were settled by a later round.

## 13.4 Repositories and workspace

**[decided]** The layouts as built. The workspace repository tracks `docs/`, `demos/` (the two committed quilts), and the files at its root; the tool repositories and the paper sources are gitignored.

```
loom-arras/                 workspace; a git repository tracking docs/, demos/, and the root files
  .gitignore                loom/  arras/  tests/fixtures/  demos/relloc/  demos/man12/  demos/acgs/  demos/scratch-*/
  CLAUDE.md, AGENTS.md      orientation for agents working across both tools
  LICENSE, COPYRIGHT        GPL-3.0-or-later, ikmartin
  clone.sh                  clones the two tool repositories beside itself
  docs/
    book/                   this book
    specs/                  the interface: README.md, dialect.md, manifest.md, diagnostics.md, fixture.md, write-api.md, runner.md
      tools/                validate-dialect.py, refresh-fixture.sh
      fixture/              generated, never edited: manifest.json, fragments/, svg/, diffs/, VERSION
    plans/implementation-plan.md   the plan that was followed, verbatim
    work-queue/             README.md (what is not done, and its trigger), one file per item,
                            closed.md and closed/ (the milestone records M0.md to M7.md)
    deviations.md           one row per deviation, each with its DR
    source/
      global-rules.md       the author's chat review rules, verbatim: the provenance of the mode files
      global-rules-mapping.md   every part of those rules mapped to its loom destination and the change applied
  demos/
    README.md, refresh.sh, hermetic.sh
    demo/                   exactly what loom init --demo writes; committed; regenerated by refresh.sh
    synthetic/              the quilt the fixture is generated from, copied from loom/tests/quilts/synthetic; committed
    relloc/ man12/ acgs/ scratch-*/   quilts built from the paper sources with hermetic.sh; gitignored
  loom/                     separate clone; own repository
  arras/                    separate clone; own repository
  tests/
    fixtures/               the paper sources (relloc/, 0805.2065/, 1709.09864/, NOTES.md, VERSIONS); never committed
```

```
loom/                       GPL-3.0-or-later; NOTICE names the files ported from the author's site generator
  pyproject.toml, uv.lock   distribution loomtex; console script loom; pytest markers tex, paper, network
  README.md, CONTRIBUTING.md, LICENSE, NOTICE
  src/loom/
    __init__.py __main__.py version.py clock.py doctor.py arras_bundle.py
    cli/                    the click command tree; --help and docs/cli-reference.md are generated from it
    scan/                   quilt, source, tokenize, macros, preamble, envtree, expand, sections, nodes, labels, alloc, edges, postnote, directives, hashing, digests, bib, graph, lint, diagnostics, scan
    records/                ledger, snapshots, annotations, selectors, store (the computed states)
    render/                 convert, fallback, fragments, marks, manifest, threads, assets, publish, serve, watch, build
    tex/                    runner (latexmk), aux, bundle, assemble, identity
    reshape/                ids, importer, anchoring, atomize (atomize and inline)
    digest/                 extract, counters, importer, fetch
    ai/                     layout, orient, runs, promote, check
    assets/                 MIT-licensed shipped files, with their LICENSE
      loom.sty  readme-contract.md
      init/                 main.tex and the .gitignore template that loom init writes
      demo/                 the demo quilt, with its AI layer initialised and one finished run
      ai/                   orientation.md  README.md  modes/ (blocks.md and the seven mode files)  vendor/ (root.md, claude/settings.json, claude/SKILL.md, claude/command.md)
      arras/                the vendored viewer bundle: index.html, _app/, robots.txt, README.md, VERSION naming the arras commit and interface version
  scripts/                  vendor_arras.py (copies an arras build into assets/arras and writes VERSION), gen_cli_reference.py (--check)
  docs/                     cli-reference.md (generated), RELEASE.md (the release checklist)
  tests/
    conftest.py             the shim on PATH, or the real toolchain for tex-marked tests; empty HOME and TeX trees for every test
    fake_latex/fake_tex.py  the shim
    quilts/                 demo/, synthetic/, edge/<eight cases>/, each with EXPECTED-LINT.txt
    fixture/                vendored conformance snapshot with VERSION
    unit/                   scan/, records/, render/, and the command tests, all on the shim
    tex/                    the real toolchain, isolated
    papers/                 skipped unless LOOM_PAPER_FIXTURES is set
    tools/validate_dialect.py   a copy of the workspace validator
  .github/workflows/        unit.yml (Python matrix plus an install-from-clone job), tex.yml (TeX Live container)
```

```
arras/                      AGPL-3.0-or-later; NOTICE
  package.json, package-lock.json   npm package arras, private and unpublished; scripts build, build:prerender, build:pip, test:unit, test:e2e
  vite.config.ts, tsconfig.json, playwright.config.ts   the SvelteKit configuration lives in vite.config.ts; there is no svelte.config.js
  README.md, CONTRIBUTING.md, LICENSE, NOTICE
  src/
    app.html, app.d.ts
    lib/                    manifest/ (types, loader, client), fragments/ (fetch, mount, Fragment.svelte), math/ (mathjax), graph/ (layout), components/ (Badge, AnnotationBox, AnnotationPanel, Diagnostics, Palette), badges.ts, diagnostics.ts, nav.ts, ui.svelte.ts, theme.css; the vitest specs (*.spec.ts) sit beside the modules they test
    routes/                 +layout, home, node/[...key], master/[stem], digest/[citekey], review, problems, blockers, graph, threads, thread/[id], tags, tag/[tag], taxa, taxon/[slug], references, loose
  static/robots.txt
  scripts/                  stage-fixture.mjs (copies tests/fixture into static/build for dev and e2e), build-prerender.mjs, copy-bundle.mjs (into python/)
  python/                   the optional arras pip package: pyproject.toml, README.md, src/arras/{__init__.py, bundle/}; unpublished
  tests/
    fixture/                vendored snapshot with VERSION
    unit/forbidden-words.spec.ts   the 10.8 guard (DR-39)
    e2e/                    home.e2e.ts, routes.e2e.ts: Playwright over the fixture
  .github/workflows/ci.yml  svelte-check, vitest, build, Playwright, the bundle as an artefact; no publish job
```

**[decided]** `LICENSE` files: GPL-3.0-or-later in `loom/`, AGPL-3.0-or-later in `arras/`, MIT in `loom/src/loom/assets/` for `loom.sty` and the demo quilt (with a `LICENSE` in that directory and a header in `loom.sty`), the workspace repository under GPL-3.0-or-later for the book and specs. Done at M0 with `ikmartin` as the holder (`docs/plans/implementation-plan.md`); arras's GitHub-generated MIT file was replaced.

## 13.5 Releases

**[decided]** The release checklist lives in `loom/docs/RELEASE.md` and is applied to every tagged release of loom. It stops before publishing: its last step, `uv build && uv publish` for `loomtex`, is the maintainer's own, nothing before it publishes anything, and no script or agent runs it. Its steps, in order:

1. The unit, TeX, and paper tiers green; `ruff`, `mypy`, and `scripts/gen_cli_reference.py --check` clean.
2. `loom check` on the demo, the synthetic quilt, and locally on the Manolache and ACGS imports (`demos/man12`, `demos/acgs`).
3. The fixture regenerated with `docs/specs/tools/refresh-fixture.sh` and both vendored snapshots equal to it; the dialect validator passing on every fragment.
4. The arras bundle re-vendored from an arras build at the commit the release notes name (`scripts/vendor_arras.py ../arras/build`), and `loom doctor` reporting that bundle and interface version 1.
5. Every command in `README.md` and `docs/cli-reference.md` exists in this release.
6. The Overleaf manual test on the demo quilt (14.5), with Overleaf's TeX Live version in the release notes.
7. `loom doctor` on a clean machine with a fresh TeX Live, following `README.md` literally by both install paths.
8. Versions: `src/loom/version.py` and `pyproject.toml` bumped together; semantic versioning, independent of arras; the interface version in the release notes; the tag `vX.Y.Z`.
9. Publish, the maintainer's step.

Arras has no checklist of its own: its release is the build the checklist vendors into loom at step 4, its npm package is private, and the pip wrapper under `arras/python/` carries the version of the npm package it wraps (`0.1.0-alpha.0` as `0.1.0a0`). No release has been tagged in either repository; at the end of M7 loom is `0.1.0.dev0`, arras `0.1.0-alpha.0`, and the interface version 1, and the install path the READMEs give is from the git repositories, not from a registry.

## 13.6 The relloc migration as acceptance

**[decided]** The author's paper is the acceptance test, not a fixture: its sources are never committed to any tool repository. The sequence, each step a demonstration recorded in `docs/work-queue/closed/`, was carried out on `demos/relloc/` (a copy under the workspace, gitignored) with every compile through `demos/hermetic.sh`:

1. `loom init relloc --from ~/papers/relloc/draft3.tex`; identity test; diagnostics triaged. Performed: import at M4 with `--fix-anchoring`, identity passing (`M4.md`); triage at M7, one dangling `\ref` repointed and two proofs separated from their lemma by `\red{}` notes attached with `[Proof of Lemma~\ref{...}]`, after which `loom lint` reports 0 errors (`M7.md`, criteria 1, 2, and 4).
2. `loom atomize drafts/draft3.tex drafts/draft4.tex --sections`; `draft3.tex` deleted; `main` updated; identity test. Performed at M7: 52 nodes and 3 deferred proofs moved, a 104-line spine, identity passing, `inline --all` passing it again, `loom check` ok (`M7.md`, criterion 3).
3. `loom digest extract Man12 ...` and ingest of one PDF-only reference; postnotes resolve. Performed: Manolache extracted at M5 (`M5.md`); at M7 the virtual-localization paper fetched and extracted, and Romagny fetched and ingested by the agent in a run then promoted, with every postnote of all three resolving (`M7.md`, criterion 7).
4. `loom ai init`; a referee run per section; comments in margins; objections fixed; acceptances. Performed at M7: five referee runs, a record on every statement and proof, one objection on a proof first marked `\incomplete`, then every statement accepted with `--proofs`, 57 accepted keys (`M7.md`, criterion 5).
5. An upstream definition edited; stale keys explained; re-accepted. Performed at M7 on Lemma `rl-000G`: 3 stale of 57 explained with the lemma's diff, then 0 stale after `accept --stale` (`M7.md`, criterion 6).
6. Arras served; every page checked; Overleaf compile of the quilt. The arras part performed at M7: every page kind of the served quilt visited in a headless browser without a console error, four faults found and fixed on the way (DR-78 to DR-80) (`M7.md`, criterion 8). The Overleaf compile was not performed: blocked on the user, with the procedure in `M7.md` under "Blocked on the user".
7. The external user's paper through step 1 and `loom status`. Not performed: blocked on the user (`M7.md`); the fresh-clone install from GitHub recorded there is the nearest substitute one agent could make.

## 13.7 Working method

**[decided]** The implementation is carried out by agents under the author's direction, in the manner the source paper's authors describe: the author supplies each milestone's plan and judges each demonstration; agents draft, test, and propose; every deviation from this book becomes a decision record before code is merged. The workspace's own `CLAUDE.md` and `AGENTS.md` point agents at this book and at `specs/`, and instruct them to mark in their pull requests which statements of the book they implemented, which they found wrong, and which were deferred.

As carried out: one agent, Claude Fable 5.1 running as Claude Code, worked through M0 to M7 under the author's `/loop` directive from the plan the author approved on 2026-09-15 (`docs/plans/implementation-plan.md`), reading `docs/work-queue/closed.md` at each wake-up to find the first milestone not yet demonstrated. Each demonstration is a record in `docs/work-queue/closed/`, and each of the 42 deviations, DR-39 to DR-80, was appended to Appendix A with a row in `docs/deviations.md` before the work went on. The work reached the tool repositories as commits on `main` rather than pull requests, each commit message naming the records it implements; the author's judgement of the demonstrations is the review the plan foresaw.

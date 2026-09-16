# 13. The plan

This chapter turns the specification into an order of work. It names the milestones, what each must demonstrate, what is cut from the MVP, how the repositories are laid out, how releases are made, and how the relative localization paper serves as the acceptance test. Estimates are absent by design: the milestones are gated by demonstrations, not dates.

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

### M1. Read a quilt

- `config.toml`, quilt discovery, user config, author resolution.
- The scanner: files, masters, theorem-like environments per file, ids and aliases, taxa from the preamble closure (including `\declaretheorem` and the `environment:` directive), proofs by adjacency and by reference, edges by `\ref` family and `\uses`, labelled regions, directives, `% !TEX program`.
- Sectioning on the expanded master with the source map, level shifts from `\nest`, ownership, uniqueness, cycles, reachability.
- Lint with every code in `specs/diagnostics.md` that concerns the source.
- `loom lint`, `loom search`, `loom deps`, `loom unravel`, `loom delete`.
- `loom.sty`, `loom init` (minimal and `--demo`), `loom new`.

Demonstrates: `loom lint` on the demo quilt and the synthetic quilt reports exactly the diagnostics the fixture description lists; `loom deps` and `loom unravel` match hand-computed answers.

### M2. Publish and view

- The converter for the LaTeX contract (9.4) with the SVG fallback, the tikz route, macro extraction, `data-src` on blocks.
- The manifest, atomic publish, `loom build`.
- Numbering from the `.aux`; `loom compile`; `loom bundle`.
- arras: node page, master view, digest view (empty until M5), problems page, graph, tags, taxa, search, live reload, static prerender.
- `loom serve`.
- The fixture generated from the synthetic quilt and vendored into both repositories.

Demonstrates: the synthetic quilt served by `loom serve` renders every page in arras; editing a node re-renders within two seconds; `arras build --prerender` produces a static site of the fixture; the dialect validator passes on every fragment.

### M3. Review

- The ledger, snapshots, `loom accept`.
- Review records, selectors, `loom comment` (all flags, `--batch`), detached resolution.
- Computed states, causes with diffs, derived states, review facts.
- `loom status` with all filters and `--explain`; discard; retired keys; positional-key recovery.
- Marks in fragments; arras review panel, blockers page, badges, annotation boxes, threads (read-only).

Demonstrates: the worked timeline of 7.11 executed on the synthetic quilt, with the panel showing the diff of the definition on day 9.

### M4. Bring a paper in

- `loom import`, `loom init --from`, `loom id`, `loom atomize` (all options), `loom inline`, `loom assemble`, the identity test.
- The Manolache fixture through 6.8; the ACGS stress test through 6.9.

Demonstrates: both papers import, atomize, and inline with the identity test passing, after at most a documented set of hand edits; the relative localization paper imports.

### M5. Digests

- Digest scanning (prefixed ids, external nodes, macro blocks at extraction sites, `requires`).
- Postnote matching, versioning, `status --undigested`.
- `loom digest extract` with counter emulation, `loom digest fetch`, `loom digest import --as`.
- Bundles including digest statements; arras digest view and references index.

Demonstrates: `loom digest extract Man12` on the Manolache source in the relloc quilt; `\cite[Theorem 4.1]{Man12}` resolves; a bundle of a relloc lemma compiles with Manolache's theorem in it.

### M6. The AI layer

- `loom ai init` (with `--permissions`), orientation document, `loom ai orient`, `loom ai start` with agent launch, runs, `run.log`, `thread.md`, `loom ai promote`, `loom ai check`, the mode templates.
- Threads in the manifest from runs.

Demonstrates: the example session of 11.11 performed with Claude Code and again with Codex on the demo quilt; findings appear as marks; a draft is promoted.

### M7. Acceptance

- The relative localization paper through every criterion of 2.3.
- The external user's paper through criterion 10.
- Overleaf manual test on the demo quilt.
- READMEs, CONTRIBUTING files, the release checklist.

Demonstrates: MVP done.

**[decided]** M1 through M3 are strictly ordered; M4 and M5 may proceed in parallel after M2; M6 after M3; M7 last.

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
- A `manifest.schema.json` derived from `specs/manifest.md` (**[deferred]** to M2 if time allows, since it makes arras's tests stricter).
- Prerender optimisations for very large quilts, precomputed graph layouts.

## 13.4 Repositories and workspace

**[decided]**

```
loom-arras/                 workspace; a git repository tracking docs/ and workspace files only
  .gitignore                loom/  arras/  tests/fixtures/
  CLAUDE.md, AGENTS.md      orientation for agents working across both tools
  clone.sh                  clones the two tool repositories
  docs/
    books/                  this book
    specs/                  the interface, tools/, fixture/
    source/
      global-rules.md       the author's chat review rules, verbatim: the provenance of the mode files
      global-rules-mapping.md   every part of those rules mapped to its loom destination and the change applied
  loom/                     separate clone; own repository
  arras/                    separate clone; own repository
  tests/
    fixtures/               arXiv sources, downloaded by hand; never committed
```

```
loom/                       GPL-3.0-or-later
  pyproject.toml            distribution loomtex; console script loom
  src/loom/
    cli/                    command definitions; help and reference generated from these
    scan/                   files, environments, sections, source map, directives, edges, lint
    records/                ledger, snapshots, annotations, states
    render/                 converter, tikz, macros, marks, manifest, publish
    tex/                    latexmk, aux reading, bundles, assemble, identity test
    digest/                 extract, postnote matching, import
    ai/                     init, orient, runs, promote
    assets/                 MIT-licensed shipped files
      loom.sty
      demo/                 the demo quilt, with its AI layer initialised and one finished run
      ai/
        orientation.md  README.md
        modes/            blocks.md and the seven mode files
        vendor/           CLAUDE.md, AGENTS.md, ai-README.md,
                          claude/settings.json, claude/skills/SKILL.md.tmpl, claude/commands/command.md.tmpl
  tests/
    quilts/demo/  quilts/synthetic/
    fixture/                vendored snapshot with VERSION
    papers/                 skipped unless LOOM_PAPER_FIXTURES is set
    fake_latex/             the shim
  docs/                     README.md, CONTRIBUTING.md, generated CLI reference
  .github/workflows/        unit (shim) and tex (container) jobs
```

```
arras/                      AGPL-3.0-or-later
  package.json              npm package arras
  src/                      SvelteKit app: routes, components, manifest client, MathJax config
  tests/
    fixture/                vendored snapshot with VERSION
    unit/  e2e/             vitest, playwright
  python/                   the arras pip package: a thin wrapper vendoring the built bundle
  docs/                     README.md, CONTRIBUTING.md
  .github/workflows/        build, test, publish npm and pip artefacts
```

**[decided]** `LICENSE` files: GPL-3.0-or-later in `loom/`, AGPL-3.0-or-later in `arras/`, MIT in `loom/src/loom/assets/` for `loom.sty` and the demo quilt (with a `LICENSE` in that directory and a header in `loom.sty`), the workspace repository under GPL-3.0-or-later for the book and specs. If any repository already carries a different license file, it is replaced.

## 13.5 Releases

**[decided]** The release checklist, applied to every tagged release of either tool:

1. `loom check` on the demo, the synthetic quilt, and locally on Manolache and ACGS.
2. The fixture regenerated and both vendored snapshots equal to it.
3. The dialect validator and the manifest schema (when it exists) pass.
4. Every command in the README exists in this release; every screenshot is regenerated from the demo.
5. The Overleaf manual test on the demo quilt (Chapter 14).
6. `loom doctor` on a clean machine with a fresh TeX Live.
7. Versions: loom and arras use semantic versioning independently; the interface version is recorded in each release's notes; the arras pip package version equals the npm package version it wraps.
8. Publish: `uv publish` for `loomtex` and `arras` (pip), `npm publish` for `arras`.

## 13.6 The relloc migration as acceptance

**[decided]** The author's paper is the acceptance test, not a fixture: its sources are never committed to any tool repository. The sequence, each step a demonstration recorded in the decision log:

1. `loom init relloc --from ~/papers/relloc/draft3.tex`; identity test; diagnostics triaged.
2. `loom atomize drafts/draft3.tex drafts/draft4.tex --sections`; `draft3.tex` deleted; `main` updated; identity test.
3. `loom digest extract Man12 ...` and ingest of one PDF-only reference; postnotes resolve.
4. `loom ai init`; a referee run per section; comments in margins; objections fixed; acceptances.
5. An upstream definition edited; stale keys explained; re-accepted.
6. Arras served; every page checked; Overleaf compile of the quilt.
7. The external user's paper through step 1 and `loom status`.

## 13.7 Working method

**[decided]** The implementation is carried out by agents under the author's direction, in the manner the source paper's authors describe: the author supplies each milestone's plan and judges each demonstration; agents draft, test, and propose; every deviation from this book becomes a decision record before code is merged. The workspace's own `CLAUDE.md` and `AGENTS.md` point agents at this book and at `specs/`, and instruct them to mark in their pull requests which statements of the book they implemented, which they found wrong, and which were deferred.

## Open questions

- Whether M4 should precede M3, since importing the real paper early would surface scanner problems sooner. **[assumed]** M3 first, because review is the tool's point and M4's fixtures can be exercised through `lint` alone from M1.
- Whether the ACGS stress test should gate M4 or only inform it. **[assumed]** Gate, with a documented allowance for hand edits.
- Whether to publish pre-1.0 releases to PyPI at all or install from git until M7. **[assumed]** Publish from M2, marked alpha, so the external user's install path is real.

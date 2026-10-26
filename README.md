# loom-arras

One repository holding loom, its viewer arras, and the documents that govern them. `loom` turns a LaTeX paper into a *quilt*, where every theorem-like environment and section carries a permanent id as an ordinary `\label`, dependencies are read from the `\ref`, `\cite[postnote]` and `\uses` an author already writes, acceptances are recorded with content hashes, and review comments are anchored to quoted text. `arras` is the viewer it publishes to. The paper still compiles with plain `pdflatex`, from the same files, on Overleaf.

| directory | what it is | language |
|---|---|---|
| `loom/` | the CLI: scanner, reshaping commands, history, digests, build | Python |
| `arras/` | the static viewer for a published quilt | Svelte |

loom and its viewer are separate codebases, each with its own build, tests and dependencies, and the viewer ships inside loom. `loom` never needs the viewer: a quilt edited in a plain text editor loses nothing.

## The documents

They are the reason this repository exists, and they govern loom rather than describing it after the fact.

- `docs/design/` — the design: what loom is for, the three people every decision is tested against, the principles, the model, how agents take part, and the invariants that must not be lost. It records current thinking and changes as the design is discovered; what is decided but not built is marked as such.
- `docs/specs/` — the formats: the loom–arras interface (manifest, HTML dialect, conformance fixture), the source contract, digests and diagnostics. They win over the design wherever shapes are concerned.
- `docs/contributing.md` — how to build, test, verify and release.
- `docs/work-queue/` — deferred work, each item with an observable trigger saying when it becomes worth doing.
- `docs/plans/` — the plan for work in progress. Earlier plans are history: what was intended at the time.
- `docs/design/decision-records-frozen.md` — the decision records of the original design book, frozen as history on 2026-10-26 so that the `DR-NNN` ids cited in code still resolve. The book itself and its deviations log are deleted; git history keeps them.
- `AGENTS.md` — the rules that hold for everyone working here, human or agent. Read it first.

`demos/` holds example quilts: `demo/` is what `loom init --demo` writes, `synthetic/` exercises every construct of the source contract and generates the conformance fixture, and `showcase/` is the one to open when you want to see what loom does. Quilts built from real papers are gitignored, because they contain the paper sources.

## Getting started

```sh
git clone https://github.com/ikmartin/loom-arras
cd loom-arras
uv tool install -e ./loom        # puts `loom` on your PATH, running this checkout
loom --version
```

`uv sync` inside `loom/` builds a virtual environment but does **not** put `loom` on your PATH; that is what `uv tool install -e` is for, and `-e` means a `git pull` takes effect without reinstalling. If the command is still not found afterwards, run `uv tool update-shell` and open a new terminal.

To see a quilt in the viewer:

```sh
cd demos/showcase && loom serve
```

For the viewer's own development, `cd arras && npm ci && npm run dev`.

## Tests

| suite | command |
|---|---|
| loom, unit tier | `cd loom && uv run pytest -m "not tex and not paper and not network and not client"` |
| loom, everything | `cd loom && uv run pytest` (needs a TeX distribution and poppler) |
| arras | `cd arras && npm run test:unit` and `npm run test:e2e` |
| the documents | `python docs/work-queue/check.py` |

The LaTeX compiles in loom's tests run with an empty `HOME` and empty TeX trees, so a test can only read what it created.

## Working here

A change that crosses loom and its viewer — a manifest field and the viewer code that reads it, say — is one branch and one pull request. That is why they are one repository (DR-196).

CI runs `scripts/verify`, one workflow per lane: `loom`, `arras` and `docs`, each triggered only by the paths its lane reads (`docs/contributing.md`).

`loom` is released to PyPI, with arras vendored into it. Publishing is done by hand, never by CI.

## License

GPL-3.0-or-later; see `LICENSE`. Files under `loom/src/loom/assets/` (`loom.sty`, the demo quilt, the AI-layer templates) are MIT, so they can travel with your paper: see `loom/NOTICE`.

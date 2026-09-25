# loom

A tool for atomized mathematical development. loom turns a LaTeX paper into a *quilt*: every theorem-like environment and section carries a permanent id as an ordinary `\label`, dependencies are read from the `\ref`, `\cite[postnote]`, and `\uses` you already write, acceptances are recorded with content hashes so you are told exactly what went stale and why, review comments are anchored to quoted text, and the whole is published to the [arras](https://github.com/ikmartin/arras) viewer. The paper compiles exactly as before, with plain `pdflatex`, from the same files, on Overleaf.

Status: alpha; every milestone of the design book is implemented and demonstrated. The book, the interface specification, and the demonstration records live in the [loom-arras workspace](https://github.com/ikmartin/loom-arras).

## Install from a clone

Nothing here depends on a package registry. You need:

| dependency | why | macOS | Debian/Ubuntu |
|---|---|---|---|
| Python 3.11 or newer with `uv` or `pipx` | runs loom | `brew install uv` or `brew install pipx` | `pipx install uv` or `apt install pipx` |
| TeX Live (`latexmk`, `pdflatex`, `dvisvgm`, `bibtex`/`biber`) | compiling, numbering, diagrams | `brew install --cask mactex-no-gui` | `apt install texlive-full` |
| poppler (`pdftotext`, `pdfinfo`) | the identity test after import and atomize | `brew install poppler` | `apt install poppler-utils` |
| git (optional) | recommended, never required | `brew install git` | `apt install git` |

Then either

```
pipx install git+https://github.com/ikmartin/loom
loom doctor
```

or, for development,

```
git clone https://github.com/ikmartin/loom
cd loom
uv sync
uv run loom doctor
```

`loom doctor` names anything missing and how to get it. The arras viewer ships inside this repository as a built bundle, so `loom serve` needs no Node.

## Quickstart

```
loom doctor                 # names every missing tool and how to install it
loom init demo --demo       # a five-node quilt with a digest, acceptances, comments, and an AI run
cd demo
loom check                  # lint plus a compile of the master
loom serve                  # http://127.0.0.1:8791, re-renders whenever a file changes
```

Then, on your own paper:

```
loom init mypaper --from ~/papers/draft.tex     # the paper arrives as one flat landmark in canon/
cd mypaper
loom draft canon/draft.tex --to drafting/main.tex   # a working copy, with an id on every node
loom status                                     # every key, its state, and its open comments
loom atomize drafting/main.tex drafting/spine.tex --sections   # one file per node, a spine of \input lines
loom canonize drafting/spine.tex -m "Submitted"  # a landmark, and a record of what every key was
loom accept rl-0004 --proofs                    # record what you have checked; later edits show up as stale
loom annotate rl-0004/proof "Why closed?" --quote "the diagonal is closed" --kind question
loom digest extract Man12 ~/papers/manolache/virtual6.tex  # a cited paper's results as nodes; \cite[Theorem 4.1]{Man12} becomes an edge
loom ai init --skills --permissions             # the optional AI layer: orientation, modes, runs, permission settings
```

Every command is described in [docs/cli-reference.md](docs/cli-reference.md), generated from the command tree. `loom <command> --help` says the same.

## What a quilt is

An ordinary LaTeX project loom can read: the documents you are working on in `drafting/`, one node per file in `nodes/` by convention, digests of cited papers in `digests/`, landmarks in `canon/` (flat, self-contained copies of a document as it stood, never scanned), and three macros from `loom.sty` that print nothing (`\uses`, `\incomplete`, `\nest`). The paper compiles with plain `pdflatex` from the quilt root and on Overleaf. Loom edits author files only when the author explicitly clicks **Incorporate pull** in a locally served Incoming review; that action applies the exact displayed patch and makes local commits. Its own data lives in `.loom/` (the acceptance ledger and the history of every key), `comments/` and `ai/runs/` (review records), and `build/` (everything derived). `loom init` writes `CONTRACT.md` into every quilt with the full contract.

## Layout of this repository

- `src/loom/scan/` reads a quilt (files, macros, environments, sections, ids, edges, lint, hashing).
- `src/loom/records/` holds the acceptance ledger, snapshots, annotations, and the computed states.
- `src/loom/history/` holds the history: the ledger of steps, the versions of every key, and the checks over them.
- `src/loom/render/` publishes the build directory arras reads (fragments, manifest, threads, serve).
- `src/loom/tex/` wraps latexmk, reads `.aux` files, builds bundles, and runs the identity test.
- `src/loom/reshape/` is `id`, `import`, `atomize`, and `inline`; `src/loom/digest/` extracts, imports, and fetches digests; `src/loom/ai/` is the AI layer.
- `src/loom/assets/` ships `loom.sty`, the demo quilt, the AI-layer templates, and the built arras viewer.

## Development

- `uv run pytest` runs the unit tier against a fake TeX toolchain in seconds; `uv run pytest -m tex` runs the TeX tier against your real TeX Live in an isolated environment; `LOOM_PAPER_FIXTURES=... uv run pytest -m paper` runs the paper tier.
- `uv run ruff check src tests` and `uv run mypy` must be clean.
- `scripts/vendor_arras.py ../arras/build` refreshes the vendored viewer after building arras; `scripts/gen_cli_reference.py` regenerates `docs/cli-reference.md` (a test fails when it is stale).
- `docs/RELEASE.md` is the release checklist; it stops before publishing.

## License

GPL-3.0-or-later. Files under `src/loom/assets/` (`loom.sty`, the demo quilt, the AI-layer templates) are MIT so they can travel with your paper. See `LICENSE` and `NOTICE`.

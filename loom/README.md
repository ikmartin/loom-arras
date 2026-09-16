# loom

A tool for atomized mathematical development. loom turns a LaTeX paper into a *quilt*: every theorem-like environment and section carries a permanent id as an ordinary `\label`, dependencies are read from the `\ref`, `\cite[postnote]`, and `\uses` you already write, acceptances are recorded with content hashes so you are told exactly what went stale and why, review comments are anchored to quoted text, and the whole is published to the [arras](https://github.com/ikmartin/arras) viewer. The paper compiles exactly as before, with plain `pdflatex`, from the same files, on Overleaf.

Status: pre-alpha, under construction milestone by milestone. See the design book in the [loom-arras workspace](https://github.com/ikmartin/loom-arras) for the full specification.

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
loom init demo --demo
cd demo
loom serve
```

(Available from milestone M2; `loom init` from M1.)

## Development

- `uv run pytest` runs the unit tier against a fake TeX toolchain in seconds; `uv run pytest -m tex` runs the TeX tier against your real TeX Live in an isolated environment; `LOOM_PAPER_FIXTURES=... uv run pytest -m paper` runs the paper tier.
- `uv run ruff check src tests` and `uv run mypy` must be clean.
- `scripts/vendor_arras.py ../arras/build` refreshes the vendored viewer after building arras.

## License

GPL-3.0-or-later. Files under `src/loom/assets/` (`loom.sty`, the demo quilt, the AI-layer templates) are MIT so they can travel with your paper. See `LICENSE` and `NOTICE`.

# Release checklist

Applied to every tagged release of loom (book 13.5). Publishing is the maintainer's own step and is never run by a script or an agent; the list ends where it begins.

1. `uv run pytest` (unit tier on the fake toolchain), `uv run pytest -m tex` (real TeX Live, isolated), and `LOOM_PAPER_FIXTURES=... uv run pytest -m paper` (the arXiv fixtures) all green; `uv run ruff check src tests`, `uv run mypy`, and `uv run python scripts/gen_cli_reference.py --check` clean.
2. `loom check` passes on the demo (`loom init /tmp/demo --demo`), on the synthetic quilt (`tests/quilts/synthetic`), and locally on the Manolache and ACGS imports (`demos/man12`, `demos/acgs` in the workspace).
3. The conformance fixture regenerated (`docs/specs/tools/refresh-fixture.sh` in the workspace) and both vendored snapshots (`tests/fixture/` here, `tests/fixture/` in arras) equal to it; `docs/specs/tools/validate-dialect.py` passes on every fragment.
4. The book's reference figures regenerated from the viewer (`npm run shots` in `arras/`, which writes `docs/book/figures/*.png` in the workspace) whenever the chrome changed since the last release, and the new images committed.
5. The arras bundle re-vendored from an arras build at the commit the release notes name (`uv run python scripts/vendor_arras.py ../arras/build`), and `loom doctor` reports that bundle and interface version 1.
6. Every command in `README.md` and `docs/cli-reference.md` exists in this release (`scripts/gen_cli_reference.py --check`).
7. The Overleaf manual test on the demo quilt (book 14.5): zip the demo without `build/`, `refs/**/paper.pdf`, and `refs/**/src/`; upload; set `drafts/main.tex` as the main document; compile; compare with the local PDF; record Overleaf's TeX Live version and the result in the release notes.
8. `loom doctor` on a clean machine with a fresh TeX Live, following `README.md` literally (`pipx install git+...` and the `uv sync` path).
9. Versions: bump `src/loom/version.py` and `pyproject.toml` together (semantic versioning, independent of arras); record the interface version in the release notes; tag `vX.Y.Z`.
10. Publish: `uv build && uv publish` for `loomtex`. This step is the maintainer's; nothing before it publishes anything.

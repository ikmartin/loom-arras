# Agents working in loom-arras

This is the workspace for two tools, `loom` (Python, in `loom/`) and `arras` (Svelte, in `arras/`), both separate git repositories cloned here and ignored by this one. Read in this order:

1. `docs/plans/implementation-plan.md`: the approved plan, milestones M0–M7, and the working method.
2. `docs/demonstrations/README.md`: the status table. Continue with the first milestone that is not `demonstrated`.
3. `docs/book/`: the design book, the specification you implement. `docs/specs/` is the loom–arras interface and wins over the book where shapes are concerned.
4. `docs/deviations.md`: what has already been changed from the book and why.

Rules that are not negotiable:

- Never edit anything under `~/notes/`. Paper sources are copies under `tests/fixtures/`; quilts built from them live under `demos/` and are gitignored.
- Every LaTeX compile in a test runs in an isolated environment (empty HOME, TEXMFHOME, TEXMFLOCAL, TEXMFVAR, TEXMFCONFIG; no TEXINPUTS) with the quilt root as cwd, so a test never passes because of a file elsewhere on the machine.
- When implementation contradicts a `[decided]` statement, append a decision record to `docs/book/A-decision-records.md`, add a row to `docs/deviations.md`, and continue. Do not silently bypass the book.
- Author files are never modified by loom; tests enforce it.
- Prose in every file is never hard-wrapped (see `CLAUDE.md`).
- Publishing to PyPI or npm is done by the user, never by an agent.

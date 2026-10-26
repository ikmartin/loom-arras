# Contributing to loom

The design is `docs/design/` in the loom-arras workspace repository, with the formats in `docs/specs/` and the workflow in `docs/contributing.md`. The design records current thinking: a change that shows it wrong corrects it in the same pull request, and the commit message says why. A change to an entry in `docs/design/invariants.md` adds a dated line there.

- Never modify an author's file except in an incorporation the author chose (P7). The test `test_never_modifies_author_files` runs every command on every fixture quilt and fails if an author file's hash changes.
- Every new diagnostic code is added to `docs/specs/diagnostics.md` before it is emitted, and at least one test emits it.
- Every external tool is looked up on PATH so tests can substitute the fake toolchain in `tests/fake_latex/`.
- Prose in docstrings and Markdown is never hard-wrapped.

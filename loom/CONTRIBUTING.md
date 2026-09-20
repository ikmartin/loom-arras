# Contributing to loom

The specification is the design book in the loom-arras workspace repository. A change that contradicts a `[decided]` statement there needs a decision record before it is merged; a pull request says which statements of the book it implements, which it found wrong, and which were deferred.

- Never modify an author's file. The test `test_never_modifies_author_files` runs every command on every fixture quilt and fails if an author file's hash changes.
- Every new diagnostic code is added to `docs/specs/diagnostics.md` before it is emitted, and at least one test emits it.
- Every external tool is looked up on PATH so tests can substitute the fake toolchain in `tests/fake_latex/`.
- Prose in docstrings and Markdown is never hard-wrapped.

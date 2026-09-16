# Appendix E. Specification index

The interface between publishers and viewers lives in `specs/`, beside this book, in the workspace repository. This appendix maps the book's chapters to the specification files and states which document is authoritative where they overlap.

| topic | book | specification | authority |
|---|---|---|---|
| the build directory layout | 9.2 | — | book |
| fragments and their markup | 9.3, 9.4 | `specs/dialect.md` | specification |
| annotation marks in fragments | 9.5 | `specs/dialect.md` §2.9 | specification |
| the manifest | 9.9 | `specs/manifest.md` | specification |
| diagnostic codes | 5.14 | `specs/diagnostics.md` | specification |
| states and colour classes | 7.6 | `specs/manifest.md` §8 | book for meaning; specification for shape |
| threads | 11.4 | `specs/manifest.md` §10 | specification |
| the write API | 9.9, 10.4 | `specs/write-api.md` | specification (deferred) |
| the runner | 11.9 | `specs/runner.md` | specification (deferred) |
| the conformance fixture | 14.3 | `specs/fixture.md` | specification |
| interface versioning | 9.9 | `specs/README.md` | specification |

Rule: where the book describes a shape (a field, a class, a code) and a specification file defines it, the specification file wins and the book is corrected. Where the book gives meaning (what "accepted" means, what a proof owes), the book wins and the specification carries only labels.

Tools under `specs/tools/`: `validate-dialect.py` (fragment validator), `refresh-fixture.sh` (regenerates `specs/fixture/` from loom's build of the synthetic quilt). Both are test tools consumed by both repositories, not shared runtime code.

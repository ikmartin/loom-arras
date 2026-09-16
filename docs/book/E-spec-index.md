# Appendix E. Specification index

The interface between publishers and viewers lives in `docs/specs/`, beside this book's `docs/book/`, in the workspace repository. This appendix maps the book's chapters to the specification files and states which document is authoritative where they overlap.

| topic | book | specification | authority |
|---|---|---|---|
| the build directory layout | 9.2 | — | book |
| fragments and their markup | 9.3, 9.4 | `specs/dialect.md` | specification |
| annotation marks in fragments | 9.5 | `specs/dialect.md` §2.9 | specification |
| the manifest | 9.9 | `specs/manifest.md` | specification |
| diagnostic codes | 5.14 | `specs/diagnostics.md` | specification |
| states and colour classes | 7.6 | `specs/manifest.md` §8 | book for meaning; specification for shape |
| threads | 11.4 | `specs/manifest.md` §10 | specification |
| the write API | 9.9, 10.4 | `specs/write-api.md` | specification (deferred; specified, not built) |
| the runner | 11.9 | `specs/runner.md` | specification (deferred; specified, not built) |
| the conformance fixture | 14.3 | `specs/fixture.md` | specification |
| interface versioning | 9.9 | `specs/README.md` | specification |

Rule: where the book describes a shape (a field, a class, a code) and a specification file defines it, the specification file wins and the book is corrected. Where the book gives meaning (what "accepted" means, what a proof owes), the book wins and the specification carries only labels.

Tools under `specs/tools/`, both test tools consumed by both repositories, not shared runtime code:

- `validate-dialect.py`: the fragment validator for interface version 1. It checks the envelope (no page shell, scripts, styles, iframes, or forms), the element and class vocabulary, that block elements from source carry `data-src`, that inclusions carry `data-key`, and that no absolute URL appears outside `a.url` and `img[src]`; exit 1 on any problem. `refresh-fixture.sh` runs it on the regenerated fixture, and loom keeps a copy at `tests/tools/validate_dialect.py` that `test_fragment_kinds_and_dialect_validity` runs on every build of the synthetic quilt.
- `refresh-fixture.sh`: regenerates `specs/fixture/` from loom's build of `loom/tests/quilts/synthetic`. It compiles both masters and builds with the real toolchain in an isolated environment (empty HOME and TeX trees) with `LOOM_FIXED_TIME` set so timestamps are fixed, copies `manifest.json`, `fragments/`, `svg/`, and `diffs/` into `specs/fixture/`, writes `VERSION` (the interface version, the loom version, the fixed time), vendors the result into `loom/tests/fixture/` and `arras/tests/fixture/`, and validates the fragments.

`specs/fixture/` is generated, never edited by hand. At the end of M7 it holds the manifest, 29 fragments (nodes, masters, digests, and one qualified key), one SVG asset, five diffs, and `VERSION` reading interface 1, loom 0.1.0.dev0. Loom's TeX-tier `test_fixture_matches_vendored` rebuilds it and compares; arras's Playwright suite renders the vendored copy.

The diagnostic codes have a second table in code: `loom/src/loom/scan/diagnostics.py` mirrors `specs/diagnostics.md` code for code (47 at the end of M7), and `test_all_emitted_codes_are_known` fails if a fixture quilt emits a code that is not in it. `specs/diagnostics.md` §4 requires the specification entry before the code is emitted; `loom:interface-version` is listed there though only the viewer emits it.

# Loom and Arras: Design Book

Internal design documentation for `loom` (a tool for atomized mathematical development), `arras` (a viewer for node-based text corpora), and the `quilt` (the directory contract between an author and loom).

Status: implemented, and this book describes what is implemented. Everything in it was decided in design conversations before a line of code existed, implemented between 2026-09-15 and 2026-09-16 following Chapter 13 milestone by milestone, extended on 2026-09-16 by the round recorded in `docs/reports/record-2026-09-16.md`, which built Chapter 15, added the `see:` relation and the brainstorm mode, and produced the three editor clients of Chapter 16, and extended again on 2026-09-17 by the round recorded in `docs/reports/record-2026-09-17.md`, which built the workbench of Chapter 17. Every deviation the implementation made is a decision record in Appendix A with one row each in `docs/deviations.md`; what each milestone demonstrated, with its commands, output and test counts, is in `docs/work-queue/closed/`. **What is not built is not in this book.** Work that remains — from a feature nobody has needed yet to the Overleaf check and the external user's paper — lives in `docs/work-queue/`, one file per item, each carrying an observable trigger that says when it becomes worth doing.

## How to read this book

The book is a specification, not an essay. Rules are stated with "must", "should", and "never". Each rule is followed by an example. Arguments for decisions are kept to a sentence; the reasoning lives in Appendix A (decision records).

Normative statements carry one marker:

- **[decided]** : this is what loom does. It is the contract, not a plan; changing it is a decision-record event, which means a record in Appendix A and a row in `docs/deviations.md`.

Unmarked statements are definitions, consequences, or explanation.

There was formerly a marker for a drafter's default and another for a question implementation would settle. Both are gone: every statement they marked has been settled and rewritten as what is, or moved to `docs/work-queue/` as an item with a trigger. `docs/work-queue/check.py` fails if either marker reappears here, because a book that describes the implementation cannot also carry its wishes (DR-107).

## Conventions

- The tool is `loom`; its PyPI distribution is `loomtex`. The viewer is `arras`. The project directory is a quilt.
- Command lines are shown as `loom <verb>`. Output shown after a command is illustrative, not byte-exact.
- File paths are relative to the quilt root unless stated.
- LaTeX examples are complete enough to compile with the stated preamble.
- "The scanner" means the part of loom that reads a quilt and produces the manifest. "The publisher" means the part that writes the build directory. Both are loom.
- Identifiers in examples use the prefix `rl` (from the relative localization paper) and the citekey `Man12` (Manolache, virtual pullbacks). They are examples, not requirements.

## Contents

Chapters (`book/`):

1. Design philosophy
2. Objectives
3. Vocabulary
4. The quilt
5. The source contract
6. Bringing a paper in
7. Review
8. Digests
9. Build and interface
10. Arras
11. The AI layer
12. CLI reference
13. The plan
14. Tests
15. Arras layout
16. Editor clients
17. The workbench

Appendices (`book/`):

- A. Decision records
- B. Open questions
- C. Mode templates
- D. `ai/orientation.md`
- E. Specification index
- F. Colophon

Source (`source/`):

- `global-rules.md` : the author's chat review rules, verbatim
- `global-rules-mapping.md` : each part mapped to its loom destination

Specifications (`specs/`):

- `README.md` : index and versioning
- `dialect.md` : the semantic HTML dialect
- `manifest.md` : the manifest schema
- `diagnostics.md` : diagnostic codes
- `write-api.md` : the write API (deferred)
- `runner.md` : the runner contract (declined, kept as a design)
- `fixture.md` : the conformance fixture
- `tools/` : `validate-dialect.py` and `refresh-fixture.sh`
- `fixture/` : the generated conformance fixture, vendored into both tool repositories

## Licenses

- `loom`: GPL-3.0-or-later.
- `arras`: AGPL-3.0-or-later.
- `loom.sty` and the demo quilts: MIT, so that they can travel with an author's paper.
- This book and the specifications: the same license as the repository they live in (the workspace repository).

Copyright holder: ikmartin (DR-39's milestone decision at M0: every `LICENSE` and `COPYRIGHT` names ikmartin). Contributions are accepted under the same licenses. If a repository's `LICENSE` file differs from the above, it is replaced.

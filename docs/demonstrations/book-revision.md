# Book revision

## Book says

The final step of the plan: walk the deviations log, edit each chapter to describe the implemented behaviour citing its decision record, re-mark settled `[assumed]` and `[deferred]` statements, replace chapter 12 with the generated CLI reference and chapter 14's lists with the actual test ids, update the specifications for every additive interface change, regenerate Appendix B, and update the front matter and colophon.

## What was done

Chapters 4 to 11, 13, 14, the front matter, the colophon, and the spec index were revised by five agents working in parallel on disjoint files, each reading the deviations table, decision records DR-39 to DR-80, the demonstration records, and the code, and each reporting what it changed and what it could not verify. Chapter 12's hand-written command sections were replaced by the reference generated from the command tree (35 commands), with 12.1's conventions and 12.10's environment variables brought up to date. The specifications gained the seven diagnostic codes the implementation had added without a spec entry plus `loom:unknown-config-key`, the fixture's actual contents, the validator's settled status, and the threads and references fields as published. Appendix B was regenerated from the chapters' "Open questions" sections (40 questions remain open). Every row of `docs/deviations.md` is marked as reflected in the book.

The agents' reports surfaced eight things the code or the records had wrong, each fixed in the same pass: `digest import` never remapped environments (DR-81 records it; DR-69's clause about import was wrong); the ingest mode file said labels take the citekey where the id rule takes its slug; `ai check` did not in fact exclude the files `loom ai promote` logged (the exclusion is now real and tested); unknown `config.toml` keys were collected but never warned (`loom:unknown-config-key`); a duplicated digest-shaped id was reported under `loom:duplicate-label`; a loose file's reference to another loose file's node produced no `loom:reference-to-loose` info; `import` checked only the master for `\usepackage{loom}`; `atomize` did not refuse a node containing `\include`. Two statements were found unimplemented and are recorded: `build/derived/` files are not written (DR-82) and `% !TEX root` is parsed but not consumed (marked deferred). A relative `--run` path was resolved against the shell's directory rather than the quilt root, which had left a copy of the migrated paper's run directories at the workspace root; the copy was removed from the working tree, the path now resolves against the quilt, and the stray files remain in the workspace repository's local history (commit 136ff8f), which has never been pushed.

## Tests

| repo | tier | count | command |
|---|---|---|---|
| loom | unit (shim) | 186 | `uv run pytest tests/unit` |
| loom | tex | 10 | `uv run pytest -m tex` |
| loom | paper | 4 | `LOOM_PAPER_FIXTURES=… uv run pytest tests/papers` |
| arras | unit | 10 | `npm run test:unit -- --run` |
| arras | e2e | 27 | `npm run test:e2e` |

Every one of the 48 diagnostic codes in `docs/specs/diagnostics.md` is registered in loom's table and asserted by a test.

## Deviations recorded

- DR-81 (`digest import` does not remap environments), DR-82 (derived region files not written), DR-83 (mechanisms that differ from the book without changing a decision).

## Blocked on the user

- The workspace repository's remote and the question of purging commit 136ff8f from its local history before it is ever pushed.

## Status

Done 2026-09-16.

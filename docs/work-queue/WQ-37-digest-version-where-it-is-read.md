# WQ-37 · A digest's version shown where an agent reads it

**Repo:** loom

## Trigger

An agent files an objection on a digest node whose discrepancy `loom:unverified-locators` already explains. **Fired 2026-09-19**: plan 0.12's fourth study iteration (report §2 E, finding R1-3).

## Why deferred

The study was stopped before the fix could be applied and tested. `loom:unverified-locators` says a digest was extracted from a preprint while the bibliography cites the published version, and since DR-181 it fires for 11 of the study's 16 digests. But only `loom lint` prints it. An agent reading Chang–Kiem–Li's digest through `refs coverage`, `refs overview` and `loom source` re-found the preprint's numbering, filed it as an extraction bug, and never saw the line that explained it.

## Rough design

Drafted in the session record as `patch_version.py`: `scan.digests.other_version` shared by the lint and three surfaces. `refs coverage` marks such a digest `preprint` and says why under the table (and in `--json`); `loom source` and `refs overview` of its nodes print one line naming both versions and pointing at `loom refs page`.

## Blast radius

`scan/digests.py`, `scan/lint.py`, `cli/refs.py` (coverage, overview), `cli/build_cmds.py` (source); tests in `tests/unit/test_refs_layer.py`.

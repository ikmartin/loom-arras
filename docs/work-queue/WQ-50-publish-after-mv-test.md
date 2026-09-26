# WQ-50 · A committed test that a publish after `loom mv` keeps Overleaf's file name

**Repo:** loom

## Trigger

The next change to how sync maps Overleaf's main to a local document (`_selection` and `source_projection` in `loom/src/loom/sync.py`), or to `loom mv`, whichever comes first.

## Why deferred

The behaviour is right today: plan 0.16's phase 5 checked it with a throwaway test (after `loom mv drafting/main.tex drafting/paper.tex`, `loom sync publish` pushes `drafting/main.tex` with `paper.tex`'s bytes, and an accepted key stays fresh), and the neighbouring cases are committed — a linearized main and an exact rename at a pull, in `tests/unit/test_sync.py`. Nothing guards this one case until one of the two pieces of code it runs through changes, which is the moment a guard pays for itself.

## Rough design

One test in `loom/tests/unit/test_sync.py`, beside `test_sync_follows_a_linearized_main_and_overleaf_keeps_its_file_name` and built from the same fixture: configure sync, accept a key, `loom mv drafting/main.tex drafting/paper.tex`, commit, publish; assert the pushed tree holds `drafting/main.tex` with `paper.tex`'s bytes and no `paper.tex`, that the sync record's `master` is unchanged, and that the key is fresh.

## Blast radius

`loom/tests/unit/test_sync.py` only.

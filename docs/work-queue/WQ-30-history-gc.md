# WQ-30 · `loom history gc`

**Repo:** loom

## Trigger

`.loom/history/texts/` exceeds a few thousand files or fifty megabytes, or `git status` on a quilt is visibly slowed by it.

## Why deferred

Anchors are frozen on edit, only for texts an annotation points at, and deduplicated by hash, so a busy year is tens of megabytes of compressible text. The cost that would matter is repository noise rather than disk, and no quilt has produced enough annotated-then-edited text to show it.

## Rough design

`loom history gc` lists, then with `--apply` removes, anchors that no annotation references and no step includes — an annotation discarded, or a run deleted, leaves its anchors behind. Never automatic; loom deletes only what a person named, and prints what it would delete first. Canon steps and stamps are never candidates.

## Blast radius

`loom/src/loom/records/` (the anchor store), one command, Chapter 7.

## Related

[[WQ-26]] (closed; absorbed into [plan 0.11](../plans/0.11-run-review-view.md)), whose discard action is what creates the garbage.

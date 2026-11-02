# WQ-30 · `loom history gc`

**Repo:** loom

## Trigger

`.loom/history/texts/` exceeds a few thousand files or fifty megabytes, or `git status` on a quilt is visibly slowed by it.

## Why deferred

Anchors are frozen on edit, only for texts an annotation points at, and deduplicated by hash, so a busy year is tens of megabytes of compressible text. The cost that would matter is repository noise rather than disk, and no quilt has produced enough annotated-then-edited text to show it.

Since plan 0.22.8 a person's look stores there too: the text of every open file that has changed since the last look, each time they keep a change, and the text an undo replaces. Still deduplicated, but it now grows with a quilt's edits as well as its annotations. Relloc's held 47 files, 856 KB, on 2026-11-02.

## Rough design

`loom history gc` lists, then with `--apply` removes, texts that no annotation references, no step includes, no person's current look names and no `undo` line names — an annotation discarded, a run deleted, or a look moved past a file's old text leaves texts behind. Never automatic; loom deletes only what a person named, and prints what it would delete first. Landmarks and stamps are never candidates.

## Blast radius

`loom/src/loom/records/` (the anchor store), one command.

## Related

[[WQ-26]] (closed; absorbed into [plan 0.11](../plans/0.11-run-review-view.md)), whose discard action is what creates the garbage.

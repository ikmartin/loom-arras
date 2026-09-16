# WQ-06 · Machine-global cache for fetched sources

**Repo:** loom

## Trigger

`refs/src/` across all quilts on one machine exceeds a few GB — check with `du -sh` across the quilts in use.

## Why deferred

With one or two quilts holding a handful of fetched papers each, per-quilt storage costs nothing and a shared cache is pure indirection.

## Rough design

Fetched bytes — arXiv tarballs, PDFs — move to a content-addressed store outside any quilt, keyed by the global id from [[WQ-01]] and shared by every project on the machine. `refs/<citekey>/` becomes a thin binding into it. This is plumbing with no design tension; the only reason it waits is that it buys nothing at current volume.

It becomes necessary rather than nice at the scale [[WQ-02]] implies: 50,000 works is roughly 150 GB, which wants a configurable root on an external disk and certainly not one copy per quilt.

Distinguish it from [[WQ-03]]: that shares *digests*, which are small, authored and valuable. This shares *bytes*, which are large, licence-encumbered and disposable. The second is a cache; the first is a dependency.

## Blast radius

`refs/` layout, `loom digest fetch`, `.gitignore` (the store leaves the quilt entirely), `loom doctor`, Chapter 8, Chapter 4 §4.7.

## Related

[[WQ-01]], [[WQ-02]], [[WQ-03]].

# WQ-06 · A shared cache for fetched bytes

**Repo:** loom

## Trigger

`refs/` across all quilts on one machine exceeds a few GB — `du -sh` across the quilts in use — or a quilt needs its fetched bytes on another disk.

## Why deferred

With one or two quilts holding a handful of fetched papers each, per-quilt storage costs nothing and a shared cache is pure indirection.

## Rough design

**`[refs] cache = "/Volumes/big/loom"`** — a setting saying where fetched bytes physically live, implemented with hardlinks or a redirect at fetch time. Nothing else changes: `refs/<scheme>/<id>/` stays the quilt's way of referring to a fetched work at every scale, from a three-reference note to a fifty-thousand-work corpus.

This item previously proposed a machine-global *store*: a second kind of place, outside any quilt, with its own keying rules. That was wrong, and the reason is worth keeping. A store would have been the library-quilt/project-quilt distinction in disguise — two kinds of thing where the design deliberately has one. Everything is a quilt, quilt concepts work at any size, and where the bytes sit is configuration rather than ontology.

Plan 0.5 did the part that made this easy: `refs/` is keyed by global id, so two quilts citing the same work already name the same directory and deduplication is a hardlink rather than a mapping layer.

Distinguish it from [[WQ-03]]: that shares *digests*, which are small, authored and valuable, and never deduplicate because two people's digests of one paper are different documents. This shares *bytes*, which are large, licence-encumbered and disposable, and deduplicate exactly. One is a dependency; this is a cache.

## Blast radius

`loom/src/loom/digest/fetch.py`, `config.toml`'s `[refs]` table, `loom doctor` (reporting where the cache is and how large), Chapter 8 §8.9, Chapter 4 §4.2.

## Related

[[WQ-02]] (whose 150 GB at depth 5 is what makes this necessary rather than tidy), [[WQ-03]]; plan 0.5, which established the global-id keying.

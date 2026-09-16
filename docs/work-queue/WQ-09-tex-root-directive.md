# WQ-09 · `% !TEX root` recorded for loose files

**Repo:** loom

## Trigger

A loose file needs to name the master it was written for — a quilt where loose files outnumber reached ones, or an author asking why their editor's root and loom's disagree.

## Why deferred

The directive is already parsed (`loom/src/loom/scan/directives.py`) and nothing consumes it; the manifest has no field for it. Adding a field no viewer reads and no diagnostic uses would be a shape asserted ahead of a need.

## Rough design

A file that is not a master and carries `% !TEX root = <path>` in its first twenty lines is recorded as belonging to that master, so a loose file can say which master it was written for **without changing reachability** — that last clause is the whole point, and it is why this is not simply an inclusion.

Related and separate: whether Overleaf honours `% !TEX root` for main-document selection is unknown, and the README instructs setting the main document in Overleaf's menu regardless. That question belongs to [[WQ-16]].

## Blast radius

`loom/src/loom/scan/directives.py` (parsing exists), the manifest (a new optional field, additive), Chapter 5 §5.2, `docs/specs/manifest.md`.

## Related

Chapter 5 §5.2; [[WQ-16]].

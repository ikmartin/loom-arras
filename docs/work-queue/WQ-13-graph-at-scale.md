# WQ-13 · Graph layout precomputed by the publisher

**Repo:** loom, arras

## Trigger

A quilt's graph exceeds roughly 2000 nodes, or the force layout takes more than a second to settle — measurable in the viewer, and the end-to-end timing assertions already in `arras/tests/e2e/` would catch the second.

## Why deferred

The ACGS fixture is the largest real graph available and the client-side force layout handles it. Precomputing layout means the manifest carries geometry, which is a shape the interface should not grow until something needs it.

## Rough design

The publisher computes a layout and the manifest gains **optional** layout hints — optional so the interface version does not change and a viewer without them falls back to computing its own. The viewer prefers hints when present.

Distinguish from [[WQ-05]]: that decides *what* is drawn (results, or papers contracted); this decides *where the coordinates come from*. A corpus large enough to need one usually needs both.

## Blast radius

`loom/src/loom/render/manifest.py`, `docs/specs/manifest.md` (additive), `arras/src/lib/` graph components, Chapter 10 §10.6, Chapter 15 §15.5.

## Related

Chapter 10; [[WQ-05]]; DR-96 (the force layout's self-dependent effect, fixed during 0.3).

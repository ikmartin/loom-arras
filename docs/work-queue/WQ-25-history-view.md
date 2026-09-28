# WQ-25 · The history view in arras

**Repo:** arras, loom

## Trigger

A quilt that is not a fixture or a demo holds three or more landmarks (an import, or a stamp given a document, book 17.9). Before that there is no history worth a view: one step is a copy, two is a diff you can read in git. The synthetic quilt holds three on purpose, to have something for the manifest and the badge to be built against; a trigger a fixture can fire is not a signal.

## Why deferred

The history exists first in loom (plan 0.9, built 2026-09-17); a view of it is worth designing against a real ledger rather than an imagined one, and the manifest fields it needs — each key's version list, each step's entry — are cheap to add once the ledger's shape has survived a few weeks of use. The seeds are already published: `keys[k].version` and the "text of @N" badge; the landmarks, which plan 0.17.3 made stamps that keep their document's text, listed under Landmarks in the panel and opened as documents; and compare (plan 0.17.4), which already reads a landmark against today or another landmark.

## Rough design

One view, three settings, decided with the author on 2026-09-17:

- **Landmarks** (default): the steps that keep a document's text only (`loom stamp DOC -m NAME`, book 17.9), as labelled major ticks, each opening the landmark the panel's Landmarks subsection already lists and offering compare against today. What a coauthor or referee opening a shared quilt expects — versions of the paper.
- **Working history**: landmarks plus stamps as minor ticks; the slider snaps to landmarks and steps through stamps when zoomed. What the author opening their own quilt expects.
- **Everything** (deferred within the deferred): the annotation log's events layered on the timeline, so a step shows what stood against the versions it replaced.

Per node: cycle a key's versions (`rl-0001@1 … @n`), each shown as a diff against the head, with a proof version displayed beside the statement version it records as `of:`. The graph drawings (15.5) drawn at a step, or with a step's additions and changes lit. Nothing here writes: `loom revert` is the write, and it is a command.

A node item that opens a recorded version, addressed `/node/<key>@<step>` and typeset with that version's macros, is the smallest piece of this view and the one compare waits on: compare's design pairs two versions of one key with a base (compare-study §3), and plan 0.17.4 left it here, since nothing opens `key@N` until this view exists.

The "text of @2" badge on a node is built with the workbench plan and is the seed of this view.

## Blast radius

`docs/specs/manifest.md` (a `history` block: steps and per-key version lists, additive), `loom/src/loom/render/manifest.py`, a new arras route and a control on the node page and the graph page, Chapter 15.

## Related

[[WQ-23]] (closed; absorbed into [plan 0.11](../plans/0.11-run-review-view.md)) for the split view, whose left pane is a versioned text; [WQ-29](WQ-29-node-manager.md), which forks from this view; [compare](../reports/compare-study.md), which compares two versions once a node item can show one.

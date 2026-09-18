# WQ-28 · An annotated view as LaTeX and PDF

**Repo:** loom, arras

## Trigger

A review has to reach someone who cannot run arras — a coauthor or a referee reading the marked-up section outside the viewer.

## Why deferred

The author's review mode grew out of a chat pattern that produced a LaTeX/PDF pair with criticisms inlined in red. In loom the durable form is annotations on the text, and arras renders them live, which the author prefers; the compiled pair was declined as a run artifact on 2026-09-17. Some readers will want it, and it is cheap once the annotations carry severity and payloads.

## Rough design

`loom export REVIEW` (name open): the target's text with each annotation inlined in red at its anchor — numbered `[R1]…` in report order, grouped by severity at the top, payloads shown as the suggested text — compiled through the bundle machinery so it stands alone. One command, no state.

## Blast radius

`loom/src/loom/tex/bundle.py` (a second document shape), `loom/src/loom/ai/` (the report's numbering), a menu entry in arras's run pane.

## Related

[WQ-26](WQ-26-annotation-surfaces.md); the review mode of plan 0.10.

# WQ-28 · An annotated view as LaTeX and PDF

**Repo:** loom, arras

## Trigger

A review has to reach someone who cannot run arras — a coauthor or a referee reading the marked-up section outside the viewer.

## Why deferred

The author's review mode grew out of a chat pattern that produced a LaTeX/PDF pair with criticisms inlined in red. In loom the durable form is annotations on the text, and arras renders them live, which the author prefers; the compiled pair was declined as a run artifact on 2026-09-17. Some readers will want it, and it is cheap now that annotations carry types and suggested edits are a record of their own (plan 0.30).

## Rough design

`loom export REVIEW` (name open): the target's text with each annotation inlined at its anchor — numbered `[R1]…` in report order, grouped by type at the top, each in its colour, and suggested edits shown as the text they propose — compiled through the bundle machinery so it stands alone. One command, no state.

## Blast radius

`loom/src/loom/tex/bundle.py` (a second document shape), `loom/src/loom/ai/` (the report's numbering), a control in the viewer where a review's annotations are read (a document's `view ▾`, or Review).

## Related

[[WQ-26]] (closed; absorbed into [plan 0.11](../plans/0.11-run-review-view.md)); the review mode of plan 0.10.

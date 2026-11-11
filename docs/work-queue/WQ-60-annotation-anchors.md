# WQ-60 · Annotation anchors: a mark from the source span, a re-anchor, and saying where a mark landed

**Repo:** loom, arras

## Trigger

An annotation drawn at block level that its writer meant for a phrase, seen in use; or an agent that has to discard a finding and file it again only to move its quote.

## Why deferred

The anchoring critique found quotes `annotate` accepted marked as their whole paragraph or section. DR-334-ikmartin fixed its causes for the TeX `selectors.project` reads -- one reading of a quote at write time and at placement, and a paragraph's span starting at `\noindent` -- which covers every case the critique saw. What is left is structural and is not needed until a quote outside that reading turns up: a `\end{…}`, a macro of the quilt's own, a quote across an argument TeX prints otherwise than it is written.

## Rough design

- **Marks from the source span.** A comparison already marks its changed words from source offsets, aligning each word TeX printed with the source word it came from (`mark_changes` in `render/changes.py`), and a block shown as its source is marked at the quote's own offsets. Mark each annotation's resolved span and id the same way and delete `_locate`'s text search in `render/marks.py`; a formula, a reference and a display keep their whole-element rules. Nothing is matched a second time, so any quote `annotate` accepts is drawn where it is.
- **Re-anchoring.** `annotate --edit ID --quote NEW` records an `edited` event carrying a new selector, which replay adopts; the log keeps the old one. Today `--edit` refuses `--quote`, and moving an anchor means a new annotation.
- **Where a mark landed.** `ai annotations --json` carries each mark's placement (inline, block, none) under a name that is not `placement`, which is the payload's; `loom lint` warns on a block-level mark. Lint does not render, so the build would record placements for lint to read.
- **A replacement longer than its anchor.** A suggestion that replaces a paragraph has to quote the paragraph, so its highlight is the paragraph. Either a placement that names the enclosing paragraph, or a replaced range given separately from the anchor.

## Blast radius

`render/changes.py`, `render/marks.py`, `render/build.py`, `records/log.py`, `cli/review.py`, `cli/ai.py`, the lint diagnostics; the dialect if a placement is published; arras only if mark markup changes shape.

## Related

DR-334-ikmartin; WQ-59, now [plan 0.21](../plans/0.21-mcp.md), phase 0.21.4.

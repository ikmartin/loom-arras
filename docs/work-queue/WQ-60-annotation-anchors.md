# WQ-60 · Annotation anchors: a mark from the source span, a re-anchor, and saying where a mark landed

**Repo:** loom, arras

## Trigger

An annotation drawn at block level that its writer meant for a phrase, seen in use; or an agent that has to discard a finding and file it again only to move its quote.

## Why deferred

The anchoring critique found quotes `annotate` accepted marked as their whole paragraph or section. DR-334-ikmartin fixed its causes for the TeX the converter knows -- one reading of a quote at write time and at placement, and a paragraph's span starting at `\noindent` -- which covers every case the critique saw. What is left is structural and is not needed until a quote outside that reading turns up: a `\end{…}`, a macro of the quilt's own, a quote across an argument the converter rewrites.

## Rough design

- **Marks from the source span.** The converter already wraps source-offset spans as it renders (`highlight_spans` in `Converter._prose`, used by review compare). Pass each annotation's resolved span and id the same way and delete `_locate`'s text search in `render/marks.py`; a formula, a reference and a display keep their whole-element rules, reimplemented where the converter draws each. Nothing is matched a second time, so any quote `annotate` accepts is drawn where it is.
- **Re-anchoring.** `annotate --edit ID --quote NEW` records an `edited` event carrying a new selector, which replay adopts; the log keeps the old one. Today `--edit` refuses `--quote`, and moving an anchor means a new annotation.
- **Where a mark landed.** `ai annotations --json` carries each mark's placement (inline, block, none) under a name that is not `placement`, which is the payload's; `loom lint` warns on a block-level mark. Lint does not render, so the build would record placements for lint to read.
- **A replacement longer than its anchor.** A suggestion that replaces a paragraph has to quote the paragraph, so its highlight is the paragraph. Either a placement that names the enclosing paragraph, or a replaced range given separately from the anchor.

## Blast radius

`render/convert.py`, `render/marks.py`, `render/build.py`, `records/log.py`, `cli/review.py`, `cli/ai.py`, the lint diagnostics; the dialect if a placement is published; arras only if mark markup changes shape.

## Related

DR-334-ikmartin; [WQ-59](WQ-59-regrade-partials.md).

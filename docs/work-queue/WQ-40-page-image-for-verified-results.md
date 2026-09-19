# WQ-40 · The page image beside a verified result

**Repo:** loom, arras

## Trigger

A verified result is found wrong after verification: a reader, the author or an agent disagrees with its rendering and has to open the PDF to settle it.

## Why deferred

DR-179 renders the anchor page only for pending proposals: a handful of pages, cached, about 135 KB each. A verified result's image would serve a reader checking a citation later, at the cost of rendering every anchored page on every fresh build. In the study the author's text-only edits were wrong twice in seven, and those are now verified results whose only defence was the image.

## Rough design

Render lazily: the page image of a verified result is produced on first request by `loom serve` and cached in `build/pages/`, never in a static build unless asked for with a flag.

## Blast radius

`render/serve.py`, `refs/images.py`, the digest page in arras.

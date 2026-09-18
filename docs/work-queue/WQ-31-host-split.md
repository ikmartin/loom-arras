# WQ-31 · The host split: the core behind a component API a person can use by hand

**Repo:** arras, loom-arras

## Trigger

A second host exists or is wanted: something other than the application shipped beside the publisher must render a corpus, or the same corpus must be made to look like a different site.

## Why deferred

There is one host today, and an API with one consumer is a cost with no reader — its shape would be decided by its only caller, which is the same failure as an interface shaped around its first publisher. The view set has to settle first as well: [0.11](../plans/0.11-run-review-view.md) adds a view, and extracting a component API around a list that is about to change means extracting it twice.

## Rough design

R3 of [plan 0.9.5](../plans/0.9.5-arras-refactor-interjection.md), whose sections 1 to 3 and 8 are the constraints and are normative. Seam 2: the core — loading, wiring, typesetting, and the derivations in `badges.ts`, `graph/layout.ts`, `contents.ts`, `reached.ts` — behind a component API and a token contract, with the application shipped beside the publisher as its first host.

The requirement that fixes the shape: **a person must be able to build a site with this by hand** — an editor, HTML and CSS, no framework and no agent. Concretely, each item being the platform's own answer rather than one of ours:

- custom elements (`<arras-note key="…">`), compiled with `shadow: 'none'` so the host's CSS still applies and one MathJax font cache serves the page;
- no build step required: a `<script type="module">` and an element are enough;
- ordinary CSS against documented class names and custom properties, with normal specificity;
- real URLs: anchors that survive a middle click, a bookmark and the back button;
- progressive enhancement over the fragments, which are already semantic HTML;
- an npm package with an `exports` map, beside the vendored bundle rather than replacing it;
- documentation whose first example is a short HTML file someone can paste into an editor and open.

R1 has already done the part this depends on: every URL the core emits is composed from a base path and a data root rather than written (10.8.1, DR-143), and `tests/unit/host-neutrality.spec.ts` keeps it that way.

## Blast radius

Everything under `arras/src/lib/` and both shells; the packaging (`package.json` exports, the bundle loom vendors); Chapters 10.1, 10.8.1 and 15; a decision record for the API's shape.

## The check to write first

The one that will otherwise be quietly dropped: a single hand-written HTML file — a script tag, a stylesheet of the author's own, and one element — renders a node from a build directory on a static server, with no build step, no framework and nothing generated. If that file needs anything this repository has to explain, seam 2 is not finished.

## Related

[WQ-26](WQ-26-annotation-surfaces.md), which adds surfaces a second host would also want; [plan 0.9.5](../plans/0.9.5-arras-refactor-interjection.md) §§1–3, 8, which this item does not restate.

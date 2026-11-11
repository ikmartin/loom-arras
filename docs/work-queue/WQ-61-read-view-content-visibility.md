# WQ-61 · The read view's blocks skipped while off screen

**Repo:** arras

## Trigger

A way to keep the reader's place when a block skipped above them changes size, shown on relloc: ten annotations filed above a reader at 60% of the paper leave the text at the pane's top within 4 px.

## Why deferred

Plan 0.19.3 tried `content-visibility: auto` on the read view's leaf blocks (paragraphs, displays, lists, tables, figures), and it was the largest gain in the plan: a divider move went from 38 ms to 15 ms of work (a move no longer lays the documents out at all, DR-341-ikmartin), a return to a document from 353 ms to 145 ms, a change of size or format from 191 and 258 ms to 75 and 57 ms, a cold load from 1,244 to 884 ms. It failed the plan's own criterion on the reader's place: with blocks skipped, the text at the pane's top moved by up to 1,700 px across ten annotations patched in above it, where without them it held at 0. Carrying each replaced block's measured size into its replacement as `contain-intrinsic-size` did not stop it, so the movement is the browser's scroll anchoring under skipped content rather than a placeholder of the wrong size. Reverted, DR-337-ikmartin.

The need has grown with TeX4ht pages. Relloc's agent copy of `examples.tex` read from its page is 333,000 elements once its 11,800 formulas are typeset. In headless Chromium a scroll down it ran at 30 fps with 110–125 long tasks per hundred wheel steps; with `content-visibility: auto` on its leaf blocks it ran at 60 fps with 3–4.

## Rough design

Find what moves: trace a patch above a skipped region and see which anchor the browser chooses and why its compensation is wrong. Candidates: pin the anchor by hand around a patch (record the block at the pane's top and its offset, patch, restore the offset, as the pane's own restore already does); skip whole sections rather than leaf blocks, so the anchor is never inside a skipped region; or exempt the blocks a patch touches from skipping until they have been on screen once. The live perf suite that measured the place directly (`tests/perf-live/live.e2e.ts`, the text at the pane's top) was deleted on 2026-10-26, unrun; it is in git history at `3de1c0bc`, and restoring it makes each candidate one run.

DR-174's clipping has an answer to try: `overflow-clip-margin` widens the clip that `content-visibility` brings, and in Chromium 153 a box hung left of a skipped-capable block painted again with it. Whether a click reaches the hung box, and what Safari does, are unchecked; guarding the rule with `@supports (overflow-clip-margin: 1px)` leaves a browser without it as it is now.

## Blast radius

`arras/src/lib/theme.css`, `arras/src/lib/fragments/patch.ts` or `Fragment.svelte`; DR-174's clipping concerns apply to anything that leaves a block's box (`.node-margin`, a gutter comment), and layout containment makes each block the containing block of any `position: fixed` element inside it.

## Related

DR-174, DR-336-ikmartin, DR-337-ikmartin; plan 0.19; `docs/reports/viewer-speed-study.md`.

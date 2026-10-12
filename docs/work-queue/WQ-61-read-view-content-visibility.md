# WQ-61 · The read view's blocks skipped while off screen

**Repo:** arras

## Trigger

A way to keep the reader's place when a block skipped above them changes size, shown on relloc: ten annotations filed above a reader at 60% of the paper leave the text at the pane's top within 4 px.

## Why deferred

Plan 0.19.3 tried `content-visibility: auto` on the read view's leaf blocks (paragraphs, displays, lists, tables, figures), and it was the largest gain in the plan: a divider move went from 38 ms to 15 ms of work (a move no longer lays the documents out at all, DR-341-ikmartin), a return to a document from 353 ms to 145 ms, a change of size or format from 191 and 258 ms to 75 and 57 ms, a cold load from 1,244 to 884 ms. It failed the plan's own criterion on the reader's place: with blocks skipped, the text at the pane's top moved by up to 1,700 px across ten annotations patched in above it, where without them it held at 0. Carrying each replaced block's measured size into its replacement as `contain-intrinsic-size` did not stop it, so the movement is the browser's scroll anchoring under skipped content rather than a placeholder of the wrong size. Reverted, DR-337-ikmartin.

## Rough design

Find what moves: trace a patch above a skipped region and see which anchor the browser chooses and why its compensation is wrong. Candidates: pin the anchor by hand around a patch (record the block at the pane's top and its offset, patch, restore the offset, as the pane's own restore already does); skip whole sections rather than leaf blocks, so the anchor is never inside a skipped region; or exempt the blocks a patch touches from skipping until they have been on screen once. The live perf suite measures the place directly (`tests/perf-live/live.e2e.ts`, the text at the pane's top), so each candidate is one run.

## Blast radius

`arras/src/lib/theme.css`, `arras/src/lib/fragments/patch.ts` or `Fragment.svelte`; DR-174's clipping concerns still apply to anything that leaves a block's box.

## Related

DR-174, DR-336-ikmartin, DR-337-ikmartin; plan 0.19; `docs/reports/viewer-speed-study.md`.

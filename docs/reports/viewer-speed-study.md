# Viewer speed: a study

Measured on 2026-10-11, after the author reported that "everything is incredibly laggy, even moving the dividing line in split view". The question is where the time goes, and what to change first.

## Method

A copy of `demos/relloc` was made in a scratch directory and deleted afterwards; the original was not touched. Into the copy went what the demo lacks and the author's quilt has: 40 quote-anchored annotations of every kind, 10 replies and 8 resolutions filed through `loom annotate`, a session, and a 34-page PDF filed for one work (the paper's own compiled PDF, with `--force`; `library add` was run with the agent markers unset, as `arras/tests/served.ts` runs loom). The copy was built and served by `loom serve --no-compile`, which serves the vendored arras bundle (838ee1d), exactly what the author runs.

The paper is `main-atomic`: 316 nodes, 1,247 formulas, 43,800 elements and about 85,000 DOM nodes once typeset.

Each action ran in a fresh browser context in Chromium (Playwright 1.63, new headless, 1600×1000 at device scale 2) on an Apple-silicon laptop. Around each action the harness read Chrome's own counters (`Performance.getMetrics`: task, script, style and layout time), every long task, and every frame interval, and stopped the clock when the page had painted and gone 400 ms without a long task. CPU profiles and Chrome traces were taken for the slow ones, and in-page experiments isolated each suspected cause. Absolute numbers on the author's machine will differ; the ratios are the finding.

## Verdict

Three problems account for the lag, and none of them is MathJax being slow or the manifest being large.

1. **The divider costs about 115 ms per pointer move** (8 frames a second). The ratio is an inline custom property, `--ratio`, on the workspace element that holds both panes. Custom properties inherit, so each move restyles all 43,800 elements of both documents and re-lays them out with nothing reusable. Writing the same width to the pane directly costs 17.5 ms.
2. **Every re-render of a document leaks the old one.** MathJax keeps every formula it has typeset in a list arras never clears, and each entry holds its DOM node, so the whole previous document stays alive: 75,000 nodes and 15 MB per re-render, through any number of garbage collections. A re-render happens on a tab switch, on a return from the graph, and on every rebuild that changes the document, which is every annotation an agent files. Ten agent annotations left the page at 825,000 nodes and 201 MB.
3. **Every rebuild replaces the whole document and typesets all 1,247 formulas again**, even when the only change is one mark. That is about a second of work per annotation, and a reader deep in the paper gets it as one freeze of 350–700 ms that grows as the leak does, plus up to two seconds of polling before anything happens.

Everything else measured — scrolling, hovering, opening a box, switching focus, idling — is within a frame or two.

## The twenty actions

Wall is from the input to the page settling; work is main-thread task time; worst is the longest single task; frames are the 95th-percentile frame interval and the number over 50 ms. Nodes is Chrome's live DOM node count afterwards, garbage included.

| # | action | wall ms | work ms | style / layout ms | worst ms | frames p95 / >50 ms | nodes | note |
|---|---|---|---|---|---|---|---|---|
| 1 | cold load of the paper | 1568 | 1099 | 161 / 125 | 66 | – | 85,092 | first formula 388 ms, all typeset 1,533 ms |
| 2 | scroll the paper, 40 wheel steps | 2034 | 481 | 1 / 2 | 0 | 17 / 0 | 85,109 | smooth |
| 3 | open a second pane by following a link | 166 | 160 | 10 / 16 | 65 | 17 / 1 | 85,484 | |
| 4 | **drag the divider, paper beside a node** | 11222 | **9142** | **6370 / 753** | 328 | **117 / 68** | 81,815 | 80 moves, ~115 ms each |
| 5 | **drag the divider, paper beside a PDF** | 8400 | **6905** | 4491 / 540 | 209 | **134 / 36** | 96,805 | 3,177 style recalcs |
| 6 | focus the other pane | 110 | 83 | 4 / 0 | 0 | 17 / 0 | 84,255 | |
| 7 | **switch tab back to the paper** | 1327 | 931 | 161 / 91 | 59 | 33 / 1 | **172,752** | re-created and re-typeset |
| 8 | jump to a reference in the paper | 102 | 69 | 0 / 0 | 0 | 33 / 0 | 84,336 | |
| 9 | hover preview of a reference | 442 | 147 | 1 / 5 | 0 | 33 / 0 | 85,168 | includes the 300 ms delay |
| 10 | open an annotation box | 134 | 103 | 5 / 1 | 0 | 33 / 0 | 84,588 | |
| 11 | toggle settled annotations (`s`) | 16 | 30 | 4 / 1 | 0 | 17 / 0 | 85,103 | |
| 12 | show all annotations (`e`) | 190 | 209 | 108 / 4 | 152 | 17 / 1 | 87,765 | 44 boxes |
| 13 | settings: text size M → L | 200 | 191 | 115 / 20 | 156 | 17 / 1 | 85,327 | whole-document restyle |
| 14 | settings: format p1 → b1 | 228 | 223 | 121 / 44 | 187 | 17 / 1 | 85,329 | whole-document restyle |
| 15 | settings: comments floating → inline | 50 | 28 | 1 / 0 | 0 | 17 / 0 | 85,328 | |
| 16 | open the graph view | 424 | 397 | 11 / 2 | 289 | 17 / 1 | 88,361 | force layout, 320 ticks on the main thread |
| 16b | **back from the graph to the paper** | 1283 | 900 | 158 / 91 | 73 | 33 / 0 | **175,833** | re-created and re-typeset |
| 17 | open a PDF to its first page | 288 | 207 | 11 / 28 | 0 | – | 8,329 | |
| 17b | scroll the PDF, 40 wheel steps | 2365 | 1279 | 211 / 268 | 0 | 33 / 0 | 13,817 | 3,814 style recalcs, 1,308 layouts |
| 18 | **write an annotation in the viewer** | 1812 | 1167 | 158 / 90 | 159 | 33 / 2 | 156,194 | submit to mark drawn; scroll kept |
| 19 | **an agent annotates from the CLI while the paper is open** | 2613 | 1043 | 152 / 87 | 351 | 33 / 2 | 171,466 | command to mark drawn; scroll kept |
| 20 | idle ten seconds | 10004 | 163 | 0 / 0 | 0 | 17 / 0 | 85,092 | the 1 s poll costs nothing |
| 21 | resize the window 1600 → 1200 → 1600 | 461 | 435 | 122 / 96 | 0 | 33 / 0 | 84,925 | |

The CLI is not where the lag is: on the same copy a build after no change takes 0.44 s, `status` and `lint` 0.3 s, a forced rebuild of 266 fragments 13 s and a cold first build 32 s. `loom serve` idles at under 2% of one core.

## Findings

### 1. The divider restyles both documents on every move

`Workspace.svelte` sets `style="--ratio: {ratio}"` on `<main class="workspace">`, and pane 0 reads it as `flex: 0 0 calc(var(--ratio) * 100%)`. Each pointer move changes the property on the ancestor of every element on screen, and the next move's `getBoundingClientRect` forces the result. Measured in the page, one step of the drag with a forced style and layout after it:

| what changes per step | ms per step |
|---|---|
| `--ratio` on the workspace (today) | 93.8 |
| pane 0's `flex` written directly | 17.5 |
| `<html>`'s five `data-*` attributes rewritten with the same values (`prefs.apply`) | 0.0 |
| the `localStorage` write of the preferences | 0.0 |

The trace agrees: a drag is a run of 120 ms tasks, nearly all of it Layout and the style recalculation before it. The suspicion that `prefs.apply` and the storage write were the cost was wrong. The 17.5 ms that remains is the real price of re-wrapping two documents at a new width, which is a frame at 60 Hz.

With a PDF beside the paper (action 5) the same cause applies, and on top of it the PDF's shown pages are redrawn at each new width (`PdfDoc.svelte`'s `contentRect` binding feeds the page width): 3,177 style recalculations in one drag.

### 2. MathJax's list holds every document it has ever typeset

`math/mathjax.ts` declares `typesetClear` and never calls it. MathJax's document keeps a `MathItem` per formula, each pointing at its node, so when `{@html}` replaces a fragment the old tree stays reachable. After forced garbage collection:

| state | MathJax list | DOM nodes | heap MB |
|---|---|---|---|
| first load | 1,247 | 81,672 | 30 |
| graph and back, once | 2,494 | 156,452 | 47 |
| graph and back, twice | 3,741 | 230,980 | 62 |
| after removing the entries whose node is disconnected | 1,247 | 81,924 | 34 |

Removing the dead entries frees everything, so nothing else retains the old documents. Typesetting also slows as the list grows (916 ms to 1,152 ms over eight re-renders, flat at about 900 ms when pruned), which is consistent with MathJax walking its whole list on each batch.

### 3. A rebuild replaces the document and re-typesets all of it

The viewer polls the manifest every second; a new hash re-runs every fragment's load and mount effects (`Fragment.svelte`). The master fragment's HTML now carries the new `<mark>`, so `{@html}` replaces all 43,800 elements, `mount` re-wires them and `typeset` sets all 1,247 formulas again. An agent filing ten findings while the author reads at 60% of the paper:

| annotation | command to mark drawn | longest freeze | DOM nodes | heap MB |
|---|---|---|---|---|
| 1 | 1,873 ms | 427 ms | 155,995 | 48 |
| 2 | 2,368 ms | 474 ms | 230,320 | 65 |
| 5 | 2,194 ms | 567 ms | 453,313 | 116 |
| 10 | 1,899 ms | 701 ms | 825,028 | 201 |

The freeze is `typeset`'s first part. It typesets everything above the reader before revealing, in batches of 48 that are each awaited but never yield to the browser, so 750 formulas above the reader are one task. At the top of the paper the same re-render is spread over small tasks (worst 73 ms). The scroll position is kept in both cases.

Of the delay, about a second is the two polls in series: `loom serve`'s watcher scans the quilt every second, rebuilds (about 0.4 s), and the viewer's own poll is another second.

### 4. A tab switch or a return from the graph re-creates the document

`Pane.svelte`'s keyed `{#each}` destroys the item's renderer when its tab is left, and `/graph` unmounts the workspace. Coming back is a full `{@html}`, wire and typeset: 1.2–1.3 s, and with finding 2 another 75,000 leaked nodes each time.

### 5. Smaller costs

- **Settings that restyle the document** (size, face, width, format): 150–190 ms in one task, nearly all style and layout of 43,800 elements. Inherent to changing every element's font; nothing is re-typeset.
- **Opening the graph**: one 289 ms task, `forceLayout`'s 320 synchronous ticks, re-run on every manifest change.
- **Scrolling a PDF**: smooth (33 ms frames), but `PdfDoc.scrolled` reads every page holder's `offsetTop` on each scroll event, 1,308 layouts in 40 wheel steps.
- **Show all annotations**: one 152 ms task for 44 boxes.

Measured and not a problem: scrolling the paper (17 ms frames), the hover preview, opening a box, focus changes, the settled toggle, the comments setting, and the idle polls on both sides.

## Plan

Ordered by what the reader gains per unit of work. Phase 1 is three small changes to arras, each verified by re-running the harness; phase 2 changes how a rebuild reaches the page; phase 3 is the rest.

### Phase 1 — the divider, the leak, the freeze

1. **Size the pane, not the workspace.** Write pane 0's `flex-basis` (or a non-inherited registered property on the pane itself) from the drag handler, keep `prefs.divider` updated for persistence but write it to storage on drop, and coalesce moves to one per animation frame. Expected: about 115 ms to about 20 ms per move. With a PDF beside, hold the canvases at their drawn size with a CSS scale while dragging and redraw once on drop.
2. **Clear MathJax's list when a fragment's markup goes.** Call `typesetClear` on the old root's math before `{@html}` replaces it and when a fragment is destroyed, or prune entries whose node is disconnected after each typeset. Expected: memory flat across any number of re-renders, and typesetting no longer slowing over a sitting.
3. **Yield between batches in typeset's first part.** Give the browser a turn (`setTimeout(0)` or `scheduler.yield()`) between the awaited batches as the background ones already do; the reveal still waits for the promise, so nothing above the reader moves. Expected: the 350–700 ms freeze becomes 30 ms slices.

### Phase 2 — a rebuild should not rebuild the page

4. **Patch the fragment instead of replacing it.** When a fragment's HTML changes under the same path, compare it with the previous HTML block by block (top-level blocks carry `data-src`) and replace only the blocks that differ, typesetting only those. An annotation becomes a one-paragraph update instead of 43,800 elements and 1,247 formulas. The larger alternative, placing marks client-side from the manifest so a new annotation changes no fragment at all, belongs with WQ-60's marks from the source span.
5. **Re-wire, don't re-mount, on a manifest that does not change the fragment.** The mount effect depends on `store.manifest`, so every rebuild runs `wire` and a `typeset` pass over the whole document even when its HTML is the same; re-wire only what the manifest feeds (marks' classes, counts).
6. **Push instead of two polls.** A server-sent event from `loom serve` when a build publishes, and filesystem events (or a shorter scan) in the watcher, would take about a second off every change an agent makes.
7. **Keep a left document alive.** Hide an item's renderer when its tab is left, and keep the workspace mounted under `/graph`, so coming back costs nothing. Bound it (the focused and the last item per pane) so memory stays small.

### Phase 3 — the rest

8. Run the graph's force layout off the main thread or in fewer ticks, and only when the graph's own inputs change.
9. Throttle `PdfDoc.scrolled` to a frame and read cached page offsets.
10. Revisit paragraph-level `content-visibility` with `contain-intrinsic-size: auto`, which the second round set aside because a page's height changed under in-page jumps; `auto` remembers each block's real size once drawn, which may answer that.

### Verification

The harness should become part of `arras/tests/perf` with budgets that would have caught all three problems: a divider move under 33 ms on a large corpus, DOM nodes flat across five re-renders, and a one-annotation rebuild re-rendering in under 100 ms. It runs against `PERF_BUILD` like the existing floor, so it needs a large corpus; `demos/relloc` with seeded annotations is enough.

## Side findings

- `demos/relloc`'s landmark `canon/draft3-v1.tex` defines all 52 of the paper's ids again, so every labelled node is `duplicate-id` and refuses annotations, although the quilt's own README says a landmark is never scanned. The seeded annotations went to file-qualified keys for that reason.

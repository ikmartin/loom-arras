# The document controls: a study

The design of where an item's controls live once they leave the global rail, settled with the author on 2026-09-26 and built in plan 0.16. The drafts, the critiques and every final state are in the demo page, [images/0.16/demo.html](../plans/images/0.16/demo.html), published at https://claude.ai/artifact/NDcAE6JhzY1ah9RVkFqjsB; the screenshots of the final designs are in [docs/plans/images/0.16/](../plans/images/0.16/).

Part one is what was decided. Part two is how it was reached, kept so that no rejected option is proposed again without its reason. Part three is what it changes in the book and the code.

## Part one: the decisions

### 1. What the rail holds

The global rail holds only what concerns both documents on screen: the annotation filter at its left and **compare** at its right, a control that arrives with plan 0.17 and is drawn from 0.16 as a placeholder. Nothing about one item is on the rail: its controls go to the toolbar (§2) and its views to the tab strip (§5).

### 2. The toolbar: a corner menu

Every item with controls has one toolbar, **drawn on the focused pane only** — the other pane shows none, whatever it holds, which is how the rail's rule that the controls are drawn once (plan 0.13.3 F4) survives the move.

- **Where:** the top-right corner of the pane, standing over the page on the pane's own layer, so the text never moves for it and it never sits on the centre line where the title and headings are.
- **What it is:** one line on the sheet with a hairline and the floating box's shadow: the two annotating tools as icons where a publisher is serving, anything used continually while reading, then **view ▾**, then the pin.
- **view ▾** opens the existing Popover (book 15.8, "the one floating surface"), where every other control is in full words with its key: `show all annotations  e`, `show settled annotations  s`, `open the PDF`. A dot on *view* says a mode inside it is on.
- **The divider** before *view* is drawn only when something stands to its left.

![A document's toolbar](../plans/images/0.16/toolbar-document.png)
![Its view menu](../plans/images/0.16/toolbar-document-view-menu.png)

### 3. How it floats

- **It wakes in a band** across the top of the pane: 96px tall, inset 96px from the pane's left edge and 4px from its right. The band always contains the toolbar: its right inset stops short of the bar, its left inset never passes the bar's left edge, and it reaches at least 8px below the bar, whatever the pane's width.
- **It shows** while the pointer is in the band, and **fades over 0.4 s** when the pointer leaves it.
- **It stays** while the pointer is on it, while its menu is open, and while it is pinned. Keyboard focus inside the pane shows it.
- **The pin** is the last thing on the bar. Off, it is a tilted outline in the faint ink; on, it stands upright, filled, heavier, in the link's colour on the link's wash. Its tooltip names what a click does: "Don't fade: keep these controls showing until you click again" when off, "Fade: let these controls fade when the pointer leaves the top of the pane" when on.
- **Pinned by default.** The pin is one preference shared by every toolbar, saved when it changes and kept between visits in the viewer's own preferences (`arras.prefs`, `lib/prefs.svelte.ts`), as the Settings panel's choices are — so, like them, it is per browser and per address.

![The band, drawn only for the demo](../plans/images/0.16/float-band.png)
![Pinned](../plans/images/0.16/pin-on.png)
![Unpinned, with its tooltip](../plans/images/0.16/pin-off-tooltip.png)
![Unpinned and faded](../plans/images/0.16/pin-off-faded.png)

### 4. Every toolbar, by item

| item | on the bar | under *view* |
|---|---|---|
| a document, a publisher serving | select · box · view · pin | show all annotations (e) · show settled annotations (s) · open the PDF |
| a document, nothing serving | view · pin (no tools: nothing can be written, DR-161) | as a document |
| a node | select · box · view · pin | show all annotations (e) · show settled annotations (s) · open its context beside · show verbatim code |
| a paper, on its Paper view | select · box · fit · zoom · page · view · pin | show settled annotations (s) · open the PDF |
| a paper on its Digest or Info, or with no readable copy | the same, drawn and greyed (DR-254-ikmartin), so nothing moves when the view changes | the same, the PDF greyed |
| a landmark, a node's context, a session | no toolbar: none has controls | — |

*show settled* on a paper is new: the PDF's marks already honour the settled mode, so the paper offers the control that governs it.

![A paper](../plans/images/0.16/toolbar-paper.png)
![A paper on its Digest: the page tools grey](../plans/images/0.16/toolbar-paper-on-digest.png)
![A node](../plans/images/0.16/toolbar-node.png)
![A document with nothing serving](../plans/images/0.16/toolbar-document-read-only.png)
![A session: views in the strip, no toolbar](../plans/images/0.16/toolbar-session.png)
![A paper, dark](../plans/images/0.16/toolbar-paper-dark.png)

### 5. Views at the end of the tab strip

An item's views — a paper's `Paper · Digest · Info`, a session's `Chat · What it did` — stand at the right end of the pane's tab strip as plain words, the current one underlined in the accent, the unavailable one greyed. They are the focused tab's item's, on both panes, and never fade.

### 6. Tabs narrow, then scroll

A tab is 148px at most. When the strip is crowded, every tab narrows by the same amount, down to a floor of 1.5 times its height (45px at a 30px tab); past the floor the row of tabs scrolls, the views keep their place at the strip's right end, and the active tab is scrolled into view. Below 90px a tab keeps its shortened name and shows its close only on hover; its full name is its tooltip.

![Two tabs](../plans/images/0.16/tabs-2.png)
![Five tabs, narrowed](../plans/images/0.16/tabs-5.png)
![Ten tabs, at the floor and scrolling](../plans/images/0.16/tabs-10.png)
![Twenty tabs](../plans/images/0.16/tabs-20.png)

## Part two: how it was reached

### 7. The principles

The viewer's visual principles are P1–P6 of plans 0.13.3 and 0.14: open on the thing itself; say it once, in the place that governs it; claim only what is known; one element, one question, and a place holds elements whose questions are asked at the same moment; following a connection must not cost the thing followed from; show less rather than more. Plan 0.13.3's F4 put the controls on the rail so that two panes would not carry the same widgets twice.

### 8. The first round, and what its critique asked for

Five looks were drafted: **A** a line of the page above the text, **B** a centred pill, **C** a corner stack of icons, **D** labelled groups, **E** a margin column. D and E were rejected by the author. The critique of A, B and C found: A has no surface and so cannot float, reads as the paper's own running head, and moves the text when it appears or wraps; B sits on the centre line where the title and headings are, lost the noun of "show all annotations" to fit, and grows with a node's extra controls; C's icons for show all and show settled must be learned, carry state as a faint wash, and stack six rows tall. The shadow objection to B and C fell away on inspection: the floating box and the local graph's toggle already cast one, so what floats over the text casts one.

The revision was held to what the critique asked: a surface of its own, anchored at a corner and never on the centre line, words in full except the two established tool glyphs, one line, standing over the page rather than in its flow, and on the focused pane only. Three drafts met it — **A′** a strip along the pane's top edge, **B′** a one-line corner bar in full words, **C′** the corner menu — and the author chose C′.

### 9. The floating behaviour

Fade durations of 0, 0.25, 0.4, 0.5 and 1 s were tried; 1 s and 0.25 s were rejected and **0.4 s** chosen. Three waking regions were tried: anywhere in the pane (with an idle timeout), the top fifth of the pane, and only over the bar itself; the top was chosen, then fixed in size rather than proportional (heights 64, 96 and 128px and left insets 8 to 96px were tried) at **96px tall and 96px from the left**, and asymmetric so that the bar is always inside it.

### 10. Where the views go

Three places were compared (demo cards 4, 4′ and 4″):

- **In the toolbar**, as a first dropdown. Rejected: the unfocused pane loses the view; the views fade with the bar; a paper's bar already fills a 527px pane; and it fails P4's place test, since which reading to see is asked on arriving at an item and the page's tools are asked while reading it.
- **In the tab**, as `Bellamy 2016 · Digest ▾`. Rejected: tabs do not widen, so the title is truncated to make room; three targets in 148px invite mis-clicks; and either every tab carries its view or tabs change shape as focus moves.
- **At the end of the tab strip.** Chosen: always visible, on both panes, never fading, all three views legible without opening anything, the tab left at one job, and the toolbar left with only what acts on the page.

## Part three: what it changes

- **Book 15.2.5** (the rail holds the filter and compare only), **15.2.4** (the tab strip carries the views; tabs narrow and scroll, amending DR-247-ikmartin's fixed 148px), **15.3** and **15.8** (the page draws "no rail, no toolbar and no header of chrome": the toolbar is the pane's, not the page's, and the Popover remains the one floating surface it opens), **15.6** ("no shadows, no filled chrome" stated as it is practised: what floats over the text casts one), **15.7** (the pin's preference), and each page's section that names where its controls are. DR-254-ikmartin stands. A decision record for the move, one for the floating rule, one for the views, and one for the tabs.
- **arras:** `workspace/GlobalRail.svelte` (the filter and compare only); the `kinds` registry in `workspace/registry.ts`, whose `controls` and views move; `DocumentControls`, `NodeControls` and `WorkControls` re-drawn as the corner menu inside the focused pane; `pdf/ToolPair.svelte` and `pdf/PdfTools.svelte` reused on the bar; `components/Popover.svelte` for *view*; the tab strip in `workspace/Pane.svelte` and `PaneHead.svelte` for the views and the narrowing; `prefs.svelte.ts` for the pin.
- **tests:** `tests/e2e/workspace.e2e.ts` asserts today that the rail holds exactly two things (the filter and the cluster, ~:104), that every control in the cluster names its target (~:113), that no control is ever drawn inside a pane (~:64), which item the cluster follows (~:186) and the narrow-window `⋯` (~:307); each changes. The control testids (`toggle-annotations`, `toggle-settled`, `tool-select`, `tool-box`, `open-context`, `source-toggle`, the zoom and page ids, `tab-paper`, `tab-digest`, `tab-info`, `tab-chat`, `tab-did`) are kept so the suites that use them follow the controls to their new place. The book's figures under `docs/book/figures` are re-shot.

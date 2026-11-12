# WQ-68 · UI changes to the toolbar

**Repo:** arras

## Trigger

The author starts the toolbar workshop, or a control that must be visible at rest has no room on a pane's toolbar at the width two panes side by side leave it.

## Why deferred

The author decided on 2026-11-12 that changes to the pane's toolbar are workshopped, through a demo the author revises until it is right, rather than added one at a time, because it is not clear the toolbar has room for more. Until the workshop starts, or a control cannot find a place, each control has found room on the bar or under **view ▾**.

## Rough design

A demo of the toolbar in its states, at desktop width, revised with the author until it is right, then a plan. It starts from the interim layout the author chose on 2026-11-12, when the annotating tools were clipped off a PDF's toolbar in any pane narrower than the window: two rows, the first for what reads and **Annotate**, which shows or puts away the second, the annotation row, with the tools that write and the hint (`arras/src/lib/workspace/ItemToolbar.svelte`, `annotationRow.svelte.ts`). What is waiting for it, found while fixing the annotation engine's states after plan 0.30:

- **A pane with its annotations turned off says so in the pane.** Today the only sign is a dot on **view ▾**; a reader who turned them off and forgot sees a clean document and no reason. A strip in the pane ("Annotations off · Turn on") was proposed and held back for want of room.
- **Settled annotations shown or hidden** is a second mode with the same dot and no other sign.
- **The counts.** At rest the stepper's count ("4 items") repeats what Comments and Changes count between them; Comments counts the annotations here and Changes the changes, while the list Comments opens holds both. Notes counts the notes here while its list holds every document's. Whether the stepper's count earns its room, and how the badges say what they count, is the workshop's.
- **The hint**, at the annotation row's right, or under the toolbar while the row is put away, carries three states, the tool in hand, words just marked ("start typing to add a comment") and a draft not yet saved; whether state belongs there or on the bar.
- **What lives under view ▾** and what on the bar, at the width two panes leave.
- **The first row at its narrowest.** On a PDF the first row still holds the views, Comments, Notes, **PDF ▾**, the page and the zoom, and in a narrow enough pane it is still clipped from its left; whether Comments and Notes shrink to icons, or more moves under view ▾.
- **Markdown and other project files** take no annotations, so they have no annotation row; that is loom's to change first.

## Blast radius

`arras/src/lib/workspace/ItemToolbar.svelte`, `ToolbarMenu.svelte`, `ToolbarItem.svelte`, the kinds' controls (`DocumentControls`, `NodeControls`, `FileControls`, `WorkControls`), `arras/src/lib/review/AnnotateBar.svelte`, and the e2e tests that read the toolbar (`workspace.e2e.ts`, `annotations.e2e.ts`).

## Related

[Plan 0.30](../plans/0.30-annotations.md), whose Implementation section records the fixes this came out of.

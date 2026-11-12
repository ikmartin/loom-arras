# WQ-68 · UI changes to the toolbar

**Repo:** arras

## Trigger

The author starts the toolbar workshop, or a control that must be visible at rest has no room on a pane's toolbar at the width two panes side by side leave it.

## Why deferred

The author decided on 2026-11-12 that changes to the pane's toolbar are workshopped, through a demo the author revises until it is right, rather than added one at a time, because it is not clear the toolbar has room for more. Until the workshop starts, or a control cannot find a place, each control has found room on the bar or under **view ▾**.

## Rough design

A demo of the toolbar in its states, at desktop width, revised with the author until it is right, then a plan. What is waiting for it, found while fixing the annotation engine's states after plan 0.30:

- **A pane with its annotations turned off says so in the pane.** Today the only sign is a dot on **view ▾**; a reader who turned them off and forgot sees a clean document and no reason. A strip in the pane ("Annotations off · Turn on") was proposed and held back for want of room.
- **Settled annotations shown or hidden** is a second mode with the same dot and no other sign.
- **The counts.** At rest the stepper's count ("4 items") repeats what Comments and Changes count between them; Comments counts the annotations here and Changes the changes, while the list Comments opens holds both. Notes counts the notes here while its list holds every document's. Whether the stepper's count earns its room, and how the badges say what they count, is the workshop's.
- **The hint line** under the toolbar now carries three states, the tool in hand, words just marked ("start typing to add a comment") and a draft not yet saved; whether state belongs there or on the bar.
- **What lives under view ▾** and what on the bar, at the width two panes leave.

## Blast radius

`arras/src/lib/workspace/ItemToolbar.svelte`, `ToolbarMenu.svelte`, `ToolbarItem.svelte`, the kinds' controls (`DocumentControls`, `NodeControls`, `FileControls`, `WorkControls`), `arras/src/lib/review/AnnotateBar.svelte`, and the e2e tests that read the toolbar (`workspace.e2e.ts`, `annotations.e2e.ts`).

## Related

[Plan 0.30](../plans/0.30-annotations.md), whose Implementation section records the fixes this came out of.

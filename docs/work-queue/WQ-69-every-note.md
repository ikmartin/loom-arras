# WQ-69 · A view of every note in the quilt

**Repo:** arras

## Trigger

The author asks to see the notes of more than one document, work or PDF at once.

## Why deferred

The author decided on 2026-11-12 that Notes beside a document lists that document's notes only, and that a view of every note comes later. Until the author asks to see more than one item's notes together, the list beside each item is enough.

## Rough design

A view of every annotation whose type is listed in Notes, from every document, work and PDF in the quilt, grouped by where each was left, each a link back to its place with its popup open. It is likely opened from a button in the left column, beside Docs and Review, rather than from an item's toolbar, since it belongs to the quilt rather than to one item.

The quilt-wide list beside a document did this until 2026-11-12: `notesIn` in `arras/src/lib/review/annotating.svelte.ts` grouped the notes by `documentOf` and labelled each group by the document's file name, a work's citekey or a PDF's file name. It is in the history at commit `ce55282f`, with its test and its e2e test, and is the starting point.

## Blast radius

`arras/src/lib/review/annotating.svelte.ts`, the left column (`arras/src/lib/shell/Column.svelte`), a route or a workspace item for the view, and an e2e test of it.

## Related

[WQ-68](WQ-68-toolbar-changes.md), the toolbar workshop, which counts and lists notes per item.

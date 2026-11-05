# WQ-65 · A PDF's marks in a sidecar rather than the manifest

**Repo:** loom, arras

## Trigger

The `notes` of a quilt's manifest cross one megabyte.

## Why deferred

A mark's rectangles and strokes are in its note's manifest row, and the manifest is read whole whenever it changes. The notes of the quilts in use are nowhere near a megabyte. A paper read closely holds a few dozen marks at a few hundred bytes each, so a heavily marked book of a few thousand comes to about a megabyte. Below that the row is the simpler place: every surface that lists a note already reads it.

## Rough design

Geometry leaves the row for the sidecar a work already has (`spans`, `manifest.md`), and one like it for a project's PDF, fetched by the one surface drawing that PDF and named by its hash. Rows keep `mark`, `quote`, `page` and `body`, which everything that lists notes reads. A viewer that finds `rects` in a row uses them, so no version of the interface changes.

## Blast radius

`loom/src/loom/notes.py`, `render/build.py` for the new files, `specs/manifest.md`, `arras/src/lib/pdf/desk.svelte.ts`.

## Related

[WQ-36](WQ-36-annotation-bodies-beside-the-manifest.md), the same arrangement for annotation bodies; [plan 0.28](../plans/0.28-marking-a-pdf.md).

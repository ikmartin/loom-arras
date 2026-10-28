# WQ-62 · A document read with its open suggestions folded in

**Repo:** loom, arras

## Trigger

In a review of the author's own text, a suggestion of a paragraph or more is too cramped to read in its box's in-place view, and the author wants to read the passage as it would stand with it taken.

## Why deferred

Plan 0.20.7 built each suggestion's in-place view: the box shows the key with the payload taken, its new words washed as Review washes a change. The proofreading review of draft4 in the earlier relloc (2026-10-02) came before it: eleven drop-in suggestions ran to 700 characters or more, the longest 2,164, and the author read them as bare text in the box and found them hard to read (`docs/reports/modes-study.md`, part three). Whether the in-place view is enough has not yet been seen on a long payload, and a document-wide view is not needed until it is not.

## Rough design

- **A view of the document with every open suggestion taken.** A document's `view ▾` gains *with suggestions*: the document as it would read with each placeable open suggestion in place, each change washed and its annotation's mark beside it, read-only like a landmark. Taking one is still the author's edit; the view only shows.
- **Built by the publisher**, as the in-place fragments are (`render/payloads.py`, `attach_changes`), so a static host shows it too. Several suggestions on one key are placed in one pass against its text (`records/suggestions.py`'s `place`, extended to compose); where two overlap, the first placed is shown and the other says it could not be.
- **Optionally the same per section,** if a whole document is too slow to build on a large quilt.

## Blast radius

`records/suggestions.py`, `render/payloads.py`, `render/build.py`; the manifest (a fragment set per document) and `docs/specs/manifest.md`; arras's document view and its `view ▾` menu.

## Related

Plan 0.20.7; [WQ-60](WQ-60-annotation-anchors.md) (a replacement longer than its anchor); `docs/reports/modes-study.md`.

# WQ-67 · Corrections to a digest's results

**Repo:** loom, arras

## Trigger

The author asks for an ingest correction to be made in a digest, or edits a digest's file by hand to make one.

## Why deferred

The author decided on 2026-11-12 that a digest stays read-only, more or less, and may reconsider: it is loom's copy of someone else's results, extracted from their source, and a doubt about the copy is something to say rather than an edit to make.

The code and the agents' instructions do not agree with that yet. Since plan 0.30.0, `loom suggest` files a suggested edit on a digest node, but `loom suggestion apply` and the viewer's Take it refuse to keep it, because no document of the person's reads the node (`apply` in `loom/src/loom/records/edits.py`). A payload on a digest node was refused the same way before. The ingest mode (`loom/src/loom/assets/ai/modes/ingest.md`) and `docs/specs/digests.md` §8 still tell an agent to file its corrections as suggested edits, which the author can then only make by hand.

## Rough design

Deciding between two directions is the item:

- **Read-only.** Ingest files each correction as an annotation on the digest node, of the type the quilt uses for a fault (Revision by default), naming what the copy gets wrong and the right text; `loom suggest` refuses a digest node and names that instead; a fault that recurs is fixed in the extractor and taken with `loom library update --redo`.
- **Kept on the author's act.** `loom suggestion apply` writes the digest's file, keeping a version first as it does for a document (P7), and Proposed Changes shows edits on a work's nodes beside its proposed results.

Either way the ingest mode and `digests.md` §8 change with it.

## Blast radius

`records/edits.py`, `cli/suggestion.py`, the ingest mode, `docs/specs/digests.md` §8, and for the second direction the digest machinery in `loom/src/loom/digest/` and Review's Proposed Changes.

## Related

[Plan 0.30](../plans/0.30-annotations.md), whose Implementation section records finding this.

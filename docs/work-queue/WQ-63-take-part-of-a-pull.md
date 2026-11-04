# WQ-63 · Taking part of a pull

**Repo:** loom, arras

## Trigger

A collaborator's pull holds a change the author wants and another they don't, and the author takes the pull whole and undoes the part they didn't want by hand.

## Why deferred

Plan 0.25.2 gave a pull the same one-pass bar as an agent's copy, but a pull is still taken whole: `sync.incorporate` applies the fetched revision as one patch (`sync.py`), with no notion of taking one result and leaving another. An agent's copy can be split because adoption compares the copy and the document result by result against a recorded base (`adopt.comparison`); a pull has the same three sides (the last synced base, the local text, the fetched text) but nothing that splits them.

## Rough design

- **Compare a pull result by result**, as adoption does: the last synced base, the person's text and the pull's, classed new, changed, removed, merged or clashing, with the prose and the preamble as their own groups. `adopt.comparison`'s per-result shaping and `_merge` are the parts to share.
- **Take and leave in the bar**, saved as a choice against the fetched revision; Apply writes only what was taken, stamping first as a pull does now.
- **What was left stays waiting**: the next fetch compares against the same base for it, so a change left out is offered again rather than lost.

## Blast radius

`sync.py`'s incorporation, the write API's `sync-*` endpoints (a decision endpoint beside `adopt-decision`), `render/incoming.py`, and `IncomingPull.svelte`.

## Related

Plan 0.25.2; `docs/reports/review-panel-study.md` (Incoming).

# WQ-52 · Agent documents of overlapping scopes

**Repo:** loom, arras

## Trigger

A person wants two agent versions of the same section, or of overlapping parts of one document, side by side, and `loom draft --ai` refuses the second because its scope overlaps an open one.

## Why deferred

Agent documents of disjoint sections, each with its own never-reused suffix, its own adoption and close and reopen, are built ([section drafts and responsive adoption](../plans/section-drafts-and-responsive-adoption.md)). The workflow asked for uses disjoint sections; no one has asked for alternatives of one scope.

## Rough design

Allowing overlapping scopes needs a meaning for comparing two alternatives of one source (their common base is the source's version each began from, which may differ) and for incorporating one after the other, where the second's baseline is the source as the first left it. Incoming lists each as its own contribution already. Keep each copy's own bases, and the source-conflict checks.

## Blast radius

`section_drafts.check_overlap` and its callers in `loom draft --ai`, `loom ai reopen` and `loom adopt`; `drafts.py`, `adopt.py`, arras's Incoming and compare.

## Related

[DR-323-luisa](../design/decision-records-frozen.md), [plan 0.17](../plans/0.17-ai-drafting-and-compare.md), [section drafts and responsive adoption](../plans/section-drafts-and-responsive-adoption.md).

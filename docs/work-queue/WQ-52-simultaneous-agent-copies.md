# WQ-52 · Alternative AI drafts of overlapping scopes

**Repo:** loom, arras

## Trigger

A person requests concurrent alternative AI drafts of the same section or overlapping document scopes, beyond the disjoint section drafts implemented by DR-323-luisa.

## Why deferred

The requested workflow uses disjoint sections; no concurrent alternatives of overlapping scopes have been requested.

## Rough design

Disjoint section drafts, never-reused numbered derived suffixes, scoped adoption and close/reopen are implemented by [section drafts and responsive adoption](../plans/section-drafts-and-responsive-adoption.md). Allowing alternative overlapping scopes additionally needs explicit direction and baseline semantics for comparing and incorporating one alternative after another. Preserve the existing independent provenance and source-conflict checks.

## Related

[DR-323-luisa](../book/A-decision-records.md), [plan 0.17](../plans/0.17-ai-drafting-and-compare.md).

# WQ-04 · Network identity resolvers

**Repo:** loom

## Trigger

`loom:unresolved-work` (added by [[WQ-01]]) exceeds a quarter of a real bibliography — the count that `doctor` reports as "34 of 41 cited works resolved".

## Why deferred

Until the identity model exists and reports its own failure rate, there is no evidence that a network resolver is needed and no way to measure whether one helped. A resolver is also the first thing in loom that would make a network request during ordinary work, which is not a step to take on a hunch.

## Rough design

A bibliographic string in, a global id out, for the entries whose `.bib` carries no identifier.

- **zbMATH Open** over MathSciNet as the default: MathSciNet's MRef is excellent for mathematics and returns MR numbers from reference strings, but it is subscription-gated with terms restricting programmatic use, while zbMATH Open's API is genuinely open. Verify both against current terms before building.
- **Crossref** `query.bibliographic` as the general-purpose fallback: fuzzy match, returns candidates with scores.
- Every binding a resolver produces is recorded with provenance `resolved`, never `declared`, so a fuzzy match stays distinguishable from a DOI that was in the file. A low-confidence match is offered, not applied.
- Never blocks: an unresolved work still gets a digest and still enters the graph. It cannot dedup across corpora or be fetched, and that is all.
- Writing a resolved identifier back into the author's `refs.bib` is offered as a visible diff the way `import` does, never silently — it is the author's file.

## Blast radius

The first network path in loom outside `loom digest fetch`, so it inherits `[refs] fetch`-style consent; the override registry from [[WQ-01]]; Chapter 8; rate-limit and terms-of-use notes in the documentation.

## Related

[[WQ-01]] (its trigger is that item's diagnostic), [[WQ-02]].

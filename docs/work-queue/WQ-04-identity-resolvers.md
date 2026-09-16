# WQ-04 · Network identity resolvers

**Repo:** loom

## Trigger

Either of: `loom:unresolved-work` exceeds a quarter of a real bibliography — `loom lint` reports the rate, and on `demos/relloc` it is already 5 of 22 — **or** you want [[WQ-02]], which cannot be built without this.

Plan 0.5's parse-rate study found that only 9% of entries in a fetched paper's bibliography carry an identifier at all, because a formatted `\bibitem` is display text and mathematics styles rarely print a DOI. That makes this item the crawl's precondition rather than a later refinement.

## Why deferred

Until the identity model exists and reports its own failure rate, there is no evidence a network resolver is needed and no way to measure whether one helped. That evidence now exists and points here. A resolver is also the first thing in loom that would make a network request during ordinary work, which is not a step to take on a hunch.

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

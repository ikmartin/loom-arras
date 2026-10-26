# WQ-03 · Reference libraries: one quilt depends on another

**Repo:** loom

## Trigger

A second quilt exists whose digests another quilt wants — for instance a Gross–Siebert or virtual-localization corpus that `demos/relloc` would rather point at than re-derive — or a reader's library spans more than one quilt: the Learner of `docs/design/README.md`, reading across a field, wants what one reading project digested available in the next.

## Why deferred

There is only one quilt at a time to test against, so nothing can exercise resolution across two, and the versioning contract cannot be validated by a single consumer.

Since 2026-10-26 this is central rather than optional: loom is for the Learner as well as the Author, and a reader's library outlives any one project. A quilt holding only digests already sees their results as nodes, since a digest declares its own result environments (branch `review-findings`).

**This trigger is a decision, not an observation.** Most items here wait for something to be noticed; this one waits for you to choose to build a library, which you can do in a weekend — fetch twenty papers in a subfield from arXiv, extract each at `--all`, curate. Worth knowing, because **this item is what unlocks library functionality, not [[WQ-02]]**: the crawl makes a large library cheap to assemble, but a hand-built one works the day this lands and needs no crawling at all.

## Rough design

**A reference library is just a quilt** — nodes, ids, a graph, a ledger. It already has everything. A paper quilt depends on one:

```toml
[refs]
libraries = ["~/math/gross-siebert"]
```

and `\uses{Man12-prop-3.2}` resolves locally first, then into the libraries. No new concept, and the subfield object becomes publishable and collaboratively maintained rather than something every author re-derives. A library here is a *quilt* holding digests someone wrote, not a crawled corpus.

Three things to settle:

- **Id stability becomes a contract.** Once a quilt depends on `Man12-prop-3.2` the library cannot renumber. Libraries need releases and quilts pin a version.
- **Acceptance does not transfer; hashes do.** The library's acceptance is theirs. What a consumer inherits is the content hash, so a statement changed under it makes the dependent nodes stale — `loom:version-mismatch` generalized.
- **Local overrides library**, since a consumer will need to add a result the library lacks or correct one.

Folded in from Chapter 8's open questions: **how a library quilt is recognized** — a flag in `config.toml`, or having no masters. Both are trivial; decide when the first library exists, which is this item's trigger.

## Blast radius

`config.toml`, key resolution throughout the scanner, the manifest (a node may now come from elsewhere), arras (a node reference that resolves to no local digest must degrade to a labelled external link rather than "Unknown key" — the same shape as the existing `unknown relation kind renders generic` test), Chapter 8, `docs/specs/manifest.md`.

## Related

[[WQ-01]], [[WQ-02]] (closed; it went to weft, which is abandoned); `docs/specs/digests.md`. This shares *digests*, which are small, authored and valuable, and never deduplicate, because two people's digests of one paper are different documents.

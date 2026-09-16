# WQ-03 · Reference libraries: one quilt depends on another

**Repo:** loom

## Trigger

A second quilt exists whose digests another quilt wants — for instance a Gross–Siebert or virtual-localization corpus that `demos/relloc` would rather point at than re-derive.

## Why deferred

There is only one quilt at a time to test against, so nothing can exercise resolution across two, and the versioning contract cannot be validated by a single consumer.

**This trigger is a decision, not an observation.** Most items here wait for something to be noticed; this one waits for you to choose to build a library, which you can do in a weekend — fetch twenty papers in a subfield from arXiv, extract each at `--all`, curate. Worth knowing, because **this item is what unlocks library functionality, not [[WQ-02]]**: the crawl makes a large library cheap to assemble, but a hand-built one works the day this lands and needs no crawling at all.

## Rough design

**A reference library is just a quilt** — nodes, ids, a graph, a ledger. It already has everything. A paper quilt depends on one:

```toml
[refs]
libraries = ["~/math/gross-siebert"]
```

and `\uses{Man12-prop-3.2}` resolves locally first, then into the libraries. No new concept, and the subfield object becomes publishable and collaboratively maintained rather than something every author re-derives. This is also where a deep crawl's output lands ([[WQ-02]]).

Three things to settle:

- **Id stability becomes a contract.** Once a quilt depends on `Man12-prop-3.2` the library cannot renumber. Libraries need releases and quilts pin a version.
- **Acceptance does not transfer; hashes do.** The library's acceptance is theirs. What a consumer inherits is the content hash, so a statement changed under it makes the dependent nodes stale — `loom:version-mismatch` generalized.
- **Local overrides library**, since a consumer will need to add a result the library lacks or correct one.

Folded in from Chapter 8's open questions: **how a library quilt is recognized** — a flag in `config.toml`, or having no masters. Both are trivial; decide when the first library exists, which is this item's trigger.

## Blast radius

`config.toml`, key resolution throughout the scanner, the manifest (a node may now come from elsewhere), arras (a node reference that resolves to no local digest must degrade to a labelled external link rather than "Unknown key" — the same shape as the existing `unknown relation kind renders generic` test), Chapter 8, `docs/specs/manifest.md`.

## Related

[[WQ-01]], [[WQ-02]], [[WQ-06]]; Chapter 8 §8.9.

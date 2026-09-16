# WQ-01 · Reference identity and the `reached` primitive

**Repo:** loom, arras

## Trigger

**Met.** Nothing blocks this; it was deferred only to build this queue first. The first walk of the queue should pop it.

## Why deferred

Nothing is missing. It was separated from the discussion that produced [[WQ-02]] to [[WQ-06]] so that the queue existed before the work it tracks.

## Rough design

Six pieces, all single-quilt and testable today. The forward-compatibility test for each is: *does a digest written today still have the right identity when a corpus arrives?*

1. **Promote `_source_ident` to first-class identity.** `loom/src/loom/digest/extract.py:308` already resolves a citekey to `arXiv:0805.2065v2` or `doi:…` from the bibliography and writes it into the digest header. It is write-only, has no `mrnumber`/`zbl`/`url` path, and its fallback is `local:<filename>` — machine-specific, not an identity. Make it read back, add the missing fields in the order `doi` > `eprint`+`archiveprefix` > `mrnumber` > `zbl` > `url` (parsed for an arXiv id or DOI), and keep the `scheme:value` shape so later schemes cost nothing.
2. **A deterministic synthetic id** for the unresolvable tail — books, seminar notes, "to appear", which is 20–30% of a real algebraic-geometry bibliography and skews toward the most-cited works. Hash normalized author surnames, title and year into `work:<hash>`. Determinism across machines is the load-bearing property: without it two corpora cannot merge.
3. **An override registry**, one TOML table per citekey in the quilt, same merge-friendly shape as the ledger. Two jobs: assert an id loom could not find, and assert that two citekeys are the same work.
4. **Provenance on every binding** — `declared` (a DOI in the file), `resolved` (a fuzzy match), `asserted` (the author said so). A wrong automatic match and a hand-checked one must be distinguishable or the corpus can never be audited.
5. **`loom:unresolved-work` (info)** with the fix inline, and a resolution count in `doctor` or the references index: "34 of 41 cited works resolved". Books stay unresolved forever; the point is that it is visible rather than silent. This count is also the trigger for [[WQ-04]].
6. **The `reached` primitive** — for each digest, the subset of its nodes in the transitive closure of what the quilt's own nodes `\uses`, plus the closure within the digest of anything so reached (a statement whose standing assumptions are off-screen is not shown). One closure over a graph loom already builds, and it pays off in three places at once: external nodes leave the review queue unless reached; the graph defaults to your nodes plus reached external, visually distinct; a full digest folds what nothing reaches. This is what makes `loom digest extract` usable at `--all` on a paper like Manolache, where 96 results arrive and 3 are load-bearing.

Bibliography is the rosetta stone **for depth 1 only** — it covers what you cite, and a depth-2 work has no entry in it and never will.

**Also in scope, as uncertainty reduction rather than a deliverable:** a `.bbl`/`.bib` parser run over sources already fetched under `refs/src/`, reporting only. No network, nothing consumes its output. It answers the largest unknown behind [[WQ-02]] — what fraction of real mathematics papers ship a parseable bibliography and how good the identifiers in them are — and its result *is* that item's trigger.

## Blast radius

`loom/src/loom/digest/extract.py`, `loom/src/loom/scan/bib.py` (already keeps every field in a dict), the digest header format, `docs/specs/diagnostics.md` (one new code), Chapter 8, and the review-queue and graph-default behaviour in Chapter 7 and Chapter 15. The `refs/` layout decision travels with it: one directory per citekey with a `work.toml` carrying the global id and its provenance, so the authoring surface never has to change when the store becomes global-id-keyed.

## Related

[[WQ-02]], [[WQ-03]], [[WQ-04]], [[WQ-05]], [[WQ-06]]; Chapter 8; DR-45 (citekey slug collisions, which this makes cosmetic rather than an error).

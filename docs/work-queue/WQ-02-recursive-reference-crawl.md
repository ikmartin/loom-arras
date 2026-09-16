# WQ-02 · Recursive reference crawl to arbitrary depth

**Repo:** loom

## Trigger

The bibliography parse-rate study that ships with [[WQ-01]] reports above 70% on the depth-1 sources of `demos/relloc` and `demos/acgs`.

## Why deferred

The crawl's whole substrate is other papers' bibliographies, and nobody has measured how often those are actually parseable. If the real rate is 40% the design changes shape entirely, so the study comes first and its number is this trigger.

## Rough design

A breadth-first walk over works, unbounded in depth. Depth 1 is your bibliography; depth 2 is theirs.

**Depth 2 is free.** Once a depth-1 source is fetched its bibliography is already on disk, so knowing the depth-2 set costs no network at all — only parsing what you already have. Network cost begins when you want depth-2 *sources*. So the knob is `fetch_depth`, and known depth always runs one level beyond it.

**The substrate is `.bbl`, not `.bib`.** arXiv does not run BibTeX, so submitters must include the compiled `.bbl`; a `.bib` comes along only when an author tarred their whole directory. Parse both, and prefer a metadata API (OpenAlex, Semantic Scholar) where it covers the work, since those return resolved ids and deduplicated edges with no parsing. Use both together: the API says *which paper*, the source says *which result* — `\cite[Theorem 3.2]{Har77}` is a locator and no metadata API has it.

**Budget by local in-degree, not by BFS order.** A naive cap spends itself on whatever arrives first, so one survey eats it while a targeted research paper is never reached. Three controls compose: expand at most ~40 references from any one work; treat a work with an unusually large bibliography, or typed as a survey or book, as a *sink* that is collected but never expanded; and expand in order of in-degree within the frontier, so a paper four of your references all cite is reached before a survey cited once in passing.

**Depth past 2 needs a topical filter, not a bigger number.** Citation graphs saturate: roughly 30 → 400 → 3k → 15k → 50–100k, and by depth 4 the ball has leaked out of the subfield entirely. What makes a deep crawl a *library* rather than a web crawl is an MSC-class predicate (zbMATH and MathSciNet both carry them). Depth 5 filtered to a set of MSC prefixes is a subfield library; depth 5 unfiltered is a crawl of mathematics.

**Operationally**: 50k works is ~150 GB of arXiv tarballs, so the byte store needs a root outside the quilt ([[WQ-06]]), and 50k sequential arXiv API fetches is precisely what their terms ask you not to do — a crawl that size wants OpenAlex or Semantic Scholar bulk data for the graph and arXiv's S3 bulk access for sources. Check current terms before writing the fetcher.

The output of a deep crawl is a **library** ([[WQ-03]]), not a 50,000-node quilt. The working quilt stays small and points at it.

## Blast radius

A new subsystem in loom, `config.toml` (a `depth` key, which must not be added before it can be honoured, and whose name must not collide with the viewer's existing local-radius control), the corpus store layout, `docs/specs/`, Chapter 8, and arXiv/OpenAlex terms of use.

## Related

[[WQ-01]] (its trigger and its identity model), [[WQ-03]], [[WQ-04]], [[WQ-05]], [[WQ-06]].

# WQ-02 · Recursive reference crawl to arbitrary depth

**Repo:** loom

## Trigger

**Candidates can bind as identities**, or the author accepts a crawl that follows only strong candidates. [[WQ-04]] graduated on 2026-09-17 into plan 0.7 as `loom refs resolve`, which finds identifiers but records them as unconfirmed candidates; a crawl needs to follow them without an author confirming each, and whether a confirmed identity is recorded anywhere but the bibliography is WQ-23's open question. The original trigger was a parse rate above 70%, and plan 0.5's study answered it — but measured the wrong half.

`loom/scripts/bibliography_parse_rate.py`, run on the two fetched works in `demos/relloc`, reports **100% of bibliographies parseable and 9% of 103 entries carrying a usable identifier**. Both numbers matter and the second is the binding one: a crawler can read every bibliography it finds and still cannot follow nine citations in ten, because a formatted `\bibitem` is display text — authors, title, journal, volume, pages — and the bibliography *style* decides whether a DOI is printed, which mathematics styles mostly do not.

So resolution is not a refinement of the crawl, it is its precondition. You cannot follow a citation you cannot identify.

## Why deferred

Nine citations in ten cannot be resolved to a work without an external lookup, so a crawl built today would fetch the tenth and stall. [[WQ-04]] is what removes that.

A second finding from the same study, to carry into the design: **neither fetched paper shipped a `.bbl` or a `.bib`.** Both inlined `\begin{thebibliography}` into a `.tex` file — one in the master, one in an included `bib.tex`. The unit a crawler must cope with is therefore `\bibitem` wherever it occurs, not a file extension, and the plan's original framing of "parse the `.bbl`" was wrong about real submissions.

## Rough design

A breadth-first walk over works, unbounded in depth. Depth 1 is your bibliography; depth 2 is theirs.

**Depth 2 is free.** Once a depth-1 source is fetched its bibliography is already on disk, so knowing the depth-2 set costs no network at all — only parsing what you already have. Network cost begins when you want depth-2 *sources*. So the knob is `fetch_depth`, and known depth always runs one level beyond it.

**The substrate is `\bibitem`, wherever it sits.** arXiv does not run BibTeX, so submitters must supply a formatted bibliography — but they usually do it by pasting `\begin{thebibliography}` into a `.tex` file rather than shipping a `.bbl`, as both of `demos/relloc`'s fetched works do. Parse all three shapes, and prefer a metadata API (OpenAlex, Semantic Scholar) where it covers the work, since those return resolved ids and deduplicated edges with no parsing. Use both together: the API says *which paper*, the source says *which result* — `\cite[Theorem 3.2]{Har77}` is a locator and no metadata API has it.

**Budget by local in-degree, not by BFS order.** A naive cap spends itself on whatever arrives first, so one survey eats it while a targeted research paper is never reached. Three controls compose: expand at most ~40 references from any one work; treat a work with an unusually large bibliography, or typed as a survey or book, as a *sink* that is collected but never expanded; and expand in order of in-degree within the frontier, so a paper four of your references all cite is reached before a survey cited once in passing.

**Depth past 2 needs a topical filter, not a bigger number.** Citation graphs saturate: roughly 30 → 400 → 3k → 15k → 50–100k, and by depth 4 the ball has leaked out of the subfield entirely. What makes a deep crawl a *library* rather than a web crawl is an MSC-class predicate (zbMATH and MathSciNet both carry them). Depth 5 filtered to a set of MSC prefixes is a subfield library; depth 5 unfiltered is a crawl of mathematics.

**Operationally**: 50k works is ~150 GB of arXiv tarballs, so the byte store needs a root outside the quilt ([[WQ-06]]), and 50k sequential arXiv API fetches is precisely what their terms ask you not to do — a crawl that size wants OpenAlex or Semantic Scholar bulk data for the graph and arXiv's S3 bulk access for sources. Check current terms before writing the fetcher.

The output of a deep crawl is a **library** ([[WQ-03]]), not a 50,000-node quilt. The working quilt stays small and points at it.

**Do [[WQ-03]] first if both triggers have fired.** The crawl's payoff is far larger once libraries exist, because a crawl with nowhere to put its result is a large `refs/` directory. And note what the crawl does *not* automate: it gives you the set of works and the edges between them, never the digests. Four hundred works still means four hundred extractions, each compiling a paper, and — if the locators are to be trusted — four hundred verifications against published PDFs. Extraction is mechanical; verification is not. So an automated library is a large corpus quilt with a **complete citation graph and selective digests**, which is the same shape as this item's own "depth 2 is metadata-only" rule seen from the library end.

## Blast radius

A new subsystem in loom, `config.toml` (a `depth` key, which must not be added before it can be honoured, and whose name must not collide with the viewer's existing local-radius control), the corpus store layout, `docs/specs/`, Chapter 8, and arXiv/OpenAlex terms of use.

## Related

[[WQ-01]] (its trigger and its identity model), [[WQ-03]], [[WQ-04]], [[WQ-05]], [[WQ-06]].

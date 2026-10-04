# Lazy digests: a study

Plan 0.18.5b item 4, measured on 2026-10-04. The question is whether the digest results that no document reaches cost enough to make the digest lazy, as the refs audit (`docs/issue-reports/refs-audit-critique-from-agent-2026-10-02.md` §1, recommendation 2) proposed.

## Method

Two copies of the author's quilt were made in a scratch directory, never the original. In each, `config.toml`'s `[refs]` table became `[library]` with `online = true`. Nothing else in the first copy, **all**, was changed.

The second copy, **reached**, keeps every digest file and its header, but cuts each file down to the results the author's text reaches by an edge (an edge in the scan whose source is outside `digests/` and whose target is inside). A reached section keeps only its heading line. Every `digests/*.results.json` is left whole. This stands in fairly for the lazy design: the graph holds only what is cited, and the full extraction stays on disk as the index that `library search` already reads. It was preferred to moving whole digest files out, which would also have removed the reached results of the 12 works that have them and changed what `library` reports.

The cut has one side effect. 26 references from a kept result to a cut result of the same paper now dangle, so lint reports 27 errors instead of 1. That does not affect the timings, but it does shape the design (see Closures below).

Each command was run once to warm it, then three times. The tables give the median wall time on an Apple-silicon laptop, from the working tree at 8a8b4ee plus 0.18.5b's lint change. `loom --version` takes 0.12 s, which is the floor.

## Reach

| | count |
|---|---|
| works in the bibliography with a digest | 52 |
| digested works the author cites (versions counted with their primary) | 35 |
| digested works nothing cites | 17 |
| digest nodes: environments / sections | 3,140 / 887 |
| environments cited directly (68 `postnote` edges, no `\ref` or `\uses`) | 51 |
| sections cited directly | 3 |
| works with a directly cited result | 12 |
| digest keys `loom status` counts as reached (transitively) | 80 |
| the author's own nodes | 84 |
| bytes scanned: digests / everything | 3.23 MB / 3.38 MB |

2.5% of the extracted results are reached, the same share as the audit's 80 of 3,140. Digests are 96% of the text every command scans, and 98% of the nodes.

## Times

| command | all digests | reached only | share of the time spent on unreached digests |
|---|---|---|---|
| `loom status` | 2.03 s | 0.37 s | 82% |
| `loom lint` | 1.80 s | 0.36 s | 80% |
| `loom build`, cached | 2.70 s | 0.55 s | 80% |
| `loom build`, cache invalidated | 76 s (4,144 fragments) | 8.8 s (171 fragments) | 88% |
| `scan()` in process, cold | 2.22 s | 0.17 s | 92% |
| `scan()` in process, tokens cached (the language server's case) | 0.52 s | 0.06 s | 88% |

The uncached build is what follows any change to loom's own code in a checkout, since the render cache keys on it, and any loom upgrade elsewhere.

## Where the time goes

Most of the scan is the tokenizer. A profile of `loom lint` and `loom status` on **all** puts more than half of `scan()` in `scan_environments` → `tokenize`, nearly all of it on digest text. With the tokens cached, the same scan drops from 2.22 s to 0.52 s. `tokenize` caches only in process (`_cached`, for `loom serve` and the language server), so every CLI call tokenizes 3.2 MB of digests again. The rest is `assemble` and `find_edges`, where `postnote_edges` builds locator forms for all 4,027 digest nodes in order to match 68 citations.

`loom status` also spends about 0.4 s in `cli/review.unmatched_cites`. It compares every `\cite` with a postnote (including each digest result's own locator title) against every edge, which is quadratic. Indexing the postnote edges by `(src, label)` removes that cost, whatever happens to digests.

The audit's 31 s `loom status` is gone: 0.18.2's speed work (DR-328) brought it to 2 s before any change here.

## The design the audit proposed

Keep the full extraction as a search index outside the node graph. A result becomes a node only when a document cites it or the author asks for it.

The index already exists. `digests/<ck>.results.json` holds every result's statement, source text, anchor and state, and `library search`, `library read`, `library why`, `library check` and the manifest's `references[ck].results` all read it rather than the nodes. What would change is what the scanner sees. `digests/<ck>.tex` would hold only promoted results, or the scanner would build nodes only for the ids the index says are promoted.

### Scan

`postnote_edges` would match a postnote against the index (taxon, number and locator per result, from `results.json`) instead of against nodes. A match promotes the result. Promotion writes it into the digest's `.tex`, or into a promoted list the scanner reads. Since `scan` reads and never writes, promotion would belong to the commands that write, such as `library update` and `loom build`. A citation to an unpromoted result would otherwise read as unmatched until one of them runs. That staleness is the main new failure mode, and `loom:unmatched-postnote` would have to say which of the two it is.

### Lint

What reaches the author's lint shrinks to the promoted results, which are the ones 0.18.5b's lint-by-citation already counts as the author's. The cited works' heading (115 errors and 65 warnings on this quilt, almost all `loom:duplicate-label`, `dangling-link` and `loom:missing-package` in unreached results) and the line for works nothing cites (40 diagnostics) would mostly disappear. Extraction faults would move to `library check`, against the index.

### Status

The `digests: reached / not_counted` split (80 / 3,060 here) becomes "promoted results", and `--include-digests` has little left to include.

### Closures

A promoted result's own `\ref` to an unpromoted result of the same paper dangles: 26 do on this quilt. Promotion must therefore be transitive over a result's references within its work, which is the 51 → 80 gap `status` already measures, or the bundle must render such a reference from the index. Closures do not grow today from unreached results, because a bundle holds only what its key depends on.

### Search

No change. `library search` already reads `results.json` and page text, never nodes. "Asked for" needs a way to ask: a new option on `library read`, or verifying the result.

### The viewer's Digest view

Today it shows `fragments/digests/<ck>.html`, rendered from the whole `.tex`, and each result also has a node fragment. Lazily, the Digest view would render from the index, either with one fragment per work built from `results.json` or with a new manifest field. Only promoted results would be nodes with their own fragments and edges. This is an interface change, so it would go through the fixture first. It is also where most of the 88% saving on an uncached build comes from.

### `library verify`

A person verifies a result read from the index. Verifying is a request, so it promotes. A verified result's node then exists whether or not anything cites it, as it does today. `moved_anchors` reads `results.json` and is unaffected.

## Recommendation

Do not build it now. Record it as WQ-58 with this trigger: **on a real quilt, lint or status spends most of its time on digest nodes no document reaches.**

By share, the trigger is met on the author's quilt today: 82% of `status` and 80% of `lint`. In absolute terms it is 1.7 s per call over a 0.36 s floor. The cost the author would feel more is the uncached build (76 s against 9 s).

Two cheaper steps take a large part of the saving without the staleness that promotion brings:

- A persistent token cache for digest files, keyed by content hash. Digests change only when `library update` runs, so tokenizing them would be paid once per update rather than once per command. In process, cached tokens already take the scan from 2.22 s to 0.52 s.
- The quadratic `unmatched_cites` in `loom status` (about 0.4 s here).

WQ-58 should name both as the first response. It should keep the lazy design for when, after them, a real quilt still shows `lint` or `status` above about 1 s with most of the time in unreached digest nodes, or a cached build above a few seconds for the same reason. Measure with this study's method: a copy with the unreached results cut out of `digests/*.tex`, three runs each, median.

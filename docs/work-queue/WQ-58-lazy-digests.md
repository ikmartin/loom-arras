# WQ-58 · Lazy digests: the extraction as an index, a result a node only when used

**Repo:** loom, arras

## Trigger

On a real quilt, after the two cheaper steps below are built, `loom lint` or `loom status` still takes above about 1 s with most of it spent on digest nodes no document reaches, or a cached `loom build` takes above a few seconds for the same reason. Measured as [the study](../reports/lazy-digests-study.md) does: a copy with the unreached results cut out of `digests/*.tex`, three runs each, the median.

## Why deferred

On the author's quilt 80 of 3,140 extracted results are reached and digests are 96% of the text every command scans, so the share is met today (82% of `status`, 80% of `lint`) — but the cost is about 1.7 s a command over a 0.36 s floor, and most of it is tokenizing, which a cache removes without the staleness that promoting results on demand brings ([lazy-digests-study.md](../reports/lazy-digests-study.md), 2026-10-04).

## The first response

1. A persistent token cache for digest files, keyed by content hash: digests change only when `loom library update` runs, so they are tokenized once per update rather than once per command (in process, cached tokens take the scan from 2.22 s to 0.52 s).
2. The quadratic `unmatched_cites` in `loom status` (`cli/review.py`), about 0.4 s on the author's quilt.

## Rough design, if the trigger still fires

The full extraction is kept as a search index outside the node graph (`results.json` already is one), and a result becomes a node of the quilt only when the author's text cites it or the author asks for it. What that changes — scan, lint, status, closures (a kept result referencing a cut one), search, the viewer's Digest view, `library verify` — is laid out in the study.

## Blast radius

`scan/` (which digest regions are nodes), `refs/build.py` and `digest/extract.py` (writing the index and the promoted file), `cli/library/read.py` (search over the index), closures (`tex/bundle.py`), arras's Digest view, chapter 8.

## Related

[plan 0.18.5](../plans/0.18-the-command-line.md), whose item 4 measured it; [the refs audit](../issue-reports/refs-audit-critique-from-agent-2026-10-02.md) §1 and recommendation 2.

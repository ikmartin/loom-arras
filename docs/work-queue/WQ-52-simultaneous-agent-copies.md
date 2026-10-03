# WQ-52 · Several agent documents drafted from one document at once

**Repo:** loom, arras

## Trigger

A person wants two agent versions of one document side by side — `loom draft DOC --ai` refuses because a copy of DOC exists, and the person wanted a second one rather than a turn in the first.

## Why deferred

One copy per document is the common case: different agents work in the same copy one after another, and nothing fills `drafting-ai/` with copies (ai-drafting-study §2). The study settled the form a second copy would take and set the bar for building it: added only if it is both simple to build and simple to use. Nobody has yet wanted two.

## Rough design

The derived suffix numbers the copies in base 36: `zk-0001-ai-01` … `-ai-0Z`, `-ai-10` … `-ai-ZZ`, the unnumbered `-ai` staying the first. `plain_key` and `pair_hash` strip any of them, so compare pairs every copy with the source and with each other; each copy records its own bases, so `loom ai drafts`, `loom ai refresh` and `loom adopt` work per copy as they do now. What needs deciding is what comparing two copies of one source means for direction (their common base is the source's version each began from, which may differ), and how Incoming lists two contributions to one document.

## Blast radius

`scan/labels.py` (`DERIVED`, `derived_of`), `reshape/copy.py`, `loom draft --ai`'s refusal, `drafts.py`, `adopt.py`, arras's Incoming and compare, chapters 5.3.1 and 17.7.

## Related

[plan 0.17](../plans/0.17-ai-drafting-and-compare.md), whose umbrella filed this; [compare](../reports/compare-study.md).

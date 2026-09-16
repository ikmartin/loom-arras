# WQ-05 · The contracted work graph

**Repo:** arras

## Trigger

Any quilt exceeds roughly 150 external nodes — the point at which the result graph is mostly other people's theorems and cannot usefully be drawn expanded.

## Why deferred

With one paper's own nodes plus a handful of digest results, there is nothing to contract. The view would be a feature with no data behind it.

## Rough design

There are two graphs at different scales, and **the work graph is the quotient of the result graph by source**: contract every paper's digest to a single node and the `\uses` edges between digests become citation edges. So there is one data structure with a `source` attribute per node, drawn contracted or expanded, not two.

Three views follow:

1. result graph, the quilt's own nodes only;
2. result graph, own nodes plus **reached** external nodes, visually distinct — the default, and it depends on the `reached` primitive from [[WQ-01]];
3. work graph, contracted — for exploring a corpus, and the only sane way to look at anything past depth 1.

**Naming hazard:** the viewer already has a "depth" control meaning local radius in the *result* graph, and [[WQ-02]] introduces crawl depth in the *work* graph. These are different knobs and must not share a name in the configuration or the interface.

## Blast radius

`arras/src/lib/` graph components, the manifest (a per-node source attribute), Chapter 15 §15.5, Chapter 10.

## Related

[[WQ-01]] (the `reached` primitive), [[WQ-02]], [[WQ-13]] (a different scaling problem: how the layout is computed, not what is drawn).

# WQ-24 · An agent's own quilt under `ai/`

**Repo:** loom, arras

## Trigger

Both of: the workbench has landed (the plan that follows the 2026-09-17 design: `drafting/`, `canon/`, the history ledger, the shared id allocator), and a run leaves behind draft nodes that reference one another — three or more `draft-*.tex` files in one run whose `\ref` or `\uses` point at each other — so that checking what the agent proposed means assembling and compiling a document by hand.

## Why deferred

The workbench is not built, so there is no shared allocator for the ai quilt to draw ids from and no ledger to record where a node arrived from. And no run has yet produced a proposal large enough that a directory of loose files was the wrong container for it; the day one does is the day this is worth a quilt.

## Rough design

An ordinary quilt inside the author's, at `ai/quilt/`, which the author's scan already skips because it is under `ai/`. It gives an agent what the author has: ids, `\uses` edges, closures, `loom lint`, `loom bundle`, `loom compile`, and a manifest arras can serve — so an agent can check its own lemma's self-containedness, compile its own proof's closure, build on last week's scaffold, and try "split this lemma in three and reorder the section" at full size where the author can look at the result rather than read a description of it. Moving a node into the author's quilt is a copy.

**Context is shared by position.** `preamble.tex` in the ai quilt is one line, `\input{../../preamble.tex}`; `refs.bib` is the author's by path. The scaffolding command writes both, so an agent cannot drift from the author's macros and bibliography.

**One id space, allocated lazily.** Ids come from the same allocator as the author's, which consults the author's live ids, the retired ids in the ledger, and the ai quilt — so a node is the same object before and after it is copied, and `\label`, `\ref` and `\uses` survive the copy untouched, including references from an agent's new lemma to the author's existing ones. Scratch work carries paper-local labels (`\label{lem:contraction}`) and no id; the agent asks for an id the moment a node becomes a candidate. Provenance is a ledger line naming the run the node arrived from, never a prefix in the id, which would go on saying "an agent wrote this" after the author had rewritten it twice.

**No canon and no history of its own.** The ai quilt is scratch; the author's quilt holds the record, and a node's history begins when it arrives.

**Serving.** Cheaply, `loom serve --quilt ai/quilt --port 8792` in a second terminal. A quilt switcher in arras is the nicer form and waits for this to be used.

**The experiment to run first.** Scaffold an ai quilt by hand, give an agent one real task in it and the same task in a run, and compare. If a quilt only gives the agent more ways to be wrong, the answer is a better run layout, not this item.

## Blast radius

`loom/src/loom/scan/labels.py` (a third source for `next_local`), `loom/src/loom/ai/` (scaffolding under `ai init`, orientation text, `ai check`'s permissions), the ledger's provenance entry, arras's server address handling, Chapter 11.

## Related

[WQ-03](WQ-03-reference-libraries.md): this is a quilt that depends on another, which is that item's subject, and the first real instance of it. [WQ-23](WQ-23-agent-review.md): a proposed revision as a document in a quilt answers its open question about the form of a proposed document.

# WQ-33 · The proposed document: an agent assembling a revision

**Repo:** loom, arras

## Trigger

An agent proposes reordering or restructuring a section, and the author wants to see the result before deciding — which a per-node diff cannot show, because a revision that reorders, rewrites and adds at once has no single preview.

## Why deferred

Carried out of [[WQ-23]] when that item graduated into [plan 0.11](../plans/0.11-run-review-view.md), which builds the review surfaces and not this. The author settled the requirement on 2026-09-17: *an agent can assemble an arbitrary collection of nodes, to propose them as an order or to construct a revision of a section or a subsection.* The selection is chosen, not computed. What is open is its form, and the form should not be guessed before a real revision has been attempted.

## Rough design

A **proposed document** in the run: an ordered selection of node keys with the agent's own connecting prose between them. It **references** nodes rather than copying them, so rereading it shows current text; the closure document `loom compile` builds copies, which is right for a snapshot and wrong for something returned to. It may include the agent's draft nodes and proposed rewrites of existing ones, and it can be commented on as a whole — `loom comment drafting/main.tex MESSAGE` already writes an annotation whose target is a document rather than a key, and 0.11 is where arras learns to show one.

What exists, checked on a scratch copy of the demo quilt: an agent can write such a file in its run as `\input` lines under the quilt's preamble, and `loom compile PATH` runs latexmk on it.

**Still open, and the reason this is an item rather than a plan:** the file's form (a `.tex` spine, or a list of keys with prose that loom renders); how its node rewrites and new nodes are carried (the existing proposal diffs and drafts, or inside it); how it is compared against the section it would replace (`loom linearize` refuses a file that is not a master, so `latexdiff` has nothing to take); how it is accepted, whether as one editor edit or piece by piece; and whether a comment on it uses the same master-path target.

## Blast radius

`loom/src/loom/tex/` for whatever renders or flattens it, `loom linearize`'s refusal, the scanner (which skips `ai/`, so nothing about it is published today), arras for showing it, Chapters 8 and 17.

## Related

[[WQ-23]] (closed; this is one of the two threads it carried that [plan 0.11](../plans/0.11-run-review-view.md) does not build); [[WQ-27]], which applies a single suggestion where this proposes a whole revision; [[WQ-24]].

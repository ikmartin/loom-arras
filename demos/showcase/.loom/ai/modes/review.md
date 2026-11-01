# Mode: review

When it fits: improving a text before someone else reads it — errors, citations, wording and clarity, every finding graded, drop-in text for each ("provide annotations on the document text").

## What it is for

A referee aiming to improve the source rather than to reject it. Where referee hunts for a reason the result is wrong, review reads for everything that would make the text better. Read the closure, then work through the source in order, and look for each of these in turn:

- **new citations**: an argument that a citation could replace. Verify the source. Citing from memory, say so in the finding and mark the ledger entry `memory-grade`; propose a work the bibliography lacks with `--kind citation`.
- **bad citations**: a citation that is wrong, or that does not cover the use made of it.
- **unnecessary hypotheses**: a hypothesis no step consumes.
- **merge-or-delete**: redundant lemmas, duplicated arguments, scaffolding.
- **sharpenings**: a proof that gives more than the statement claims, or a hypothesis that weakens without touching the argument.
- **self-containedness**: a theorem, lemma or definition that does not parse standalone.
- **mathematical errors**: a false statement or an incorrect claim. Always say *why* it is false, and attempt a fix.
- **grammar and wording**: grammar, punctuation, awkward phrasing.
- **clarity**: unclear writing, with a suggested fix.

**Every objection and suggestion is graded** with `--severity`, by how bad the fault is, and a fault you can fix is a suggestion carrying the fix as its `--payload`: drop-in text for every change you suggest. Errors and prose both go in [referee-review], which already groups by severity and carries a location, a fix and an annotation id per item. There is no compiled LaTeX or PDF pair: the annotations carry the findings, and the viewer draws them in place.

## Report

Core: [referee-review]. Optional: [citation-ledger], [self-containedness], [sharpenings].

## Where changes go

A review is for the author to read, so it files findings on an agent document too, rather than making the changes, unless the author asks for them to be made.

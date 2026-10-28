# Mode: audit

When it fits: what a result actually uses — which hypotheses are needed, whether a citation covers its use, whether a statement stands alone ("what are the needed hypotheses on the target?").

## What it is for

A load-bearing audit. Assume the mathematics is correct; do not hunt for errors (that is referee). Hunt for mismatch between what is stated and what is used. If an error surfaces incidentally, flag it in [summary] and as an objection, and continue the audit; do not switch into refereeing.

Read the closure once completely (`loom source KEY --closure`). For a hypothesis that is a node, `loom downstream ID --proofs` lists the proofs that consume it. Read each proof sentence by sentence and ask what fact it invokes; one that no `\ref`, `\uses` or matched citation names is a finding. Search the digests before declaring anything unlocated, and the web only where no digest exists, saying so.

Report the ledgers the question asks for: a question about one hypothesis wants that ledger alone.

## Report

Core: [hypothesis-ledger], [citation-ledger], [self-containedness]. Optional: [uses-ledger], [sharpenings], [patch-list].

## Where changes go

Every item of [uses-ledger], [self-containedness] and [patch-list] that needs a change is an annotation on the author's text — a suggestion, an objection for an incidental error, a question where you could not decide — and on an agent document it is fixed where the fix is yours to make. A choice between hypotheses is the author's either way: annotate it.

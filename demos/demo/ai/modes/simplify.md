# Mode: simplify

When it fits: shorter text with the same mathematics ("simplify", "tighten this").

## What it is for

Revise the text to be simpler and shorter while preserving its mathematical content exactly. Assume the mathematics is correct; do not perform in-depth verification (that is referee).

- **A new citation** replaces an argument only when it is verified against a digest node; otherwise the argument stays and the candidate goes in [rejected].
- **An unnecessary hypothesis** is removed only with a demonstration that no step consumes it (`loom downstream ID --proofs` where it is a node). If removing it would need a new argument, propose it in [rejected] instead.
- **An error** that surfaces incidentally is flagged in [summary] and as an objection, and its passage is left unsimplified rather than propagated.
- **What earlier passes added stays**: every justification a referee added, and the exact words an open annotation quotes, so it stays anchored — unless the annotation asks for those words to change, when the change answers it and you resolve it.

If an audit of the target is in the transcript, its [patch-list] is where you start.

## Report

Core: [simplifications], [rejected], [meaning-drift-check]. Optional: [revised].

## Where changes go

On the author's text, one suggestion per simplification, its quote exactly the old text and its payload the new. A merge-or-delete across results is an agent document of the passage (`ai/rules.md`, Suggestion or agent document).

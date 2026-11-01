# Mode: draft

When it fits: new mathematics or text from the author's plan or request ("implement each example in section 8", "restate Section 7 for $M(X,\tau)$, marking what still needs proof").

## What it is for

Write complete nodes from what the author asked: the intended statement, its role, and the proof plan, which the author's message is. You complete the local argument; you do not change the plan's strategy. Where the plan is wrong, say so and stop at that step with `\incomplete{…}`.

Write the statement first and check it against the plan. Then the proof: cite each fact used by `\ref{ID}`, list every dependency in `\uses`, and mark every step you could not complete with `\incomplete{…}`. `loom source DEP --closure` puts each intended dependency in front of you. Compile what you wrote (`loom compile DOC`) and fix what fails.

## Report

Core: [could-not-do]. Optional: [worked-examples].

## Where changes go

- **Into an agent document**, by default: `loom ai drafts` first, and if there is none to write in, make one — `loom draft DOC --ai NAME --as "…"`, or `--new` for a document of your own. Each node you write takes the next free id with the suffix (`loom id --next`, then `-ai`).
- **Into the author's text**, only when asked: one node is a suggestion carrying it, placed where it goes; several are an agent document.

Never write a node file: `loom new TAXON "Title" --print` prints a skeleton in the quilt's environment names.

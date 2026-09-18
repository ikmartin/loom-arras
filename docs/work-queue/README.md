# Work queue

What is not being done now, and what would make each of it worth doing. **Start here**: this is the one place that says what remains.

**This is not an ordered queue.** Items come out when their trigger fires, not in sequence. Reading it top to bottom tells you what exists, not what to do next; reading the triggers tells you whether anything is ready.

## How it works

- Every item has an **observable trigger** — a condition you can check in thirty seconds. A measurement crossing a threshold, a capability existing, a dependency landing. "Someday" is not a trigger, and an item that cannot get one belongs in a plan or nowhere.
- An item's **"why deferred" is its trigger inverted**: deferred *because* X is missing, trigger *is* X existing. If they do not invert cleanly the item is vague.
- Ids are `WQ-NN` and are **never reused**, so a reference from a chapter or a decision record stays resolvable after the item closes.
- **The cap is 45 active items.** A forty-sixth means promoting, merging or dropping one. Free addition is what kills a list like this; the cap was raised from 20 on 2026-09-17, when the workbench design arrived with a queue's worth of deferred work behind it.
- An item **graduates** to `docs/plans/` when the author commits to building it — not at any size threshold.
- An item **closes** by deleting its file and its row and adding one line to [closed.md](closed.md): a pointer to the plan or record that carries it, or one sentence on why it was dropped.
- `python docs/work-queue/check.py` enforces the mechanical parts, and also that the book carries no unfinished business of its own.

Several triggers below are numbers loom already prints. That is the property to aim for: you find out a port is ready to open by running `loom doctor`, not by remembering to read this file.

## Active

| id | item | repo | trigger |
|---|---|---|---|
| [WQ-03](WQ-03-reference-libraries.md) | reference libraries: one quilt depends on another | loom | a second quilt exists whose digests another quilt wants |
| [WQ-08](WQ-08-nest-sectioning-classes.md) | `\nest` under `\part` and class-specific sectioning | loom | a fixture uses memoir, KOMA-Script or `\part` |
| [WQ-10](WQ-10-locator-normalization.md) | locator normalization beyond English | loom | a digest whose locators do not match its citations |
| [WQ-11](WQ-11-lsp-rename.md) | rename as a loom command with an editor trigger | loom-lsp | renaming an id by hand goes wrong once |
| [WQ-13](WQ-13-graph-at-scale.md) | graph layout precomputed by the publisher | loom, arras | a quilt's graph exceeds roughly 2000 nodes, or the force layout takes over a second |
| [WQ-16](WQ-16-overleaf.md) | the Overleaf procedure | — | cutting the first tagged release |
| [WQ-17](WQ-17-external-user.md) | acceptance criterion 10: an external user | — | someone outside the project has a paper to bring in |
| [WQ-19](WQ-19-publishing.md) | publishing to PyPI and npm | loom, arras | the author decides to release |
| [WQ-22](WQ-22-extraction-node-model.md) | digest extraction shares the node model | loom | extraction and atomize disagree about what a node is |
| [WQ-24](WQ-24-ai-quilt.md) | an agent's own quilt under `ai/`, sharing the author's id space | loom, arras | the workbench has landed, and a run leaves three or more draft nodes that reference one another |
| [WQ-25](WQ-25-history-view.md) | the history view in arras: landmarks, stamps, versions per node, the graph at a step | arras, loom | a quilt's ledger holds three or more canonize steps |
| [WQ-27](WQ-27-applying-suggestions.md) | applying a suggestion: patches, `bundle --with`, editor code actions | loom, editors | one run leaves ten or more payloads |
| [WQ-28](WQ-28-annotated-export.md) | an annotated view exported as LaTeX and PDF | loom, arras | a review has to reach someone who cannot run arras |
| [WQ-29](WQ-29-node-manager.md) | the node manager: fork from history, retire, merge, rename (absorbs WQ-11) | loom, arras, loom-lsp | ten or more forks, or a fork or rename by hand goes wrong once |
| [WQ-30](WQ-30-history-gc.md) | `loom history gc` | loom | `.loom/history/texts/` exceeds a few thousand files or fifty megabytes |
| [WQ-32](WQ-32-modes-against-the-cli.md) | rewrite every mode against loom's CLI, and let the gaps name the missing commands | loom | 0.10 has landed, so the annotation log is the modes' output contract |
| [WQ-33](WQ-33-the-proposed-document.md) | the proposed document: an agent assembling a revision | loom, arras | an agent proposes reordering a section and a per-node diff cannot show the result |
| [WQ-34](WQ-34-write-surfaces.md) | writing through the editor and the viewer | loom, editors, arras | the author works a review without the terminal |

Nineteen active, twenty-six slots of headroom.

Every item above has an observable trigger, which is the rule. The rule does not catch a second failure: **a trigger that is observable and will never be observed is a polite way of saying no.** Such an item looks like a plan and is actually a decline, which is worse than an empty queue because it suggests work is coming. So each review asks two questions, not one — is the trigger checkable, and will it ever fire? Five items failed the second on 2026-09-16 and were closed for it; their reasons are in [closed.md](closed.md), and their ids are retired rather than reused.

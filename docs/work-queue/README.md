# Work queue

What is not being done now, and what would make each of it worth doing. **Start here**: this is the one place that says what remains.

**This is not an ordered queue.** Items come out when their trigger fires, not in sequence. Reading it top to bottom tells you what exists, not what to do next; reading the triggers tells you whether anything is ready.

## How it works

- Every item has an **observable trigger** — a condition you can check in thirty seconds. A measurement crossing a threshold, a capability existing, a dependency landing. "Someday" is not a trigger, and an item that cannot get one belongs in a plan or nowhere.
- An item's **"why deferred" is its trigger inverted**: deferred *because* X is missing, trigger *is* X existing. If they do not invert cleanly the item is vague.
- Ids are `WQ-NN` and are **never reused**, so a reference from a chapter or a decision record stays resolvable after the item closes.
- **The cap is 20 active items.** A twenty-first means promoting, merging or dropping one. Free addition is what kills a list like this.
- An item **graduates** to `docs/plans/` when the author commits to building it — not at any size threshold.
- An item **closes** by deleting its file and its row and adding one line to [closed.md](closed.md): a pointer to the plan or record that carries it, or one sentence on why it was dropped.
- `python docs/work-queue/check.py` enforces the mechanical parts, and also that the book carries no unfinished business of its own.

Several triggers below are numbers loom already prints. That is the property to aim for: you find out a port is ready to open by running `loom doctor`, not by remembering to read this file.

## Active

| id | item | repo | trigger |
|---|---|---|---|
| [WQ-02](WQ-02-recursive-reference-crawl.md) | recursive reference crawl to arbitrary depth | loom | [WQ-04](WQ-04-identity-resolvers.md) has landed: 0.5's study found only 9% of a fetched bibliography's entries carry an identifier, so resolution is the crawl's precondition |
| [WQ-03](WQ-03-reference-libraries.md) | reference libraries: one quilt depends on another | loom | a second quilt exists whose digests another quilt wants |
| [WQ-04](WQ-04-identity-resolvers.md) | network identity resolvers (Crossref, zbMATH, OpenAlex) | loom | `loom:unresolved-work` exceeds a quarter of a real bibliography |
| [WQ-05](WQ-05-work-graph-view.md) | the contracted work graph (papers, not results) | arras | any quilt exceeds roughly 150 external nodes |
| [WQ-06](WQ-06-byte-cache.md) | a shared cache for fetched bytes | loom | `refs/` across all quilts on one machine exceeds a few GB, or a quilt needs its fetched bytes on another disk |
| [WQ-07](WQ-07-atomize-relative.md) | `atomize --relative` | loom | a quilt wants its section files to read as standalone sections |
| [WQ-08](WQ-08-nest-sectioning-classes.md) | `\nest` under `\part` and class-specific sectioning | loom | a fixture uses memoir, KOMA-Script or `\part` |
| [WQ-09](WQ-09-tex-root-directive.md) | `% !TEX root` recorded for loose files | loom | a loose file needs to name the master it was written for |
| [WQ-10](WQ-10-locator-normalization.md) | locator normalization beyond English | loom | a digest whose locators do not match its citations |
| [WQ-11](WQ-11-lsp-rename.md) | rename as a loom command with an editor trigger | loom-lsp | renaming an id by hand goes wrong once |
| [WQ-13](WQ-13-graph-at-scale.md) | graph layout precomputed by the publisher | loom, arras | a quilt's graph exceeds roughly 2000 nodes, or the force layout takes over a second |
| [WQ-14](WQ-14-manifest-schema.md) | `manifest.schema.json` derived from the specification | loom | a third implementation of the interface, or a manifest regression a schema would have caught |
| [WQ-15](WQ-15-ai-runner.md) | the AI runner (`specs/runner.md`) | loom | an agent needs to be run by loom rather than beside it |
| [WQ-16](WQ-16-overleaf.md) | the Overleaf procedure | — | cutting the first tagged release |
| [WQ-17](WQ-17-external-user.md) | acceptance criterion 10: an external user | — | someone outside the project has a paper to bring in |
| [WQ-18](WQ-18-codex-session.md) | the Codex half of the AI layer | loom | Codex is installed on the machine |
| [WQ-19](WQ-19-publishing.md) | publishing to PyPI and npm | loom, arras | the author decides to release |
| [WQ-21](WQ-21-arras-pdf-viewer.md) | arras displays PDFs and resolves reference links into them | arras | plan 0.5 has landed — a decision, not an observation |
| [WQ-22](WQ-22-extraction-node-model.md) | digest extraction shares the node model | loom | extraction and atomize disagree about what a node is, or a corpus makes the per-paper LaTeX compile the bottleneck |

Nineteen active, one slot of headroom. WQ-01 graduated to `docs/plans/0.5-reference-identity-and-layout.md` and WQ-12 was dropped; both are in [closed.md](closed.md), and their ids are retired rather than reused.

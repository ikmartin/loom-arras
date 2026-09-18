# WQ-29 · The node manager: forks from history, retiring, merging, renaming

**Repo:** loom, arras, loom-lsp

## Trigger

A quilt holds ten or more forks, or a fork or rename done by hand goes wrong once — the same trigger [WQ-11](WQ-11-lsp-rename.md) carries for rename, which this item absorbs.

## Why deferred

`loom fork` is built with the workbench plan because `linearize --fork` needs it. Everything else a person does to nodes as objects — fork from an old version in a view, retire a node deliberately, merge two forks back, rename an id — waits until there are enough nodes with history for the operations to be worth a surface.

## Rough design

Ancestry is already a ledger entry (`rl-0042 forked from rl-0007@2`) and versions are content-addressed, so none of these needs new storage:

- **Fork from history**, in the history view: pick `rl-0007@2`, name or allocate an id, choose the document it lands in; the same command underneath.
- **Retire**: mark an id as deliberately absent, so `orphan-node` and `undefined-node` stop mentioning it and a later recovery is reported as a recovery, not a reuse.
- **Merge**: two forks back into one id, as a fork in reverse with both parents recorded.
- **Rename**: WQ-11's operation — an id change as a loom command that the editor triggers, rewriting every `\ref`, `\uses` and postnote through the language server rather than by hand.

Arras shows a node's family — ancestors, forks, the version it was forked at — on the node page.

## Blast radius

`loom/src/loom/reshape/ids.py`, the ledger's ancestry entries, `loom-lsp/` for rename, a node-page component, Chapter 5.

## Related

[WQ-11](WQ-11-lsp-rename.md), which this absorbs when it fires; [WQ-25](WQ-25-history-view.md).

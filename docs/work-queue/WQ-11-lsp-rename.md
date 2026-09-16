# WQ-11 · Rename as a loom command with an editor trigger

**Repo:** loom-lsp, loom

## Trigger

Renaming an id by hand goes wrong once — a stale `\ref`, or a ledger row orphaned from the node it accepted.

## Why deferred

An LSP rename would have to rewrite every `\ref` **and every ledger row**, which makes it a write into the quilt's review history rather than a text edit. That is a loom command with an editor trigger, not an LSP capability, and no one has yet needed it badly enough to justify a command that edits acceptances.

## Rough design

`loom rename OLD NEW`: rewrite the id at its definition, every `\ref`, `\uses` and `\cite[…]` site, and the ledger's table key, preserving the acceptance and its content hash (the text does not change, so the hash must not either). The editor client offers it as a rename that shells out and confirms first, like the other code actions that write.

## Blast radius

A new loom command and its CLI-reference row, the ledger format's key rewriting, `loom-lsp` code actions, Chapter 16, Chapter 7 (acceptance survives a rename).

## Related

Chapter 16; the write-confirming code actions already in `loom-lsp`.

# WQ-27 · Applying a suggestion: patches, previews, editor code actions

**Repo:** loom, loom-lsp, loom-nvim, loom-vscode

## Trigger

One run leaves ten or more payloads, so that copying each by hand is the slow part of a review. Until then, preview-and-copy is the intended pattern: it keeps every decision with the author and costs nothing to build.

## Why deferred

The author chose preview-and-copy on 2026-09-17 for exactly its intentionality. Applying a suggestion automatically is the WorkspaceEdit line from WQ-23's build order, and it is only worth its machinery once a review produces more text than a person can paste.

## Rough design

Three pieces, in order:

1. `loom suggest show <annotation>` prints the payload as a patch against the target's current text, refusing when the annotation's hash no longer matches — the stronger form of `git apply --check`. Loom never applies it.
2. `loom compile KEY --with <annotation>` compiles the node as if the suggestion were taken: the existing `--with` preview generalised from a proposal diff to a payload with a placement; `payload` and `placement` landed in 0.10 (DR-147), so this item's inputs now exist.
3. Proposals as editor code actions: the language server returns a `WorkspaceEdit` carrying the hash it was written against, marked `needsConfirmation` so VS Code previews it; loom-nvim shows the diff itself. Promoting a draft node is a `CreateFile` edit. Then hand-offs between arras and the editor (`vscode://file/PATH:LINE`; `nvim --listen` and `--remote`), and the AI commands in the editor clients.

Accepting a suggestion resolves its annotation as applied with the resulting hash, so the next stamp or canonize records what changed and why.

## Blast radius

`loom/src/loom/ai/`, `loom/src/loom/cli/`, `loom/src/loom/tex/bundle.py`, `loom-lsp/` and both editor clients, Chapter 16.

**What 0.11 already built and this item must not rebuild** (checked 2026-09-18): a suggestion's payload is shown in red beneath its anchor, placed by its `placement` hint, with copy and copy-for-chat beside it. Everything up to applying is therefore done, and what is missing is exactly the act this item is named for. The write API is served and has five review endpoints; applying is not one of them, because applying edits the author's source and nothing in the write API touches a source file.

## Related

[[WQ-23]] (closed; absorbed into [plan 0.11](../plans/0.11-run-review-view.md)), whose build order this is; [[WQ-26]] (closed; absorbed into [plan 0.11](../plans/0.11-run-review-view.md)), which builds the surfaces a suggestion is applied from.

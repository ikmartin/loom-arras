# WQ-49 · Rework the editor clients

**Repo:** loom-lsp, loom-nvim, loom-vscode

**Status: deprecated and breakable.** The three clients are out of date with loom and are not maintained in the meantime. A change to loom may break them, and nobody needs to keep them working, update their tests, or hold a loom change back because of them. Their suites run in `clients.yml` only when a client's own files change, and a red run there blocks nothing but the loom-nvim mirror.

## Trigger

Someone starts to work seriously in a quilt and wants loom inside their editor.

## Why deferred

Nobody works in a quilt from an editor yet, so there is no use to design the clients against. They were built before sessions, the drafting layout and the annotation log, and a patch now would only chase a loom that is still moving.

## Rough design

Start from what the person working in the quilt actually asks for. Then decide what survives from each client, rather than restoring what exists. Before relying on the language server, fix one known fault: `loom_lsp/workspace.py:uri_of` resolves symlinks, so a quilt under a symlinked path gets back URIs its editor never opened. That breaks definitions, the call hierarchy and atomize. The editor parts of WQ-27 and WQ-29 wait on this item. From WQ-34 (closed 2026-10-26): hand-offs between arras and the editor, the reverse of the open-in-arras action, as `vscode://file/PATH:LINE` for VS Code and a server socket (`nvim --listen`, `--remote`) for Neovim. An agent in an editor that speaks MCP (VS Code, Zed, JetBrains) attaches to loom through plan 0.21's server with no client of loom's own, so what the editor clients are for is the person's own work in the source.

## Blast radius

`loom-lsp/`, `loom-nvim/`, `loom-vscode/`, `.github/workflows/clients.yml`, `.github/workflows/mirror-nvim.yml`, and the clients' READMEs.

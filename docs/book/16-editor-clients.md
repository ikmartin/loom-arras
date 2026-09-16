# 16. Editor clients

**[decided]** Three projects exist beside loom and arras: a language server and two editor plugins. They are clients. P8 holds unchanged: no loom command requires any of them, none of them is assumed by anything in this book, and a quilt edited in a plain text editor loses nothing but convenience.

They are separate repositories because they have separate release cycles, separate ecosystems, and separate dependencies, and because a reader who wants only loom should not have to build a TypeScript extension to get it.

| project | what it is | repository |
|---|---|---|
| `loom-lsp` | a language server over stdio, a Python package depending on `loomtex` and `pygls` | `loom-arras/loom-lsp` |
| `loom-nvim` | a Lua plugin for lazy.nvim | `loom-arras/loom-nvim` |
| `loom-vscode` | a TypeScript extension | `loom-arras/loom-vscode` |

## 16.1 What the server does, and what it does not

**[decided]** Everything the server answers comes from loom's own entry points: `scan` for the analysis, `all_diagnostics` for what `loom lint` reports including the codes the review ledger contributes, `Assembly.labels` for the definition table, `resolve_key` for key resolution, and `Records` for states. It runs no analysis of its own and contains no second parser. If loom is wrong about something, the editor is wrong about it in the same way, which is the point.

**[decided]** It finds the quilt by walking up from the file being edited to a `config.toml` holding a `[quilt]` table, and refuses politely when there is none. An ordinary LaTeX file is untouched, so a general-purpose LaTeX plugin keeps every buffer that is not part of a quilt.

**[decided]** Open buffers are held as an overlay and the quilt is rescanned on a quarter-second debounce; every request is answered from the last good scan. A full scan is 100 to 170 ms on real papers, which is comfortable at that delay and would not be per keystroke. A scan that raises leaves the last good result in place, so a half-written buffer never takes the editor's diagnostics away.

**[decided]** What it provides: diagnostics with their codes and a link to `specs/diagnostics.md`; go to definition for `\ref`, `\eqref`, `\cref`, `\uses`, `\cite`, `\input` and `\nest`; find references; hover with the taxon, title, number in the default master, state and staleness, and the first lines of the statement; a document symbol tree with proofs under their statements; completion of ids and aliases with their titles, citekeys from the bibliography, taxa from the preamble closure, `% !LOOM` directive keys, and digest node ids after `\cite[`; and code actions.

**[decided]** A code action that is a pure edit — adding a `\uses` entry the proof references but does not list, which `loom:uses-missing` already finds — is applied as a workspace edit. Every other action is a `loom` command line the client runs after confirming, because it writes to the quilt and the author should see what is about to happen. The server itself never writes.

**[decided]** Positions are converted between loom's code-point offsets into CRLF-normalised text and the client's negotiated encoding in one module, and nothing else in the server does arithmetic on a column. The two disagree for any character outside the Basic Multilingual Plane and for any file with CRLF line endings, and both cases are tested.

## 16.2 The Neovim client

**[decided]** It registers the server through Neovim 0.12's `vim.lsp.config` and `vim.lsp.enable`, falling back to `nvim-lspconfig`, and attaches only inside a quilt. It complements a general LaTeX plugin rather than replacing one: vimtex keeps the `tex` filetype and this client attaches beside it.

**[decided]** Eight commands put loom on the command line — status, lint into the quickfix list, new, accept, serve, open in arras, bundle, deps — each building an argument vector rather than a shell string, and the ones that write confirming first. A statusline function names the node under the cursor.

## 16.3 The VS Code client

**[decided]** It activates only inside a quilt and starts a client for the server there; in a plain LaTeX folder it starts nothing. Eight palette entries under `Loom:` mirror the Neovim set, and a status bar item names the node under the cursor.

**[decided]** Opening a node **launches the browser** rather than embedding a webview. Arras is a web application; a browser tab is what it wants to be, and it is the same page `loom serve` already offers. A webview would be a second rendering surface to keep in step with the first, for no gain.

**[decided]** `LOOM_BIN` and `LOOM_LSP` in the environment override the two path settings. An extension host does not inherit a shell's `PATH`, so a server installed in a virtual environment cannot be found by name, and writing an absolute path into a user's settings is worse than the problem.

## Open questions

- Whether the server should offer rename, which would have to rewrite every `\ref` and every ledger row and is therefore a loom command with an editor trigger rather than an LSP rename. **[deferred]**
- Whether an Emacs client is worth writing, given that `eglot` needs only the server and a root function. **[deferred]**
- Whether the code actions that write should become one `loom.run` command the clients share, rather than each client building the same argument vectors. **[assumed]** They should; the server already returns the vector, and only the confirmation differs.

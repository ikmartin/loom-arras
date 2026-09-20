# 16. Editor clients

**[decided]** Three projects exist beside loom and arras: a language server and two editor plugins. They are clients. P8 holds unchanged: no loom command requires any of them, none of them is assumed by anything in this book, and a quilt edited in a plain text editor loses nothing but convenience.

They are directories of this repository, each with its own release cycle, ecosystem and dependencies: a reader who wants only loom builds only `loom/`, and nothing here is built to get it. They were separate repositories until a change crossing the server and both plugins proved to be three pull requests nothing tied together (DR-196). `loom-nvim/` is additionally mirrored to a repository of its own, since a Neovim plugin manager installs from a repository whose root is the plugin.

| project | what it is | directory |
|---|---|---|
| `loom-lsp` | a language server over stdio, a Python package depending on `loomtex` and `pygls` | `loom-lsp/` |
| `loom-nvim` | a Lua plugin for lazy.nvim | `loom-nvim/` |
| `loom-vscode` | a TypeScript extension | `loom-vscode/` |

## 16.1 What the server does, and what it does not

**[decided]** Everything the server answers comes from loom's own entry points: `scan` for the analysis, `all_diagnostics` for what `loom lint` reports including the codes the review ledger contributes, `Assembly.labels` for the definition table, `resolve_key` for key resolution, `Records` for states, `search_entries` for what `loom search` finds, and the scan's graph for what `loom deps` reports. It runs no analysis of its own and contains no second parser. If loom is wrong about something, the editor is wrong about it in the same way, which is the point.

**[decided]** It finds the quilt by walking up from the file being edited to a `config.toml` holding a `[quilt]` table, and refuses politely when there is none. An ordinary LaTeX file is untouched, so a general-purpose LaTeX plugin keeps every buffer that is not part of a quilt.

**[decided]** Open buffers are held as an overlay and the quilt is rescanned on a quarter-second debounce; every request is answered from the last good scan. A full scan is 100 to 170 ms on real papers, which is comfortable at that delay and would not be per keystroke. A scan that raises leaves the last good result in place, so a half-written buffer never takes the editor's diagnostics away.

**[decided]** What it provides: diagnostics with their codes and a link to `specs/diagnostics.md`; go to definition for `\ref`, `\eqref`, `\cref`, `\uses`, `\cite`, `\input` and `\nest`; find references; hover with the taxon, title, number in the default master, state and staleness, and the first lines of the statement; a document symbol tree with proofs under their statements; completion of ids and aliases with their titles, citekeys from the bibliography, taxa from the preamble closure, `% !LOOM` directive keys, and digest node ids after `\cite[`; workspace symbols, which are every key `loom search` finds for the query, named with taxon and title, so a node is found by title, alias, tag or id; dependencies as a call hierarchy, outgoing calls being what a node's statement and proofs use and incoming calls what uses it, each with its reference sites; inlay hints naming the taxon, number and title of what each reference and inclusion points to; and code actions.

**[decided]** A code action that is a pure edit — adding a `\uses` entry the proof references but does not list, which `loom:uses-missing` already finds — is applied as a workspace edit. Every other action is a command the editor carries out: `loom.run`, an argument vector and a confirmation the editor asks before running a command that writes, because it writes to the quilt and the author should see what is about to happen; and `loom.open`, a statement's key, which the editor opens in arras on the server it owns. The server itself never writes, registers no commands, and knows no server URL: a command a server advertises is routed back to the server by the VS Code client, and only the editor knows where its `loom serve` is.

**[decided]** Two actions reshape the node under the cursor, and both are workspace edits rather than commands, because loom plans them and the editor applies them (6.4.2): *atomize* creates `nodes/<id>.tex` and replaces the node's region with its inclusion line in one edit, whose effect on the draft the editor's undo reverses, the created file staying on disk; *give this node an id* inserts `\label{<next free id>}` and is offered exactly when a missing id is what refuses the atomize. A client that cannot carry a file creation in a workspace edit is offered neither, and runs `loom atomize --key` as a command instead.

**[decided]** Positions are converted between loom's code-point offsets into CRLF-normalised text and the client's negotiated encoding in one module, and nothing else in the server does arithmetic on a column. The two disagree for any character outside the Basic Multilingual Plane and for any file with CRLF line endings, and both cases are tested.

## 16.2 The Neovim client

**[decided]** It registers the server through Neovim 0.12's `vim.lsp.config` and `vim.lsp.enable`, falling back to `nvim-lspconfig`, and attaches only inside a quilt. It complements a general LaTeX plugin rather than replacing one: vimtex keeps the `tex` filetype and this client attaches beside it.

**[decided]** Eight commands put loom on the command line — status, lint into the quickfix list, new, accept, serve, open in arras, bundle, deps — each building an argument vector rather than a shell string, and the ones that write confirming first. A statusline function names the node under the cursor.

**[decided]** A session owns its servers: one `loom serve` per quilt, on a port the plugin finds free and passes as `--port`, in a tmux pane below Neovim's own when Neovim runs inside tmux and in an unentered terminal split otherwise. Open in arras starts it when it is not running, waits until the manifest answers, says where it started, and leaves the cursor in the file; quitting Neovim stops every server the session started. Two sessions on one quilt run two servers over the same files, which show the same thing, and never compete for a port. Code actions' `loom.run` and `loom.open` are carried out by the plugin.

**[decided]** Compiling stays vimtex's. A master in `drafting/` names everything relative to the quilt root (P12), and vimtex runs latexmk in the master's own folder, so while a file inside a quilt is the current buffer the plugin puts the quilt root first on `TEXINPUTS` and `BIBINPUTS` in Neovim's own environment, which the latexmk vimtex starts inherits; a file outside any quilt restores the original values. The quilt holds no search path and its source depends on none: the variables are the editor adapting to how it launches TeX, and they exist only in that Neovim process.

## 16.3 The VS Code client

**[decided]** It activates only inside a quilt and starts a client for the server there; in a plain LaTeX folder it starts nothing. Eight palette entries under `Loom:` mirror the Neovim set, and a status bar item names the node under the cursor. A window owns its servers as a Neovim session does, one `loom serve` per quilt on a free port, run in a terminal that is not brought forward and disposed when the window closes, and it carries out `loom.run` and `loom.open` itself.

**[decided]** LaTeX Workshop, which compiles in the main file's folder by default, is made to compile a quilt from its root through its own setting `latex-workshop.latex.build.fromFolder`, written to the workspace folder's settings only after the author agrees, once per quilt or on demand from the palette; before LaTeX Workshop 10.15.0 the boolean `fromWorkspaceFolder` serves a quilt that is its workspace folder. A setting the author can see and remove, rather than a changed search path inside the extension host, is what a VS Code user expects and can debug.

**[decided]** Opening a node **launches the browser** rather than embedding a webview. Arras is a web application; a browser tab is what it wants to be, and it is the same page `loom serve` already offers. A webview would be a second rendering surface to keep in step with the first, for no gain.

**[decided]** `LOOM_BIN` and `LOOM_LSP` in the environment override the two path settings. An extension host does not inherit a shell's `PATH`, so a server installed in a virtual environment cannot be found by name, and writing an absolute path into a user's settings is worse than the problem.

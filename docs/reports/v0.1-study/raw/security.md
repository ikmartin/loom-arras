# v0.1 security review — raw findings

Defensive review of loom (`loom/`) and arras (`arras/`) at `v01-study` (= main, 71621877), ahead of the v0.1 pilot where 2–4 mathematicians run `loom serve` and an AI agent in their own quilt on their own Macs. Scope and method: the six-item brief. Everything below was reproduced on copies of `demos/showcase` in a scratch directory, against servers I started on localhost:48700, with `XDG_CONFIG_HOME` pointed at scratch; the author's running servers (8791/8792) and real quilts were not touched. Every proof of concept wrote only marker files inside the scratch directory or read a dummy file I planted there. Environment: TeX Live 2024, Python 3.13, `make4ht`/`latexmk`/`lualatex` all present.

Bottom line first. The two sanitisers that matter most are good: the Markdown HTML allowlist (`loom/raw_html.py`) and the TeX4ht-output normaliser (`loom/render/normalise.py`) both rebuild from an allowlist and escape every value, and TeX code execution via `\directlua`/`\write18` is blocked by TeX Live's default restricted shell-escape (confirmed by running it). The real problems are elsewhere: a `python -m loom` module-shadowing hole that is arbitrary code execution from quilt contents, a DNS-rebinding hole in the HTTP server that leaks the write token and the whole quilt to a web page, untrusted TeX that can read any file the user can, an HTML-file-in-a-quilt script that can exfiltrate the quilt to the internet, and an agent boundary that is advice rather than enforcement.

---

## SEC-1 — `loom mcp` runs `python -m loom` from the quilt, so a file in the quilt can run as the user (code execution)

What it is. The MCP server runs every tool as a subprocess `[sys.executable, "-m", "loom", *words]` with `cwd=root` (the quilt): `loom/src/loom/mcp/server.py:204`, in `_run`. Python's `-m` puts the current working directory on the front of `sys.path`, so a top-level `loom.py` or `loom/` package sitting in the quilt root shadows the installed `loom` and its code runs instead — on every tool call, as the user, outside loom's own write API and any agent guard.

How I showed it. In a scratch dir containing a `loom.py` whose body writes a marker, `.venv/bin/python -m loom --version` (cwd = that dir, `AI_AGENT=1`, as `_run` does) printed `SHADOW LOOM RAN`, wrote the marker `markers/PYTHON_M_LOOM_SHADOW`, and the real `loom --version` never ran. `sys.path[0]` was confirmed to be the cwd. The fix below (`-P`) was then confirmed to run the real loom and leave no marker.

Who could exploit it and what they need. Anyone who can place a file named `loom.py`/`loom/__init__.py` in the quilt root: a co-author whose quilt the pilot opens, a cloned/downloaded quilt, or — most realistically for the threat model — the AI agent itself. The agent writes files in the quilt directly; a prompt injection in a cited paper (item 4) that says "create a helper `loom.py` in the project root" turns the next MCP tool call into attacker code running as the user. The console-script launch path (`loom/src/loom/ai/clients.py:94` `command()`) prefers the `.venv/bin/loom` script, which is *not* shadowed, so the MCP server's own startup is usually safe; the per-call `_run` is the hole.

How bad for a pilot. Critical. It is unsandboxed code execution triggered by ordinary use, and it converts an agent prompt-injection (normally confined to loom's API) into full code execution on the pilot's Mac.

Fix. Stop putting the cwd on `sys.path`: add `-P` (or set `PYTHONSAFEPATH=1` in the env) in `_run`. Both were tested and neutralise the shadow. A belt-and-braces alternative is to launch with the resolved console-script path from `ai.clients.command()` instead of `-m loom`.

Files the fix owns. `loom/src/loom/mcp/server.py` (`_run`).

Size. One line.

---

## SEC-2 — the HTTP server does not check the Host header: a web page can read the whole quilt and steal the write token by DNS rebinding

What it is. The write token is a CSRF token, not a login (by design: `loom/src/loom/render/serve.py:119` `write_serve_json`). Cross-origin protection rests entirely on `from_elsewhere()` (`serve.py:69`), which inspects `Origin` and `Sec-Fetch-Site` but never the `Host` header. The frames server does check Host (`FramesHandler._target`, `serve.py:598`); the main `LoomHandler` does not. So a page served from an attacker domain whose DNS is rebound to `127.0.0.1` becomes "same-origin" with the loom server: a same-origin `GET` carries no `Origin` and `Sec-Fetch-Site: same-origin`, both of which `from_elsewhere` accepts.

Consequences, each reproduced against localhost:48700:
- `GET /_api` with no `Origin` returns the discovery JSON including `"token"` and the frames-origin port. (Cross-origin `GET /_api` with an `Origin` header is correctly refused — the control case.)
- `GET /_files/<path>`, `GET /build/<path>`, `GET /digests/storage/<path>` require **no token at all** (`serve.py:262` `_resolve`, `do_GET`), so under rebinding a page reads every shown project file (drafts, notes, library). I read my planted `notes/private-dummy.md` back through `/_files/` with a spoofed `Host`.
- `GET /_api/here` (reading place + selected text) needs the token, which the first call just leaked.

What a rebound page cannot do: writes. A browser attaches `Origin` to every `POST`, and under rebinding that is the attacker origin, which `from_elsewhere` refuses — I confirmed `POST /_api/change-keep` with the stolen token and `Origin: http://attacker.evil:48700` is rejected `refused`. So rebinding is read/exfiltration + token theft, not remote write. Still serious: a mathematician's unpublished work and the token leave the machine to any site they happen to have open while `loom serve` runs on the default port (8791/8792, both guessable; the attacker can also scan).

How bad for a pilot. Serious. Confidentiality of the entire quilt, plus token disclosure, from a drive-by web page.

Fix. Give `LoomHandler` the same Host allowlist `FramesHandler` already has: refuse any request whose `Host` is not `127.0.0.1:<port>` or `localhost:<port>`. This closes rebinding for the token, `/_api`, and the file routes in one place.

Files the fix owns. `loom/src/loom/render/serve.py` (`LoomHandler.do_GET`/`do_POST`/`_resolve`, or a shared Host check beside `from_elsewhere`).

Size. Small (a few lines; the frames handler is the template).

---

## SEC-3 — untrusted TeX can read any file the user can read; loom sets no kpathsea hardening

What it is. loom compiles quilt and (potentially) cited TeX with `latexmk -norc …` (`loom/src/loom/tex/runner.py:249`) and `make4ht …` (`loom/src/loom/tex/tex4ht.py:462`). Good news, all verified: `-norc` ignores a quilt `latexmkrc`; no `-shell-escape` is passed; `make4ht`'s Lua take-over files (`.mk4`, `.make4ht`, `tex4ht.env`, `.tex4ht`) are stripped before the run (`CARRIED`, `tex4ht.py:25`, `_prepare`); the staging copy forbids symlinks; and `\directlua{os.execute(...)}`/`io.popen` are blocked by TeX Live's default restricted shell-escape — I ran both from a `lualatex` document (`% !TEX program = lualatex` is honoured, `scan/preamble.py:109`) and neither marker was created. So arbitrary **code** execution from a compiled document is not reachable with the stock config.

The residual: this TeX Live has `openin_any = a` (checked with `kpsewhich`), and loom sets nothing to tighten it (`runner.py`'s env is only `tex_date()`). So a document can `\input{/absolute/path}` and read any file the user can read, embedding its contents in the rendered PDF/HTML. I planted `outside/loot.tex` outside the compile directory and compiled a document that `\input`s it by absolute path; the log shows TeX opened the absolute path and pulled `LOOT_abc123_outside_the_compile_dir` into the input stream. With valid-LaTeX contents it prints into the output. Because the output lands under `/build/`, this chains with SEC-2: untrusted TeX reads `~/.ssh/id_rsa` (or another quilt) into the PDF, and a rebinding page reads the PDF off `/build/` — off-machine exfiltration of arbitrary files.

Who could exploit it and what they need. A cited arXiv source the pilot adds, or a co-author's `.tex` opened/compiled in the quilt.

How bad for a pilot. Serious (arbitrary local file read; critical in combination with SEC-2).

Fix. Set hardened kpathsea variables in the env of every TeX subprocess: `openin_any=p`, `openout_any=p`, `shell_escape=0` (defence in depth even though shell-escape is already off). I confirmed `openin_any=p` in the env makes the absolute `\input` fail and the loot absent, and `shell_escape=0` blocks even a restricted `\write18`. Note this may need to stay `r` (not `p`) for documents that legitimately `\input` a sibling via `../macros`; `r` (no absolute, no parent-of-root, no dotfiles) is the right level and still blocks the attack.

Files the fix owns. `loom/src/loom/tex/runner.py` (`compile_tex` env), `loom/src/loom/tex/tex4ht.py` (`_pass` env; `extractbb`/`dvisvgm` calls inherit it).

Size. Small (extend the two env dicts; verify a couple of real papers still build).

---

## SEC-4 — the agent boundary is advice, not enforcement

What it is. "Only the author may" is enforced two ways, both forgeable by anything that can spawn a subprocess or craft one HTTP request:

1. CLI guard. `refuse_under_agent` fires only when an agent-marker environment variable is set (`AI_AGENT`, `CLAUDECODE`, …: `loom/src/loom/cli/_common.py:217`, `agent_marker`). The module's own docstring says loom reads them "only to refuse what an agent may not do … never to change what any other command does." An agent with a shell runs `env -u AI_AGENT -u CLAUDECODE loom …` and the guard is silent.
2. Write API. Every author-only endpoint decides with `is_agent(_str(body, "author") or who)` (`loom/src/loom/render/api.py:128,188,285,415,517,596,…`), and `is_agent` (`_common.py:257`) is just a substring test for the words `agent/ai/bot/assistant` in a **self-declared** name; `who` defaults to the person's configured reviewer identity. Omit `author` (or name a person) and the check passes.

The token that gates the write API lives in `.loom/serve.json` and the agent can read it (SAFE-11). I read the token from the scratch quilt's `serve.json`, then as a non-browser client (so I set `Origin: http://127.0.0.1:48700` myself — a header only a browser is forced to tell the truth about) POSTed `change-keep {"all":true}` with the token and no `author`: loom answered `{"ok": true, "result": "kept 2 changes; a version of talk.tex is kept"}`. The same call declaring `"author":"Referee (Agent)"` returned `403 author-only`. So an agent can accept its own suggested edits, add to the library, restore versions, and change settings — all "author-only" acts — by reading the token and not calling itself an agent.

What a hostile document could do. A prompt injection in a paper the agent reads (via `loom library read`) could instruct a well-meaning agent to: drop its env markers and run `loom` author verbs; or read `.loom/serve.json` and drive the write API as the person; or (per SEC-1) write `loom.py` into the quilt for code execution. None of these requires the agent to be malicious — only to follow text in a document.

Which is enforcement vs advice. All of the agent/author split above is advice. The genuine enforcement in the system is the CSRF trio (`Origin`/`Sec-Fetch-Site`, JSON content-type, token header) that keeps *browser pages* out — and even that is undone for reads by SEC-2.

How bad for a pilot. Serious, but partly inherent to the "semi-trusted agent sharing the filesystem" design. The honest statement is that the agent runs with the user's authority; the markers and the author-name check stop accidents and keep the audit log truthful, not a determined or injected agent.

Fix (for what is fixable). Treat author-only as a real capability: require a separate secret for author actions that is *not* stored in a file the agent routinely reads, or have the viewer (not the request body) assert the human actor. At minimum, do not keep the write token in `.loom/serve.json` world-readable (SEC-6) and state the limit plainly (item 6). A full fix is a design change, not a v0.1 patch.

Files the fix owns. `loom/src/loom/render/api.py`, `loom/src/loom/cli/_common.py`, `loom/src/loom/render/serve.py` (token storage) — design-level.

Size. Large (design); the honest v0.1 move is to document it.

---

## SEC-5 — an HTML file in the quilt runs arbitrary JavaScript on the frames origin with no CSP, and can read and exfiltrate the whole quilt

What it is. A project `.html` file is shown in an iframe pointed at the **frames origin** (`arras/src/lib/workspace/items/HtmlFrame.svelte:57`) with `sandbox="allow-scripts allow-same-origin …"`. The separate origin is the right call: `allow-same-origin` there grants the frame *its own* (frames) origin, not the viewer's, so the page cannot read the write token — confirmed by design and by the distinct ports. But the frames server sends **no Content-Security-Policy** (`FramesHandler._answer`, `serve.py:616`: only `Content-Type`, `Cache-Control`, `X-Content-Type-Options`). So a script in a quilt HTML file can: enumerate every shown file via `GET /.loom/files.json`, `fetch` any of them same-origin, and `fetch`/`sendBeacon` to any external host to exfiltrate.

How I showed it. Against the scratch frames origin I retrieved `/.loom/files.json` (the full shown-file list) and read `notes/private-dummy.md` with a same-origin request; response headers carried no CSP, and the served HTML had loom's `BRIDGE` script injected (confirming scripts run). I did not make an outbound request (review rules), but `fetch('https://…', {method:'POST', body})` is an ordinary capability of an `allow-scripts` page with no `connect-src` restriction.

Who could exploit it and what they need. An HTML file in the quilt — written by the agent, or a co-author's `.html` — that the pilot opens in the viewer. The viewer draws it automatically for `.html` files.

How bad for a pilot. Serious (silent quilt exfiltration on opening a file), mitigated by requiring the user to open an HTML file and by the token staying out of reach.

Fix. Send a CSP on frames-origin responses. Scripts are wanted for embedded players, so `script-src` can stay permissive, but `connect-src` should be tightened (e.g. `'self'` plus any hosts the project genuinely needs) to stop blind exfiltration; or, if HTML files are not meant to phone home, `default-src 'self'`. If any script at all is undesirable for untrusted HTML, serve it scriptless (the viewer already has that mode for static hosts, `HtmlFrame.svelte:62`).

Files the fix owns. `loom/src/loom/render/serve.py` (`FramesHandler._answer`).

Size. Small-to-medium (choosing the connect-src policy is the work).

---

## SEC-6 — smaller items

- SEC-6a (minor). The Markdown allowlist keeps `<iframe>` and forces `sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms …"` on any `https:` host (`loom/src/loom/raw_html.py:70` `FRAME`, `TAGS`). An agent-written or co-author `.md` can therefore embed a live third-party frame that runs scripts and can open popups that escape the sandbox — a phishing/tracking surface inside the viewer. It is cross-origin to the viewer, so the token is safe. Fix: drop `iframe` from `TAGS`, or at least drop `allow-popups-to-escape-sandbox`. Owner: `raw_html.py`. Size: tiny.
- SEC-6b (minor). `.loom/serve.json`, which holds the token, is written `0644` (world/group-readable) — looser than needed on a shared Mac; write it `0600`. The token is correctly kept out of URLs and out of the request log by default (verified: no token in `serve.log`). Owner: `render/serve.py` `write_serve_json`. Size: tiny.
- SEC-6c (reassurance, keep watching). pdf.js runs on the viewer's own origin (where the token is), but loom uses the library's `getDocument` with no scripting manager (`arras/src/lib/pdf/document.ts:40` `sourceOf`) — embedded PDF JavaScript and XFA are off by default, so a malicious PDF is parsed, not executed. The residual is an upstream pdf.js parser bug; keep `pdfjs-dist` current. `/build/`, `/_files/`, `/store/` all carry `Content-Security-Policy: sandbox` + `nosniff` (`CONFINED`, `serve.py:59`), so even the raw TeX4ht HTML served there cannot script the viewer.
- SEC-6d (reassurance). arXiv archive unpacking (`loom/src/loom/refs/fetch.py:138` `_unpack`) uses `is_relative_to` and skips symlinks/hardlinks — path traversal and link escape are handled. MCP argument building (`loom/src/loom/mcp/tools.py` `argv`) passes options as `[flag, value]` pairs and inserts `--` before any positional that looks like an option, and refuses a bare `-`, so option-injection into the `loom` subprocess is handled. Subprocesses are argv lists, never a shell string — no shell injection found.

---

## The five fixes to make before anyone else runs loom

1. SEC-1: add `-P` (or `PYTHONSAFEPATH=1`) to the MCP `_run` subprocess, so a `loom.py` in the quilt cannot run as the user. One line, highest priority — it turns an agent prompt-injection into code execution.
2. SEC-2: check the `Host` header in `LoomHandler` (the frames handler already shows how), closing the DNS-rebinding read of the token and of every quilt file.
3. SEC-3: set `openin_any=r`, `openout_any=p`, `shell_escape=0` in the env of every TeX subprocess, so an untrusted paper cannot read arbitrary files into its output.
4. SEC-5: send a CSP (tight `connect-src`) on the frames origin, so opening a quilt HTML file cannot exfiltrate the quilt to the internet.
5. SEC-6b: write `.loom/serve.json` `0600`; and ship the item-6 readme note below.

## What is acceptable to state as a known limit for a pilot among friends

- SEC-4: the AI agent runs with the user's authority. loom's agent/author split (env markers, the `(Agent)` name, the author-only write endpoints) keeps the audit log honest and stops accidents; it is not a security boundary. A pilot should treat an agent working in a quilt as able to do anything they can do in that quilt, and should not point an agent at a quilt holding secrets they would not hand it. This is a design property, not a bug to fix for v0.1.
- Residual TeX risk after SEC-3: compiling a stranger's TeX is still running a stranger's document; with code execution fenced (restricted shell-escape, Lua blocked) and file reads tightened, the remaining exposure is denial-of-service (a pathological document) bounded by the existing per-run timeout and process-group kill (`runner.py` `stop_run`).
- Readme line for pilots: "While `loom serve` is running it exposes a local web server on 127.0.0.1. Treat your quilt as readable by any website you have open in the same browser until the Host-header fix ships, and treat any AI agent you run in a quilt as having your full access to that quilt. Don't open HTML files or compile TeX from sources you don't trust."

---

Reproduction artifacts (all under the scratch dir, nothing in the repo or under `~/quilts`): a copy of `demos/showcase` as the test quilt; marker files from the PoCs; `tex/lua.tex` (directlua test), `texin/read.tex` + `outside/loot.tex` (openin test), `shadowtest/loom.py` (module-shadow test). The scratch server on 48700 and all TeX/loom subprocesses were stopped; `serve.json` was removed on clean shutdown.

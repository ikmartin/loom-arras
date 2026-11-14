# v0.1 study: the install and the attach, done for real

Auditor: live. Checkout `.claude/worktrees/v01-study` at 71621877. `$S` below is `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live`; every screenshot is `$S/shots/*.png`, every Claude Code event stream `$S/sessions/*.jsonl`, every MCP exchange `$S/presence/<start>-<pid>/{meta,stdin.jsonl,stdout.jsonl}`, command transcripts `$S/logs/`. loom was installed into `$S/uv` with `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR` and `XDG_*` in scratch; person commands ran through `$S/p.sh` (an `env -i` with no agent markers). Ports 48201-48220 only; at the end `lsof -iTCP -sTCP:LISTEN` shows nothing in 48200-48249 and no process from `$S` runs. `~/.claude.json` holds no entry for any scratch folder afterwards.

## How the attach trial was run, and what it could not do

The real-model trial was not possible. `~/.local/bin/claude` (2.1.312) is not signed in: `claude auth status` gives `"loggedIn": false`, and the first session (`$S/sessions/s1-orient.jsonl`) answered every turn with `Failed to authenticate: OAuth session expired and could not be refreshed`. The desktop app's own CLI (2.1.321, `$CLAUDE_CODE_EXECPATH`) is also `loggedIn: false` when run on its own; the desktop app feeds auth to its sessions itself. Signing in is the person's to do, so I did not.

What I ran instead is the real Claude Code CLI against a scripted stand-in for the Messages API (`$S/fake/api.py` on 127.0.0.1:48220, `ANTHROPIC_BASE_URL` pointed at it, a dummy key). The client's own MCP start-up, permission rules, workspace-trust handling, slash commands and tool execution are all real; only the model's choices are fixed in advance (`$S/fake/script.json` per run). Each session used `--model haiku --strict-mcp-config --mcp-config <loom only> --setting-sources project,local --permission-prompts none`, so no other MCP server, no user setting and no human approval was involved, and anything that would have prompted the person was refused and recorded. Twelve sessions, all against `$S/agent/showcase` (a copy of `demos/showcase` after `loom ai init`), with the person's tab held open by Playwright (`$S/holder.mjs`).

**Not tried:** what a model says in its own words ("what can you see…", "what am I looking at?"), whether it chooses to orient, read annotations or follow the journey unprompted; the Code tab's own UI (trust dialog, server approval, `/` menu); Codex in any form (not installed); `open -a Claude` or any deep link; a clean Mac (Command Line Tools shim, no Homebrew); TeX installation. The driver `$S/session.py` reruns every turn with a real model once the CLI is signed in: drop `FAKEAPI` from the environment.

## Findings

| id | finding | weight | rec |
|---|---|---|---|
| LIVE-1 | Without TeX a paper cannot enter a quilt at all; once copied in by hand it shows as source with no reason on screen | blocks (no-TeX pilot) | fix (INST-5) |
| LIVE-2 | Both READMEs fail a newcomer: 4 of loom's quickstart commands no longer exist or take other options | hurts | fix (INST-2) |
| LIVE-3 | The first screen is the quilt's README, full of CLI commands; the paper is a click away | cosmetic | fix |
| LIVE-4 | doctor without TeX: remedies under the wrong rows, `tlmgr` offered with no TeX, `brew` with no Homebrew | hurts | fix (INST-22) |
| LIVE-5 | `uv tool install` binds loom to whatever `python3` resolves first (here a miniconda interpreter) | hurts | fix |
| LIVE-6 | The Code tab passes the login-shell PATH, so `loom mcp` finds TeX there; under a bare PATH loom says "latexmk is not installed" and the viewer shows only "did not compile" | hurts (launcher) | fix |
| LIVE-7 | `loom serve`'s refusals are clear but terminal-only; an open page never says its server has gone | hurts | fix |
| LIVE-8 | Claude Code ignores all 55 of loom's allow rules until the folder is trusted; loom's server sits "Pending approval"; `enabledMcpjsonServers` does not change that | hurts (blocks if the Code tab does not trust on folder pick) | verify, then fix |
| LIVE-9 | What the client tells the server: `server/discover` with clientInfo in every request's `_meta`, a per-conversation `CLAUDE_CODE_SESSION_ID`, and an end by SIGINT then SIGTERM, never EOF | design input for ATT-2 (blocks) | fix |
| LIVE-10 | "What am I looking at?" loses the selection in any document that `\input`s node files | hurts | fix |
| LIVE-11 | The agent's comments and suggestion arrive silently: counters move, nothing announces them | hurts | fix (ATT-7) |
| LIVE-12 | An in-place edit to a draft in Accept-edits mode leaves no trace anywhere in the viewer | blocks | fix (ATT-3) |
| LIVE-13 | The boundary holds in Claude Code once the settings apply, even in bypass mode, except writes by a subprocess | hurts (say so) | keep, state |
| LIVE-14 | Modes are offered and work as `/mcp__loom__<mode>` slash commands in Claude Code | — | keep; verify Code tab |
| LIVE-15 | A server that fails to start shows the agent "Connection closed" and the person nothing; loom's remedy is lost on stderr | hurts | fix |
| LIVE-16 | Replacing loom under an open conversation mixes versions silently; the viewer's notice needs a reload and a terminal | hurts | fix (INST-17) |
| LIVE-17 | Arrival is about 25k tokens in Claude Code 2.1.312; `loom mcp` takes 0.85-3.0 s to answer here | cosmetic (Claude), hurts (Codex grace) | measure on a clean Mac |
| LIVE-18 | Texts the agent relays still tell the person to type commands | hurts | fix (ATT-12) |
| LIVE-19 | `loom_source sh-0009` returns the statement without its proof; a suggestion card shows `\eqref{eq:rank}` as "(eq:rank)" | cosmetic | fix |

### LIVE-1 · without TeX nothing comes in · blocks · rec fix

- With TeX and poppler off PATH (`PPATH=$S/uv/bin:/usr/bin:/bin:/usr/sbin:/sbin`), `loom init nt --from $S/papers/flows/main.tex` stops after its two questions: `Error: the original does not compile from a clean copy of …/papers/flows (latexmk is not installed); fix it before importing`. No quilt is left behind. `loom init nt --ai claude --yes` then `loom import … --no-check --yes` refuses with the same words, so `--no-check` does not help (`$S/logs/notex-init.log`).
- The only way in is copying the folder by hand. `loom serve` then logs `compiled paper/main.tex: FAILED: latexmk is not installed` to the terminal, and the page shows every block as raw LaTeX in grey boxes with "PDF did not compile" in the tree and no reason on screen (`03-notex-draft.png`). The reason exists only as a hover `title` (eval of `[title]` on the bare-PATH page: four times "latexmk is not installed").
- A library PDF displays normally through pdf.js (`04b-notex-library-Arden24.png`). `loom library add` of a PDF files it "without page text (pdftotext is not installed (it ships with poppler; `brew install poppler`))". A digest's results show as source (`04d-arden-info.png`).
- **Rec:** INST-5's private TeX. Until then, an import that cannot compile should still bring the paper in, with a banner in the viewer naming the missing TeX.

### LIVE-2 · the READMEs, read as a newcomer · hurts · rec fix

Root `README.md:30-38`: needs git for the clone and uv, and says nothing on getting either; never mentions TeX; installs editable from a clone; `loom serve` without `--open` leaves the person to find the URL; line 62 says loom "is released to PyPI", which contradicts INST-2 (not checked on the network). `loom/README.md`:

| step | result here |
|---|---|
| `pipx install git+https://github.com/ikmartin/loom` | not run (no network); INST-2 says the repository does not exist |
| table: `brew install uv / mactex-no-gui / poppler` | assumes Homebrew without saying how to get it |
| `loom init mypaper --from …` "arrives as one flat landmark in canon/" | works, but writes `main/main.tex`; no `canon/`, no `CONTRACT.md` (a `README.md` instead) |
| `loom draft canon/draft.tex --to drafting/main.tex` | `Error: No such option '--to'` |
| `loom canonize …` | `Error: No such command 'canonize'. Did you mean 'atomize'?` |
| `loom annotate … --kind question` | `Error: No such option '--kind'` (it is `--type`) |
| `loom digest extract …` | `Error: No such command 'digest'` |
| `loom atomize drafting/main.tex …` | path wrong for a fresh import; `main/main.tex` works |

The install itself is fine: `uv tool install $REPO/loom` took 1.85 s wall, resolved 31 packages, printed only uv's PATH warning (`$S/logs/install.err`).

### LIVE-3 · the first screen · cosmetic · rec fix

From an empty directory with loom installed and TeX present: `loom init mypaper --from …` (16.4 s, three questions: id prefix, which AI, `Apply? [y/N]` whose default aborts), `cd mypaper`, `loom serve` (listening in about 1 s). The browser opens on the quilt's `README.md`, which teaches `loom new`, `loom library add`, `loom ai init` and `loom upgrade` (`01-first-screen-mypaper.png`); the paper is a click on `main.tex` in the tree, then it is well typeset (`02-mypaper-main-tex.png`, about 6 s from page load). Three typed commands, three answers, one click, four decisions (prefix, AI, apply, which file). **Rec:** open the default document first.

### LIVE-4 · doctor without TeX · hurts · rec fix

`loom doctor` exits 2 (`$S/logs/notex-doctor.txt`). The `brew install --cask mactex-no-gui` remedy is printed under `extractbb`, not under the three failing rows `latexmk`, `pdflatex` and `dvisvgm`, which carry none. `biber` and `make4ht` say `fix: tlmgr install …` on a machine with no TeX and so no `tlmgr`. Poppler's fix is `brew install poppler`, and a fresh Mac has no `brew`. A mathematician cannot act on this. Confirms INST-22.

### LIVE-5 · the interpreter uv chose · hurts · rec fix

`$S/uv/tools/loomtex/bin/python -> /Users/isaac/miniconda3/bin/python3`: uv used the first `python3` on PATH. A pilot with conda, pyenv or a python.org Python gets loom tied to it, and loom breaks when that environment changes. **Rec:** `--managed-python --python 3.13` in the install line (INST-19 rank 1 already says so; confirmed needed).

### LIVE-6 · PATH, as the apps really give it · hurts for a launcher · rec fix

- This study's own process is a Code tab session (`CLAUDE_CODE_ENTRYPOINT=claude-desktop`). Its `PATH` holds the login shell's entries: `/opt/homebrew/bin`, `/usr/local/texlive/2024/bin/universal-darwin`, `~/.config/emacs/bin`. The desktop app therefore resolves the shell environment, and a stdio server it starts inherits it. Every wrapper log shows the CLI passing its PATH to `loom mcp` unchanged (`$S/presence/*/meta`, `env PATH=`).
- Under `env -i HOME=… PATH=/usr/bin:/bin:/usr/sbin:/sbin`, `loom mcp` starts (it re-runs itself as `sys.executable -m loom`, `loom/src/loom/mcp/server.py:198-205`). Every tool answers, but `loom_compile` says `drafting/main-atomic.tex did not compile: latexmk is not installed`, which is false: TeX is installed, just not on that PATH. An agent would relay this to the person.
- `loom serve` under the same environment shows source for every document, says "did not compile" in the tree, and gives the reason only in a hover (`05-bare-path-serve.png`).
- **Rec:** INST-5's `private.py`, which puts known TeX locations on PATH, must land before any Dock launcher. Show a compile's error on the page, not in a `title`.

### LIVE-7 · `loom serve` at its edges · hurts · rec fix

All refusals exit 2 in about 0.3 s with clear words (`$S/logs/serve-edges.log`):
- a second serve in the same quilt: `loom serve is already running for this quilt at http://127.0.0.1:48204/; open that, or stop it first`;
- another quilt on a busy port: `cannot listen on port 48204: Address already in use; pass --port N for another, or stop what holds it`;
- outside a quilt: `not inside a quilt: no config.toml with a [quilt] table above …; cd into one, or make one with loom init DIR`.

Every quilt defaults to port 8791, so the second quilt a person opens fails until they pick a port. When the server is stopped, the open page carries on as if nothing happened, a minute later included: no banner, only `ERR_CONNECTION_REFUSED` in the console (`09b-viewer-after-serve-stopped.png`, `09c-…-1min.png`). **Rec:** INST-1's launcher, and a "loom is not running" banner.

### LIVE-8 · folder trust gates loom's whole permission file · hurts, possibly blocks · rec verify, then fix

- `claude mcp get loom` in the fresh quilt reports `Status: ⏸ Pending approval (run 'claude' to approve)`.
- Adding `"enabledMcpjsonServers": ["loom"]` to `.claude/settings.json`, and separately `enableAllProjectMcpServers` plus `enabledMcpjsonServers` to `.claude/settings.local.json`, left it `Pending approval` (`$S/approve`). ATT-5's fix does nothing before trust.
- Every session printed `Ignoring 55 permissions.allow entries from .claude/settings.json: this workspace has not been trusted.` Without trust, all three loom tool calls (orient, here, since) needed an approval and were refused (`f1-untrusted.jsonl`).
- With the file applied (passed as `--settings`, as `loom/tests/client/test_claude.py` does), no loom tool needed one (`f2-orient.jsonl`).
- So what the person meets in the Code tab turns on whether picking a folder there counts as trusting it. If it does not, every loom call asks.
- **Rec:** check this in the Code tab before building ATT-5. The "Connect" flow should tell the person to trust the folder; pre-approval helps only after trust.

### LIVE-9 · what the client tells loom's server · design input · rec fix

Read from the stdin of a logging wrapper placed in front of `loom mcp` (`$S/loom-wrap.py`, ten sessions):

- **No `initialize`, as a rule.** The CLI speaks MCP `2026-07-28`: it sends `server/discover`, then `prompts/list`, `resources/list` and `tools/list`, and puts `io.modelcontextprotocol/clientInfo` = `{"name":"claude-code","title":"Claude Code","version":"2.1.312",…}` in the `_meta` of every request. One of ten sessions also sent `initialize` with protocol `2025-11-25` (`$S/presence/1794601974-38775`). A presence record keyed to `initialize`, as in attach.md C2, would see one conversation in ten.
- **What the server's environment carries:** `CLAUDE_CODE_SESSION_ID` (one per conversation), `CLAUDE_PROJECT_DIR`, `AI_AGENT=claude-code_2-1-312_harness`, `CLAUDECODE=1`, and `CLAUDE_CODE_ENTRYPOINT=sdk-cli`. The Code tab would set `claude-desktop`, judging by this session's own environment; the server's view of it is unverified.
- **Lifetime:**
  - The server starts 0.8-1.1 s after the CLI, before the first model request.
  - One process serves the whole conversation: pid 42364 through three turns and a 14 s idle gap (`f10-swap-and-stop.jsonl`).
  - At the CLI's exit the server gets SIGINT, then SIGTERM 100 ms later, and exits `rc=-15`. Its stdin is never closed. Ten of ten sessions ended this way.
- **What a truthful "attached" indicator can rest on:**
  - Write a record at the first request of either kind, carrying `clientInfo`, the `CLAUDE_CODE_SESSION_ID`, the pid and the ppid (the client process).
  - Update it on each call.
  - Remove it in SIGINT and SIGTERM handlers, and let `loom serve` prune it by pid liveness, because EOF never comes.
  - Bind loom's session to `CLAUDE_CODE_SESSION_ID`, which settles ATT-8 for Claude Code.
- **What it cannot see:** whether the person is looking at that conversation, and whether the Code tab keeps idle conversations' processes alive.

### LIVE-10 · the selection disappears in atomized documents · hurts · rec fix

- **What the person had open:** the showcase's `main-atomic.tex`, with "is the set of integer vectors summing to zero" selected in Theorem 3.1's proof (`06-person-selection.png`).
- **What the viewer reported:** `{"file": "drafting/nodes/sh-0009.tex", "text": "is the set of integer vectors summing to zero"}` (`loom here --json`, `place.selection`).
- **What the agent got:** `loom_here` returned `the person is looking at drafting/main-atomic.tex, at sh-0010 …` with no selection. The same text reached the scripted agent in `f2-orient.jsonl`.
- **Why:**
  - Each included node sits in a `div.included[data-file]`, so `textSelection` takes the project-file branch before the `data-src` one (`arras/src/lib/here.svelte.ts:121-129`).
  - `_resolve` keeps a file selection only when the file is the open item (`loom/src/loom/cli/here_cmd.py:154`).
- **Where it works:** in an inline document (`mypaper/main/main.tex`) the same selection comes back as `selected q-000C/proof (Proof) "is the set of integer vectors summing to zero"`.
- **Rec:** inside a document, prefer the block's key over `data-file`.

### LIVE-11 · the agent's work arrives unannounced · hurts · rec fix

- **What the agent wrote:** over MCP, as "Claude Code Agent": a Question on `sh-0009/proof`, a Note on `sh-0009` and a suggested edit (`f3-journey.jsonl`). The person's files were unchanged (hash equal before and after).
- **What the open page did,** without a reload, within about 2 s:
  - Comments 14→16, Changes 2→3, items 16→19, Notes 2→3 (`07a-viewer-before-agent.png`, `07b-viewer-after-agent-no-reload.png`);
  - the margin markers became stacks "2" and "3";
  - the suggestion appears inline as green tracked text, interleaved with another agent's earlier one.
- **What did not happen:** no toast or notice; the footer still reads "not writing in a session".
- **In the Comments panel:** cards are ordered by position, not by time. The agent's cards say "Claude Code Agent · Question · Nov 13" with no badge beyond the name (`07c-comments-panel.png`, `07d-comments-panel-agent-cards.png`).
- **What the person must do:**
  - read or reply to each comment in the panel;
  - Keep or Discard the suggestion there or in Review › Your Changes (`10a-review-your-changes.png`).
- **Rec:** ATT-7's activity list, plus a notice when an agent writes.

### LIVE-12 · an in-place edit is invisible · blocks · rec fix

- **The edit:** in `acceptEdits` mode, Claude Code's Edit tool changed `drafting/nodes/sh-0009.tex` with no prompt (`f5-boundary-acceptedits.jsonl`, diff in that run's output).
- **What the viewer showed:** the page re-rendered the new words. Changes stayed at 3, and nothing marked the edit (`08a-viewer-after-inplace-edit.png`).
- **What loom says:** `loom changes` prints "suggested edits; edits in place are not tracked: 3 changes".
- **What Settings shows:** "Review edits made in place" is off (`10b-settings-agents.png`).
- **In Manual (default) mode** the same Edit needed the person's approval.
- Confirms ATT-3 live; the author must choose between turning on `track_edits` with the agent layer and denying documents to agents.

### LIVE-13 · the boundary, tried · hurts (state it) · rec keep

Settings applied as a trusted folder would apply them:

| attempt | mode | outcome | by |
|---|---|---|---|
| `loom_changes` with `keep` | default | `loom_changes takes no keep; it takes by, change, document, json` | loom's tool schema |
| Bash `loom accept sh-0009` | default | `Permission to use Bash with command loom accept sh-0009 has been denied.` | Claude Code deny rule |
| Bash `loom changes --keep e-…` | default | ran, then `Keeping and discarding a change is the author's, and an agent is running this shell (AI_AGENT is set); run it in a terminal of your own.` | loom's marker check |
| Bash `loom library add …pdf` | default | denied | Claude Code deny rule |
| MCP annotate `delete` of the person's annotation | acceptEdits | `a-2026-09-16-0gvvrg is The loom showcase's, and an agent deletes only its own annotations` | loom |
| Edit `config.toml`; Write in `.loom/annotations/` | default, bypass | `File is in a directory that is denied by your permission settings.` | Claude Code |
| Edit a draft | default | needs approval (refused here) | Claude Code mode |
| Edit a draft | acceptEdits | **written** | — |
| `/abs/path/loom accept`; `env -u AI_AGENT … loom accept`; `env -i … loom accept`; `cd drafting && loom accept` | acceptEdits, bypass | denied | Claude Code deny rules see through all four |
| `echo … >> config.toml` | bypass | denied | Claude Code |
| `python3 -c "open('.loom/annotations/x','w')…"` | bypass | **written** | — (documented limit) |

No author act got through. The MCP surface never offers one. The only writes past the protected list were by a subprocess in bypass mode. **Rec:** say so in the panel ATT-6 proposes; Codex was not tried.

### LIVE-14 · modes are slash commands in Claude Code · changes ATT-10

- The CLI's init event lists `mcp__loom__quick, …question, …audit, …referee, …review, …simplify, …flow, …draft, …ingest` among its slash commands.
- Sending `/mcp__loom__referee sh-0009` made the client call `prompts/get {"name":"referee","arguments":{"target":"sh-0009"}}`. The model received "Work in loom's referee mode on `sh-0009` (quilt:sh-0009). If you have not called `loom_ai_orient` …", 1,527 characters (`f8-mode.jsonl`).
- **Not tried:** the Code tab's `/` menu and Codex.
- **Rec:** skills are needed for Codex, not for Claude Code's CLI; check the Code tab before adding `.claude/skills`.

### LIVE-15 · a server that fails · hurts · rec fix

| failure | what the agent saw | what the person saw |
|---|---|---|
| MCP SDK missing (`$S/nomcp`) | init `status: failed`; ToolSearch: `loom (CONNECTION_CLOSED): "Connection closed"` | nothing in the viewer |
| binary path wrong in the config | `loom (ENOENT): "ENOENT: no such file or directory, posix_spawn 'stdio'"` | nothing in the viewer |

- **Where loom's remedy goes:** loom's own message, `loom mcp needs the MCP SDK, which this loom's environment does not have; reinstalling loom brings it: uv pip install --python …`, goes to stderr, and the client drops it.
- **The fallback in the CLAUDE.md line:** the scripted agent followed it (`loom ai orient`, `loom doctor` in a shell). It worked only because a good loom was on PATH.
- **What doctor would say:** run with the broken loom, `loom doctor` says `warn mcp the MCP SDK is not installed`.
- **Rec:** presence (LIVE-9) makes "no agent connected" visible. `loom mcp` should write its start failure where `loom serve` can show it.

### LIVE-16 · loom replaced while a conversation is open · hurts · rec fix

- **The trial:** mid-conversation, `uv tool install --force` of a copy marked `0.1.0.dev1` (`f10-swap-and-stop.jsonl`).
- **What the agent got:** the server process, started as `0.1.0.dev0`, kept answering. Its next `loom_doctor` call printed `loom 0.1.0.dev1`, because each call re-runs the package on disk, so one conversation mixed two versions with no notice to the agent.
- **What the open page did:** within 8 s, nothing (`09a-viewer-after-loom-replaced.png`). After a reload: "loom has been updated since `loom serve` started, so some of this page may not work. Stop it and run it again, then reload this page." (`09d-viewer-restart-notice.png`, `/_api` `"stale": true`).
- Confirms INST-17.
- **Rec:** the supervisor restarts `loom serve`. `loom mcp` should compare `code_stamp()` (`loom/src/loom/render/serve.py:201`) on each call and tell the agent to ask for a restart.

### LIVE-17 · arrival cost and start-up · cosmetic / hurts · rec measure on a clean Mac

Request sizes the stand-in received (`f2-orient`; tokens are characters ÷ 4, an estimate):

| request | bytes | about |
|---|---|---|
| first | 54,093 | 13.5k tokens: Claude Code's system prompt 8,965 chars, 12 built-in tool definitions 30,352 chars, messages 15,105 chars, which carry loom's instructions and the CLAUDE.md line; loom's tools are deferred |
| after `loom_ai_orient` | 99,206 | 25k tokens; the orient result is 41,090 chars |
| after the first `loom_since` | — | 6,915 chars plus eight PNG crops of 480-990 × 102-172 px, about 0.8k image tokens |

- **Cost:** attach.md's 11k leaves out Claude Code's own baseline; the orient share (about 10k) is confirmed.
- **Start-up:** `loom mcp` answered its first request in 2.99, 1.19 and 0.85 s on three runs on this machine, which other agents were loading. That is above Codex's 1,000 ms grace for optional servers.

### LIVE-18 · commands pushed at the person · hurts · rec fix (ATT-12)

Seen live in what the agent received:
- `loom_here` with no viewer: "`loom serve` starts the viewer; the person opens it".
- `loom changes --keep`: "run it in a terminal of your own … Keep and discard in a terminal of your own, or in the viewer."
- `loom init`'s last line: `next: cd mypaper, then loom doctor; loom lint`.
- The orientation's first bullet: "**In a shell, sign everything you write** with `--as`", even over MCP.

### LIVE-19 · small things · cosmetic

- `loom_source sh-0009` returns the statement only; the proof needs `sh-0009/proof`.
- The agent's suggestion card renders `\eqref{eq:rank}` as "(eq:rank)", while the page shows "(3)" (`07d-…png`).

## The two reports' claims, as tested

| claim | verdict | evidence |
|---|---|---|
| INST-1 no launcher, one quilt per process, fixed port, terminal | confirmed | LIVE-7 |
| INST-2 install docs wrong | confirmed (offline); the missing GitHub repository not rechecked; root README claims PyPI | LIVE-2 |
| INST-3 without TeX loom is a source viewer | confirmed, and worse: no import at all | LIVE-1 |
| INST-5 private TinyTeX | not tested (no installs allowed) | — |
| INST-6 apps get launchd's bare PATH | changed: the Code tab passes the shell PATH; a bare PATH matters for a Dock launcher, and for Codex if it does not resolve the shell (untested) | LIVE-6 |
| INST-7 git shim | not tested (Command Line Tools present) | — |
| INST-22 doctor speaks to developers | confirmed, plus misattached remedies | LIVE-4 |
| INST-23 per-quilt MCP files for both apps, written by a CLI step | confirmed; `init --ai claude` writes Codex, Gemini and Cursor files too | `$S/newcomer/mypaper` |
| first ten minutes, today | confirmed after install: 3 commands, 3 answers, 1 click; TeX is the long pole and was not tried | LIVE-3 |
| ATT-1 setup needs a typed command; an agent cannot do it | confirmed: `AI_AGENT=… loom ai init` → `may not run 'loom ai init', which is the author's` | — |
| ATT-2 no presence | confirmed: nothing in the viewer; with no active session nothing is logged; only `.loom/since/claude-code-agent.json` moved | LIVE-9 |
| ATT-3 in-place edits invisible | confirmed live | LIVE-12 |
| ATT-4 Codex may not start the server | not tried | — |
| ATT-5 second approval; fix with `enabledMcpjsonServers` | approval confirmed; the fix as stated is refuted before trust | LIVE-8 |
| ATT-6 nowhere says what an agent sees and may change | confirmed (`10b-settings-agents.png`: deny list, protected list, four apps "Set up") | — |
| ATT-7 no activity list | confirmed; no announcement either | LIVE-11 |
| ATT-8 sessions quilt-global | confirmed (no active session, nothing logged); changed: `CLAUDE_CODE_SESSION_ID` gives a per-conversation key | LIVE-9 |
| ATT-10 modes reachable only as MCP prompts; the Code tab may not list them | changed: the CLI lists and expands them; Code tab and Codex untested | LIVE-14 |
| ATT-11 boundary enforced only in Claude Code, partly | confirmed and measured | LIVE-13 |
| ATT-12 texts push commands | confirmed | LIVE-18 |
| ATT-15 about 11k tokens; 0.4 s start | changed: about 25k in total; 0.85-3.0 s here | LIVE-17 |
| ATT-16 four clients' files; "Set up" means the file exists | confirmed | — |
| live-wave list: one server per session; inherits `CLAUDE_CODE_ENTRYPOINT` | confirmed in the CLI (`sdk-cli`); the Code tab untested | LIVE-9 |
| live-wave list: Code tab prompts, `/` menu, `claude://code/new`; everything Codex | not tried | — |

## From "loom is installed" to "my agent commented on my proof and I can see it"

**Today**, with TeX installed and Claude Code in the Code tab. The CLI stood in for the Code tab, so steps 5-7 are as documented, not observed.

1. Terminal: `cd` to where the quilt should go (1 command).
2. `loom init flows --from ~/papers/flows/main.tex`, answering Enter, `1` and `y` (1 command, 3 answers).
3. `cd flows` (1 command).
4. `loom serve --open`, and leave the terminal open (1 command). The browser shows the quilt's README; click `main.tex` (1 click).
5. Claude app › Code: pick the folder `flows` (1 decision).
6. Accept folder trust (1 prompt). Approve the loom server (1 prompt; LIVE-8 shows it pending).
7. Type the request (1 message). If the folder is not trusted, approve each loom tool call (3 or more prompts).
8. Back in the browser: notice Comments 14→16, then open the Comments panel or click the margin stack (2 clicks).

Total: 4 typed commands, 3 answers, 2 approval prompts (5 or more without trust), 1 message, 4 clicks, and a terminal held open. A person without TeX stops at step 2 (LIVE-1).

**With the confirmed recommendations built:** a launcher with "New quilt from a paper" (INST-1, INST-16), "Use with Claude" writing the agent files (ATT-1, ATT-16), private TeX (INST-5), presence and an activity notice (ATT-2, ATT-7, LIVE-9, LIVE-11), the selection fix (LIVE-10), and edits in place made visible (ATT-3).

1. Open Loom from the Dock, then New quilt and drop the paper (1 decision).
2. Click "Use with Claude", then "Open Claude", which copies the path (2 clicks).
3. In the Code tab, pick the folder; accept trust; approve the loom server, unless pre-approval holds after trust (unverified) (1 decision, 1-2 prompts).
4. Type the request (1 message).
5. The viewer's chip reads "Claude Code connected" and a notice says "2 comments and 1 suggestion on Theorem 3.1" (1 click).

Total: no typed command, 2 decisions, 3 clicks, 1-2 prompts, 1 message. The folder pick in step 3 stays manual, because no documented link opens the Code tab on a local folder.

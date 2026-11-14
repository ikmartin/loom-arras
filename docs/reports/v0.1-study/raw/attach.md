# v0.1 study: how an agent app attaches to a quilt, and what the person sees of it

Auditor: attach. Checkout: `.claude/worktrees/v01-study` at 71621877 (main). Hand checks ran in a scratch copy of `demos/showcase` with `XDG_CONFIG_HOME` in scratch and the agent markers unset for `loom ai init` only; no server was left running. Client facts come from the vendors' current documentation, fetched 2026-11-13, through two research subagents and my own fetches; each carries a URL. Weighting follows the lead's update: the pilot users run **Claude Code in the Claude desktop app's Code tab** and **Codex in the ChatGPT desktop app**; desktop chat is a footnote. Effort lines say what each piece owns and whether it waits on another, for parallel Opus-class implementers.

## Findings

| id | finding | weight | effort | rec |
|---|---|---|---|---|
| ATT-1 | Setting agents up needs a typed command, and an agent cannot do it for the person | blocks | a day | fix |
| ATT-2 | Nothing records or shows whether an agent is attached, which one, or when it last called | blocks | days | fix |
| ATT-3 | An agent's edits in place to the person's files are invisible by default | blocks | hours | fix |
| ATT-4 | Codex in the ChatGPT app may never start loom's server: project config needs trust, and the app's handling is undocumented | blocks until verified | hours, then a day | fix |
| ATT-5 | Claude Code asks a second approval for loom's server that loom could pre-grant | hurts | hours | fix |
| ATT-6 | No place in the viewer says what an agent is told, sees and may change | hurts | a day | fix |
| ATT-7 | No list of what agents wrote; it is scattered over five views | hurts | days | fix |
| ATT-8 | Sessions are quilt-global, not per conversation; `since` is per app name | hurts | a day | fix |
| ATT-9 | The viewer cannot hand a request to the agent app | hurts | a day | fix |
| ATT-10 | Modes are reachable only as MCP prompts, which Codex lacks and the Code tab may not list | hurts | hours | fix |
| ATT-11 | "What an AI may edit" is enforced for the agent's own edits only in Claude Code, and partly | hurts | hours (say it), days (Codex profiles) | fix |
| ATT-12 | Loom's texts push commands at the person through the agent | hurts | hours | fix |
| ATT-13 | Codex's shell route weakens the guard and fails under its sandbox | hurts | hours | fix |
| ATT-14 | "Transcript" means the agent's own summary, which nobody tells the person | hurts | hours | fix |
| ATT-15 | Arrival costs about 11k tokens in Claude Code and about 23k in Codex | cosmetic | days | defer |
| ATT-16 | Gemini CLI and Cursor files and rows in every quilt; "Set up" means "file exists" | cosmetic | hours | hide |
| ATT-17 | Docs and shipped texts disagree with the clients as they are now | cosmetic | hours | fix |
| ATT-18 | The shell variant is offered to the person | irrelevant | hours | hide |

### ATT-1: setup needs a typed command

- Settings › Agents with no agent layer says "To write one, run `loom ai init` in a terminal" (`arras/src/lib/shell/settings/Agents.svelte:43-45`), and each app row without a file shows a command to run (`Agents.svelte:79`, commands from `loom/src/loom/config_edit.py:431-436,469`).
- The person cannot delegate it to their agent: `ai init` is outside `AGENT_COMMANDS` (`loom/src/loom/ai/layout.py:21-37`), so it refuses under any agent marker (`loom/src/loom/cli/help.py:163-188`). In this Code tab session it refused with "an agent is running this shell (AI_AGENT is set) and may not run `loom ai init`".
- **Fix:** a viewer action that calls `install_layer` (`loom/src/loom/cli/ai.py:136-189`) through a new write endpoint, refused to a declared agent like `agents-update` (`loom/src/loom/render/api.py:591-601`).
- **Owns:** `render/api.py` (new endpoint), `Agents.svelte`. Independent.

### ATT-2: no presence

- `loom mcp` keeps nothing about its client. The server never reads `clientInfo`, keeps no heartbeat and writes no record of being attached (`loom/src/loom/mcp/server.py:34-195`).
- A call is logged only when a session is active (`server.py:331-347`). The probe below confirms that a fresh agent, with no session, leaves no trace.
- **The viewer's "Set up" means "the file exists",** not "connected" (`config_edit.py:430`).
- The one per-agent trace is the `since` marker (`.loom/since/<slug>.json`, `loom/src/loom/since.py:1-3`). The probe wrote `probe-agent.json`, but nothing reads it for the viewer, and the watcher ignores the directory (`loom/src/loom/render/watch.py:101`).
- This is the author's first complaint ("Is an agent currently attached?").
- **Fix:** the design in C2.
- **Owns:** `mcp/server.py`, a new `presence.py`, `paths.py`, `gitignore.py`, `watch.py`, a `serve` endpoint, and one arras component. Two to three days. The server half is independent; the viewer half waits on the API shape, so fix that first.

### ATT-3: edits in place are invisible

- **What the agent is told:** it may edit "every other file the quilt does not protect … the author's documents and notes among them". It is warned that "unless the quilt tracks edits … an edit in place is seen nowhere else" (`loom/src/loom/assets/ai/orientation.md:30`).
- **The default:** `track_edits` is False (`loom/src/loom/scan/quilt.py:66`).
- **The consequence:** in Claude Code's Accept edits or Auto mode, an agent rewriting a `.tex` file leaves nothing in Your Changes or anywhere else. "Where did the agent's work end up" then has no answer.
- **Fix, either way:**
  - Turn `track_edits` on whenever the agent layer is written.
  - Or add the person's documents to the default `[agents] deny`, so agents must `loom suggest`.
- **Owns:** `scan/quilt.py` default, or `ai/layout.py` init. Hours. Needs the author's choice of which.

### ATT-4: Codex may not start the server

- **What loom writes:** `.codex/config.toml` with `[mcp_servers.loom]`, an absolute `--quilt` and `default_tools_approval_mode = "approve"` (`loom/src/loom/ai/clients.py:54,103-113`; observed in scratch).
- **What Codex documents:**
  - Project `.codex/config.toml` is read for "trusted projects only" (https://learn.chatgpt.com/docs/extend/mcp).
  - An untrusted project "disables project-local configuration" (https://learn.chatgpt.com/docs/agent-approvals-security).
  - Neither page says whether the ChatGPT app's Codex side loads project-scoped MCP servers.
  - Codex finds the project root by `.git` (https://learn.chatgpt.com/docs/config-file/config-advanced). Folders without version control get `read-only` recommended (agent-approvals-security).
- **Quilts are not git repositories by default:** `loom init` runs git only with `--git` (`loom/src/loom/cli/quilt.py:231`).
- **The quilt path is pinned:** the `--quilt` path breaks if the quilt is moved (`clients.py:108`).
- **If the server never starts,** a Codex user has no loom tools. AGENTS.md then sends the agent to the shell route, with ATT-13's problems.
- **Fix:**
  1. Verify in the live wave first (hours).
  2. Fallback (a day, and needs the author's decision, because it writes outside the quilt): a user-level entry in `~/.codex/config.toml` with `cwd` per quilt. Alternatively, a Codex desktop plugin bundling the server, installed through `codex://plugins/<name>?marketplacePath=` (https://learn.chatgpt.com/docs/reference/commands).
- **Owns:** `ai/clients.py`. Independent.

### ATT-5: a second approval for loom's server in Claude Code

- Claude Code prompts in interactive sessions before using a project `.mcp.json` server.
- `enabledMcpjsonServers` in the project's `.claude/settings.json` is ignored only in an untrusted folder, so it is honoured once the person trusts the folder (https://code.claude.com/docs/en/mcp).
- Loom writes that settings file whole (`layout.py:170-190`) but does not pre-approve its own server. The person may therefore meet a folder-trust dialog and then a server approval.
- How the Code tab shows either prompt is undocumented (https://code.claude.com/docs/en/desktop).
- **Fix:** add `"enabledMcpjsonServers": ["loom"]` to `permissions_json`.
- **Owns:** `ai/layout.py`, which ATT-10 also edits, so give both to one implementer. Hours. Verify in the live wave.

### ATT-6: nowhere says what an agent is told, sees and may change

- The viewer says two things about agents:
  - the file tree's "AI" mark per path (`arras/src/lib/shell/AgentMark.svelte`);
  - Settings › Agents' deny list (`Agents.svelte`).
- **What nothing shows:**
  - the line in CLAUDE.md/AGENTS.md;
  - the server's instructions (`loom/src/loom/ai/orient.py:134-156`);
  - that an agent can ask for the open page and selection (`loom here`, fed by `arras/src/lib/here.svelte.ts:1-3`);
  - that every annotation the person writes reaches the agent through `loom since`;
  - which client enforces which boundary.
- **Fix:** the panel in C3.
- **Owns:** a new arras component and a small manifest addition. A day. The live parts wait on ATT-2.

### ATT-7: no activity list

**Where agents' work shows today:**
- Review › Your Changes lists suggestions and "To do: the open annotations from others" (`arras/src/routes/review/+page.svelte:2`).
- The Sessions table lists transcripts (`arras/src/routes/review/record/sessions/+page.svelte:2`).
- A session's "What it did" reads its command log (`arras/src/lib/workspace/items/SessionDid.svelte:2`).
- `/threads` is a leftover list (`arras/src/routes/threads/+page.svelte`).

**What has no home:**
- resolved or closed agent annotations;
- agent documents in `.loom/copies/`;
- pages written with `loom write`;
- library proposals;
- an agent's edits in place.

No view answers "what did Codex do today, and where".

- **Fix:** C4.
- **Owns:** a new arras route, built from manifest data (annotations carry `author.kind`). Two to three days. Independent of ATT-2.

### ATT-8: sessions are quilt-global

- **One shared active session:** `loom session new` makes its session the quilt's one active session (`loom/src/loom/cli/session.py:56-78`, `loom/src/loom/sessions.py:207-224`). Every MCP call logs to that active session (`server.py:305-312`). Two conversations, or the person and an agent, therefore write into whichever session was opened last.
- **No session to start with:** an agent arriving with none open must open one before `loom session say` works. The showcase has none (`.loom/sessions/active` is absent).
- **`since` markers per app, not per conversation:** the marker is one per agent name (`since.py:1-3`), so two Claude Code conversations share "Claude Code Agent". The second never hears what the first already consumed.
- **Both pilot clients run one server process per conversation:**
  - Codex runs one per chat under its default protocol (https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/connection_pool.rs).
  - Claude Code stops a stdio server when the session ends (https://code.claude.com/docs/en/mcp).
- **Fix:** the server binds one loom session per process, lazily on the first write, passes `--session` to each call, and keys `since` by that session.
- **Owns:** `mcp/server.py`, `since.py`. A day. Same file as ATT-2, so same implementer.

### ATT-9: the viewer cannot hand a request to the agent app

- **What exists:**
  - Quote copies words and their place (`docs/design/agents.md:106`).
  - "Ask an agent" exists only for a work's overview (`arras/src/lib/review/ask.ts`).
  - The viewer can already `open -a <App>` (`loom/src/loom/files.py:470-483`, `render/api.py:641-654`).
- **Codex:** `codex://new?path=<abs>&prompt=<text>` opens a new local chat in that folder with the prompt in the composer, not sent (https://learn.chatgpt.com/docs/reference/commands).
- **Claude desktop:** no local-folder link is documented.
  - `claude://code/new` is documented with `ssh_host`/`ssh_folder`/`q` only (https://code.claude.com/docs/en/desktop).
  - `claude-cli://open?cwd=&q=` opens a terminal, not the app, and registers only after the CLI has been used (https://code.claude.com/docs/en/deep-links).
  - `claude --desktop` opens Desktop on the current directory, but needs the CLI at v2.1.285 or later (same desktop page).
- **Fix:** C5.
- **Owns:** an arras "Ask agent" control, and a `serve` endpoint that opens a `codex://` URL. A day. Independent.

### ATT-10: modes are MCP prompts only

- The nine modes are MCP prompts (`loom/src/loom/mcp/prompts.py`, `server.py:92-123`). The design says "Nothing is shaped for one vendor's skill or command files" (`docs/design/agents.md:116`).
- **Codex:** does not support MCP prompts (https://github.com/openai/codex/issues/5059, open). Its custom prompts are deprecated (https://learn.chatgpt.com/docs/custom-prompts). Skills in `.agents/skills/<name>/SKILL.md` are its way (https://learn.chatgpt.com/docs/build-skills).
- **Claude Code CLI:** lists MCP prompts as `/loom:flow (MCP)` (https://code.claude.com/docs/en/mcp).
- **Code tab:** its `/` menu is documented as built-in commands, custom, project and plugin skills (https://code.claude.com/docs/en/desktop). Whether it lists MCP prompts is undocumented.
- **Fix:** thin skills `loom-<mode>` in both `.claude/skills/` and `.agents/skills/`, each saying only "call `loom_ai_mode` with this name and follow it". The mode file stays the one copy.
- **Owns:** `ai/layout.py` (with ATT-5) and `gitignore`/upgrade handling. Hours to a day.

### ATT-11: the edit boundary for the agent's own edits

**Loom-made writes are refused everywhere:**
- Every loom command refuses a protected path under an agent (`loom/src/loom/cli/_common.py:197-212`).
- The MCP server sets `AI_AGENT=1` for each call (`server.py:202`).

**Claude Code:**
- Claude Code's own Edit tool is refused through loom's generated deny rules (`layout.py:170-190`; observed: 20 `Edit(/…)` denies).
- But "Edit/Read deny rules … do not cover arbitrary subprocesses", and the sandbox covers shell commands only (https://code.claude.com/docs/en/permissions, https://code.claude.com/docs/en/sandboxing).

**Codex:**
- Codex's own edits are not limited at all by what loom writes. `.codex/rules/loom.rules` holds command-prefix rules only (`layout.py:198-216`).
- The orientation says so: "Codex, Gemini CLI and Cursor do not, so there the list is yours to keep" (`orientation.md:36`).
- A Codex agent can rewrite `.loom/annotations/`, `config.toml` or the research state by hand.
- Codex now has permission profiles with per-subpath read and write (https://learn.chatgpt.com/docs/permissions). Whether a project file may set them is undocumented.

**Fix:**
- For v0.1, state this truthfully in C3 (hours).
- Try a Codex profile after the live wave (days; defer if it fails).

### ATT-12: loom's texts push commands at the person through the agent

**Where loom puts commands in the agent's way:**
- The CLAUDE.md/AGENTS.md line tells the agent to run `loom doctor` "to tell the author why" (`layout.py:69`).
- `loom_here` with no viewer answers "`loom serve` starts the viewer; the person opens it" (`loom/src/loom/cli/here_cmd.py:33-37`).
- The `ai init` report's next step is `loom session new` (`cli/ai.py:265`).

An agent relays these as instructions to type, against the v0.1 bar.

- **Fix:** reword them to point at viewer actions.
- **Owns:** the three strings. Hours. Coordinate the wording with the install auditor.

### ATT-13: Codex's shell route

**Detection depends on a marker Codex may not set:**
- Loom detects a Codex agent's shell only by `CODEX_SANDBOX` (`_common.py:217,231`).
- From memory and unverified: Codex sets that variable only when it runs a command under its sandbox. In Full access mode, `loom accept` typed by a Codex agent would then run as the person.
- `.codex/rules/loom.rules` forbids the author's commands (`layout.py:213-215`), but only if Codex reads project rules, which needs trust (unverified).

**The sandbox breaks loom's writes and network:**
- Network is off by default (https://learn.chatgpt.com/docs/agent-approvals-security), so `loom library update` fails in the shell.
- A non-git quilt gets `read-only` recommended, so shell `loom annotate` would fail.

**The MCP server avoids both:**
- It runs outside the sandbox ("MCP servers use their own process", https://learn.chatgpt.com/docs/permissions).
- It sets `AI_AGENT=1` itself.

**What Claude Code sets, observed in this Code tab session:** `AI_AGENT=claude-code_2-1-321_agent`, `CLAUDECODE=1`, `CLAUDE_CODE_ENTRYPOINT=claude-desktop`.

- **Fix:**
  1. Make MCP the default (C6).
  2. Check Codex's environment in each permission mode during the live wave, and add any marker it sets.
- Hours. Independent.

### ATT-14: what a transcript is

- A transcript is what the agent chooses to write with `loom session say` (`docs/design/agents.md:91-104`), not the conversation. The conversation lives in the agent app.
- The viewer does not say this. When an agent does not comply, the transcript is simply empty.
- The orientation asks for it (`orientation.md:64`), but nothing checks.
- **Fix:** name it "the agent's report" or similar in C4 and explain it in C3. With ATT-8, show an empty conversation as "connected, wrote no report".
- Hours, riding on C4.

### ATT-15: arrival cost

Measured in the scratch copy:

| What | Size | About |
|---|---|---|
| Server instructions | 2,668 characters | 0.7k tokens |
| `tools/list`, 42 tools | 48,776 characters | 12k tokens |
| `loom_ai_orient` result | 41,178 characters, 6,935 words | 10k tokens |
| The CLAUDE.md line | 330 characters | 0.1k tokens |

- The orient result is never moved to a file (`server.py:29`).
- **Claude Code** defers MCP tool definitions by default and loads only names and instructions, then cuts instructions at 4,096 characters (https://code.claude.com/docs/en/mcp). Total about 11k tokens before work.
- **Codex:** I found no deferral documented, so assume about 23k tokens. Codex keeps "the first 512 characters" of instructions as the summary (https://learn.chatgpt.com/docs/extend/mcp). Loom's first 512 stand alone.
- Startup is about 0.4 s to initialize, warm, against Codex's 1,000 ms grace for optional servers.
- **Rec: defer.**

### ATT-16: extra clients

- `loom ai init` writes `.gemini/settings.json` and `.cursor/mcp.json` into every quilt (`clients.py:52-67`; observed).
- Settings › Agents lists four apps, each "Set up" meaning only that the file exists (`config_edit.py:426-437`).
- **For the pilot:** noise in the person's folder, and a false "Set up".
- **Fix:** write only Claude Code's and Codex's files by default; keep `--client` for the rest.
- Hours. `clients.py` and `config_edit.py`.

### ATT-17: stale texts

**Where the texts are stale:**
- **`docs/design/agents.md:80`:** says Codex's entry skips the per-tool prompt. The documented values of `default_tools_approval_mode` leave `approve` undefined, and "Destructive app/MCP tool calls always require approval" (agent-approvals-security). `loom_write` is marked destructive (`loom/src/loom/mcp/tools.py:199-207`).
- **`layout.py:201`:** still says "Unverified: Codex was not installed".
- **Settings' Apps row text:** "Claude Code refuses a denied path itself; the others are told the list" (`arras/src/lib/shell/settings/catalog.ts:68`) predates Codex's permission profiles.

**Fix:** hours.

### ATT-18: the shell variant in the person's view

- `--shell` and its viewer line (`Agents.svelte:83`, `config_edit.py:436`) offer the person a choice they should not face in v0.1.
- **Rec: hide** it from the viewer, and keep the flag for tests and agents without MCP.

## Part A: what exists

### Files written (observed: `loom ai init` in the scratch copy)

| File | For | Says | Committed? |
|---|---|---|---|
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | Claude Code, Codex, Gemini | One line: call `loom_ai_orient` first; with no loom tools, run `loom ai orient` and `loom doctor`; write anywhere but the protected paths (`layout.py:69`). Appended to the person's text, never owning it (`layout.py:247-271`). | yes |
| `.loom/ai/orientation.md`, `rules.md`, `formatting.md`, `modes/*.md` (9), `README.md`, `.loom-modes-version` | every agent, via `loom_ai_orient` | The contract: what a quilt is, where to write, author-only acts, where to look, sessions and transcript, modes; rules and blocks; formatting | yes |
| `.claude/settings.json` | Claude Code | 55 allows: `Edit(.loom/sessions/**)`, `.loom/build/**`, `.loom/copies/**`, the types file, `Bash(loom <agent cmd>*)`, `mcp__loom__*`. 54 denies: `Edit(/…)` on loom's records, `config.toml`, the research state and `[agents] deny`; `Bash(loom <author cmd>*)`; `Bash(rm *)` (`layout.py:170-190`). | yes |
| `.codex/rules/loom.rules` | Codex | `prefix_rule` allow for agent commands, forbidden for author commands and `rm` (`layout.py:198-216`) | yes |
| `.mcp.json` | Claude Code (CLI and Code tab), VS Code | `loom` server: absolute loom path, `mcp --as "Claude Code Agent"`, no `--quilt`, `type: stdio` | gitignored |
| `.codex/config.toml` | Codex (CLI, app, IDE) | `[mcp_servers.loom]` with `--as "Codex Agent" --quilt <abs>` and `default_tools_approval_mode = "approve"` | gitignored |
| `.gemini/settings.json`, `.cursor/mcp.json` | Gemini CLI, Cursor | Same server with `--quilt`; Gemini `trust: true` | gitignored |

### How the server starts

- **Who starts it:** the client spawns `loom mcp --as NAME` over stdio from the files above (`loom/src/loom/cli/mcp_cmd.py:20-37`). No daemon, and nobody else starts it.
- **How long it lives:** until the client closes stdin (`server.py:191-195`). Both pilot clients run one process per conversation (ATT-8).
- **What it refuses:** a name with no Agent or AI in it, and an environment without the MCP SDK.
- **How a call runs:** each call is a `loom` subprocess in the quilt root with `AI_AGENT=1`, `LOOM_PROGRESS=off` and `LOOM_LOGGED=1` (`server.py:198-205`). Reading tools run in parallel; writes are serialised by one lock (`server.py:69-74`).
- **What it advertises:** capabilities `tools`, `prompts` and `resources`, all with `list_changed: false`. There is no logging capability (observed in the stdio probe).

### What it exposes (stdio probe)

- **Tools (42),** one per agent command, minus `mcp` and `serve` (`loom/src/loom/mcp/tools.py:97-101`; the list is in `layout.py:21-37`).
- **Tool hints** come from `ACTS` (`tools.py:199-207`):
  - read-only for readers;
  - destructive only for `loom_write`.
- **Prompts (9),** one per mode, each with one optional `target` word (`prompts.py:11-13`).
- **Resources (36)** in the showcase: `quilt:KEY`, `cited:ID[?page=N]`, `quilt:state`, and templates (`loom/src/loom/mcp/resources.py`).
- **Large results:** past 40,000 characters a result goes to `.loom/build/agent/<session>/` and the tool returns the path (`server.py:26-31,229-233`).

### What an agent is told on arrival, and the cost

1. **First, the root file line** (CLAUDE.md or AGENTS.md).
2. **Then the server instructions** (`orient.py:134-156`). They say:
   - who the agent is attached as;
   - to call `loom_ai_orient` first and after compaction;
   - that tools map to commands;
   - that `loom_here` and `loom_since` are the bridge;
   - the annotation types;
   - the mode index.
3. **Then `loom_ai_orient`:** orientation, rules, annotation types, formatting, modes, live state and research state.

Costs are under ATT-15: about 11k tokens in Claude Code, about 23k in Codex.

### Page and selection

- **The viewer reports the place:** each viewer tab reports its place to `loom serve` when it settles and on focus. That covers the item, the block at the pane's top, the selection or PDF region, the open annotation, the block under review, and the chosen session. The tab touched last wins, and the place is held in memory only (`here.svelte.ts:1-3`, `render/api.py:657-692`).
- **The agent reads it:** `loom_here` fetches the place with the token and resolves it to links (`here_cmd.py:29-61`).
- **Without the viewer:** with no server it answers "nothing serves this quilt" (probe).
- **The person is not told** that this happens, and has no record of when an agent read it unless a session was active (ATT-2, ATT-6).

### What the viewer knows of agents

- Annotations, suggestions and records carry author name and kind.
- Sessions and transcripts, with each session's command log.
- The file tree's AI marks.
- Settings › Agents: the deny list, the protected list, "Review edits made in place", and the four apps with "Set up" or a command.
- **Not known:**
  - whether any agent is attached;
  - which app or version;
  - the last call;
  - the conversation;
  - the `since` markers.

### Where "what an AI may edit" is expressed and enforced

| Write | Claude Code (Code tab) | Codex (ChatGPT app) | Gemini CLI, Cursor |
|---|---|---|---|
| Through a loom command or MCP tool | Enforced by loom (`_common.py:197-212`; author verbs `help.py:163-188`) | Same | Same |
| By the agent's own edit tool | Enforced by Claude Code's `Edit(/…)` denies, once settings apply; not for arbitrary subprocesses | Not enforced; stated only (`orientation.md:36`); profiles possible, unverified for project scope | Stated only |
| By shell commands | Denied `Bash(loom <author>*)`, `Bash(rm *)`; loom refuses under markers | `loom.rules` forbids author commands if the project is trusted; marker detection unsure (ATT-13) | Loom refuses under markers |
| Approval of loom's tools | `mcp__loom__*` allowed (no prompts) | `approve` mode, meaning undocumented; destructive tools always ask | Gemini `trust: true` |

## Part B: what the pilot clients offer (2026-11-13)

### Claude Code in the Claude desktop app's Code tab

**MCP registration**
- The Code tab reads `.mcp.json` and `~/.claude.json` as the CLI does, and also `claude_desktop_config.json`. It adds a Connectors UI.
- A same-name user-scope stdio server in `~/.claude.json` beats `.mcp.json`, unlike the CLI.
- `.mcp.json` and `.claude/settings.json` are view-only in its file pane.
- Source: https://code.claude.com/docs/en/desktop (Shared configuration).
- No one-click install for a project server.

**First-run prompts**
- The CLI asks approval for project `.mcp.json` servers in interactive sessions. `enabledMcpjsonServers` in the project's `.claude/settings.json` holds once the folder is trusted (https://code.claude.com/docs/en/mcp).
- Project allow rules apply after workspace trust (https://code.claude.com/docs/en/permissions).
- How the Code tab presents either prompt is undocumented.

**Instruction file**
- CLAUDE.md and CLAUDE.local.md are read by both CLI and Desktop (desktop page).
- AGENTS.md is read natively only when no CLAUDE.md exists, or with a setting (https://code.claude.com/docs/en/memory). Loom writes both files, so this is fine.

**Skills, commands and prompts**
- Project skills from `.claude/skills/` appear in the `/` menu and "+ › Slash commands" (desktop page).
- MCP prompts appear as `/loom:flow (MCP)` in the CLI (mcp page). In the Code tab: undocumented.
- Resources can be @-mentioned in the CLI.

**Permissions**
- Modes: Manual, Accept edits, Plan, Auto, and Bypass once enabled.
- `settings.json` rules apply. `/permissions` replies "isn't available in this environment"; edit the files instead (desktop page).
- Path rules use `Edit(…)`. The sandbox covers Bash only, and "Claude's file tools, MCP servers, and hooks run outside it" (https://code.claude.com/docs/en/sandboxing).

**Opening from another program**
- No documented local-folder link for the Code tab.
- `claude://code/new?ssh_host=…&ssh_folder=…&q=…` is documented for SSH only.
- `claude --desktop` opens Desktop on the current directory and needs the CLI at v2.1.285 or later.
- `claude-cli://open?cwd=&q=` opens a terminal CLI session with the prompt filled in and not sent (https://code.claude.com/docs/en/deep-links).
- Loom can already `open -a Claude`.

**Handshake and lifetime**
- `clientInfo` may be `claude-code`; the docs say not to gate on it (https://claude.com/docs/connectors/building/testing).
- Elicitation is declared as `{form, url}` to stdio servers.
- Claude Code answers `roots/list` with the launch directory and sets `CLAUDE_PROJECT_DIR` in the server's environment.
- Tool search defers tools; instructions are cut at 4,096 characters.
- A stdio server stops when the session ends; a crash marks it failed until the person reconnects (mcp page).
- Observed in this very Code tab session's shell: `CLAUDE_CODE_ENTRYPOINT=claude-desktop`, `AI_AGENT=claude-code_<version>_agent`, `CLAUDECODE=1`. Whether the MCP server inherits them is unverified.

### Codex in the ChatGPT desktop app

**MCP registration**
- One config is shared by the app, the CLI and the IDE extension: `~/.codex/config.toml`.
- The project file `.codex/config.toml` is for "trusted projects only".
- In the app: Settings › MCP servers › Add server (STDIO, command), then Restart (https://learn.chatgpt.com/docs/extend/mcp).
- Whether the app loads project-scoped servers: undocumented.
- Desktop-only plugins can bundle a stdio server and install through a `codex://plugins/…` deep link (https://developers.openai.com/plugins/deploy/desktop-only, https://learn.chatgpt.com/docs/reference/commands).

**First-run prompts**
- Codex "may also start in `read-only` until you explicitly trust the working directory (for example, via an onboarding prompt or `/permissions`)".
- Version-controlled folders get Auto (workspace write plus on-request approvals) recommended; others get `read-only`.
- Untrusted "disables project-local configuration" (https://learn.chatgpt.com/docs/agent-approvals-security).

**Instruction file**
- AGENTS.md is read from the project root down to the current directory, capped at 32 KiB in total.
- CLAUDE.md is read only through `project_doc_fallback_filenames` (https://learn.chatgpt.com/docs/agent-configuration/agents-md).
- The docs describe CLI behaviour; the app is assumed to match (unverified).

**Skills, commands and prompts**
- Skills live in `.agents/skills/` up to the repo root, and in `~/.agents/skills`. `codex://skills` opens them (https://learn.chatgpt.com/docs/build-skills).
- MCP prompts are unsupported (https://github.com/openai/codex/issues/5059).
- Custom prompts are deprecated.
- Resources are exposed to the model through helper tools, with no user picker.

**Permissions**
- Sandbox modes: `read-only`, `workspace-write` and full access. The app's composer offers Ask, Approve for me, Full access and Custom.
- Writable roots keep `.git`, `.codex` and `.agents` read-only.
- Network is off by default.
- Permission profiles can set per-subpath read and write (https://learn.chatgpt.com/docs/permissions).
- MCP tools are approved per server or per tool. Only `writes` is defined; destructive-annotated tools always ask.
- The MCP server process is not sandboxed.

**Opening from another program**
- `codex://new?path=<abs>&prompt=<text>` opens a new local chat with that folder as the workspace and the prompt in the composer, not sent.
- `codex://threads/<id>` opens a chat.
- `codex://settings` and `codex://skills` exist (https://learn.chatgpt.com/docs/reference/commands).

**Handshake and lifetime**
- `clientInfo` is `codex-mcp-client`, with Codex's version and the title "Codex". The protocol defaults to 2025-06-18.
- No roots and no sampling are declared; elicitation is (https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/rmcp_client.rs).
- Each chat gets its own server process.
- The server receives only HOME, PATH, LANG and similar, plus `env` (source, connection_pool.rs and rmcp-client/src/utils.rs).
- Instructions: "the first 512 characters" are used as the summary.

### What forces loom to treat them differently

**Claude Code**
- It gives the server its project (roots, `CLAUDE_PROJECT_DIR`), so `.mcp.json` needs no path.
- It enforces path denies for its own edits.
- It lists skills, and in the CLI also MCP prompts.
- There is no documented way to open its desktop app on a folder with a prompt.

**Codex**
- It gives no project, so the entry needs `--quilt`.
- It loads the project file only when the project is trusted.
- It does not enforce loom's paths for its own edits unless profiles are used.
- It has no MCP prompts.
- It sandboxes its shell, with no network, while leaving MCP servers unsandboxed.
- Its deep link opens a chat in the quilt with a prompt.

**Footnote: Claude desktop chat**
- It uses only the user-level `claude_desktop_config.json` or a `.mcpb` extension: per user, a full restart after edits, and per-tool Allow once or Always allow.
- It has no project directory and no instruction file.
- MCP prompts appear as attachable items, not commands (https://modelcontextprotocol.io/docs/develop/connect-local-servers, https://claude.com/docs/connectors/building/mcpb).
- Loom's `--client claude-desktop` prints an entry. Out of v0.1.

## Part C: a design for v0.1

### 1. "Connect an agent" in the viewer

A first-run card on the home page when the quilt has no agent layer, and Settings › Agents always, each offering **Use with Claude** and **Use with Codex**. Nothing is written until the person clicks.

**Claude, three actions:**
1. Click **Use with Claude**. Loom writes:
   - `.loom/ai/`;
   - the CLAUDE.md and AGENTS.md line;
   - `.claude/settings.json`, now with `enabledMcpjsonServers: ["loom"]` (ATT-5);
   - `.claude/skills/loom-*` (ATT-10);
   - `.mcp.json`.
2. Click **Open Claude**. The viewer shows the quilt's path with Copy and Show in Finder, and says "In Claude, choose Code, then this folder". Loom runs `open -a Claude`, or `claude --desktop` in the quilt where a recent `claude` CLI exists (to verify).
3. In Claude, accept the folder-trust prompt and send any first message. The viewer changes from "Waiting for Claude…" to "Connected: Claude Code (desktop app) at 14:02" when the presence record from C2 arrives.
   - If none arrives within a minute of a message, it says which of trust, server approval or an old Claude version to check.

**Codex, two actions:**
1. Click **Use with Codex**. Loom writes:
   - `.loom/ai/`;
   - the AGENTS.md line;
   - `.codex/config.toml`;
   - `.codex/rules/loom.rules`;
   - `.agents/skills/loom-*`.
2. Click **Open in Codex**, which opens `codex://new?path=<quilt>&prompt=Start working with loom.`. Trust the folder if Codex asks, then send.
   - Confirmation is presence with `clientInfo` `codex-mcp-client`.
   - If none arrives, the viewer offers the fallback from ATT-4 once the author has decided it.

### 2. Presence, truthfully

**What `loom mcp` writes**
- **At initialize,** a record in a protected, gitignored and watched directory (proposed `.loom/live/<pid>.json`) with:
  - the `--as` name;
  - `clientInfo` name, version and title;
  - the protocol version;
  - `CLAUDE_CODE_ENTRYPOINT` and `CLAUDE_PROJECT_DIR` when present;
  - the parent pid;
  - the start time;
  - the bound loom session (ATT-8).
- **At each call,** it updates the last tool and time.
- **On EOF of stdin,** it deletes the record.

**What `loom serve` does with them**
- It lists the records and drops any whose pid is gone.
- It pushes the list over its events stream.

**What the viewer shows:** a chip in the top bar, "No agent connected" or "Claude Code · 2 conversations · last call 3 min ago", that opens C3.

**What is observable:**
- the server process is alive, which in both pilot clients means a conversation holds a connection;
- the client's name and version;
- each loom call;
- which loom session it writes to.

**What is not observable:**
- whether the person is in that conversation now;
- whether the model is working between calls;
- anything the agent does outside loom (its own edits and shell, except `loom` commands);
- the conversation's title or id (unless a client passes one, unverified);
- whether a desktop app keeps idle sessions' servers alive.

**So the chip says "connected" (process alive) and "active" (a call within two minutes), never "watching" or "working".** A shell-route agent has no process; loom commands run under a marker can stamp "last seen via shell" without claiming a connection.

### 3. "What the agent sees and may change": one panel

Opened from the chip and from Settings › Agents.

- **Told:**
  - the line in CLAUDE.md or AGENTS.md, verbatim;
  - the server's instructions, verbatim;
  - links that open the orientation, rules and modes in the viewer (the author may edit them).
- **Sees:**
  - "When it asks what you are looking at, it gets:" followed by what `loom here` would return now, live;
  - "It reads every annotation and reply you write, and what you keep, discard or accept; Claude Code Agent last read them at 14:05", from the `since` marker;
  - "It can read every file in this folder with its own tools."
- **May change:**
  - "Edits in place: every file but these", with the protected and deny lists and a link to the tree marks;
  - "Your documents: changes show in Your Changes" or "are not shown, turn on Review edits made in place" (ATT-3);
  - "Enforced by: loom for its commands; Claude Code also for its own edits; Codex does not stop its own edits" (ATT-11).
- **Never:** the author's acts, in words ("accept, keep or discard edits, delete annotations, file papers").

### 4. "Where did its work go": an activity list

**The page**
- One page, **Agent activity**, newest first.
- Each row: when, who (agent and conversation), what, a link to its place, and its state now.
- Kinds of row:
  - annotation on X;
  - reply;
  - suggested edit in Y;
  - agent document;
  - page written (research state, overview);
  - library proposal;
  - a file edited in place, when tracked;
  - report message.
- Rows are grouped by conversation (the loom session bound per server process), and each group opens to its report (today's transcript view, `ChatView.svelte`) and its "What it did" log.
- All of it comes from the manifest, so it does not wait on presence.

**What becomes of the existing pages**
- The Sessions table merges into it.
- `/threads` is hidden.
- Review › Your Changes stays the to-do of decisions; the activity list is the history of what happened, and each row whose decision waits links there.

### 5. Handing a request to the agent app, with no chat box

**Ask agent**
- An **Ask agent** control appears on a selection, a block, an annotation and a paper page.
- It composes `In loom: <link> — “<quote>”. ` with a field for the person's words. Since `loom_here` exists, the default text can be just "Look at what I have open in loom."
- **Codex:** **Open in Codex** sends it through `codex://new?path=…&prompt=…`, as a new chat with the prompt not sent.
- **Claude:** **Copy and open Claude** (clipboard plus `open -a Claude`), since no local-folder link exists.

**Modes, per client:**
- **Code tab:** `/loom-flow` skills, plus `/loom:flow (MCP)` if listed.
- **Codex:** `$loom-flow` or `/skills`.
- **Viewer:** the mode buttons beside Ask agent prefill the matching command for the chosen app.
- The skills stay thin pointers to `loom_ai_mode`, so the mode files remain the one copy.

### 6. MCP or shell: MCP is the default, and the shell is a fallback the agent may use

**Why MCP:**
- Both pilot clients run stdio MCP.
- Presence and identity exist only over MCP, with `clientInfo` and a signed `--as`.
- Codex's sandbox leaves the MCP server unsandboxed. Over the shell, the read-only recommendation for non-git folders and the network-off default break loom's writes and `library update` (ATT-13).
- The server sets `AI_AGENT=1`, so the guard never depends on a client's marker.
- Claude Code's tool search keeps the tool list cheap.
- Desktop chat, were it ever wanted, is MCP-only.

**What the shell keeps:**
- Agents keep it as a second channel for `--batch`, filtering and a server that failed to start.
- The permission files already allow it.
- The orientation should say tools first and shell only when a tool fails.

**What goes from the person's view:** the `--shell` variant (ATT-18).

### 7. Build order

| # | Work | Effort | Owns | Waits on |
|---|---|---|---|---|
| 1 | Viewer setup endpoint and cards (ATT-1), writing only Claude and Codex files (ATT-16) | a day | `render/api.py` (new endpoint), `Agents.svelte`, home card, `ai/clients.py` defaults | nothing |
| 2 | Pre-approve the server and add mode skills (ATT-5, ATT-10) | hours to a day | `ai/layout.py`, `gitignore.py`, the upgrade path | nothing; one owner with #1's `clients.py` edits, or sequence after |
| 3 | Edits in place visible by default (ATT-3) | hours | `scan/quilt.py` or `ai/layout.py` | the author's choice |
| 4 | Presence records, and sessions per conversation (ATT-2, ATT-8) | 2-3 days | `mcp/server.py`, new `presence.py`, `since.py`, `paths.py`, `watch.py`, a `serve` endpoint | nothing, but fix the API shape first for #5 |
| 5 | Presence chip and the panel (C2, C3, ATT-6, ATT-11 wording) | 1-2 days | new arras components, manifest config fields | #4's API shape; static parts can start |
| 6 | Agent activity page, merging Sessions and hiding Threads (ATT-7, ATT-14) | 2-3 days | new arras route, `routes/threads`, `routes/review/record/sessions` | nothing |
| 7 | Ask agent, Open in Codex, Copy and open Claude (ATT-9) | a day | arras control, `serve` open-URL endpoint (`codex://` only) | nothing |
| 8 | Wording sweep (ATT-12, ATT-17) | hours | the strings named | after #1 to #3 |
| 9 | Codex fallback if the live wave shows project config is not loaded (ATT-4) | a day | `ai/clients.py` | the live wave and the author's decision |

**Left out of v0.1:**
- desktop chat and `.mcpb`;
- Gemini and Cursor by default;
- Claude or Codex plugins as the install route;
- Codex permission profiles;
- slimming the orientation;
- links into a client's conversation;
- coordination between simultaneous agents beyond per-conversation sessions.

## For the live wave (unverified here)

- **Code tab: approvals and prompts.**
  - What the Code tab shows for a project `.mcp.json` server, and whether `enabledMcpjsonServers` in `.claude/settings.json` silences it after trust.
  - Whether it lists MCP prompts in `/`.
- **Code tab: server process.**
  - Whether one server runs per session, and whether idle sessions keep it alive.
  - Whether the server inherits `CLAUDE_CODE_ENTRYPOINT`.
  - Whether `claude://code/new?q=…` without `ssh_host` opens a local session.
- **ChatGPT app's Codex: config and trust.**
  - Whether it loads project `.codex/config.toml` MCP servers.
  - Which trust prompt appears for a non-git folder.
  - Whether `.codex/rules/*.rules` and `.agents/skills` are read.
- **ChatGPT app's Codex: approvals.**
  - What `default_tools_approval_mode = "approve"` does.
  - Whether `loom_write` prompts.
- **ChatGPT app's Codex: environment.**
  - Which environment variables its shell sets in each permission mode (ATT-13).
  - Whether `CODEX_SANDBOX` is absent under Full access.
- **Both apps:** cold-start time of `loom mcp` on a fresh Mac against Codex's 1,000 ms grace.

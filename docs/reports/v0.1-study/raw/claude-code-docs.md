# Claude Code facts, checked against its documentation

A check of ten facts the attach design rests on, against Claude Code's published documentation on 2026-11-13, by a documentation agent. Each is marked documented, not documented, or ambiguous. Ids are DOCS-1 to DOCS-10. Nothing here was tried in the app.

| id | question | marking | what the documentation says | source |
|---|---|---|---|---|
| DOCS-1 | Does picking a folder in the desktop app's Code tab count as trusting it? | ambiguous, leaning not documented | The trust dialog is documented for the terminal CLI and the VS Code extension, not for `claude -p` or the SDK. The desktop app is not named. The only desktop trust text concerns SSH folders. A project's `permissions.allow` is withheld until trust in CLI-style sessions; desktop behaviour is unknown. | code.claude.com/docs/en/permissions.md, desktop.md |
| DOCS-2 | How are a project's `.mcp.json` servers approved? | documented for interactive CLI sessions; not documented for the Code tab | Claude Code prompts for each project server, shown as "Pending approval". In untrusted folders `enableAllProjectMcpServers` and `enabledMcpjsonServers` committed in the repository are ignored. Whether the Code tab loads project servers, and where a prompt appears, is not stated. | mcp.md, desktop.md, errors.md |
| DOCS-3 | Do an MCP server's prompts appear as commands? | documented for the CLI; not documented for the Code tab | CLI: `/servername:promptname` and `/mcp__servername__promptname`. The Code tab's `/` menu is described as built-in commands, custom skills, project skills and plugin skills, with no mention of MCP prompts. | mcp.md, desktop.md |
| DOCS-4 | Are project skills discovered? | documented | `.claude/skills/<name>/SKILL.md` is discovered and invoked as `/skill-name`; the Code tab's `/` menu lists project skills. | skills.md, desktop.md |
| DOCS-5 | Can a project hook report an agent's file edits and a session's start? | documented for the CLI; ambiguous for the Code tab | `PostToolUse` input carries `session_id`, `cwd`, `permission_mode`, `tool_name`, `tool_input` (with `file_path` for Edit and Write), `tool_response`. Edit and Write matchers do not see file writes made through Bash; the options are a `Stop` hook, matching Bash, or a `FileChanged` hook (input: `file_path`, `event`). `SessionStart` carries `source` (startup, resume, clear, compact, fork), `session_id`, `cwd`. Settings-file hooks are held until the trust dialog is accepted in interactive sessions. MultiEdit is called legacy. Whether hooks fire in the Code tab was not found stated. | hooks.md, hooks-guide.md |
| DOCS-6 | How are file deny rules enforced? | documented, with one ambiguity | Deny is evaluated first. `Edit(...)` patterns use gitignore syntax. `Write(...)` rules do not match: use `Edit(...)`. Read and Edit denies also cover file commands in Bash (`cat`, `sed`, `tee`) and redirects, but not arbitrary scripts that write files, and Bash rules are not a security boundary. Whether deny rules hold in bypass mode is not stated. | permissions.md |
| DOCS-7 | Server lifetime and identity | partly documented | On session end a stdio server gets SIGINT, then SIGTERM, then SIGKILL. `CLAUDE_PROJECT_DIR` and `CLAUDECODE=1` are set for stdio MCP servers; `CLAUDE_CODE_CHILD_SESSION` is set for Bash and hooks, explicitly not for MCP servers. Start time, one process per session, restart on resume, `CLAUDE_CODE_ENTRYPOINT`, a session id variable, and `clientInfo` are not documented. | mcp.md, env-vars.md |
| DOCS-8 | Can another program open a folder in the Code tab? | documented for the CLI only | `claude-cli://open?cwd=...&q=...` opens Claude Code in a new terminal window with an unsent prompt, once an interactive session has run. `claude://` is documented for desktop only for SSH links. No way to open a local folder in a Code tab session is documented. | deep-links.md, desktop.md |
| DOCS-9 | Do subagents share the parent's server connection? | documented | A string reference in `mcpServers` shares the parent's connection; an inline definition gets its own. Whether a server can tell a subagent's call from the parent's is not documented. | sub-agents.md |
| DOCS-10 | Other CLI and desktop differences | documented | `dontAsk` is CLI only; the desktop app reads `~/.claude/settings.json` for `permissions.defaultMode` and `env`; a per-folder mode outranks a project's default mode. The sandbox covers Bash only: file tools, local MCP servers and hooks run outside it; it is off by default. Where a failed MCP start-up is logged for a desktop user is not documented. | desktop.md, sandboxing.md |

## Checked by the lead against loom

- Loom's generated deny rules for Claude Code are all of the form `Edit(/path/**)` or `Bash(loom …*)` (`demos/showcase/.claude/settings.json`: 20 Edit denies, 34 Bash denies, 55 allows), which is the form DOCS-6 says is enforced. The showcase quilt denies loom's records and `config.toml`, and none of the person's document directories.
- This study's own session runs in the Code tab, and its shell has `CLAUDE_CODE_ENTRYPOINT=claude-desktop`, `CLAUDECODE=1` and `AI_AGENT` set. That is the Bash tool's environment, not an MCP server's.
- The agents working in the author's quant quilt, from Code tab sessions, used loom's MCP tools (`loom_ai_orient`, `loom_here`, `loom_since`) according to their findings log. That is indirect evidence that the Code tab starts a project's `.mcp.json` server.

## Only settled by trying it in the app

- Whether a picked folder shows a trust prompt, and whether a project's allow rules apply before it.
- Where the approval for a project's MCP server appears in the Code tab.
- Whether MCP prompts appear in the Code tab's `/` menu.
- Whether `PostToolUse`, `FileChanged` and `SessionStart` hooks fire there.
- Whether `Edit(...)` deny rules hold in default and bypass modes.
- Which environment variables reach a stdio MCP server started from the Code tab, and whether a server process is reused when a session is resumed.
- Where a failed MCP start-up is logged for a desktop user.
- Whether any URL or flag opens a folder in a Code tab session; the documentation describes none.

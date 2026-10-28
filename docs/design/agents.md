# Agents

How AI agents take part in a quilt: what they may do, what only the author may do, how they attach, and what they leave behind. Loom calls no model and assumes no vendor (P8, P9). An agent is a client, like an editor, and the person decides how much it does.

## What an agent may do

An agent reads the quilt through loom, never by reading directories wholesale: `loom status` for what needs doing, `loom search` to resolve "Theorem 4.8" to its id, `loom source KEY --closure` for exactly the context a key rests on, `loom library search` and `loom library read` for the literature. Reading through loom means what it reads is what loom resolved, and what it quotes can be checked against the page it came from.

It writes only through loom's records and its own places:

- **Annotations** on any target, with a kind, a severity where something is wrong, and proposed text as a payload the author can apply (`model.md`).
- **Proposed library results**, each quotation checked against the page before it is stored, waiting for the author to verify.
- **Relations** between results, each with its reason.
- **Agent documents** in `drafting-ai/`, copies it makes with `loom draft DOC --ai NAME` and edits there; the author adopts what they want.
- **Notes** about the mathematics (not built yet, see [README](README.md#decided-not-yet-built)).
- **The session's transcript**, with `loom session say` (below).
- **Files it hands the author** in its session's directory, which is never deleted from, and intermediates in `build/SESSION/`, which it may overwrite.

Every write names its writer with `--as`, and an agent's name says it is an agent (it contains "Agent" or "AI"), so that every record says what wrote it. Identity is declared, never sniffed from a shell; a session command with no declared name refuses.

## What only the author may do

Some acts make a claim only a person can make (*I checked this*, *I accept this mathematics*) or destroy what cannot be had back. They refuse any agent, whatever name it declares:

- `loom accept`, the author's claim that a key's mathematics is right;
- `loom library verify`, `discard`, `ignore`, `add`, `import` and `drop`;
- `loom adopt` and `loom sync incorporate`, which write the author's files (P7);
- `loom history restore`, `loom session delete --purge`, `loom ai discard`, `loom sync publish --push`;
- removing a relation someone else asserted.

Refusal is enforced, not requested. A declared name that calls itself an agent is refused. Under an agent's shell, recognised by the markers agent tools set (`AI_AGENT`, `CLAUDECODE`, `CODEX_SANDBOX`, `GEMINI_CLI`, `CURSOR_AGENT` and others), these acts are refused whatever name is declared, because a name cannot be checked and an agent typing the author's name is exactly the case to stop. The author runs them in a terminal of their own.

An agent that wants one of these acts writes a suggestion on the thing concerned, with its reasoning. There is no request object: a request becomes a queue that nags, and an agent that "requested verification" is one summary away from reporting that it verified (P15).

## How an agent attaches

Today an agent attaches through the command line. `loom ai init` writes a one-line `CLAUDE.md` and `AGENTS.md` telling the agent to run `loom ai orient`, which prints the orientation, the rules and the quilt's live state. It also writes permission files for the agents loom knows how to configure, generated from one table of agent commands (`AGENT_COMMANDS` in `loom/src/loom/ai/layout.py`). Under an agent's shell, a loom command outside that table refuses before it reads anything.

MCP is the intended way for any agent to attach (not built yet, see [README](README.md#decided-not-yet-built)):

- **A server per conversation.** `loom mcp` runs as a local subprocess the agent's app starts, with no daemon, no key and no model. It exposes one tool per agent command, generated from the same table, its schema from the command's options and its result the command's own output. Text is the default; JSON is there when the agent needs fields.
- **The author's acts are absent.** They are not tools at all, and the shell refusal stays behind them as a second line.
- **Large results go to a file** in the session's build area, and the tool returns its path, so the agent's own file tools can search it. Every result, and `run.log`, records the equivalent `loom …` command, so a person can rerun it.
- **Read-only tools say so,** so clients can skip approval prompts for them. The server's instructions carry the orientation and the index of the modes, so an agent attached over MCP needs no shell to be oriented.
- **The agent's name is set per client** in the configuration loom generates, which is never committed and never one someone else wrote.
- **Two commands are the bridge** that replaces the chat composer as the way a person points an agent at something (plan 0.21.8):
  - *where the person is looking*: the document and block, down to the selected words or the PDF page and region, from the viewer tab touched last. The viewer reports it to `loom serve`, which keeps it in memory only.
  - *what the person did since this agent last looked*: their annotations and replies, and their acceptances, including keys that went stale, with one marker per agent name.
- **It is optional.** Loom generates two settings variants, one for an agent that uses the shell and one for an agent that uses MCP, and `loom doctor` checks whichever applies. Both must be tried with the real client before they ship, not only checked by unit tests (`invariants.md`); nothing tests this automatically yet.

Shell permissions for an agent are generated only when asked, for an agent without MCP such as Aider.

**Open.** Whether `loom session next` and `loom session watch` survive. With the composer retired, only agents write to a session's inbox, so there is nothing for them to wait for. They are left out of the MCP tools until something needs them; `loom session say` stays, since it is how an agent writes the transcript.

Every major coding agent can start a local MCP server: Claude Code and Claude desktop, Codex and ChatGPT desktop, Gemini's CLI, Cursor, VS Code, Zed, JetBrains, and local-model clients such as LM Studio. The web chat apps cannot, and they have no shell either.

## Transcripts

Conversations happen in the agent's own app, which owns the model, streaming, interruption and permissions. Loom keeps a record, not a copy: the transcript is what the agent writes deliberately with `loom session say`.

An agent writes the transcript so that the person, coming back to it later, sees the broad strokes and the outcomes without the conversation:

- what was asked;
- the main line of the discussion;
- what was decided or found, and what is still open;
- links to everything durable that came of it: annotations, notes, drafts.

It writes at natural pauses and before it stops, and it links rather than restates (`loom link` prints a correct link). The viewer shows the transcript beside the documents it refers to.

The viewer's chat composer, and loom launching an agent for one turn when a message waits, are retired (plan 0.20.1). A turn that could not ask, be interrupted or get a permission approved served nobody well, and the agent apps already reach people away from their desks.

## What an agent is told

What an agent reads at the start is generated from `loom/src/loom/assets/ai/`, and `loom ai orient` prints it: the orientation (where the agent is, where it may write, what only the author does, where to look), the standing rules (how to work, where its work goes, the blocks a report is built from), the formatting rules for what the author reads, and an index of the modes. Those files are the agent's contract, and they are the one copy; nothing else restates them. An author may edit any of them, and `loom upgrade` keeps the edit.

**Modes are reached for, not assigned.** A mode is a way of doing one kind of work well — quick, question, audit, referee, review, simplify, flow, draft, ingest — and each file opens with one line saying when it fits. The index is those lines, so an agent picks a mode itself when one fits, composes blocks when none does, and says in one line of its reply which it used; `loom ai mode NAME` prints one in full. A mode names the blocks its report always has and the ones it may, never a checklist, and its target is whatever the author named. Nothing is shaped for one vendor's skill or command files.

**Where an agent's work goes** is one rule, because what the viewer does not show is never seen:

- its report is a message in the session's transcript, the mode's blocks under their headings;
- on an agent document it makes its changes and lists them in the report, annotating only where the author must look, and it may resolve any annotation there; it never merges the document into the author's (that is `loom adopt`);
- on the author's text, a change is a suggestion the author can take on its own, however long, and changes that only work together, or that move or reorder results, are an agent document of the passage;
- a dead end, a counterexample or a decision is a `note` annotation on what it concerns.

Epistemic labels are on claims in reports and annotations, not on every sentence of conversation, and a script a report cites is saved in the session's directory, named for what it computes.

What stays is the boundary above, identity on every write, page-checked quotations, agent documents kept apart from the author's, and loom as the only writer of its records.

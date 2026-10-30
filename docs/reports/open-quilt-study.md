# The open quilt: a study

Written 2026-10-30. It draws on the ideas in `docs/long-prompts/ideas.md` that ask for a quilt laid out by the person who owns it (its second and third items), on the author's answers in the conversation that produced this study, and on the code as it stands. It is current thinking for a plan to take over, not a decision. The author is learning quantitative finance with an agent's help in the quilt `~/quilts/quant`, which is the Learner's test of this study, as relloc is the Author's.

## The question and the stance

Can a quilt be a directory the person lays out as they like, holding whatever they work with (LaTeX, Markdown, HTML, PDFs, notebooks), with loom a layer over it rather than its shape?

The answer proposed here is yes, and most of the change is loom doing less. Loom stops naming the person's directories, stops deciding where a document may live, hands version control of a shared paper back to the person, and lets an agent write wherever the person has not said no. What loom adds is mostly display: more formats shown in the viewer, and quotable there. What loom understands does not widen. The graph, acceptance and the rest of the trust machinery stay on LaTeX (P1).

Loom does not learn what a course is. How a course is designed and carried out (its topic list, lessons, problem sets, progress, flash cards) belongs to the person and their agent, in whatever files they choose; loom shows those files and makes the links in them work. That is the present need, not a boundary for all time: if a course later needs loom to know something, it is reconsidered then.

**Evidence.** The quant quilt's `syllabus.md` looks like loom: ids, prerequisite links, a checker script, a preview applied after approval. But its agent was told to read loom's orientation before anything else, so its shape shows what an agent makes inside loom, not what a course needs. It is used here only for the friction it shows (see "Found in the quant quilt"). The case rests on what the author asked for and on what a learner does.

## Today's root, entry by entry

`loom init` and `loom ai init` between them put twelve visible entries and six hidden ones at quant's root, beside the one file the person's work has produced so far, `syllabus.md`. More appear with use (`annotations/`, `build/`, `research-state.md`).

| entry | what it does today | proposed |
|---|---|---|
| `config.toml` | marks the quilt and holds its settings | stays, the one file loom puts in view |
| `README.md` | explains the layout | a tutorial `loom init` writes, safe to delete |
| `drafting/` | holds the live documents (`[quilt] drafting`); placement declares liveness (DR-132) | deleted; a document may be anywhere |
| `drafting-ai/` | holds agent documents (`[quilt] drafting_ai`) | moves into `.loom/`; each copy is shown beside the document it copies |
| `nodes/` | where `loom new` writes | deleted; `loom new` takes a destination |
| `refs/` | the drop folder for PDFs and `.bib` files | deleted; a PDF anywhere becomes a work with `loom library add`, and a bibliography is wherever a document's `\bibliography` names it |
| `digests/` | digests and the store of works | moves into `.loom/` |
| `annotations/`, `reference-notes.jsonl` | the annotation log; the library's notes | move into `.loom/` |
| `ai/` | orientation, rules, modes | moves into `.loom/`; agents already reach it through `loom ai orient` and `loom ai mode` |
| `research-state.md` | the research state | `[quilt] research_state` still places it; its default is open |
| `loom.sty` | the three macros | deleted; a marked block in the preamble instead |
| `build/`, `retired/` | derived output; the sources `atomize --retire` sets aside | move into `.loom/` |
| `notes/` | a directory loom never scans | the special case goes; the person ignores what they choose |
| `.gitignore` | loom's ignore lines, most naming loom's directories | shrinks: `.loom/` carries its own |
| `.loom/` | history, ledger, sessions, the Overleaf clone, `since` markers | gains everything above and loses the clone |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | one line each, telling an agent to orient | stay: each client reads its file at the root, and only `loom ai init` writes them |
| `.claude/`, `.codex/`, `.gemini/`, `.cursor/`, `.mcp.json` | client configuration | stay, already hidden |

A fresh quilt is then `config.toml`, `README.md` and `.loom/`, plus the agent files once `loom ai init` has run. The hidden directory holds shared records (history, ledger, annotations, digests) beside local ones (build output, `since` markers, `serve.json`), so its own `.gitignore` says which is which.

## Documents and compiling

**A document may be anywhere.** A file with `\documentclass` is a document wherever it sits, and is live unless it is ignored or superseded. DR-132 made placement the declaration of liveness because `canon/` held the frozen versions of a paper in the same tree. `canon/` is gone, landmarks live in the history (plan 0.17.3), and a superseded document is a recorded state, so placement no longer declares anything the records do not. Ignoring is the one declaration left. `% !LOOM ignore` exists already; whether an ignore file joins it is open. An ignore file would be a different list from the agent deny list below, since "loom does not read this" and "an agent may not write this" are two ideas (K2).

**A document compiles from its own directory** (the author's choice, 2026-10-30). That is what LaTeX and most editors expect, and what an Overleaf project with its main file at the top already does. P12 changes from "compiles from the quilt root" to "compiles from its own directory, on any TeX, on Overleaf".

- **The code change is contained.** `resolve_inclusion` in `scan/expand.py` already resolves each master's inclusions against one base directory and refuses `..`, so it takes the master's directory in place of the root. The compile runner (`tex/runner.py`) takes the same directory as its working directory.
- **`..` stays refused,** because Overleaf cannot follow it. The cost is that documents in sibling directories cannot share a file; documents that share files sit together.
- **Agent copies compile from their source's directory.** A copy lives in `.loom/`, but it compiles from the directory of the document it copies, so its figures and local packages resolve as the source's do.

**The macros go inline.** `loom.sty` holds three `\providecommand`s (`\uses`, `\incomplete`, `\nest`). It sits at the root only because a document that loads it compiles from the root and P12 rules out `TEXINPUTS`; once documents compile from their own directories, it would have to sit beside each one. Loom already writes the same macros as a marked block, the one `loom history show --plain` puts in place of `\usepackage{loom}` (`reshape/linearize.py`). So a document loom starts, imports or restores carries the block in its preamble, and no file is needed. The cost: a change to the macros reaches a document only as a patch the person applies (P7), where today `loom upgrade` rewrites one file. Because the block is marked, `loom doctor` can find an old one and print that patch.

**What else moves with it.**

- **`loom new`** writes `nodes/<id>.tex` today and needs a destination instead: `--to`, or a default that is still open.
- **Agent documents written from scratch** (`loom draft --ai NAME --new`, taken in with `loom adopt NAME --to FILE`) exist because an agent could write nowhere outside `drafting-ai/`. With the deny list below, an agent creates a file wherever it may, so they probably go.
- **`loom:no-live-document`** stops speaking of a drafting directory.
- **Code that reads the setting.** About sixteen modules read the `drafting` or `drafting_ai` setting today, among them `scan/scan.py`, `scan/lint.py`, `adopt.py`, `section_drafts.py`, `sync.py` and `ai/layout.py`. The source contract's §1 defines a master by the drafting directory. All of them change, and the fixture with them (C3).

## What the viewer shows

**Docs is the project's tree,** the person's directories and files with loom's hidden, and it is the working view. `[quilt] main` names the default master today. It names the front door instead: any file the viewer shows, opened when the browser remembers no place to return to, so a project can open on its homepage or on the day's list.

Every file sits in one or more of four layers. Each layer holds more formats than the one below it, and loom requires no layer of any file:

| layer | what it means | formats |
|---|---|---|
| shown | the viewer displays it | LaTeX documents, Markdown, HTML, PDFs, images; anything else opens in its own application |
| linkable | a link names it and a place in it | any shown file: a heading, a page, a block |
| quotable | a person or agent can attach something to a place in it | text, by a quoted passage; PDFs and images, by a region |
| understood | ids, edges, closure, computed states, acceptance | LaTeX only |

`links.py` already holds the rule that relates the first two layers: only what the viewer can show is linkable.

- **Markdown** is rendered by the publisher the way pages and messages are (`render_markdown` in `records/store.py`: CommonMark with tables, `$…$` mathematics, and `quilt:` and `cited:` links). Pages and messages pass no raw HTML through. Whether a person's own Markdown may, and is then shown in the sandboxed frame below, is open.
- **HTML** is shown in a sandboxed frame that does not share the viewer's origin. The viewer's write API acts for the author, including accepting, so a page running in the viewer's origin could accept on the author's behalf without any agent check (K5) seeing it.
  - **Embedded content,** a video among it, comes with HTML and needs nothing of its own. It needs the network, so a viewer working offline shows the page without it.
  - **Links out of the frame:** a `quilt:` link inside it reaches the viewer through a bridge that can only open things, never write.
  - **Quoting:** the viewer puts the page's text into the frame itself, so it can add a small script that reports a selection back.
- **PDFs and images** are shown as files. A PDF becomes a work in the library, with page text and locators, only when the person adds it.
- **Notebooks:** whether the viewer renders a notebook's saved cells and outputs read-only, or only opens it in the person's application, is open. Loom runs nothing either way (running code is deferred).
- **Other applications** are reached by a link that opens them, such as an "open Anki" link in the day's list. How such a link names an application (its own URL scheme, or a control `loom serve` offers locally) is open. Whether Anki on the desktop registers a URL scheme has not been checked. An agent with its own access to Anki reads and writes the deck, and loom needs to know nothing about Anki for that.
- **Links in from outside,** a web address that another tool (an Anki card, say) could open at a result, are not needed now and are not proposed here. A way in for anyone building on loom partly exists already: the build interface and the write API are specified (P11), and the MCP server serves `quilt:` addresses.

## Where agents write

Today an agent may edit its session's directory, `build/` and `drafting-ai/`. It is denied the quilt's other directories, its records, the research state, and every `.tex`, `.sty` and `.bib` at the root; `ai/layout.py` generates both lists.

Only Claude Code's permission file restricts which files an agent writes. In the MCP variant, loom's Codex rules forbid the `loom` and `rm` commands and nothing else, and the Gemini and Cursor files configure the MCP server only. So the file boundary already holds for just one client of four. The boundary that holds for all four is loom's own refusal of the author's acts (K5).

**Proposed: a deny list in the config.** It holds gitignore-style patterns naming where an agent may not write; everywhere else is open.

- **The default:** a fresh quilt's list protects `.loom/` and `config.toml` only (the author's choice, 2026-10-30). The person adds a paper's directory when they want it protected.
- **Enforcement:** loom generates the list into each permission file a client has. The orientation gives every agent the list and says plainly which clients enforce it, so a list that only asks never reads as one that guarantees (P15).
- **The setting's name** is open.

The list decides which of two ways of contributing applies to a file:

- **Open files** are edited in place, and Review shows what changed (next section).
- **Protected files** are copied and adopted, as today. `loom draft DOC --ai NAME` makes the copy in `.loom/`, the viewer shows it beside its source, and `loom adopt` takes it in.

The Author keeps everything they have now, at the cost of one line naming their paper. In-place edits to mathematics are also less dangerous than they sound. Acceptance holds hashes of a key's text and its closure, so an agent's edit to an accepted result shows as stale, with its cause, whoever made the edit (P3, P15).

## Review as the meta view

Docs is where the person works. Review is where they see what has changed or is waiting on them, and keep it or throw it away. Its sections, as proposed:

- **Changes to open files** since the person last looked, each kept or undone, with who made it where loom knows.
- **Agent documents** to adopt.
- **Suggestions** waiting to be applied, and **library proposals** waiting to be verified.
- **Acceptance** of the mathematics, kept apart from the rest. "Accept" means only that a key's mathematics is right; keeping an edit gets a verb of its own (K7).
- **Sessions, History and Problems,** as today.

Coauthors' pulls leave Review (see "Overleaf: backing off").

**Open: where the old text comes from.** Undoing a change to a file loom does not understand needs the text from before the change. There are four options, and none is chosen here:

| option | gives | costs |
|---|---|---|
| the person's git, read where it is present | the diff since their last commit, with no storage of loom's own | loom reads history for the first time, against DR-105 ("it never … reads history"); a file outside git shows as changed, with no undo |
| snapshots of open files, kept by loom at checkpoints | undo, always | loom becomes partly a version store, and when to take a checkpoint must be chosen under the history's rule of recording what loom was told, never on save |
| the agent client's own checkpoints | undo, where the client offers it | invisible to loom, and different in every client (P9) |
| open files left out of Review | nothing new to build | Review loses the use the author named first |

"Since the person last looked" also needs a marker for the person, as `loom since` keeps one for each agent.

## Annotations: discussion and review

One record serves two purposes today:

- **Discussion:** pointing at words and saying something about them to the agent, as a person quotes a passage in a reply. Every person in every quilt wants this.
- **Review:** an objection, suggestion, question, citation or note on a draft, with a severity, proposed text, and a life of resolved, applied and detached. This serves mostly the Author proofreading a paper.

Because one record serves both, a discussion carries review's weight.

**Proposed: quoting is the universal layer.**

- **Anything shown can be quoted** into a discussion: text by a passage, a PDF or image by a region, and the session's transcript itself. It takes one gesture and no kind, severity or resolution, and the quote fades when the conversation moves on.
- **Review keeps its five kinds** and its lifecycle, used mostly on LaTeX drafts.
- **The widening is a discussion's.** Today an annotation can target only a key, a labelled equation, a whole document, or a page of a cited work.

Two existing facts shape it:

- **The hop to the agent.** Loom cannot put a quote into the agent's conversation, since conversations happen in agent apps (plan 0.20.1). The agent reads it with `loom since` or `loom here`, and how much that hop costs the person is worth measuring (P14).
- **Notes.** The fleeting notes already decided on (`model.md`, Notes) also fade and attach to anything. Whether a discussion quote and a fleeting note are one mechanism (P4) is open.

## Overleaf: backing off

This part adds nothing. It gives the person ownership of their shared paper, with the responsibility that comes with it, and removes loom's machinery for it.

**The person's way.** They make a directory, clone their Overleaf project's git repository into it, and pull and push themselves. Loom shows the directory like any other. Because a document compiles from its own directory, the paper compiles in loom as it does on Overleaf, and loom needs no setting to know which directory is Overleaf's.

**What goes:**

- `.loom/workspace/`, loom's own clone, and `loom sync` with `init`, `documents`, `publish`, `fetch` and `incorporate`: `sync.py` and `cli/sync.py`, about 1,400 lines, and `tests/unit/test_sync.py`, about 650.
- The source projection, and the review origins kept for pulls.
- Pulls in Review's Incoming: the pull half of `render/incoming.py` and `incorporation_review.py`, and the viewer's `IncomingPull.svelte`.
- The write API's `sync-preview` and `sync-incorporate`, and the manifest's sync fields.
- The invariant "Sync never writes to the quilt's own repository", since loom would then run no git that writes. `sync publish --push` and `sync incorporate` leave the list of the author's acts.

What each job of the projection becomes:

| job | today | after |
|---|---|---|
| keeping loom's files out of Overleaf | the projection copies only the sources | loom's files are in `.loom/`, and the macros are a block in the preamble |
| paths | documents compile from the quilt root, Overleaf compiles from the project's root | both compile from the document's directory |
| coauthors' changes reviewed before they land | Incoming, then `sync incorporate`, which stamps first | lost: `git pull` writes them; every accepted key a coauthor changed shows as stale with its cause, and git keeps the old text |
| a landmark of what was published | `publish` stamps each document | `loom stamp` when the person wants one, or their commits |
| a coauthor's rename | recorded as a move | `document-gone`, with `loom mv` as its fix |
| agents and the paper | agents never wrote the author's files | the deny list: protect the paper's directory, and agents work on copies |

**The loss, stated plainly:** loom no longer reviews coauthors' changes before they land. Nothing unchecked looks checked all the same, because staleness is computed from the text (P3, P15), and loom writes no author file in any of it (P7).

**A nested repository.** If the quilt is itself a git repository, the paper's directory is a repository inside it, and a coauthor who clones the quilt does not get the paper unless the person makes it a submodule. That choice is the person's; loom does not need to care.

DR-327's record stays in the frozen history. DR-105's "a quilt is not a repository unless the author asks" holds more firmly than before, since loom then writes to no repository at all.

## What stays

- **Mathematics is LaTeX** (P1). The trust machinery (acceptance, staleness, verification, K5) is unchanged.
- **For now:** loom knows nothing of courses, runs no code, and calls no model.
- **Integrations, as current thinking, revisited when a need appears:**
  - loom integrates with what feeds what it understands: works (a Zotero library, the first item of `ideas.md`) and coauthors' text;
  - the person's other tools (Anki, Jupyter, a calendar) are their agent's to integrate, through its own connectors.

## What changes in the design

- **P12** reads "compiles from its own directory".
- **P5** holds with no exceptions: no directory carries meaning, and the scan's named exclusions shrink to loom's own directory.
- **P7** is unchanged. An agent writing an open file acts on the person's permission to the agent; it is not loom writing.
- **DR-132**'s placement rule is retired along with `drafting/`.
- **Documents that change:**
  - `docs/design/`: `model.md` (the quilt, documents, the viewer's frame), `agents.md` (what an agent may write) and `invariants.md` (the sync invariant);
  - `docs/specs/`: `source-contract.md` §1, `manifest.md` and `write-api.md` (sync), and `diagnostics.md` (`loom:no-live-document`);
  - the init assets and `loom upgrade`.
- **A possible principle,** for the author to decide: *loom hosts the project; it does not shape it.* A layout, a medium or a way of working is the person's, and a feature that works only when the person organises their work loom's way needs a reason.

## Found in the quant quilt

- **A moved quilt loses its agents.** `.mcp.json`, `.codex/config.toml`, `.gemini/settings.json` and `.cursor/mcp.json` each start the server with `--quilt /Users/isaac/notes/quilts/quant`, the quilt's absolute path as `ai/clients.py` writes it. The quilt now lives at `~/quilts/quant`, and the old path no longer exists. Running `loom upgrade` (or `loom ai init`) in the new place rewrites the four files. A person who owns their directories moves them, so the open-quilt answer would be for the server to find the quilt by walking up from where it is started, as every command does, in every client that starts it inside the project.
- **No way to propose an edit to a file that is not LaTeX.** Asked to merge new topics into `syllabus.md`, the agent wrote `syllabus.proposed.md` and a merge script in its session, asked for approval in chat, and then applied the change. Edit in place, with Review afterwards, is the general answer.
- **The person's one file sits outside everything the viewer shows:** `syllabus.md`, at the root among loom's entries.

## Open questions

1. Ignoring: `% !LOOM ignore` alone, or an ignore file as well.
2. Where Review's old text comes from (the four options above).
3. Whether a person's own Markdown passes raw HTML through.
4. Notebooks: rendered read-only, or only opened in their application.
5. How a link names an application, and whether Anki on the desktop has a URL scheme.
6. Whether a discussion quote and a fleeting note are one mechanism.
7. The research state's default place: `.loom/`, or the root.
8. `loom new`'s default destination.
9. The deny list's setting name.
10. How the viewer shows an agent copy beside its source.

## Phases

1. **The layout.**
   - `.loom/` takes in loom's directories and files, and `drafting/`, `nodes/` and `refs/` go.
   - A document may be anywhere and compiles from its own directory.
   - The macro block replaces `loom.sty`.
   - `loom init` writes the config, the tutorial README and `.loom/`.
   - The scanner, the compile runner, `init`, `upgrade` and `doctor` change, with the source contract and the fixture.
2. **Overleaf.** `loom sync` and everything listed under it are deleted. This comes after phase 1, which gives documents their own compile directory.
3. **Agents.**
   - The deny list: its generation into each client, and its statement in the orientation.
   - Agent copies in `.loom/`.
   - Agent documents written from scratch removed.
4. **The viewer.**
   - Docs as the project's tree, with its front door.
   - Markdown documents, and HTML in its sandbox.
   - Links that open other applications.
5. **Review and quoting.** Review as the meta view, and quoting any shown thing into a discussion. This waits until the open questions about the old text and about notes are answered.

Each phase is checked against two quilts. In relloc, the Author must lose nothing they have now. In the quant quilt, the person and their agent must be able to build whatever they choose without loom getting in the way.

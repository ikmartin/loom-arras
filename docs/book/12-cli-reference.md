# 12. CLI reference

Every loom command, with syntax, flags, behaviour, exit codes, and machine output. Behaviour is specified in the earlier chapters; this chapter is the index and the fixed surface. The implementation generates the `--help` text and the user-facing reference from the same definitions, so that this chapter, the help, and the code cannot drift apart without a test failing; 12.2 below is that generated reference.

## 12.1 Conventions

**[decided]**

- Quilt discovery: every command except `init` and `doctor` walks up from the current directory to the nearest `config.toml` with a `[quilt]` table and runs against that quilt. `--quilt PATH` overrides. `doctor` needs no quilt, and checks the one it finds the same way.
- Exit codes: `0` success; `1` a content problem (lint errors, a failed identity test, a failed compile, a refused write that the author can fix in the source); `2` a usage or environment problem (bad arguments, an argument that names no key, annotation, session, work or result, missing tools, no author name, consent `config.toml` does not give, a destination that exists). The rule decides by what the person must change: the quilt's source is `1`, the command or the machine is `2` (DR-290-ikmartin).
- `--json`: machine output on stdout, one JSON document, nothing else on stdout; diagnostics and progress go to stderr.
- `--yes`: skip confirmations that would otherwise be asked on a terminal. Commands that would ask and have no terminal and no `--yes` exit 2.
- `--session SESSION`: on `source`, `compile`, `annotate`, `status`, `search`, `deps`, `unravel`, `lint`, `id`, `new`, `ai orient` and `ai annotations`: append the invocation to the session's `run.log` (`LOOM_SESSION` is the default). `annotate` writes into the active session when neither is given. **[decided]** `SESSION` is a session's id, its title, or an unambiguous part of either; an ambiguous one names its matches and refuses (DR-199). On `annotate` it names where the annotation belongs, never its author, because a session is a place and an author is a person or a named agent (DR-200).
- `--author NAME`: on `accept` and `annotate`, the author name, overriding the user config.
- `--quiet` / `-q` and `--verbose` / `-v` were planned and are not implemented; diagnostics go to stderr, summaries to stdout (M7).
- Keys are written as ids (`rl-0004`), proof keys (`rl-0004/proof`, `rl-0004/proof/2`), qualified keys (`rl-0004#eq:main`, `drafting/main.tex#section:3`), or master paths. Aliases are accepted wherever an id is and resolved. An **address** adds a step: `rl-0004@3`, or `rl-0004@paper-v2` naming the landmark instead of the number (17.4).
- `-m MESSAGE`: required by `canonize` and `stamp`, as by a commit. A landmark nobody named is a landmark nobody can ask for.
- Ids in output are always shown with their number in the default master when known: `rl-0004 (Lemma 3.4)`.
- **`loom doctor`** (DR-288-ikmartin) is the one command to run when something is off. Every item it reports is `ok`; `warn`, it works but the person will hit something; or `fail`, a command they need will refuse or misbehave. Each item that is not `ok` carries a one-line remedy, the command where there is one. It exits `0` when nothing fails and `2` when anything fails; `--strict` counts a warning as a failure, so doctor never exits `1`, which means a content problem. The summary line names every failing item, and under `--strict` every warning. Machine items come first: the TeX tools (`latexmk`, `pdflatex` and `dvisvgm` required; `latex`, `xelatex`, `lualatex`, `bibtex`, `biber`, `kpsewhich` optional), poppler (`pdftotext`, `pdfinfo`, `pdftocairo`, optional), `git`, `claude` and `codex` when the quilt configures an agent or `--agents` is given, the author name and the arras bundle. A required tool missing fails and an optional one warns; any tool that is present but hangs, will not start, or lacks what loom uses (a `pdftotext` without `-bbox-layout`) fails, since loom runs it when it is there; a biber and biblatex that do not pair warn. Inside a quilt a second section reuses the checks the owning commands make: the configured engine is installed (fails if not); the agent configuration as `loom agent check` finds it (a fault fails when `launch` is on and warns when off); the permission files, the mode files and `loom.sty` against what `loom upgrade` would write, by its dry run; the `.gitignore` lines `loom upgrade` adds; and `config.toml`'s warnings, pointing to `loom lint`. `--json` prints `{python, loom, interface_version, quilt, ok, failing, warnings, items}`, where `ok` is the exit code being 0, `failing` and `warnings` are item names, and each item has `name`, `status`, `severity` (`required`, `optional` or `quilt`), `detail` and `remedy` (empty when `ok`); a tool adds `path`, the bundle `source`, `path` and `interface`. Every probe has a deadline (10 s), so a hung tool is reported rather than waited on, and doctor writes nothing.

## 12.2 Commands

**[decided]** The reference below is generated from the command tree by `loom/scripts/gen_cli_reference.py`; `loom/docs/cli-reference.md` is the same text, and the test `test_cli_reference_matches_checked_in` fails when either drifts from the code. Every command's `--help` prints the same usage and options. Behaviour is specified in the earlier chapters; the sections 12.2 to 12.8 of the pre-implementation book, which listed the commands by hand, are replaced by this generated list (M7). Aliases: `rm` and `remove` for `delete`; `downstream`, `reach`, and `pop` for `unravel`; `canonicalize` and `canonise` for `canonize`, which print `canonicalize → canonize` rather than run silently.

Generated by `scripts/gen_cli_reference.py` from the command tree; do not edit. Aliases: `rm` and `remove` for `delete`; `downstream`, `reach`, and `pop` for `unravel`.

## `loom`

`loom [OPTIONS] COMMAND [ARGS]...`

loom: a tool for atomized mathematical development.

Every command except `init` and `doctor` runs against the nearest quilt, found by walking up from the current directory to a `config.toml` with a [quilt] table; `doctor` checks that quilt too when there is one.

| option | description |
|---|---|
| `--version`, `-V` | Show the version and exit. |

### `loom accept`

`loom accept [OPTIONS] [KEYS]...`

Record acceptance rows and snapshots for KEYS; the only writer of the ledger.

| option | description |
|---|---|
| `--proofs` | Also accept every proof attached to each statement given. |
| `--stale` | Accept every key that is currently accepted-stale, after confirmation. |
| `--all-live` | Accept every live author-owned statement and proof, after confirmation. |
| `--master` | Accept every statement and proof reached by MASTER. |
| `--author` |  |
| `--yes`, `-y` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom agent`

`loom agent [OPTIONS] COMMAND [ARGS]...`

The agent loom serve may start for a turn: ai/ai-config.toml, and whether config.toml lets it.

#### `loom agent check`

`loom agent check [OPTIONS]`

Say whether loom serve will start an agent here, with what command, and what would stop it. Runs nothing.

Exits 1 when the config is incomplete, its command is not on PATH, or git tracks ai/ai-config.toml -- a command a quilt carries came from whoever committed it, and loom refuses to run it.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom ai`

`loom ai [OPTIONS] COMMAND [ARGS]...`

The optional AI layer: orientation, sessions, annotations, and discarding review records.

#### `loom ai annotations`

`loom ai annotations [OPTIONS]`

What this session has annotated: id, target, kind, status, and the quoted text; `--json` carries the whole annotation.

An agent re-reading its own annotations is the common case — a re-check resolves what is met and edits what still stands, and needs the ids to do it. The JSON form carries `message`, `payload` and `placement` too, so a re-check can tell what it already said and what it already suggested without reading the log itself.

| option | description |
|---|---|
| `--session` `SESSION` | The session to report on. |
| `--severity` | Only annotations of this severity. |
| `--kind` | Only annotations of this kind. |
| `--status` | Only annotations in this state: open, resolved or discarded. |
| `--all` | Include withdrawn annotations, with the reason they were withdrawn. |
| `--json` | Print the annotations as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai check`

`loom ai check [OPTIONS] SESSION`

Report files outside SESSION, the annotation log, and build/ modified since it opened (loom:agent-wrote-outside-run).

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai discard`

`loom ai discard [OPTIONS] [RUN]`

Flag a session's or an author's annotations ignored (or unflag with --undo). Nothing is deleted.

Discarding appends an event like any other change, so a sitting's annotations can be dismissed and brought back without anything being rewritten or lost.

| option | description |
|---|---|
| `--before` `DATE` | Discard every record created before this date (YYYY-MM-DD). |
| `--author` | Discard every record whose author matches. |
| `--target` | Discard every record with an annotation on this key. |
| `--undo` | Reverse: mark matching records not discarded. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai init`

`loom ai init [OPTIONS]`

Write ai/ (orientation, rules, modes), the vendor files CLAUDE.md and AGENTS.md, and what agents may run for Claude Code (.claude/settings.json) and Codex (.codex/rules/loom.rules); refuses if ai/ exists.

| option | description |
|---|---|
| `--skills` | Also write skill stubs and slash commands for Claude Code. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai name`

`loom ai name [OPTIONS] NEW_NAME`

Retitle a session. The id it was opened under does not change, because that is its address.

| option | description |
|---|---|
| `--session` `SESSION` | The session to rename. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai orient`

`loom ai orient [OPTIONS]`

Print the orientation documents followed by the quilt's live state, and with --session the end of that session's chat.

This is also how an agent joins a session it did not open: `loom ai orient --session <id>` prints the orientation, the quilt's live state, and the last messages of that session's chat with its command log, which is what a later sitting resumes from.

| option | description |
|---|---|
| `--session` `SESSION` | Attach to this session: also print the end of its chat and its command log. An id, a title, or a unique id suffix. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai start`

`loom ai start [OPTIONS] [NAME]`

Open a session named NAME and make it active, printing its id.

The same session a person opens with `loom session new`, so an agent and the author working the same job land in one place. Loom does not launch your agent -- `loom ai init` writes the line in CLAUDE.md and AGENTS.md that tells one to run `loom ai orient`.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom annotate`

`loom annotate [OPTIONS] [TARGET] [MESSAGE]`

Write an annotation on TARGET: a key, an equation's qualified key, a master path -- or, with --page, a cited work.

A note on a page of a cited work names the work by citekey or identifier and the place by --page with --quote (text on the page) or --box (a rectangle on it). It lands in the same log and the same session as every other annotation, and `loom status --reading` lists it.

| option | description |
|---|---|
| `--quote` | Anchor to this exact text: once in a key's own text, or on the page of a cited work given by --page. |
| `--page` `N` | A note on page N of a cited work (TARGET a citekey or a work identifier); with --quote or --box. |
| `--box` `X0,Y0,X1,Y1` | Anchor to a rectangle on the page, in points with the origin at the top left; ';' separates several. |
| `--kind` `objection|suggestion|question|citation|note` |  |
| `--session` | Write into this session: an id, a title, or a unique id suffix. Default the active one. |
| `--author`, `--as` | Who is writing; an agent names itself, with Agent or AI in the name. |
| `--reply` `ID` |  |
| `--resolve` `ID` |  |
| `--edit` `ID` | Supersede an annotation's body; the history stays in the log. |
| `--discard` `ID` | Withdraw a finding you should not have raised; resolving would claim the author addressed it. |
| `--severity` | How bad the fault is, not how keen you are. |
| `--payload` | Suggested text the author may preview and copy. |
| `--placement` | Where the payload goes, as a hint. |
| `--in` `DOC` | A claim about the node as read in this document: marked there, listed on the node's own page, absent elsewhere. |
| `--undo` | With --resolve or --discard, put the finding back: an undo is another event, never a removal. |
| `--batch` | Read JSON lines from stdin, one annotation or one change per line; an unknown key is an error. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom atomize`

`loom atomize [OPTIONS] [SRC] [DEST]`

Move each node of SRC into nodes/<id>.tex and write DEST, a copy of SRC with inclusion lines in their place. SRC is not modified; the history records that DEST superseded it, so it defines nothing until `loom live`.

| option | description |
|---|---|
| `--to` `DEST` |  |
| `--key` `KEY` | Move only these nodes, wherever they live; SRC is not needed. Writes the node files and prints the patch for the source, which loom never edits. |
| `--json` | With --key: print the plan and write nothing. |
| `--proofs` |  |
| `--sections` | Also move labelled sections and subsections to nodes/. |
| `--all` | Act on SRC and every file it reaches, writing spines under --to-dir. |
| `--to-dir` `DIR` |  |
| `--retire` | Move SRC into retired/ once DEST is written, instead of leaving it superseded in place. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom build`

`loom build [OPTIONS]`

Scan, derive, render, and publish build/. Exit 1 if any error-severity diagnostic exists (the build is still published).

Rendering is cached per fragment by its inputs, which include loom's own version and, in a checkout, loom's code; --force renders everything regardless, and tries again every block whose SVG failed before.

| option | description |
|---|---|
| `--keys` | Limit rendering to these keys and their masters; the manifest is always complete. |
| `--force` | Render every fragment again, ignoring the cache and retrying remembered SVG failures. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom canonicalize`

`loom canonicalize [OPTIONS] DOCUMENT`

The same as canonize.

| option | description |
|---|---|
| `--to` `FILE` | The canon file (default: <canon>/<stem>.tex). |
| `--message`, `-m` | What this landmark is. |
| `--no-check` | Skip the identity test. |
| `--parent` | The step this one continues. |
| `--json` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom canonise`

`loom canonise [OPTIONS] DOCUMENT`

The same as canonize.

| option | description |
|---|---|
| `--to` `FILE` | The canon file (default: <canon>/<stem>.tex). |
| `--message`, `-m` | What this landmark is. |
| `--no-check` | Skip the identity test. |
| `--parent` | The step this one continues. |
| `--json` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom canonize`

`loom canonize [OPTIONS] DOCUMENT`

Write DOCUMENT as one flat, self-contained canon file and record a step: every key's text at this moment, quilt-wide, with what the document reaches named.

| option | description |
|---|---|
| `--to` `FILE` | The canon file (default: <canon>/<stem>.tex). |
| `--message`, `-m` | What this landmark is. |
| `--no-check` | Skip the identity test. |
| `--parent` | The step this one continues. |
| `--json` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom check`

`loom check [OPTIONS]`

lint, then compile every master, then bundles. Exit 1 on any failure. The CI command.

| option | description |
|---|---|
| `--no-compile` | Lint only. |
| `--bundles` | Which bundles to compile (stale needs the ledger, milestone M3). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom compile`

`loom compile [OPTIONS] [TARGET]`

Run latexmk from the root into build/<stem>/ for a master (default: the default master), or for a key.

Compiling a key builds the document of its closure and runs latexmk on that, so `--with` previews a proposed diff and `--draft` a node that has no id yet: neither writes into the quilt, and a failure names the digests whose packages are missing before it names the error.

| option | description |
|---|---|
| `--engine` | Override the engine (pdflatex, lualatex, xelatex). |
| `--with` `FILE` | Substitute a unified diff, a .tex file, or an annotation's proposed text for KEY's text; the quilt is not touched. |
| `--draft` `FILE` | Compile a node file not yet in the quilt. |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom delete`

`loom delete [OPTIONS] [ARGS]...`

Refuse: loom never deletes your notes.

### `loom deps`

`loom deps [OPTIONS] KEY`

What KEY depends on: direct statement-edges and proof-edges, grouped.

| option | description |
|---|---|
| `--closure` | The transitive statement closure in dependency order. |
| `--json` |  |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom digest`

`loom digest [OPTIONS] COMMAND [ARGS]...`

Digests of cited papers: extract one from a paper's source, or port one in.

To search what the digests hold, see `loom refs find` (statements) and `loom refs grep` (page text); to read a page, `loom refs page`; for the whole mechanical pass over every cited work, `loom refs build`.

#### `loom digest extract`

`loom digest extract [OPTIONS] CITEKEY [SRC]`

Produce digests/CITEKEY.tex mechanically from the reference paper's source (proofs dropped, ids prefixed).

With no SRC, the source loom holds for CITEKEY: the file in the store declaring `\documentclass`, which is what `loom refs fetch` or `loom refs add` put there. A path may be given instead, and must be inside the store -- a digest made from a file nobody else holds cites pages nobody else can open.

| option | description |
|---|---|
| `--to` `PATH` | Write here instead of digests/<citekey>.tex. |
| `--engine` | Engine for compiling the reference (default: its magic comment or pdflatex). |
| `--no-compile` | Skip compiling the reference; number results by emulation. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom digest import`

`loom digest import [OPTIONS] PATH`

Copy a digest from another quilt into digests/, rewriting its id prefix when --as renames the citekey.

| option | description |
|---|---|
| `--as` `CITEKEY` | Rename the digest's citekey on the way in. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom doctor`

`loom doctor [OPTIONS]`

Check the TeX toolchain and what loom needs of it, poppler, git, the author name and the arras bundle; inside a quilt, also its engine, its agent configuration, its generated files, its .gitignore and its config.

Each item is ok, warn (works, but you will hit it) or fail (a command you need will refuse), with the command that fixes it. Exits 0 when nothing fails and 2 when anything does; under --strict a warning counts as a failure. Writes nothing; a tool is run only to ask its version or test what loom needs of it, and one that has not answered in 10 s is reported as hung.

| option | description |
|---|---|
| `--json` | Machine-readable report on stdout. |
| `--strict` | Count a warning as a failure: exit 2 when any item warns. |
| `--agents` | Also look for claude and codex, as when the quilt configures an agent. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom draft`

`loom draft [OPTIONS] CANON`

Copy a canon document into the drafting directory as a working draft, with \usepackage{loom} and an id on every node; the canon file is not touched.

| option | description |
|---|---|
| `--to` `FILE` | The draft to write (default: <drafting>/<stem>.tex). |
| `--no-ids` | Copy without inserting ids. |
| `--fix-anchoring` | Rewrite the copy so every theorem-like \begin and \end is alone on its line. |
| `--prefix` | Id prefix for the ids inserted. |
| `--no-check` | Skip the identity test. |
| `--yes`, `-y` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom fork`

`loom fork [OPTIONS] NODE_ID`

Give FILE its own copy of a node under a new id: a node file when FILE includes the node, else the copy inline; printed as a patch for FILE, with its references rewritten. Nothing outside FILE changes.

| option | description |
|---|---|
| `--in` `FILE` | The document that gets its own copy. |
| `--from` `@N` | Copy the text the key had at step N instead of the head. |
| `--as` `ID` | The new id (default: the next free one). |
| `--json` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom history`

`loom history [OPTIONS] [KEY]`

The steps and stamps of this quilt, one per line; with KEY, that key's versions and whether the head equals one. `loom history verify` walks every step directory against the ledger.

KEY is an id, a proof key, or the word `verify`.

| option | description |
|---|---|
| `--json` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom id`

`loom id [OPTIONS] [FILE]`

Print a patch (or write a copy with --to) inserting \label{<id>} on every untagged theorem-like environment and section in FILE, or with --next the next free id. Never modifies FILE.

| option | description |
|---|---|
| `--to` `DEST` | Write the patched copy here instead of printing a diff. |
| `--sections`, `--no-sections` | Also label sections through subsubsection (default on). |
| `--all-levels` | Also label paragraphs and subparagraphs. |
| `--prefix` |  |
| `--fix-anchoring` | Include line-anchoring repairs in the patch or written copy. |
| `--next` | Print the next free id and nothing else; inserts nothing. |
| `--json` | With --next: print it as JSON. |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom import`

`loom import [OPTIONS] FILE`

Copy a paper into the quilt as one flat canon document, its styles, bibliography and figures at the root, changing nothing else; step 0001 of the history.

| option | description |
|---|---|
| `--yes`, `-y` |  |
| `--no-check` | Skip the identity test. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom init`

`loom init [OPTIONS] [DIRECTORY]`

Create a quilt in DIRECTORY (default: the current directory); with --from FILE, import a paper into it as its first canon document (then: loom draft).

| option | description |
|---|---|
| `--from` `FILE` | Import an existing paper: FILE is its main .tex file, anywhere on disk. |
| `--demo` | Write the demo quilt instead of a minimal master. |
| `--prefix` | Id prefix for new nodes. |
| `--author` `NAME` | Who this quilt's records name; written to config.toml. Asked for when not given, and left empty when nobody answers. |
| `--git` | Also run git init. A quilt is files; loom reads no history. |
| `--ai` | Which AI you use, instead of being asked: its command goes in ai/ai-config.toml. |
| `--launch-agents`, `--no-launch-agents` | Let loom serve start the agent for a turn when a message waits (config.toml [ai] launch). Off by default. |
| `--yes`, `-y` | Skip questions; take defaults and confirm the import. |

### `loom inline`

`loom inline [OPTIONS] SRC [DEST]`

Write DEST, a copy of SRC with every \input of a node file replaced by its contents. The reverse of atomize.

| option | description |
|---|---|
| `--to` `DEST` |  |
| `--all` | Inline recursively. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom linearize`

`loom linearize [OPTIONS] SPINE`

Write FILE: SPINE with every \input, \include and \nest (levels shifted) expanded in place. The spine and every file it inlined are then superseded.

| option | description |
|---|---|
| `--to` `FILE` | The flat document to write. |
| `--fork` | Give this document its own copy of every node another document shares. |
| `--keep-shared` | Leave shared node files as inclusions, marked. |
| `--no-check` | Skip the identity test. |
| `--json` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom link`

`loom link [OPTIONS] THING`

Print a markdown link to THING that the viewer can follow.

THING is a node or any key in it, a document's path, an annotation id, a session id, or a cited work's citekey or identifier. The link's text is empty: the viewer names the thing itself, as `Theorem 3.1`, and keeps the name right when the document is renumbered; write your own words between the brackets to show those instead. A thing the viewer does not show is refused, with why.

| option | description |
|---|---|
| `--at` | A key inside the document or node: link to that place in it. |
| `--page` | A page of a cited work, from 1. |
| `--quote` | Text on that page to find. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom lint`

`loom lint [OPTIONS]`

Scan and print every diagnostic. Fast; no LaTeX runs.

| option | description |
|---|---|
| `--json` |  |
| `--nodes` | One block per node id: what is wrong with its identity, and the superseded files. |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom live`

`loom live [OPTIONS] FILE`

Make a superseded document live again: it defines its nodes once more.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom new`

`loom new [OPTIONS] TAXON [TITLE]`

Allocate an id and write nodes/<id>.tex with a skeleton for TAXON.

| option | description |
|---|---|
| `--prefix` | Allocate under this prefix instead of [quilt] prefix. |
| `--print` | Print the skeleton without allocating an id or writing a file. |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom refs`

`loom refs [OPTIONS] COMMAND [ARGS]...`

Fetched works: where their artifacts are, how to add one by hand, and identifiers for works that state none.

#### `loom refs add`

`loom refs add [OPTIONS] CITEKEY FILE`

File FILE as CITEKEY's PDF, or its LaTeX source, in loom's store.

A published PDF usually sits behind a subscription that loom cannot and should not automate past, so the author supplies the bytes and names the citekey they know; loom resolves the identifier and does the filing. A `.tex` file, or a directory of them, is filed as the work's source, which is what `loom digest extract` reads: fetching is the usual way source arrives, and this is the way for a paper that is not on a preprint server.

| option | description |
|---|---|
| `--force` | Replace an artifact that is already there. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs build`

`loom refs build [OPTIONS] [CITEKEYS]...`

Make everything about this quilt's cited works that a machine can make: resolve, fetch, extract, report.

The one command that starts a digest. It runs `loom refs scan` first, and each step is a no-op where its work is done, so running it again after a new entry reaches the bibliography resolves, fetches and extracts that entry alone. Nothing here touches the network unless `[refs] resolve` and `[refs] fetch` say it may; without them it still extracts from whatever sources are already on disk. The last two lines say what is left for a person and what is left for an agent.

| option | description |
|---|---|
| `--refresh` | Ask the lookup services again where an answer is recorded. |
| `--no-candidates` | Fetch only on identifiers an entry declares itself. |
| `--force` | Re-extract digests that are already present. |
| `--fetch` | Allow fetching for this run, without setting [refs] fetch in config.toml. |
| `--resolve` | Allow looking identifiers up for this run, without setting [refs] resolve in config.toml. |
| `--only` `STEP[,STEP]` | Run only these steps: resolve, fetch, extract, map. |
| `--json` | Print the report as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs cite`

`loom refs cite [OPTIONS]`

Accept or reject an agent's citation suggestion.

Accepting appends to `reference-notes.jsonl` and resolves the annotation; rejecting resolves it and records nothing, the reason riding on the resolve event. Neither touches `refs.bib`: a candidate becomes a work's identity when your own bibliography entry says so, and nothing else (DR-122). This is the breadcrumb for the day you add it.

| option | description |
|---|---|
| `--from` `SESSION` | The session whose suggestion this is. |
| `--accept` `ID` | Record this citation suggestion and resolve it. |
| `--reject` `ID` | Resolve the suggestion without recording it. |
| `--reason` | Why, optionally; it rides on the resolve event. |
| `--author` | Who accepted, when the user config and git do not say. |
| `--list` | Print what has been accepted. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs coverage`

`loom refs coverage [OPTIONS] [CITEKEYS]...`

What the quilt knows about each cited work: source, PDF, page text, digest, and proposals waiting on the author.

A search over a partly digested corpus is a search over silence, so this is the line every other answer should be read against. Each argument is a citekey or a fragment of an author's name or a title -- `romagny`, `intrinsic normal cone` -- and a fragment that matches several works lists them all, because two papers by the same authors in the same year is exactly when guessing goes wrong.

| option | description |
|---|---|
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

#### `loom refs discard`

`loom refs discard [OPTIONS] TARGET`

Discard a proposed result, with a reason.

The reason is not a courtesy. `loom refs propose` refuses a discarded work-and-local-id and returns it, so the agent that proposed the thing learns why in the turn it fails rather than proposing it again next session. Nothing is deleted: the log keeps it and `loom refs why` reports it.

| option | description |
|---|---|
| `--reason` | Why it should not stand; the agent that proposed it is shown this. |
| `--author` | Who discarded, when the user config and git do not say. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs drop`

`loom refs drop [OPTIONS]`

Remove recorded results. The store is safe to delete: dropping it costs re-reading, never correctness.

A verified node already written into `digests/<citekey>.tex` is the author's file and is never touched here; only the records and the proposals are removed.

| option | description |
|---|---|
| `--work` | Everything recorded for this work. |
| `--session` | Everything proposed in this session. |
| `--unverified` | Every result not yet verified, in every work. |
| `--yes`, `-y` | Do not ask. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs fetch`

`loom refs fetch [OPTIONS] [CITEKEYS]...`

Fetch sources and PDFs for cited works into loom's store, checking on arrival that each is the work its entry names.

Fetches on an identifier the entry declares, or on a strong candidate a lookup proposed (plan 0.12 §4.3): a candidate is enough to fetch with and never enough to be an identity, because fetching is reversible and checkable and identifying is neither. A source whose own title does not match the entry is discarded rather than filed. With no CITEKEYS, every cited work that has no artifact yet.

| option | description |
|---|---|
| `--no-pdf` | Take the source only; the PDF is fetched by default. |
| `--no-candidates` | Fetch only on identifiers an entry declares itself. |
| `--fetch` | Allow fetching for this run, without setting [refs] fetch in config.toml. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs find`

`loom refs find [OPTIONS] TEXT`

Search the statements this corpus has digested.

**Every answer carries how much of the corpus it could have searched**, because a search over a partly digested corpus is a search over silence and a result set that does not say so reads like a finding. When nothing matches, the fallback is named.

| option | description |
|---|---|
| `--work` | Limit to these citekeys. |
| `--limit` | Stop showing after this many. |
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

#### `loom refs forget`

`loom refs forget [OPTIONS] TARGET`

Stop the store offering a bibliography entry for TARGET, a citekey or a content hash.

The store is a seed of last resort: a document nobody's entry names is offered one on the next scan, from the copy ledger's record of how it arrived. That is right until you have deliberately deleted the entry, at which point the offer is loom undoing your decision every time. This is the tombstone that stops it, and like every deletion in loom it removes nothing -- the document stays in the store and the ledger keeps its arrival.

| option | description |
|---|---|
| `--why` | Why the store should stop offering it; required unless --undo. |
| `--undo` | Withdraw the tombstone, so the document is offered again. |
| `--author` | Who forgot it, when the user config and git do not say. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs grep`

`loom refs grep [OPTIONS] TEXT`

Search the raw page text of every mapped work for TEXT, a literal phrase (not a pattern).

The cold-start path: before anything is digested this is the only thing that can answer, and it answers with pages to read rather than with statements. **Page text is mathematics that has been through a text layer**, so a hit is a pointer and never a quotable statement — read the page with `loom refs page`, and quote from that.

| option | description |
|---|---|
| `--work` | Limit to these citekeys. |
| `--limit` | Show at most this many hits; every work is still searched. |
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

#### `loom refs ingest`

`loom refs ingest [OPTIONS] DIRECTORY`

Match every PDF under DIRECTORY to a bibliography entry and file the ones that are unambiguous.

Three signals: an identifier in the text of the first pages, the paper's own title, and the filename. **Two agreeing signals attach**, and an identifier read off the page attaches on its own. Everything else is listed by `loom refs match` with its evidence, because a wrong PDF filed against the right entry is worse than an unfiled one — the corpus this was built against has 25 files for 22 entries, eleven of which match nothing at all.

| option | description |
|---|---|
| `--dry-run` | Say what would be filed and file nothing. |
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs link`

`loom refs link [OPTIONS]`

Assert a typed relation between two results, with a reason.

**Nobody verifies this and it says so.** A relation has no page span to check it against, so a verification step would be theatre; a link is an assertion, attributed to whoever made it. Links are never citable, never enter a closure, and are never written into a digest — they are navigation, not mathematics.

| option | description |
|---|---|
| `--from` `ID` | The result the claim is about. |
| `--to` `ID` | The result it relates to. |
| `--kind` | same-notion, generalises, specialises, depends-on, contradicts. |
| `--why` | One or two sentences. This is what you read six months later. |
| `--session` | The session asserting it; an agent must say which. |
| `--author`, `--as` | Who asserted it; an agent names itself, with Agent or AI in the name. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs links`

`loom refs links [OPTIONS] [TARGET]`

Links touching TARGET, out to --depth hops, or every link when TARGET is omitted.

An agent walking a chain of results called this once per node; --depth walks it in one.

| option | description |
|---|---|
| `--depth` | Follow links this many hops out from TARGET. |
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

#### `loom refs locate`

`loom refs locate [OPTIONS] CITEKEY TEXT`

Print the region of CITEKEY's page PAGE that TEXT occupies, so an anchor need not compute geometry.

Token geometry is thirty times the size of plain page text, so it is produced for the one page asked about and kept there; nothing writes it in bulk. Where `loom serve` is running, an `open:` line follows with a link into the viewer **at the place** -- `?page=4&span=812-871` -- so that following it lights the quotation rather than leaving it to be found by eye.

| option | description |
|---|---|
| `--page` | The page the text is on. |
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

#### `loom refs map`

`loom refs map [OPTIONS] [CITEKEYS]...`

Write page text and the section map for cited works that have a PDF.

Deterministic, eager and cheap: no model, nothing to review, and re-running costs nothing where the artifact has not changed. The page text is committed, which is what lets a coauthor who holds no PDF re-check an anchor; the token geometry an anchor's quad needs is written per page by `loom refs locate`, on demand, because it is thirty times the size.

| option | description |
|---|---|
| `--force` | Re-map even where the recorded map matches the PDF on disk. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs match`

`loom refs match [OPTIONS]`

The cited works a person has to look at: no artifact and no identifier, or a source discarded on arrival.

Reads disk only; it never fetches and never asks a service. This is the list `loom refs build` counts on its `needs you` line.

| option | description |
|---|---|
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs overview`

`loom refs overview [OPTIONS] CITEKEY`

Print a digest's Overview: the paper's own framing, which is prose and so is no result.

Agents read it from the digest's `.tex` by hand in every study iteration -- it is where a paper says which results it considers main and what it assumes throughout, and no other command reaches it.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

#### `loom refs page`

`loom refs page [OPTIONS] CITEKEY PAGES`

Print CITEKEY's page text for PAGES (`12` or `10-14`), with the section each page falls in.

The sanctioned read. A quotation an agent proposes must come from here, because this is the text the anchor is checked against; anything quoted from elsewhere may be right and cannot be verified.

| option | description |
|---|---|
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

#### `loom refs path`

`loom refs path [OPTIONS] CITEKEY`

Print where CITEKEY's artifacts live, under digests/storage. Nothing there is meant to be navigated by hand; the author's own pile goes in refs/ (book 8.16).

| option | description |
|---|---|
| `--pdf` | The PDF rather than the directory. |
| `--src` | The unpacked source rather than the directory. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

#### `loom refs propose`

`loom refs propose [OPTIONS] CITEKEY`

Propose one result of CITEKEY, its quotation checked against the page or source file it claims to come from.

The only write an agent makes to the reference layer. SOURCE-TEXT must appear on PAGE — whitespace, hyphenation across lines and ligatures are normalised, nothing else is — and on failure nothing is stored and the page's text is printed so the quotation can be corrected in the same turn. For a work with a LaTeX source, quote the source with --source-file instead: the mathematics is there, and in a PDF's text layer it is often control bytes. A proposal lands in `digests/CITEKEY.proposed.tex`, which no bundle inputs, and waits there for the author to verify or discard it.

| option | description |
|---|---|
| `--local` | The paper's own name for the result: thm-4.1, cor-2.3.1, eq-1, thm-star-2. |
| `--page` | The page the statement is on, or 353-354 if it runs over. |
| `--source-file` `FILE` | Quote the work's LaTeX source instead of a page: a file under the directory `loom refs path` prints. |
| `--source-text` | The paper's own words, verbatim; checked against the page or file. |
| `--statement` | The same result as LaTeX, in the paper's words only; the author verifies it. |
| `--taxon` | theorem, lemma, definition, equation, …; read off --local when omitted. |
| `--number` | The paper's numbers when it states several results together: '3.2, 3.3'. |
| `--level` | 1 is a main result. |
| `--supersedes` `ID` | Re-propose something discarded, recording the chain. |
| `--session` | The session proposing this. |
| `--json` | Print the stored record as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs recheck`

`loom refs recheck [OPTIONS] [CITEKEYS]...`

Re-read every verified result's anchor and report what moved. It does not re-check extraction: a mis-numbered or missing result in a mechanical digest is invisible to it.

This is what makes `transcription verified` a claim a command can falsify. It re-reads the page the anchor names and compares it to the stored `source_text`; it never re-verifies anything by itself, because re-verifying is a person saying the copy is still faithful, which is `loom refs verify`. **A verified node's LaTeX is never re-checked** — that rendering was judged by a person once, and re-judging it mechanically would claim a check that does not exist.

| option | description |
|---|---|
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs resolve`

`loom refs resolve [OPTIONS] [CITEKEYS]...`

Look up identifiers for cited works whose bibliography entry states none. Requires [refs] resolve = true, or --resolve for one run.

Asks zbMATH Open, then Crossref, and prints candidates with how well each matched. Nothing is changed: a candidate becomes the work's identity when you add the field to your own bibliography entry. Answers are kept in the store, so `loom lint` can name them and a second run asks nothing. With no CITEKEYS, every cited entry that states no identifier.

| option | description |
|---|---|
| `--refresh` | Ask again even where an answer is recorded. |
| `--json` | Print the candidates as JSON. |
| `--resolve` | Allow looking up for this run, without setting [refs] resolve in config.toml. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs scan`

`loom refs scan [OPTIONS]`

Add every bibliography entry the canon documents carry to digests/bibliography.bib.

Reads each canon document's inline `thebibliography` and the `.bib` files it names. The file is only ever appended to: an entry already there is never rewritten or removed, so a hand correction survives. A `\bibitem` becomes an entry with its text in `loom-text`, its identifiers, and a heuristic author, title and year. `import`, `canonize` and `refs build` run this themselves.

It also files what the author dropped in `refs/`, and **adopts** any document the store holds that no entry names -- an entry deleted by hand leaves a PDF and its page text that nothing can reach, and an entry is what names it. Adoption happens once per document; a later scan leaves it alone.

| option | description |
|---|---|
| `--dry-run` | Report what would be added and write nothing. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs unlink`

`loom refs unlink [OPTIONS] LINK_ID`

Remove a link.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs unreadable`

`loom refs unreadable [OPTIONS] CITEKEY`

Declare that CITEKEY has no document loom can hold, and stop it being asked for.

Nothing in a bibliography entry says that the Stacks Project is a living work with no fixed version, so loom would chase a PDF that does not exist on every build. This records the claim -- in loom's own file, never in your `.bib` -- and the invariant's lint goes quiet for the work while `loom refs build` lists it in a section of its own. It is a claim about the world, so it is yours to make and an agent is refused.

| option | description |
|---|---|
| `--why` | Why no document can be held for this work; required unless --undo. |
| `--undo` | Withdraw the declaration; --why then says why it was wrong. |
| `--author` | Who declared it, when the user config and git do not say. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs verify`

`loom refs verify [OPTIONS] TARGET`

Record that a transcription is faithful: promote a proposal into the digest, or re-verify one already there.

Two claims must not share a word. `loom accept` says *I have proved this, or I am satisfied it holds* and is about your own mathematics; this says *this copy is faithful to the paper it came from*, and settles nothing mathematical. With --statement you fix the rendering first: you are editing `statement`, never `source_text`, so the anchor is untouched and the result stays re-checkable — and both parties are recorded, because a record that credits an agent with a sentence you wrote cannot be audited.

| option | description |
|---|---|
| `--statement` | Your own rendering, replacing the proposed one before verifying. |
| `--local` | The paper's own name for it, correcting the proposal's: cor-3.2.1. |
| `--taxon` | The environment, when --local does not imply it. |
| `--author` | Who verified, when the user config and git do not say. |
| `--yes`, `-y` | Skip the question; you have read both texts. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom refs why`

`loom refs why [OPTIONS] TARGET`

Where a result came from, what state it is in, and who changed it.

Provenance names every party, not just the first: a record that credits an agent with a sentence you wrote cannot be audited.

| option | description |
|---|---|
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

### `loom revert`

`loom revert [OPTIONS] ADDRESS`

Print the patch that puts KEY@N's recorded text back in place of the head's; the file is the author's to change. Reverting materializes a version, it never points at one.

| option | description |
|---|---|
| `--json` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom review`

`loom review [OPTIONS]`

Observe current review causes and publish the review panel without accepting any key.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom search`

`loom search [OPTIONS] QUERY`

Find ids by id, alias, title, taxon, tag, or citekey; exact matches first.

A number as a reader sees it -- `Theorem 3.4`, `3.4`, `(3)` -- finds what each drafting document numbers so, the default document's first and marked; `--in DOC` asks one document only.

| option | description |
|---|---|
| `--kind` |  |
| `--in` `DOC` | Resolve a number like `Theorem 3.4` in this document only. |
| `--json` |  |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom serve`

`loom serve [OPTIONS]`

Watch, republish, and serve arras at / and build/ at /build/ until interrupted.

| option | description |
|---|---|
| `--port` | Port to listen on; fails if busy. |
| `--open` | Open the browser. |
| `--no-compile` | Never run latexmk after a change. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom session`

`loom session [OPTIONS] COMMAND [ARGS]...`

Sessions: the stretch of work an annotation belongs to, and which one is current.

A session has a stable id (`s-2026-09-20-0001`) that never changes and is what records and URLs use, and a title you may change whenever you like. One is active at a time, for you and for any agent working in this quilt, so that a person and an agent at the same job land in the same place.

#### `loom session close`

`loom session close [OPTIONS] [WHICH]`

End a session's current round. With no WHICH, the active one, which then stops being active.

| option | description |
|---|---|
| `--author` | Who closed it, when the user config and git do not say. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session delete`

`loom session delete [OPTIONS] WHICH`

Remove a session from view, or with --purge erase it and everything written in it.

A plain delete is a tombstone: the session stops being shown and every annotation made in it stays in the log, which is the rule the log has always had. `--purge` is the other thing, and is deliberately only here and never in the viewer: it rewrites the annotation log, and what it removes is gone.

| option | description |
|---|---|
| `--purge` | Really erase it, annotations and all. This cannot be undone. |
| `--why` | Why it was deleted; kept on the tombstone. |
| `--author` | Who deleted it, when the user config and git do not say. |
| `--yes`, `-y` | Skip the question --purge asks. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session list`

`loom session list [OPTIONS]`

What sessions this quilt has, newest last, with the active one marked.

| option | description |
|---|---|
| `--all` | Include closed and deleted sessions. |
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session new`

`loom session new [OPTIONS] [TITLE]`

Open a session and make it the active one. With no TITLE, one named after today.

| option | description |
|---|---|
| `--author` | Who opened it, when the user config and git do not say. |
| `--no-use` | Create it without making it the active session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session next`

`loom session next [OPTIONS]`

Park until something lands in a session, print it, and exit. One call is one turn.

For an agent. It returns the moment a message arrives rather than on a poll interval, so latency is an append and a wakeup; with nothing waiting it returns empty-handed when `--wait` runs out, and the agent parks again. Keep `--wait` under whatever timeout your harness puts on a tool call.

The inbox is read and never consumed: your cursor moves, the message stays, and a second reader sees it too. Nothing here assigns you anything -- it is a broadcast, and what to do about a message is your judgement.

| option | description |
|---|---|
| `--session` | The session to park on. |
| `--wait` | Seconds to park before returning empty-handed. |
| `--json` | Print as JSON, with the same text under `text`. |
| `--as` | Who is parking. An agent names itself, including Agent or AI. |
| `--since` | Start after this sequence number instead of your own cursor. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session rename`

`loom session rename [OPTIONS] WHICH TITLE`

Change a session's title. Nothing moves: the id is the address and does not change.

| option | description |
|---|---|
| `--author` | Who renamed it, when the user config and git do not say. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session say`

`loom session say [OPTIONS] TEXT`

Say TEXT in a session's chat, as the agent; `-` reads it from stdin.

The agent's half of the transcript, as `send` is the person's: the message goes into the session's inbox as written and carries no annotations. A `quilt:` or `cited:` link that names nothing the viewer shows is refused; `loom link` prints a correct one. Your own cursor moves past it when you had read everything before it, so `next` does not hand you your own words, and never past a message you have not read.

| option | description |
|---|---|
| `--session` | The session to speak in. |
| `--as` | Who is speaking: your name, including Agent or AI. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session send`

`loom session send [OPTIONS] [TEXT]`

Post TEXT into a session, from the terminal, with what you marked since the last message; with no TEXT, what you marked alone.

The symmetric verb to the composer in the viewer: both append to the same inbox, and a message lands whether or not anybody is listening. Loom is a mailbox: a parked reader wakes because a file grew, and where the quilt lets it, `loom serve` starts the configured agent for a turn.

| option | description |
|---|---|
| `--session` | The session to post into. |
| `--as` | Who is speaking. An agent names itself, including Agent or AI. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session use`

`loom session use [OPTIONS] WHICH`

Make WHICH the active session, resuming it when it was closed. WHICH is an id, a title, or a unique id suffix.

| option | description |
|---|---|
| `--author` | Who resumed it, when the user config and git do not say. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session watch`

`loom session watch [OPTIONS] [WHICH]`

Tail a session: print what lands, until you stop it.

For a person. It delivers nothing and assigns nothing -- it blocks on the log, prints, and keeps a heartbeat so the composer can say honestly whether anybody is listening.

| option | description |
|---|---|
| `--as` | Who is watching. An agent names itself, including Agent or AI. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom source`

`loom source [OPTIONS] TARGET`

Print TARGET's LaTeX source: a key's own text, or a document flattened with every inclusion expanded in place.

This is how a reader or an agent gets the text of a result or of a whole paper. It writes nothing: there is no file to clean up, none to keep out of version control, and none to go stale against the author's next edit.

With --closure, a key is preceded by exactly the statements it depends on, in dependency order. A document is already whole, so --closure does not apply to one.

| option | description |
|---|---|
| `--closure` | Everything TARGET depends on, in dependency order, then TARGET itself. |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom stamp`

`loom stamp [OPTIONS]`

Record every key whose text moved since the last step, quilt-wide (or within one document with --in), without writing a canon file.

| option | description |
|---|---|
| `--message`, `-m` | What this stamp marks. |
| `--in` `FILE` | Only the keys this document reaches. |
| `--json` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom status`

`loom status [OPTIONS]`

Every key with its computed state, cause if stale, and review facts. Never exits nonzero.

Notes on pages of cited works are not keys and appear in no row; `--reading` lists them by work, and `--json` always carries them under `reading`.

| option | description |
|---|---|
| `--stale` |  |
| `--draft` |  |
| `--incomplete` |  |
| `--loose` |  |
| `--unmatched-cites` |  |
| `--undigested` |  |
| `--retired` |  |
| `--runs` |  |
| `--master` |  |
| `--tag` |  |
| `--severity` | Keys carrying an annotation of this severity. |
| `--kind` | Keys carrying an annotation of this kind. |
| `--status` | Keys carrying an annotation in this state. |
| `--detached` | Keys whose annotations no longer find their quoted text. |
| `--include-digests` | Also list the digest keys nothing in this quilt depends on; they are left out by default. |
| `--reading` | List the notes on pages of cited works, by work; they are in no row and count toward nothing otherwise. |
| `--explain` `KEY` |  |
| `--json` |  |
| `--session` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom sync`

`loom sync [OPTIONS] COMMAND [ARGS]...`

Prepare and review a source-only document workspace; the quilt uses ordinary Git.

#### `loom sync documents`

`loom sync documents [OPTIONS] [add|remove] [DOCUMENT]`

Change the persistent document workspace selection without staging, committing, or publishing.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom sync fetch`

`loom sync fetch [OPTIONS]`

Fetch document workspace changes for Incoming review without changing author files.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom sync finish`

`loom sync finish [OPTIONS]`

Verify the author's Git application and commit the source and sync record.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom sync incorporated`

`loom sync incorporated [OPTIONS]`

Record that the author has incorporated a pull; accept no mathematics.

| option | description |
|---|---|
| `--yes` | Confirm that the incoming source was applied and committed. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom sync init`

`loom sync init [OPTIONS]`

Configure the document workspace for this quilt's selected documents.

| option | description |
|---|---|
| `--remote` |  |
| `--branch` |  |
| `--publish-main` | Document workspace main TeX path when it differs from the quilt master. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom sync patch`

`loom sync patch [OPTIONS]`

Print a patch for the author to inspect and apply in the editor.

| option | description |
|---|---|
| `--to` | Write the incoming Git patch to a new file. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom sync prepare`

`loom sync prepare [OPTIONS]`

Prepare a pinned patch for the author to apply with Git.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom sync publish`

`loom sync publish [OPTIONS]`

Build and compile the committed document workspace projection locally.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom sync status`

`loom sync status [OPTIONS]`

Show document workspace revisions, selection, and the prepared local ref.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom unravel`

`loom unravel [OPTIONS] ID`

Everything downstream of ID: dependents, reference and inclusion sites, ledger rows, annotations. Reports; changes nothing.

| option | description |
|---|---|
| `--json` |  |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom upgrade`

`loom upgrade [OPTIONS]`

Refresh loom.sty, ai/orientation.md, ai/README.md, the vendor files, and unedited mode files; report edited ones.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

## 12.9 Machine output

**[decided]** Every `--json` output is a single JSON document. Shapes reuse the manifest's (specs/manifest.md) wherever the same data appears: `status --json` uses the `keys` shape; `deps --json` and `unravel --json` use the `edges` shape; `search --json` uses the `search` shape plus `file` and `url`. New shapes are documented here before they exist.

**[decided]** `deps --json` carries `relations` beside `statement`, `proof` and `closure`: both directions of every `see:` declaration touching the key, as `{"key": ID, "kind": "see"}`, in target order. In the printed form they are a final section headed "see also (not a dependency):", after the edge lists, so that nothing reads them as dependencies. `unravel` does not list relations: it reports consequences, and a relation has none.

## 12.10 Environment variables

**[decided]** `LOOM_QUILT` (quilt root, overrides discovery); `LOOM_SESSION` (default for `--session`); `LOOM_FIXED_TIME` (fixture generation: all timestamps take this value); `LOOM_PAPER_FIXTURES` (tests: directory of arXiv sources for the paper tier); `LOOM_ARRAS_BUNDLE` (a viewer bundle directory that overrides the installed `arras` package and the vendored copy, 12.5); `LOOM_SVG_KEEP` (debugging: a directory that receives every fallback document that failed to compile, DR-79). The test shim reads `FAKE_TEX_LOG`, `FAKE_TEX_FAIL`, and `FAKE_TEX_FAIL_MATCH`. No other variable is read (M7).

## 12.11 Withdrawn commands

For readers of earlier design notes: `impact` became `unravel`; `dependents` and `closure` folded into `deps`/`unravel`; `resolve` folded into `search --json`; `tag` became `id`; `state set`/`state refresh` became `accept`/`status`; `ref use` disappeared when digests became LaTeX; `ai finish`, `ai resume`, `ai list`, `ai restore` folded into `session close`, `ai orient --session`, `ai runs` and `status --runs`, and `ai discard --undo`; `digest export` is `cp`; `init --ai` is `ai init`; `bundle --for-review` is the modes' business; `new --in FILE` is `new --print`; `assemble` is `linearize`, which takes `--to` and knows the identity rule (DR-139); `atomize --ignore-src` is gone, the history recording that a spine superseded its source and `--retire` moving the file when asked (DR-138); `ai runs` is `session list [--all]`, which listed the same sessions; `ai promote` is gone entirely: a drafted node is previewed in arras and pasted by the author with an id from `loom id --next` (DR-140), and a digest is produced by `loom digest extract` rather than typed by an agent, so there is nothing left for it to copy (DR-173). `loom refs crawl plan`, `fetch` and `status` went to weft with the rest of the crawl, and the `[crawl]` table with them (8.13, DR-144). `loom bundle` is gone: reading a key and its dependencies is `loom source KEY --closure`, which prints, and checking that a proposal compiles is `loom compile KEY --with FILE`; the document itself is still written under `build/bundles/` by the compile that needs it (DR-148). `loom ai start` no longer launches an agent and `[ai] agent` and `--no-launch` are withdrawn with it (DR-149). `loom digest fetch` is `loom refs fetch`, which also fetches on a strong resolver candidate and on a bibliography `url` that is a PDF, and records which identifier a source came from; `loom refs build` runs it with every other mechanical step (DR-176, DR-181). There has never been a `loom label`: the command that writes ids is `loom id`. `comment` is `annotate`, `ai findings` is `ai annotations` and `refs note` is `refs cite`: an annotation is the one noun for the record, and `note` names only a kind (DR-292-ikmartin).

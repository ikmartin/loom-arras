# 12. CLI reference

Every loom command, with syntax, flags, behaviour, exit codes, and machine output. Behaviour is specified in the earlier chapters; this chapter is the index and the fixed surface. The implementation generates the `--help` text and the user-facing reference from the same definitions, so that this chapter, the help, and the code cannot drift apart without a test failing; 12.2 below is that generated reference.

## 12.1 Conventions

**[decided]**

- Quilt discovery: every command except `init` and `doctor` walks up from the current directory to the nearest `config.toml` with a `[quilt]` table and runs against that quilt. `--quilt PATH` overrides. `doctor` needs no quilt, and checks the one it finds the same way.
- Exit codes: `0` success; `1` a content problem (lint errors, a failed identity test, a failed compile, a refused write that the author can fix in the source); `2` a usage or environment problem (bad arguments, an argument that names no key, annotation, session, work or result, missing tools, no author name, consent `config.toml` does not give, a destination that exists). The rule decides by what the person must change: the quilt's source is `1`, the command or the machine is `2` (DR-290-ikmartin).
- `--json`: machine output on stdout, one JSON document, nothing else on stdout, on failure as on success; diagnostics and progress go to stderr. Every command that reports takes it, and its JSON is the envelope of 12.9, built from the same report as the text, so the two cannot drift (DR-329-ikmartin).
- Output: every command that reports prints through one layer (`loom/cli/report.py`): the verdict first, then groups each with a heading and a count, a long list cut with `… and N more` and the command that lists it whole, a `fix:` or `next:` line naming each command that acts, lines within 100 columns, an identifier never cut, and notes on stderr. A dry run's verdict begins `dry run:`. Diagnostics are grouped by code with their locations and `fix:` lines, in three parts by whose they are (DR-332-ikmartin): the author's, which include a diagnostic on a cited work's result the author's text reaches; the cited works', counted under a heading of their own; and those of works nothing cites, one line in the text, every one in `--json`, which never set an exit code and which `loom library check` lists by work. Commands whose body is the author's own text, a patch, a page or a link (`source`, `id`, `revert`, `sync status --patch`, `history show`, `library read`, `library locate`, `link`, `ai orient`, `session next`) print that body as it is (DR-329-ikmartin).
- Errors: a refusal is one line on stderr, `Error: …`, with nothing on stdout, and exits by the rule above.
- Progress: a command still working after 2 s says so on stderr, with its stage, its item, the item's place in the count and the time elapsed; an item past 15 s adds `still working`; on a terminal it is one line that rewrites itself, elsewhere a plain line at most every 2 s (T6).
- How what a command prints should read — the verdict first, repeated lines grouped and counted, the next command named, the reader's words, numbers that add up, progress for anything slow, saying only what happened, and `--json` that carries what the text does — is T1–T8, in Chapter 1 (1.10); the shape of the command line itself, its commands, flags, validation and help, is K1–K7 (1.12).
- `--yes`: skip confirmations that would otherwise be asked on a terminal. Commands that would ask and have no terminal and no `--yes` exit 2.
- `--session SESSION`: on `source`, `compile`, `annotate`, `status`, `search`, `deps`, `downstream`, `lint`, `id`, `new`, `ai orient` and `ai annotations`: append the invocation to the session's `run.log` (`LOOM_SESSION` is the default). `annotate` writes into the active session when neither is given. **[decided]** `SESSION` is a session's id, its title, or an unambiguous part of either; an ambiguous one names its matches and refuses (DR-199). On `annotate` it names where the annotation belongs, never its author, because a session is a place and an author is a person or a named agent (DR-200).
- **One idea, one flag** (K2, DR-330-ikmartin, DR-331-ikmartin):
  - `--as NAME` is who acts: the person's name, overriding the user config (4.3), or an agent's declared name. On `accept`, `annotate`, the `session` writers and `session say`/`next`/`watch`.
  - `--by NAME` filters by who wrote: `ai discard --by`.
  - `--name NAME` names something new: `fork --name ID`, `session new --name TITLE`, `session rename --name TITLE`.
  - `--to FILE` is the file to write, always an option. A relative path is the quilt root's. It is refused, exit 2, among the quilt's sources (`.tex`, `.sty`, `.cls` and `.bib` outside `build/`) and in the drafting directories, except by a command that writes a drafting document (`linearize`, `history restore`), which must write directly into one, and by `atomize`, whose output takes its source's place; and refused when it exists, except where the command overwrites by design.
  - `--why TEXT` is a reason.
  - `--dry-run` shows what a writer would write and writes nothing; its verdict begins `dry run:` and its envelope carries `dry_run`. Every writer takes it. `--json` is never a dry run: it reports what was done. `adopt`'s preview is its dry run.
- Values are checked before anything runs (K3): a value with a fixed set of answers is a choice (`compile --engine`, `ai annotations --severity/--kind/--status`), and one that must name something in the quilt (a key, a session, `status --kind/--master/--tag`, a `--prefix` that must fit the id grammar) is refused by name, exit 2, before anything prints or a session log is written.
- No command has an alias (K1). `delete`, `rm` and `remove` are not commands; loom answers each with why it does not delete and exits 2 (7.9).
- Help (K6): `loom --help`, and `loom` alone, which exits 0, lists the commands in sections by task, the person's first — Start, Write, Review, History, Library, Agents, Publish, Upkeep — each with a line of what it is for, every command with its first sentence whole, and `*` on each command an agent may run, or some of whose subcommands it may (11.8). 12.2 lists them in the same order.
- `--quiet` / `-q` and `--verbose` / `-v` were planned and are not implemented; diagnostics go to stderr, summaries to stdout (M7).
- Keys are written as ids (`rl-0004`), proof keys (`rl-0004/proof`, `rl-0004/proof/2`), qualified keys (`rl-0004#eq:main`, `drafting/main.tex#section:3`), or master paths. Aliases are accepted wherever an id is and resolved. An **address** adds a step: `rl-0004@3`, or `rl-0004@paper-v2` naming the landmark instead of the number (17.4).
- `-m MESSAGE`: required by `stamp`, as by a commit; given a document, it names the landmark. A landmark nobody named is a landmark nobody can ask for.
- **`loom doctor`** (DR-288-ikmartin) is the one command to run when something is off. Every item it reports is `ok`; `warn`, it works but the person will hit something; or `fail`, a command they need will refuse or misbehave. Each item that is not `ok` carries a one-line remedy, the command where there is one. It exits `0` when nothing fails and `2` when anything fails; `--strict` counts a warning as a failure, so doctor never exits `1`, which means a content problem. The summary line names every failing item, and under `--strict` every warning. Machine items come first: the TeX tools (`latexmk`, `pdflatex` and `dvisvgm` required; `latex`, `xelatex`, `lualatex`, `bibtex`, `biber`, `kpsewhich` optional), poppler (`pdftotext`, `pdfinfo`, `pdftocairo`, optional), `git`, `claude` and `codex` when the quilt configures an agent or `--agents` is given, the author name and the arras bundle. A required tool missing fails and an optional one warns; any tool that is present but hangs, will not start, or lacks what loom uses (a `pdftotext` without `-bbox-layout`) fails, since loom runs it when it is there; a biber and biblatex that do not pair warn. Inside a quilt a second section reuses the checks the owning commands make: the configured engine is installed (fails if not); the agent configuration (a fault fails when `launch` is on and warns when off; `--agents` prints it in full: the start, resume and prompt lines, and each fault with its fix); the permission files, the mode files and `loom.sty` against what `loom upgrade` would write, by its dry run; the `.gitignore` lines `loom upgrade` adds; and `config.toml`'s warnings, pointing to `loom lint`. `--json` prints the envelope (12.9) with `python`, `loom`, `interface_version`, `quilt`, `failing`, `warnings` and `items` beside it, where the envelope's `ok` is the exit code being 0, `failing` and `warnings` are item names, and each item has `name`, `status`, `severity` (`required`, `optional` or `quilt`), `detail` and `remedy` (empty when `ok`); a tool adds `path`, the bundle `source`, `path` and `interface`. Every probe has a deadline (10 s), so a hung tool is reported rather than waited on, and doctor writes nothing.

## 12.2 Commands

**[decided]** The reference below is generated from the command tree by `loom/scripts/gen_cli_reference.py`; `loom/docs/cli-reference.md` is the same text, and the test `test_cli_reference_matches_checked_in` fails when either drifts from the code. Every command's `--help` prints the same usage and options. Behaviour is specified in the earlier chapters; the sections 12.2 to 12.8 of the pre-implementation book, which listed the commands by hand, are replaced by this generated list (M7). Aliases: `rm` and `remove` for `delete`; `downstream`, `reach`, and `pop` for `unravel`.

Generated by `scripts/gen_cli_reference.py` from the command tree; do not edit. Every command has one name, listed in the sections of `loom --help`; a group that runs on its own is documented as a command, then with its subcommands.

## `loom`

`loom [OPTIONS] COMMAND [ARGS]...`

loom: a tool for atomized mathematical development.

Every command except `init` and `doctor` runs against the nearest quilt, found by walking up from the current directory to a `config.toml` with a [quilt] table; `doctor` checks that quilt too when there is one.

| option | description |
|---|---|
| `--version`, `-V` | Show the version and exit. |

### Start

Make a quilt, bring a paper into it, and check what loom needs.

#### `loom init`

`loom init [OPTIONS] [DIRECTORY]`

Create a quilt in DIRECTORY (default: the current directory); with --from FILE, import a paper into it: the paper as received kept as the first landmark, and the working document drafted from it.

| option | description |
|---|---|
| `--from` `FILE` | Import an existing paper: FILE is its main .tex file, anywhere on disk. |
| `--demo` | Write the demo quilt instead of a minimal master. |
| `--prefix` | Id prefix for new nodes. |
| `--git` | Also run git init. A quilt is files; loom reads no history. |
| `--ai` | Which AI you use, instead of being asked: Claude or Codex get the agent layer, as loom ai init writes it. |
| `--launch-agents`, `--no-launch-agents` | Let loom serve start the agent for a turn when a message waits (config.toml [ai] launch). Off by default. |
| `--fix-anchoring` | With --from: rewrite the drafted document so every theorem-like \begin and \end is alone on its line. |
| `--yes`, `-y` | Skip questions; take defaults and confirm the import. |
| `--dry-run` | Say what would be created, and write nothing; no identity test. |
| `--json` | Print the report as one JSON object (book 12.9). |

#### `loom import`

`loom import [OPTIONS] FILE`

Bring a paper into the quilt: its styles, bibliography and figures at the root, the paper as received kept as a landmark in step 0001, and the working document drafted from it at once in the drafting directory.

| option | description |
|---|---|
| `--yes`, `-y` | Import without asking for confirmation. |
| `--no-check` | Skip the identity test. |
| `--fix-anchoring` | Rewrite the drafted document so every theorem-like \begin and \end is alone on its line. |
| `--dry-run` | Say what the import would write, and write nothing; no identity test. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom atomize`

`loom atomize [OPTIONS] [SRC]`

Move each node of SRC into nodes/<id>.tex and write the spine --to FILE, a copy of SRC with inclusion lines in their place.

SRC is not modified; the history records that the spine superseded it, so it defines nothing until `loom live`.

| option | description |
|---|---|
| `--to` `FILE` | The spine to write: SRC with inclusion lines in place of its nodes. |
| `--key` `KEY` | Move only these nodes, wherever they live; SRC is not needed. Writes the node files and prints the patch for the source, which loom never edits. |
| `--proofs` | Keep each proof in its statement's node file, or give it a file of its own. |
| `--sections` | Also move labelled sections and subsections to nodes/. |
| `--all` | Act on SRC and every file it reaches, writing spines under --to-dir. |
| `--to-dir` `DIR` | With --all: the directory the spines are written under. |
| `--retire` | Move SRC into retired/ once its spine is written, instead of leaving it superseded in place. |
| `--dry-run` | Say what would be written and moved, and write nothing; no identity test. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom doctor`

`loom doctor [OPTIONS]`

Check the TeX toolchain and what loom needs of it, poppler, git, the author name and the arras bundle; inside a quilt, also its engine, its agent configuration, its generated files, its .gitignore and its config.

With --agents, the agent `loom serve` would start is reported in full: whether launching is on, the config, the start, resume and prompt lines, and each fault with its fix. Nothing is run.

Each item is ok, warn (works, but you will hit it) or fail (a command you need will refuse), with the command that fixes it. Exits 0 when nothing fails and 2 when anything does; under --strict a warning counts as a failure. Writes nothing; a tool is run only to ask its version or test what loom needs of it, and one that has not answered in 10 s is reported as hung.

| option | description |
|---|---|
| `--json` | Machine-readable report on stdout. |
| `--strict` | Count a warning as a failure: exit 2 when any item warns. |
| `--agents` | Also look for claude and codex, and inside a quilt report the agent loom serve would start: its commands, its prompt, and what would stop it. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### Write

Make and find nodes, and see what state each is in.

#### `loom new`

`loom new [OPTIONS] TAXON [TITLE]`

Allocate an id and write nodes/<id>.tex with a skeleton for TAXON; with --print, print the skeleton instead.

| option | description |
|---|---|
| `--prefix` | Allocate under this prefix instead of [quilt] prefix. |
| `--print` | Print the skeleton without allocating an id or writing a file. |
| `--dry-run` | Say which id and file would be written, and write nothing. |
| `--session` `SESSION` | Log this call to the session. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom id`

`loom id [OPTIONS] [FILE]`

Print a patch inserting \label{<id>} on every untagged theorem-like environment and section in FILE, or write the patched copy with --to; with --next, print the next free id.

FILE is never modified.

| option | description |
|---|---|
| `--to` `FILE` | Write the patched copy here instead of printing a diff; never among the quilt's sources. |
| `--sections`, `--no-sections` | Also label sections through subsubsection (default on). |
| `--all-levels` | Also label paragraphs and subparagraphs. |
| `--prefix` | The id prefix (default: the quilt's). |
| `--fix-anchoring` | Include line-anchoring repairs in the patch or written copy. |
| `--next` | Print the next free id and nothing else; inserts nothing. |
| `--json` | With --next: print it as JSON. |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom lint`

`loom lint [OPTIONS]`

Scan and print every diagnostic. Fast; no LaTeX runs.

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--nodes` | One block per node id: what is wrong with its identity, and the superseded files. |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom status`

`loom status [OPTIONS]`

List every key with its computed state, cause if stale, and review facts. Never exits nonzero.

Notes on pages of cited works are not keys and appear in no row; `--reading` lists them by work, and `--json` always carries them under `reading`.

| option | description |
|---|---|
| `--stale` | Accepted keys whose text, closure or preamble moved since. |
| `--draft` | Keys never accepted. |
| `--incomplete` | Keys marked \incomplete. |
| `--loose` | Keys no live document reaches. |
| `--unmatched-cites` | Located citations of a digested work that match no digest node. |
| `--undigested` | Works cited with a locator and not digested. |
| `--retired` | Keys accepted once and defined by no document now. |
| `--runs` | Every session on record, with its annotations. |
| `--master` `DOC` | Keys this document reaches. |
| `--tag` | Keys carrying this tag. |
| `--severity` | Keys carrying an annotation of this severity. |
| `--kind` `objection|suggestion|question|citation|note` | Keys carrying an annotation of this kind. |
| `--status` | Keys carrying an annotation in this state. |
| `--detached` | Keys whose annotations no longer find their quoted text. |
| `--include-digests` | Also list the digest keys nothing in this quilt depends on; they are left out by default. |
| `--reading` | List the notes on pages of cited works, by work; they are in no row and count toward nothing otherwise. |
| `--explain` `KEY` | Why KEY is in its state, with the diff of what moved. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--session` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom source`

`loom source [OPTIONS] TARGET`

Print TARGET's LaTeX source: a key's own text, or a document flattened with every inclusion expanded in place.

This is how a reader or an agent gets the text of a result or of a whole paper. It writes nothing: there is no file to clean up, none to keep out of version control, and none to go stale against the author's next edit.

With --closure, a key is preceded by exactly the statements it depends on, in dependency order. A document is already whole, so --closure does not apply to one.

| option | description |
|---|---|
| `--closure` | Everything TARGET depends on, in dependency order, then TARGET itself. |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom search`

`loom search [OPTIONS] QUERY`

Find ids by id, alias, title, taxon, tag, or citekey; exact matches first.

A number as a reader sees it -- `Theorem 3.4`, `3.4`, `(3)` -- finds what each drafting document numbers so, the default document's first and marked; `--in DOC` asks one document only.

| option | description |
|---|---|
| `--kind` | Only matches of this kind. |
| `--in` `DOC` | Resolve a number like `Theorem 3.4` in this document only. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom link`

`loom link [OPTIONS] THING`

Print a markdown link to THING that the viewer can follow.

THING is a node or any key in it, a document's path, an annotation id, a session id, or a cited work's citekey or identifier. The link's text is empty: the viewer names the thing itself, as `Theorem 3.1`, and keeps the name right when the document is renumbered; write your own words between the brackets to show those instead. A thing the viewer does not show is refused, with why.

| option | description |
|---|---|
| `--at` | A key inside the document or node: link to that place in it. |
| `--page` | A page of a cited work, from 1. |
| `--quote` | Text on that page to find. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### Review

Annotate, accept, and see what rests on what.

#### `loom annotate`

`loom annotate [OPTIONS] [TARGET] [MESSAGE]`

Write an annotation on TARGET: a key, an equation's qualified key, a master path -- or, with --page, a cited work.

A note on a page of a cited work names the work by citekey or identifier and the place by --page with --quote (text on the page) or --box (a rectangle on it). It lands in the same log and the same session as every other annotation, and `loom status --reading` lists it.

| option | description |
|---|---|
| `--quote` | Anchor to this exact text: once in a key's own text, or on the page of a cited work given by --page. |
| `--page` `N` | A note on page N of a cited work (TARGET a citekey or a work identifier); with --quote or --box. |
| `--box` `X0,Y0,X1,Y1` | Anchor to a rectangle on the page, in points with the origin at the top left; ';' separates several. |
| `--kind` `objection|suggestion|question|citation|note` | What the annotation is; any unambiguous prefix. Default note. |
| `--session` | Write into this session: an id, a title, or a unique id suffix. Default the active one. |
| `--as` `NAME` | Who is writing; an agent names itself, with Agent or AI in the name. |
| `--reply` `ID` | Answer annotation ID; the message is the reply. |
| `--resolve` `ID` | Mark annotation ID resolved, with the message as why. |
| `--edit` `ID` | Supersede an annotation's body; the history stays in the log. |
| `--discard` `ID` | Withdraw a finding you should not have raised; resolving would claim the author addressed it. |
| `--severity` | How bad the fault is, not how keen you are. |
| `--payload` | Suggested text the author may preview and copy. |
| `--placement` | Where the payload goes, as a hint. |
| `--in` `DOC` | A claim about the node as read in this document: marked there, listed on the node's own page, absent elsewhere. |
| `--undo` | With --resolve or --discard, put the finding back: an undo is another event, never a removal. |
| `--batch` | Read JSON lines from stdin, one annotation or one change per line; an unknown key is an error. |
| `--dry-run` | Say what would be written, and write nothing, not even a session. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom accept`

`loom accept [OPTIONS] [KEYS]...`

Record acceptance rows and snapshots for KEYS; the only writer of the ledger.

| option | description |
|---|---|
| `--proofs` | Also accept every proof attached to each statement given. |
| `--stale` | Accept every key that is currently accepted-stale, after confirmation. |
| `--all-live` | Accept every live author-owned statement and proof, after confirmation. |
| `--master` | Accept every statement and proof reached by MASTER. |
| `--as` `NAME` | Who accepts; default your configured name. |
| `--force` | Accept even when the document the acceptance is recorded against does not compile. |
| `--yes`, `-y` | Accept --stale, --all-live or --master without asking. |
| `--dry-run` | Say what would be accepted, and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom deps`

`loom deps [OPTIONS] KEY`

Show what KEY depends on: direct statement-edges and proof-edges, grouped.

| option | description |
|---|---|
| `--closure` | The transitive statement closure in dependency order. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom downstream`

`loom downstream [OPTIONS] ID`

Show everything downstream of ID: dependents, reference and inclusion sites, ledger rows, annotations. Reports; changes nothing.

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### History

Record steps, read and restore earlier text, and move documents.

#### `loom stamp`

`loom stamp [OPTIONS] [DOCUMENT]`

Record every key whose text moved since the last step, quilt-wide; given DOCUMENT, only the keys it reaches, and its flat text kept as a landmark.

A landmark is how a document stood at a moment worth returning to: `loom history show NAME` prints it and `loom history restore NAME --to FILE` starts a document from it (book 17.9).

| option | description |
|---|---|
| `--message`, `-m` | What this stamp marks; given a DOCUMENT, it names the landmark (`widgets-v3`). |
| `--dry-run` | Say what the step would record, and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom history`

`loom history [OPTIONS]`

`loom history [OPTIONS] [KEY | COMMAND [ARGS]...]`

Run alone, `loom history` is a command; its subcommands follow its options.

List the steps and stamps of this quilt, one per line; `loom history KEY` lists that key's versions and whether the head equals one.

A landmark, which `show` prints and `restore` starts a document from, is named by its name, its step, or `DOC@STEP` (book 17.9).

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom history restore`

`loom history restore [OPTIONS] NAME`

Start a document from a landmark.

A new drafting document from the landmark NAME, with the package line and an id on every node that has none; the author's alone.

| option | description |
|---|---|
| `--to` `FILE` | The new document, directly in the drafting directory. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom history show`

`loom history show [OPTIONS] NAME`

Print a landmark's text.

The text of the landmark NAME as its step kept it, raw; with --plain, the paper without loom.

| option | description |
|---|---|
| `--plain` | The paper without loom, its package line swapped for the macro block. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom history verify`

`loom history verify [OPTIONS]`

Check the history against its ledger.

Every step directory is walked against the ledger: missing or edited version files, preambles, copies, and ancestry that no longer resolves.

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom revert`

`loom revert [OPTIONS] ADDRESS`

Print the patch that puts KEY@N's recorded text back in place of the head's; the file is the author's to change. Reverting materializes a version, it never points at one.

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom mv`

`loom mv [OPTIONS] OLD NEW`

Move the drafting document OLD to NEW and record the move, so every record naming OLD follows it. When OLD is already gone and NEW is a live document, record a rename made elsewhere; nothing is moved.

Both are .tex files directly in the drafting directory. Moving the default document moves [quilt] main with it.

| option | description |
|---|---|
| `--dry-run` | Say what would be moved and recorded, and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom fork`

`loom fork [OPTIONS] NODE_ID`

Give FILE its own copy of a node under a new id: a node file when FILE includes the node, else the copy inline.

The copy is printed as a patch for FILE, with its references rewritten; nothing outside FILE changes.

| option | description |
|---|---|
| `--in` `FILE` | The document that gets its own copy. |
| `--from` `@N` | Copy the text the key had at step N instead of the head. |
| `--name` `ID` | The new id (default: the next free one). |
| `--dry-run` | Print the plan and the patch, and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom linearize`

`loom linearize [OPTIONS] SPINE`

Write FILE, SPINE with every \input, \include and \nest (levels shifted) expanded in place; the spine and every file it inlined are then superseded.

| option | description |
|---|---|
| `--to` `FILE` | The flat document to write. |
| `--fork` | Give this document its own copy of every node another document shares. |
| `--keep-shared` | Leave shared node files as inclusions, marked. |
| `--no-check` | Skip the identity test. |
| `--dry-run` | Say what would be written and superseded, and write nothing; no identity test. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom deloom`

`loom deloom [OPTIONS] SOURCE`

Write FILE, the document SOURCE flattened, with loom taken out and every other line as written.

Removed: `\usepackage{loom}`, `% !LOOM` lines, `\uses{…}`, and every label that is a loom id; a reference to an id moves to your own label beside it. A referenced result whose only label is its id, and any `\incomplete{…}`, block the deloom until you give the result a label or resolve the incomplete, or pass the flag that keeps them.

| option | description |
|---|---|
| `--to` `FILE` | The file to write: one flat document, never among the quilt's sources (build/ or outside the quilt). |
| `--keep-referenced-ids` | Keep the id label of a referenced result that has no label of yours, and the references to it. |
| `--keep-incomplete` | Keep every \incomplete{…}, defined to print nothing as loom.sty defines it. |
| `--dry-run` | Say what would be removed and written, and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### Library

The papers you cite and the results taken from them.

#### `loom library`

`loom library [OPTIONS]`

`loom library [OPTIONS] [WORK | COMMAND [ARGS]...]`

Run alone, `loom library` is a command; its subcommands follow its options.

Report what the quilt's cited works need: from you, from an agent, and in review; `loom library WORK` reports one work.

A WORK is a citekey, a fragment of one or of its author or title, or one of its result ids.

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--session` `SESSION` | Log this call to the session. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library add`

`loom library add [OPTIONS] FILE...`

File PDFs and LaTeX sources in loom's store, each under the work it shows it is.

A FILE is a PDF, a `.tex` file, or a folder: each PDF in a folder is a document, and a folder holding no PDF is one LaTeX source. A document is filed on a strong match only: an identifier on its first pages equals the entry's, or its whole title is the entry's and the entry's first author leads its byline. Anything weaker is skipped with its reason, and a document naming two entries equally is refused. With `--for`, every FILE is that work's: a PDF that does not show it, or any document that shows it is another work's, is refused unless `--force`, and a source is refused when its own title is another's. A work that holds a document gets the new one beside it under a sibling entry, never over it (book 8.16), unless it is a copy of one of the work's documents: it states that version's identifier, or its title, byline and page count are that document's. A copy is recorded in the ledger and not filed. A PDF's page text is written at once.

| option | description |
|---|---|
| `--for` `WORK` | The work every FILE is; without it each is matched to the bibliography by what it shows. |
| `--force` | With --for, file a document that does not show it is that work; the override is recorded. |
| `--as` `NAME` | Who is filing, when the user config and git do not say. |
| `--dry-run` | Say what would be filed, skipped and refused, and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library check`

`loom library check [OPTIONS] [WORK...]`

Check the library for what has gone wrong, each problem with its fix.

Re-reads every verified result's anchor against the page or source it names; never re-judges a verified rendering, which a person judged once, and never re-checks extraction. Then: a stored PDF whose first page carries another work's title, a digest with no results, a section map with far too few sections for its length, and entries or versions holding one document, once per work. Exit 1 when anything is wrong. Works nothing cites whose digests lint finds wrong are listed too, and do not fail it.

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

##### `loom library discard`

`loom library discard [OPTIONS] ID...`

Discard a proposed result, or reject a citation suggestion, with a reason.

`loom library propose` refuses a discarded result and returns the reason, so the agent that proposed it learns why in the turn it fails. A rejected suggestion is resolved with the reason on the resolve event and records nothing. Nothing is deleted: the log keeps it and `loom library why` reports it.

| option | description |
|---|---|
| `--why` | Why it should not stand; whatever proposes it again is shown this. |
| `--as` `NAME` | Who is deciding, when the user config and git do not say. |
| `--dry-run` | Check everything and say what would be recorded; write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library drop`

`loom library drop [OPTIONS]`

Remove recorded results: one work's, one session's proposals, or every one still proposed.

Dropping costs re-reading, never correctness. A verified node already written into digests/<citekey>.tex is the author's file and is never touched; only the records and the proposals go.

| option | description |
|---|---|
| `--work` `WORK` | Everything recorded for this work. |
| `--session` `SESSION` | Everything proposed in this session. |
| `--proposed` | Every result still proposed, in every work. |
| `--yes` | Do not ask. |
| `--dry-run` | Say what would be dropped; drop nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library ignore`

`loom library ignore [OPTIONS] WORK`

Stop loom asking for a work's document, or offering a stored document an entry.

A work with no document is declared unreadable -- the Stacks Project is a living work with no fixed version -- so the lint stops asking for a PDF that does not exist. A work whose store holds a document is set aside: once your bibliography no longer names it, the store stops offering it an entry on every scan. WORK may also be a prefix of a stored document's hash, for one no entry names. Both are recorded in loom's own file, never in your .bib, and --undo withdraws whichever stands.

| option | description |
|---|---|
| `--why` | Why loom should stop asking for it; with --undo, why that was wrong. |
| `--undo` | Withdraw what stands, so the work is asked for or offered again. |
| `--as` `NAME` | Who is deciding, when the user config and git do not say. |
| `--dry-run` | Check everything and say what would be recorded; write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library import`

`loom library import [OPTIONS] PATH`

Copy a digest from another quilt into digests/, rewriting its citekey and id prefix when --name renames it.

It never overwrites a digest already there.

| option | description |
|---|---|
| `--name` `CITEKEY` | File it under this citekey, rewriting its ids. |
| `--dry-run` | Say what would be written; write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library locate`

`loom library locate [OPTIONS] WORK TEXT`

An agent's tool: print the region of WORK's page PAGE that TEXT occupies, so an anchor need not compute geometry.

Token geometry is thirty times the size of plain page text, so it is produced for the one page asked about and kept there; nothing writes it in bulk. Where `loom serve` is running, an `open:` line follows with a link into the viewer **at the place** -- `?page=4&span=812-871` -- so that following it lights the quotation rather than leaving it to be found by eye.

| option | description |
|---|---|
| `--page` | The page the text is on. |
| `--json` | Print the anchor as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

##### `loom library propose`

`loom library propose [OPTIONS] WORK`

An agent's tool: propose one result of WORK, its quotation checked against the page or source file it claims to come from.

The only write an agent makes to the library's results. SOURCE-TEXT must appear on PAGE — whitespace, hyphenation across lines and ligatures are normalised, nothing else is — and on failure nothing is stored and the page's text is printed so the quotation can be corrected in the same turn. For a work with a LaTeX source, quote the source with --source-file instead: the mathematics is there, and in a PDF's text layer it is often control bytes. A proposal lands in `digests/CITEKEY.proposed.tex`, which no bundle inputs, and waits there for the author to verify or discard it.

| option | description |
|---|---|
| `--local` | The paper's own name for the result: thm-4.1, cor-2.3.1, eq-1, thm-star-2. |
| `--page` | The page the statement is on, or 353-354 if it runs over. |
| `--source-file` `FILE` | Quote the work's LaTeX source instead of a page: a file under the directory `loom library read WORK --where src` prints. |
| `--source-text` | The paper's own words, verbatim; checked against the page or file. |
| `--statement` | The same result as LaTeX, in the paper's words only; the author verifies it. |
| `--taxon` | theorem, lemma, definition, equation, …; read off --local when omitted. |
| `--number` | The paper's numbers when it states several results together: '3.2, 3.3'. |
| `--level` | 1 is a main result. |
| `--supersedes` `ID` | Re-propose something discarded, recording the chain. |
| `--session` `SESSION` | The session proposing this. |
| `--dry-run` | Check the quotation and say what would be proposed, storing nothing. |
| `--json` | Print the stored record as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library read`

`loom library read [OPTIONS] WORK [PAGES]`

Print a cited work's page text for PAGES (`12` or `10-14`), each page with its section, or without PAGES its digest's Overview.

The page text is the sanctioned read: a quotation an agent proposes must come from it, because it is the text the anchor is checked against. The Overview is the paper's own framing, which is prose and so no result. `--where` prints where loom keeps the work instead; nothing there is meant to be navigated by hand, and the author's own pile goes in refs/ (book 8.16).

| option | description |
|---|---|
| `--where` | Print where the work's directory, PDF or source is kept, instead of reading it. |
| `--json` | Print the pages, the overview or the location as one JSON object. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

##### `loom library relate`

`loom library relate [OPTIONS] FROM TO`

Assert a typed relation between two results, FROM and TO, with a reason; with --undo LINK_ID, remove one.

**Nobody verifies this and it says so.** A relation has no page span to check it against, so a verification step would be theatre; it is an assertion, attributed to whoever made it. Relations are never citable, never enter a closure, and are never written into a digest: they are navigation, not mathematics. `loom library why ID` lists a result's relations.

| option | description |
|---|---|
| `--kind` | How FROM relates to TO; required unless --undo. |
| `--why` | One or two sentences: what you read six months later, or why a relation is removed. |
| `--undo` `LINK_ID` | Remove this relation instead; an agent removes only an agent's. |
| `--as` `NAME` | Who asserts it; an agent names itself, with Agent or AI in the name. |
| `--session` `SESSION` | The session asserting it; it is recorded as who did. |
| `--dry-run` | Check everything and say what would change, writing nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library review`

`loom library review [OPTIONS] [WORK]`

List what waits for you to review: proposed results and open citation suggestions, one line each with its id.

With WORK, only that work's proposals. Each line ends with the id that `loom library verify` and `loom library discard` take.

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

##### `loom library search`

`loom library search [OPTIONS] TEXT`

Search the library's results for every word of TEXT, ignoring case, best match first; with --pages, its page text.

A word in a result's locator, its local name or its work's title counts three, one in its statement one; a main result (level 1) and each citation of it in your documents count more. **Every answer says how much of the library it could search**, because a search over a partly digested corpus is a search over silence. Page text is mathematics after a text layer, so a page hit is a pointer and never a quotation: read the page with `loom library read`, and quote from that.

| option | description |
|---|---|
| `--pages` | Search the page text of every mapped work, not the results digested from them. |
| `--work` `WORK` | Search only this work; repeatable. |
| `--limit` | Show at most this many hits; everything is still searched. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

##### `loom library update`

`loom library update [OPTIONS] [WORK]...`

Make what a machine can about the cited works: gather the bibliography, look up, fetch, extract digests, map pages.

Each step is a no-op where its work is done, so a second run does only what is new. WORK narrows every step to the works it names (a citekey, a fragment of one or of an author or title, or a result id); naming works leaves gathering out, since it reads the whole bibliography. Looking up and fetching use the network only under `[library] online = true` or `--online`, and an agent only under the config's: it may not grant itself the network. Offline, every local step still runs. Progress shows on stderr.

| option | description |
|---|---|
| `--only` | Run one step: gather (the bibliography, from the landmarks and refs/), resolve, fetch, extract or map. |
| `--redo` | Do the steps again where they are done: ask the lookups again, re-extract, re-map; verified results are kept. |
| `--online` | Let this run look identifiers up and fetch documents, without setting [library] online in config.toml. |
| `--no-candidates` | Fetch only on identifiers an entry declares, never on a lookup's candidate. |
| `--no-compile` | Extract without compiling each paper; its numbering is emulated, and the digest says so. |
| `--dry-run` | Say what each step would act on, from what is on disk; no network, nothing written. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library verify`

`loom library verify [OPTIONS] ID...`

Record that a result's transcription is faithful, or accept a citation suggestion.

A result id promotes a proposal into the digest, or re-verifies one already there: the claim is that this copy is faithful to the paper, never that its mathematics holds, which is `loom accept`. --statement edits the rendering, never the quotation, so the anchor stays re-checkable and both parties are recorded. A suggestion's annotation id (`a-…`) files the work it names in reference-notes.jsonl and resolves it; your bibliography is never touched.

| option | description |
|---|---|
| `--statement` | Your own rendering, replacing the proposed one; one ID only. |
| `--local` | The paper's own name for it, correcting the proposal's (cor-3.2.1); one ID only. |
| `--taxon` | The environment, when --local does not imply it; one ID only. |
| `--as` `NAME` | Who is deciding, when the user config and git do not say. |
| `--yes` | Skip the question; you have read both texts. |
| `--dry-run` | Check everything and say what would be recorded; write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom library why`

`loom library why [OPTIONS] ID`

Show where a result came from, what state it is in and who changed it, then its relations to other results.

Provenance names every party, not just the first: a record that credits an agent with a sentence you wrote cannot be audited. A relation is somebody's reading, asserted and never checked. ID may also be a citation suggestion's annotation id.

| option | description |
|---|---|
| `--depth` | Follow its relations this many hops out. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |
| `--session` `SESSION` | Log this call to the session. |

### Agents

Hand a document to an agent, take its changes back, and the sessions you both work in.

#### `loom draft`

`loom draft [OPTIONS] DOCUMENT`

Draft an agent document NAME from a live working document: flat, in the agent's drafting directory, with every label it defines derived.

A copy step records what each of its nodes began from (book 17.7). Starting a document from an old version of one is `loom history restore`.

| option | description |
|---|---|
| `--ai` `NAME` | The agent document to write, directly in the agent's drafting directory. |
| `--dry-run` | Say what would be written, and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom adopt`

`loom adopt [OPTIONS] DOCUMENT [KEYS]...`

Preview an agent document's changes to the working document it was drafted from, and incorporate them once confirmed; mathematics is never accepted.

The preview is the dry run: without a terminal to confirm on, or with --json or --to, adopt stops there and names the `--incorporate TOKEN` that applies exactly it.

| option | description |
|---|---|
| `--document-changes` | Include proposed prose, preamble and ordering changes. |
| `--document-only` | Include document-level changes while keeping every node version. |
| `--incorporate` `TOKEN` | Incorporate exactly the previously inspected preview. |
| `--to` `FILE` | Write the preview's patch to FILE without incorporating; never among the quilt's sources. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom session`

`loom session [OPTIONS] COMMAND [ARGS]...`

Open, name and follow sessions: the stretch of work an annotation belongs to, and which one is current.

A session has a stable id (`s-2026-09-20-0001`) that never changes and is what records and URLs use, and a title you may change whenever you like. One is active at a time, for you and for any agent working in this quilt, so that a person and an agent at the same job land in the same place.

##### `loom session close`

`loom session close [OPTIONS] [WHICH]`

End a session's current round. With no WHICH, the active one, which then stops being active.

| option | description |
|---|---|
| `--as` `NAME` | Who acts; an agent names itself, including Agent or AI. |
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom session delete`

`loom session delete [OPTIONS] WHICH`

Remove a session from view, or with --purge erase it and everything written in it.

A plain delete is a tombstone: the session stops being shown and every annotation made in it stays in the log. `--purge` is deliberately only here and never in the viewer: it rewrites the annotation log, and what it removes is gone.

| option | description |
|---|---|
| `--purge` | Really erase it, annotations and all. This cannot be undone. |
| `--why` | Why it was deleted; kept on the tombstone. |
| `--as` `NAME` | Who acts; an agent names itself, including Agent or AI. |
| `--yes`, `-y` | Skip the question --purge asks. |
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom session list`

`loom session list [OPTIONS]`

List this quilt's sessions, newest last, with the active one marked.

| option | description |
|---|---|
| `--all` | Include closed and deleted sessions. |
| `--json` | Print as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom session new`

`loom session new [OPTIONS]`

Open a session and make it the active one.

| option | description |
|---|---|
| `--name` `TITLE` | What to call it; default untitled. |
| `--as` `NAME` | Who acts; an agent names itself, including Agent or AI. |
| `--no-use` | Create it without making it the active session. |
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom session next`

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

##### `loom session rename`

`loom session rename [OPTIONS] WHICH`

Change a session's title. Nothing moves: the id is the address and does not change.

| option | description |
|---|---|
| `--name` `TITLE` | The new title. |
| `--as` `NAME` | Who acts; an agent names itself, including Agent or AI. |
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom session say`

`loom session say [OPTIONS] [TEXT]`

Say TEXT in a session's chat, with what you marked since your last message; `-` reads TEXT from stdin.

The same post the viewer's composer makes, for a person and an agent alike: it carries the annotations you made since your last message, and with no TEXT it carries them alone. A `quilt:` or `cited:` link that names nothing the viewer shows is refused; `loom link` prints a correct one. Your own cursor moves past the message when you had read everything before it, so `next` does not hand you your own words.

| option | description |
|---|---|
| `--session` | The session to speak in. |
| `--as` | Who is speaking. An agent names itself, including Agent or AI. |
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom session use`

`loom session use [OPTIONS] WHICH`

Make WHICH the active session, resuming it when it was closed. WHICH is an id, a title, or a unique id suffix.

| option | description |
|---|---|
| `--as` `NAME` | Who acts; an agent names itself, including Agent or AI. |
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom session watch`

`loom session watch [OPTIONS] [WHICH]`

Tail a session: print what lands, until you stop it.

For a person. It delivers nothing and assigns nothing -- it blocks on the log, prints, and keeps a heartbeat so the composer can say honestly whether anybody is listening.

| option | description |
|---|---|
| `--as` | Who is watching. An agent names itself, including Agent or AI. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai`

`loom ai [OPTIONS] COMMAND [ARGS]...`

Set up the agent layer and read what an agent works from: its orientation, its documents and its annotations.

##### `loom ai annotations`

`loom ai annotations [OPTIONS]`

List a session's annotations: id, target, kind, status and the quoted text; `--json` carries each one whole.

An agent re-reading its own annotations is the common case — a re-check resolves what is met and edits what still stands, and needs the ids to do it. The JSON form carries `message`, `payload` and `placement` too, so a re-check can tell what it already said and what it already suggested without reading the log itself.

| option | description |
|---|---|
| `--session` `SESSION` | The session to report on. |
| `--severity` | Only annotations of this severity. |
| `--kind` | Only annotations of this kind. |
| `--status` | Only annotations in this state. |
| `--all` | Include withdrawn annotations, with the reason they were withdrawn. |
| `--json` | Print the annotations as JSON. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom ai discard`

`loom ai discard [OPTIONS] SESSION`

Withdraw a session's annotations, or those matching --before, --by or --target; --undo restores them.

Withdrawing appends an event like any other change, so a sitting's annotations can be withdrawn and restored without anything being rewritten or lost. A withdrawn session is closed, and a restored one opened again.

| option | description |
|---|---|
| `--before` `DATE` | Withdraw every record created before this date (YYYY-MM-DD). |
| `--by` `NAME` | Withdraw every record with an annotation by NAME. |
| `--target` `KEY` | Withdraw every record with an annotation on KEY. |
| `--undo` | Restore the matching records instead. |
| `--dry-run` | Say what would be withdrawn and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom ai drafts`

`loom ai drafts [OPTIONS]`

List each agent document drafted from a working document, and what has moved in that document since.

Before a large instruction, an agent checks its document here: a stale one is refreshed first, or the agent says what it is working against.

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom ai init`

`loom ai init [OPTIONS]`

Write the agent layer: ai/ (orientation, rules, modes), ai/ai-config.toml, CLAUDE.md and AGENTS.md, and the permission files.

The permission files say what agents may run, for Claude Code (.claude/settings.json) and Codex (.codex/rules/loom.rules). Where ai/ exists this refreshes what `loom upgrade` would, keeping an edited mode file and writing the new version beside it; an existing ai/ai-config.toml is the person's and is kept.

| option | description |
|---|---|
| `--skills` | Also write skill stubs and slash commands for Claude Code. |
| `--agent` | The agent a new ai/ai-config.toml names; default every key commented out. An existing one is kept. |
| `--dry-run` | Say what would be written and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom ai orient`

`loom ai orient [OPTIONS]`

Print the orientation documents followed by the quilt's live state, and with --session the end of that session's chat.

This is also how an agent joins a session it did not open: `loom ai orient --session <id>` prints the orientation, the quilt's live state, and the last messages of that session's chat with its command log, which is what a later sitting resumes from.

| option | description |
|---|---|
| `--session` `SESSION` | Attach to this session: also print the end of its chat and its command log. An id, a title, or a unique id suffix. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom ai refresh`

`loom ai refresh [OPTIONS] DOCUMENT`

Update an agent document from the working document it was drafted from, keeping its outstanding proposals.

| option | description |
|---|---|
| `--dry-run` | Say what would be refreshed and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### Publish

Build the site and the PDFs, serve them, and exchange sources with a workspace.

#### `loom build`

`loom build [OPTIONS]`

Scan, derive, render, and publish build/. Exit 1 if any error-severity diagnostic exists outside the works nothing cites (the build is still published).

Rendering is cached per fragment by its inputs, which include loom's own version and, in a checkout, loom's code; --force renders everything regardless, and tries again every block whose SVG failed before. Only errors are listed; `loom lint` lists every diagnostic.

| option | description |
|---|---|
| `--keys` | Limit rendering to these keys and their masters; the manifest is always complete. |
| `--force` | Render every fragment again, ignoring the cache and retrying remembered SVG failures. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom serve`

`loom serve [OPTIONS]`

Watch, republish, and serve arras at / and build/ at /build/ until interrupted.

| option | description |
|---|---|
| `--port` | Port to listen on; fails if busy. |
| `--open` | Open the browser. |
| `--no-compile` | Never run latexmk after a change. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom compile`

`loom compile [OPTIONS] [TARGET]`

Run latexmk from the root into build/<stem>/ for a master (default: the default master), or for a key.

Compiling a key builds the document of its closure and runs latexmk on that, so `--with` previews a proposed diff and `--draft` a node that has no id yet: neither writes into the quilt, and a failure names the digests whose packages are missing.

| option | description |
|---|---|
| `--engine` | Override the document's engine. |
| `--with` `FILE` | Substitute a unified diff, a .tex file, or an annotation's proposed text for KEY's text; the quilt is not touched. |
| `--draft` `FILE` | Compile a node file not yet in the quilt. |
| `--session` `SESSION` | Log this call to the session. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom check`

`loom check [OPTIONS]`

Lint, then compile every document, then the closures asked for. Exit 1 on any failure; the CI command.

`loom lint` is the same check without LaTeX.

| option | description |
|---|---|
| `--closures` | Which statements' closures to compile after the documents: all of them, or none; stale compiles none yet. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom sync`

`loom sync [OPTIONS] COMMAND [ARGS]...`

Exchange the paper's sources with a document workspace, such as an Overleaf project.

##### `loom sync documents`

`loom sync documents [OPTIONS] [add|remove] [DOCUMENT]`

Change which documents publish to the workspace, without publishing.

| option | description |
|---|---|
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom sync fetch`

`loom sync fetch [OPTIONS]`

Fetch document workspace changes for Incoming review without changing author files.

| option | description |
|---|---|
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom sync incorporate`

`loom sync incorporate [OPTIONS]`

Apply the fetched pull to the quilt's files, stamping first each document it reaches; Incoming does the same.

| option | description |
|---|---|
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom sync init`

`loom sync init [OPTIONS] URL`

Pair the quilt with a document workspace, such as an Overleaf project's Git URL.

Loom clones the workspace into .loom/workspace/ and runs Git only there; the quilt need not be a repository, and its own is never touched.

| option | description |
|---|---|
| `--publish-main` | The main document's path in the workspace, when it differs from the quilt's. |
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom sync publish`

`loom sync publish [OPTIONS]`

Prepare the selected documents' sources as a workspace revision, check each compiles, and stamp each as published.

| option | description |
|---|---|
| `--push` | Push the prepared revision to the document workspace. |
| `--dry-run` | Say what would change and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

##### `loom sync status`

`loom sync status [OPTIONS]`

Show the document workspace's revisions, the selection and what is prepared; --patch prints the incoming diff.

| option | description |
|---|---|
| `--patch` | Print the incoming revision as a patch against the quilt's paths instead. |
| `--to` `FILE` | With --patch, write the patch to FILE, a new file outside the quilt's sources. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### Upkeep

Keep loom's own files current, and documents live.

#### `loom upgrade`

`loom upgrade [OPTIONS]`

Refresh loom.sty, ai/orientation.md, ai/README.md, the vendor files, and unedited mode files; report edited ones.

| option | description |
|---|---|
| `--dry-run` | Say which files would be refreshed, and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom live`

`loom live [OPTIONS] FILE`

Make a superseded document live again, so that it defines its nodes once more.

| option | description |
|---|---|
| `--dry-run` | Say what making it live would define twice, and write nothing. |
| `--json` | Print the report as one JSON object (book 12.9). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

## 12.9 Machine output

**[decided]** Every `--json` output is a single JSON object, the envelope (DR-329-ikmartin): `verdict` (the text's first line), `ok` (nothing is wrong), `exit` (the process's exit code), `groups` (each `{heading, count, items, next?}`, every item `{text, key?, fixes?}` and never cut), `notes` (what went to stderr), `dry_run` when the run was one, and beside them the command's own data under its keys. A list that used to be the whole document is a named key: `lint --json` puts its diagnostics under `diagnostics`. Shapes reuse the manifest's (specs/manifest.md) wherever the same data appears: `status --json` uses the `keys` shape; `deps --json` and `downstream --json` use the `edges` shape; `search --json` puts its matches under `matches`, each in the `search` shape plus `file`, `line` and `url`. New shapes are documented here before they exist.

**[decided]** `deps --json` carries `relations` beside `statement`, `proof` and `closure`: both directions of every `see:` declaration touching the key, as `{"key": ID, "kind": "see"}`, in target order. In the printed form they are a final section headed "see also (not a dependency):", after the edge lists, so that nothing reads them as dependencies. `downstream` does not list relations: it reports consequences, and a relation has none.

## 12.10 Environment variables

**[decided]** `LOOM_QUILT` (quilt root, overrides discovery); `LOOM_SESSION` (default for `--session`); `LOOM_FIXED_TIME` (fixture generation: all timestamps take this value); `LOOM_PAPER_FIXTURES` (tests: directory of arXiv sources for the paper tier); `LOOM_ARRAS_BUNDLE` (a viewer bundle directory that overrides the installed `arras` package and the vendored copy, 12.5); `LOOM_SVG_KEEP` (debugging: a directory that receives every fallback document that failed to compile, DR-79). The test shim reads `FAKE_TEX_LOG`, `FAKE_TEX_FAIL`, and `FAKE_TEX_FAIL_MATCH`. No other variable is read (M7).

## 12.11 Withdrawn commands

For readers of earlier design notes: `impact` became `unravel`; `dependents` and `closure` folded into `deps`/`unravel`; `resolve` folded into `search --json`; `tag` became `id`; `state set`/`state refresh` became `accept`/`status`; `ref use` disappeared when digests became LaTeX; `ai finish`, `ai resume`, `ai list`, `ai restore` folded into `session close`, `ai orient --session`, `ai runs` and `status --runs`, and `ai discard --undo`; `digest export` is `cp`; `bundle --for-review` is the modes' business; `new --in FILE` is `new --print`; `assemble` is `linearize`, which takes `--to` and knows the identity rule (DR-139); `atomize --ignore-src` is gone, the history recording that a spine superseded its source and `--retire` moving the file when asked (DR-138); `ai runs` is `session list [--all]`, which listed the same sessions; `ai promote` is gone entirely: a drafted node is previewed in arras and pasted by the author with an id from `loom id --next` (DR-140), and a digest is produced by `loom digest extract` rather than typed by an agent, so there is nothing left for it to copy (DR-173). `loom refs crawl plan`, `fetch` and `status` went to weft with the rest of the crawl, and the `[crawl]` table with them (8.13, DR-144). `loom bundle` is gone: reading a key and its dependencies is `loom source KEY --closure`, which prints, and checking that a proposal compiles is `loom compile KEY --with FILE`; the document itself is still written under `build/bundles/` by the compile that needs it (DR-148). `loom ai start` no longer launches an agent and `[ai] agent` and `--no-launch` are withdrawn with it (DR-149). `loom digest fetch` became `loom refs fetch`, now `loom library update`'s fetch step, which also fetches on a resolver candidate and on a bibliography `url` that is a PDF, and records which identifier a source came from; `loom library update` runs it with every other mechanical step (DR-176, DR-181). There has never been a `loom label`: the command that writes ids is `loom id`. `comment` is `annotate`, `ai findings` is `ai annotations` and `refs note` became `refs cite`, now `library verify` and `discard` on the suggestion: an annotation is the one noun for the record, and `note` names only a kind (DR-292-ikmartin).

The command surface of plan 0.18.4 (DR-330-ikmartin): `unravel`, `reach` and `pop` are `downstream`; `delete`, `rm` and `remove` are answered with a refusal (7.9); `review` is `build`, which publishes, with `status --stale`, which lists; `check --no-compile` is `lint`; `check --bundles` is `check --closures`, and the diagnostic `loom:bundle-failed` is `loom:closure-failed`; `ai start` is `session new --name`; `ai name` is `session rename --name`; `agent check` is `doctor --agents`; `ai check` is withdrawn until a write can be attributed to an agent by something other than its time (11.8); `session send` is `session say`; `sync patch` is `sync status --patch`; `history`'s words are its subcommands `show`, `restore` and `verify`, each taking only its own flags; `fork --as` is `fork --name`; `atomize SRC DEST` is `atomize SRC --to DEST`; `--author` is `--as` outside `refs`, and `ai discard --author` is `--by`; `init --author` is gone, the reviewer's name coming from Settings or git (4.3).

The library of plan 0.18.5 (DR-331-ikmartin): `loom refs` and `loom digest` are `loom library`. `refs coverage`, `refs match`, `refs cite --list` and `refs build`'s report are bare `library [WORK]`; `refs build`, `refs scan`, `refs resolve`, `refs fetch`, `refs map` and `digest extract` are `library update`, a step of it alone with `--only`; `refs add` and `refs ingest` are `library add`; `refs verify` and `refs cite --accept` are `library verify`; `refs discard` and `refs cite --reject` are `library discard`; `refs unreadable` and `refs forget` are `library ignore`; `refs page`, `refs overview` and `refs path` are `library read`; `refs find` and `refs grep` are `library search`; `refs why` and `refs links` are `library why`; `refs link` and `refs unlink` are `library relate` and `relate --undo`; `refs recheck` is `library check`; `refs propose`, `refs locate` and `refs drop` are `library propose`, `locate` and `drop`; `digest import` is `library import`, its `--as` now `--name`. `--fetch` and `--resolve` are `--online`, `--refresh` and the `--force` of `build` and `map` are `--redo`, `--reason` is `--why`, `--author` is `--as`, and `[refs] fetch`, `resolve` and `contact` are `[library] online` and `contact`. The write API's `refs-cite`, `digest-verify` and `digest-discard` are `library-cite`, `library-verify` and `library-discard`, their `reason` now `why`.

# The open quilt: a study

Written 2026-10-30. It draws on the ideas in `docs/long-prompts/ideas.md` that ask for a quilt laid out by the person who owns it (its second and third items), on the author's answers in the conversation that produced this study, and on the code as it stands, which a read-only map of the repository on the same day measured ("What the code says"). It is current thinking for a plan to take over, not a decision. The author is learning quantitative finance with an agent's help in the quilt `~/quilts/quant`, which is the Learner's test of this study, as `~/quilts/relloc` is the Author's.

## The question and the stance

Can a quilt be a directory the person lays out as they like, holding whatever they work with (LaTeX, Markdown, HTML, PDFs, notebooks), with loom a layer over it rather than its shape?

The answer proposed here is yes, and most of the change is loom doing less. Loom stops naming the person's directories, stops deciding where a document may live, hands the directory of a shared paper back to the person, and lets an agent write wherever the person has not said no. What loom adds is mostly display: more formats shown in the viewer, and quotable there. What loom understands does not widen. The graph, acceptance and the rest of the trust machinery stay on LaTeX (P1).

Loom does not learn what a course is. How a course is designed and carried out (its topic list, lessons, problem sets, progress, flash cards) belongs to the person and their agent, in whatever files they choose; loom shows those files and makes the links in them work. That is the present need, not a boundary for all time: if a course later needs loom to know something, it is reconsidered then.

**Evidence.** The quant quilt's `syllabus.md` looks like loom: ids, prerequisite links, a checker script, a preview applied after approval. But its agent was told to read loom's orientation before anything else, so its shape shows what an agent makes inside loom, not what a course needs. It is used here only for the friction it shows (see "Found along the way"). The case rests on what the author asked for, on what a learner does, and on what the code says.

## What the code says

Paths below are under `loom/src/loom/` unless they name `arras/`, `docs/` or `loom/tests/`.

### Who owns the layout

Nobody does. About forty modules encode it. Some paths have a constant (`STORAGE` and `storage_root` in `refs/pages.py`, `log_path` in `records/log.py`, `notes_path` in `refs/notes.py`, the sessions' `DIR` in `sessions.py`, the `history_dir` property in `scan/quilt.py`). Others are hardcoded at every use: `nodes/` in five modules, `ai/` in eight, `build/` in twenty-two, and `retired/`, `notes/` and `digests/` itself in several each. `[quilt] history` is a setting, but four copies ignore it (`records/snapshots.py:12`, `records/lastseen.py:28`, `ai/layout.py:68`, `cli/quilt.py:167,180`).

### Documents, and how they are named

- **Found by directory.** A file is a master only when its parent is exactly `[quilt] drafting` or `drafting_ai` (`scan/scan.py:202-216`); anywhere else it gets `loom:documentclass-outside-drafts`. The same rule is restated in six more places (`records/store.py:90-92`, `cli/_common.py:159-167`, `adopt.py:666`, `cli/paper.py:262`, `cli/history_cmds.py:133,1134`, `sync.py:592`).
- **A role read from the directory.** `document_role` returns the strings `drafting` and `drafting-ai`, compared at 22 sites in 7 modules and published as the manifest's `masters[].directory` (`render/manifest.py:324`), which six viewer files read (`arras/src/lib/shell/Column.svelte`, `shell/views.ts`, `workspace/history.ts`, `workspace/compare.svelte.ts`, `routes/review/+page.svelte`, `manifest/types.ts`). Which copy a copy is of comes from the history (`copy_of`), not the directory.
- **Named by stem.** Two documents may not share a stem (`loom:document-stem-taken`, `scan/scan.py:122-136`), because the stem is the key of the build directory `build/<stem>/`, the fragment `fragments/masters/<stem>.html` (`render/build.py:202`), the `.aux` lookup (`tex/aux.py:65-72`) and the viewer's route `/master/<stem>` (`arras/src/lib/nav.ts:14-17`, resolved back by `itemFromPath` in `workspace/item.ts`). In an open layout, two `main.tex` files in two directories are the normal case, and they collide.

### Compiling

The quilt root is the compile base everywhere. Every document compile goes through one `compile_tex` (`tex/runner.py:136`), with the root as its working directory (`:151`). The root is also the base of every resolver:

- `\input` and its relatives, through `resolve_inclusion` in `scan/expand.py`, called from the scanner's `expand_master` and from `flatten` in `reshape/linearize.py`, which has 22 callers;
- packages and classes, `_local` in `scan/preamble.py`;
- the bibliography (`refs/scan.py:302-323`), graphics (`render/assets.py:15-21`) and the `.aux` lookup;
- the SVG fallback, which sets `TEXINPUTS` to the root (`render/fallback.py:183-186`).

Three facts make a change cheaper than this list suggests. The resolvers already take a base directory as an argument. Digest extraction (`digest/extract.py`) and import (`cli/paper.py:282`) already compile a paper from its own directory with them. And the fake TeX the tests use resolves `\input` from its working directory (`loom/tests/fake_latex/fake_tex.py:47-60`), so the suite already models a compile from wherever it is run.

Two kinds of derived text resolve today against the root, wherever they sit: landmarks, read from the history (`scan/scan.py:144-154`, `render/canon.py`), and agent copies, which are flattened but keep `\includegraphics`, `\bibliography` and `\usepackage{loom}` as written (`reshape/copy.py:46-51`).

### `[quilt] main`

`[quilt] main` defaults to `<drafting>/main.tex` (`scan/quilt.py:95`) and names the default master, which 20 modules use for LaTeX work: the preamble and engine of closures, the order of taxa, the acceptance context, the serve compile. A front door that may be a Markdown or HTML file cannot share that setting.

### The macros

`loom.sty` is written by `loom init` (`cli/quilt.py:177`), refreshed by `loom upgrade` (`refresh_sty`, `ai/layout.py:109-138`) and checked by `loom doctor` (`doctor.py:593-601`). `\usepackage{loom}` is added on import and restore (`reshape/canon.py:94-96`), forced into closure preambles (`tex/bundle.py:40-41`), and keyed on by two lints (`scan/lint.py:353-380`). The marked block `loom history show --plain` writes in its place (`reshape/linearize.py:110-133`) is the reusable piece.

### Where documents may be written

`destination()` (`cli/_common.py:130-180`) knows two homes, the drafting directories, and `import`, `history restore`, `adopt --to` and `draft --ai` each refuse anything else. `loom new` writes `nodes/<id>.tex` (`cli/nodes.py:118`); atomize and fork write `nodes/<id>` files and `\input{nodes/<id>}` lines (`reshape/atomize.py`, `reshape/fork.py:190-197`). Import scatters a paper's figures and styles at the root while its draft goes to `drafting/` (`reshape/canon.py:36-65`), so the draft compiles only from the root.

### Sync

Sync is about 2,700 lines: about 1,670 in loom's source (`sync.py` and `cli/sync.py` whole, the rest in parts), about 850 in its tests, about 110 in the viewer and about 110 in the documents. Its error type, `SyncError`, is also adoption's: 93 uses in 10 modules outside `sync.py`, most of them adoption. `incorporation_review.py`, `review_origins.py` and the viewer's `IncomingMath.svelte` serve both. Every git call but the first clone goes through one function, `workspace()` (`sync.py:174-186`), and publishing and fetching move only loom's own refs (`refs/loom/publication`, `refs/loom/incoming/*`) through a temporary index, never a working tree. Neither of the author's quilts has a sync record.

### The agent layer

- **Recognising an agent copy** happens at three points by location: `document_role`, master discovery, and `.loom` in the scanner's `SKIP_DIRS` (`scan/source.py:14`), so nothing under `.loom/` is scanned today except what is read on purpose, as landmarks are.
- **The boundary** is generated in `ai/layout.py`: the writes (`AGENT_WRITES`, plus `drafting_ai` added by `agent_dirs`), the read-only directories and files, and `permissions_json` (`:220-241`). The one-line instruction file is kept by `ensure_root_line` (`:301-321`), which matches the old line exactly, so changing the line's text appends a second line to an existing quilt's file rather than replacing it.
- **Section drafts** compile against a copy of the whole quilt root, skipping only `.loom` and `drafting_ai` (`section_drafts.py:146-156, 226-262`). In an open quilt that holds notebooks and data, that copy grows with the project.
- **`--quilt`** is written into each client file as the quilt's absolute path (`ai/clients.py:105`). `loom mcp` does not need it, since it walks up from its working directory as every command does (`scan/quilt.py:145-153`). But applications configured outside the quilt (`ai/clients.py:54-63`) have no project directory, so dropping it is a decision per client. `loom doctor` already warns when a client file differs from what loom would write (`doctor.py:532-537`).

### The viewer

- **No item kind for a file.** A pane shows a document, a work, a node, a context, a session or a page (`arras/src/lib/workspace/item.ts:10`), and the one page is the research state. No pane shows an arbitrary file, Markdown, HTML, a PDF that is not a library work, or an image.
- **No frame, and HTML in the viewer's own origin.** There is no iframe in the viewer, and the dialect forbids iframes and scripts in fragments (`docs/specs/dialect.md` §3). Rendered bodies and fragments are inserted with `{@html}` or `innerHTML`, unsanitised; the publisher escapes raw HTML when it renders Markdown (`records/store.py:911-939`).
- **The write API trusts its origin.** `GET /_api` hands out the write token with no origin check (`render/serve.py:344-350`). `/build/*` and `/digests/storage/*` are served from the same origin with a type guessed from the file's extension (`render/serve.py:176-201`). Author acts trust the declared author, and none means the author's own click (`render/api.py:590-603`). See "Found along the way".

### Tests and fixtures

In loom's tests, 865 lines in 69 files name `drafting/`, `nodes/`, `refs/` or `loom.sty`, and the 16 fixture quilts carry `drafting/` and `loom.sty`. The generator (`loom/scripts/gen_quilts.py`), `docs/specs/tools/refresh-fixture.sh` and the spec fixture (137 lines with `drafting/`) hardcode the layout. In the viewer's tests, 111 vitest lines in 11 files and 33 end-to-end lines in 10 files name the drafting directories, and 149 lines in 26 files use `/master/<stem>` routes.

## Today's root, entry by entry

`loom init` and `loom ai init` between them put twelve visible entries and six hidden ones at quant's root, beside the one file the person's work has produced so far, `syllabus.md`. More appear with use (`annotations/`, `build/`, `research-state.md`).

| entry | what it does today | proposed |
|---|---|---|
| `config.toml` | marks the quilt and holds its settings | stays, the one file loom puts in view |
| `README.md` | explains the layout | a tutorial `loom init` writes, safe to delete |
| `drafting/` | holds the live documents (`[quilt] drafting`); placement declares liveness (DR-132) | deleted; a document may be anywhere |
| `drafting-ai/` | holds agent documents (`[quilt] drafting_ai`) | moves into `.loom/`; each copy is shown beside the document it copies |
| `nodes/` | where `loom new` writes | deleted; `loom new` writes beside the default document |
| `refs/` | the drop folder for PDFs and `.bib` files | deleted; a PDF anywhere becomes a work with `loom library add`, and a bibliography is wherever a document's `\bibliography` names it |
| `digests/` | digests and the store of works | moves into `.loom/` |
| `annotations/`, `reference-notes.jsonl` | the annotation log; the library's notes | move into `.loom/` |
| `ai/` | orientation, rules, modes | moves into `.loom/`; agents already reach it through `loom ai orient` and `loom ai mode` |
| `research-state.md` | the research state | `[quilt] research_state` still places it; its default is open |
| `loom.sty` | the three macros | deleted; a marked block in the preamble instead |
| `build/`, `retired/` | derived output; the sources `atomize --retire` sets aside | move into `.loom/` |
| `notes/` | a directory loom never scans | the special case goes; the person ignores what they choose |
| `.gitignore` | loom's ignore lines, most naming loom's directories | shrinks: `.loom/` carries its own |
| `.loom/` | history, ledger, sessions, the Overleaf clone, `since` markers | gains everything above and loses the clone, since sync works in a directory the person names |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | one line each, telling an agent to orient | stay: each client reads its file at the root, and only `loom ai init` writes them |
| `.claude/`, `.codex/`, `.gemini/`, `.cursor/`, `.mcp.json` | client configuration | stay, already hidden |

A fresh quilt is then `config.toml`, `README.md` and `.loom/`, plus the agent files once `loom ai init` has run. The hidden directory holds shared records (history, ledger, annotations, digests) beside local ones (build output, `since` markers, `serve.json`), so its own `.gitignore` says which is which.

`[quilt] main` keeps its meaning, the default LaTeX master, and stops defaulting to a path under `drafting/`. The front door, the file a quilt opens on when the browser remembers no place to return to, is a separate setting (its name is open; `home` is a candidate), because it may be Markdown or HTML.

## Documents and compiling

**A document may be anywhere.** A file with `\documentclass` is a document wherever it sits, and is live unless it is ignored or superseded. DR-132 made placement the declaration of liveness because `canon/` held the frozen versions of a paper in the same tree. `canon/` is gone, landmarks live in the history (plan 0.17.3), and a superseded document is a recorded state, so placement no longer declares anything the records do not. The seven restatements of the drafting-directory rule become one. Ignoring is the one declaration left: `% !LOOM ignore` exists already, and the scanner reads only `.tex` files, so an ignore file would matter mainly to the viewer's tree (see the open questions). It would be a different list from the agent deny list below, since "loom does not read this" and "an agent may not write this" are two ideas (K2).

**A document is named by its path.** The stem stops being a document's key, because in an open layout stems repeat. Every structure keyed by the stem (the build directory, the fragment, the `.aux` lookup, the manifest's `pdf`, the viewer's route) is keyed instead by the document's path without `.tex`, kept as a path (the author's choice, 2026-10-30): `paper/main.tex` builds into `build/paper/main/`, its fragment is `fragments/masters/paper/main.html`, and the viewer opens it at `/master/paper/main`, so the address reads as the Docs tree does. Two such names cannot collide, so `loom:document-stem-taken` goes and no lint replaces it. `masters[].directory` goes too: whether a document is an agent copy is `copy_of`, which the manifest already publishes from the history. This is a change in both codebases and in the spec fixture, and the largest single change in the study after the compile directory.

**A document compiles from its own directory** (the author's choice, 2026-10-30). That is what LaTeX and most editors expect, and what an Overleaf project with its main file at the top already does. P12 changes from "compiles from the quilt root" to "compiles from its own directory, on any TeX, on Overleaf".

- **The change is not small.** A per-document base has to reach `compile_tex`, the scanner's expansion, `flatten`'s 22 callers, the package, bibliography, graphics and `.aux` resolvers, and the SVG fallback's `TEXINPUTS`. A resolved path is still returned relative to the quilt root, since the scanner's file table is keyed that way.
- **The machinery exists.** The resolvers take a base already, and digest extraction and import already compile a paper from its own directory with them, so the work is threading the right base to each caller rather than writing new resolution.
- **`..` stays refused,** because Overleaf cannot follow it. The cost is that documents in sibling directories cannot share a file; documents that share files sit together.
- **Derived texts compile from their source's directory.** A landmark and an agent copy both live in `.loom/`, and each compiles from the directory of the document it came from, so its figures, packages and bibliography resolve as the source's do.

**The macros go inline.** `loom.sty` holds three `\providecommand`s (`\uses`, `\incomplete`, `\nest`). It sits at the root only because a document that loads it compiles from the root and P12 rules out `TEXINPUTS`; once documents compile from their own directories, it would have to sit beside each one. Loom already writes the same macros as a marked block, the one `loom history show --plain` puts in place of `\usepackage{loom}`. So a document loom starts, imports or restores carries the block in its preamble, closures copy it with the preamble rather than forcing the package in, the two lints key on the block, and no file is needed. The cost: a change to the macros reaches a document only as a patch the person applies (P7), where today `loom upgrade` rewrites one file. Because the block is marked, `loom doctor` can find an old one and print that patch.

**What else moves with it.**

- **`loom new`** writes `nodes/<id>.tex` in the default document's directory, so the `\input{nodes/<id>}` line it suggests keeps working relative to the document; `--to` names another place. Atomize and fork do the same relative to the document they work on.
- **Import** writes the paper's draft and its figures and styles together, in a directory of their own, so the draft compiles there as it did in the paper's archive.
- **Agent documents written from scratch** (`loom draft --ai NAME --new`, taken in with `loom adopt NAME --to FILE`) exist because an agent could write nowhere outside `drafting-ai/`. With the deny list below, an agent creates a file wherever it may, so they probably go.
- **Section drafts** take their context from the document's directory, not a copy of the whole quilt.
- **`loom:no-live-document`** stops speaking of a drafting directory.

## What the viewer shows

**Docs is the project's tree,** the person's directories and files with loom's hidden, each directory collapsing and expanding as in VS Code's explorer, and it is the working view. It opens on the front door when the browser remembers no place to return to.

Every file sits in one or more of four layers. Each layer holds more formats than the one below it, and loom requires no layer of any file:

| layer | what it means | formats |
|---|---|---|
| shown | the viewer displays it | LaTeX documents, Markdown, HTML, PDFs, images; anything else opens in its own application |
| linkable | a link names it and a place in it | any shown file: a heading, a page, a block |
| quotable | a person or agent can attach something to a place in it | text, by a quoted passage; PDFs and images, by a region |
| understood | ids, edges, closure, computed states, acceptance | LaTeX only |

`links.py` already holds the rule that relates the first two layers: only what the viewer can show is linkable. It refuses an included file today because the viewer shows no file on its own; a file item kind changes that.

- **A new item kind, the file,** opens any shown file in a pane, beside today's document, work, node, context, session and page.
- **Markdown** is rendered by the publisher the way pages and messages are (`render_markdown` in `records/store.py`: CommonMark with tables, `$…$` mathematics, and `quilt:` and `cited:` links). Raw HTML in it stays escaped, as it is in pages and messages; a person who wants raw HTML writes an HTML file.
- **HTML** is shown in a sandboxed frame, and it is served from somewhere that is not the viewer's origin, or under `Content-Security-Policy: sandbox`, so that it has an origin of its own. A sandboxed frame alone is not enough: the same file opened directly at its address would run in the viewer's origin, where it could read the write token and accept as the author. The dialect's rule against iframes keeps holding for fragments; the frame belongs to the file item, not to rendered mathematics.
  - **Embedded content,** a video among it, comes with HTML and needs nothing of its own. It needs the network, so a viewer working offline shows the page without it.
  - **Links out of the frame:** a `quilt:` link inside it reaches the viewer through a bridge that can only open things, never write.
  - **Quoting:** the viewer puts the page's text into the frame itself, so it can add a small script that reports a selection back.
- **PDFs and images** are shown as files. A PDF becomes a work in the library, with page text and locators, only when the person adds it; until then pdf.js shows it as the viewer shows a work's PDF today.
- **Notebooks:** whether the viewer renders a notebook's saved cells and outputs read-only, or only opens it in the person's application, is open. Loom runs nothing either way (running code is deferred).
- **Other applications** are reached by a link that opens them, such as an "open Anki" link in the day's list. How such a link names an application (its own URL scheme, or a control `loom serve` offers locally) is open. Whether Anki on the desktop registers a URL scheme has not been checked. An agent with its own access to Anki reads and writes the deck, and loom needs to know nothing about Anki for that.
- **Links in from outside,** a web address that another tool (an Anki card, say) could open at a result, are not needed now and are not proposed here. A way in for anyone building on loom partly exists already: the build interface and the write API are specified (P11), and the MCP server serves `quilt:` addresses.

## Where agents write

Today an agent may edit its session's directory, `build/` and `drafting-ai/`. It is denied the quilt's other directories, its records, the research state, and every `.tex`, `.sty` and `.bib` at the root; `ai/layout.py` generates both lists.

Only Claude Code's permission file restricts which files an agent writes. In the MCP variant, loom's Codex rules forbid the `loom` and `rm` commands and nothing else, and the Gemini and Cursor files configure the MCP server only. So the file boundary already holds for just one client of four. The boundary that holds for all four is loom's own refusal of the author's acts (K5).

**Proposed: a deny list in the config.** It holds gitignore-style patterns naming where an agent may not write; everywhere else is open.

- **The default:** a fresh quilt's list protects `.loom/` and `config.toml` only (the author's choice, 2026-10-30). The person adds a paper's directory when they want it protected.
- **Enforcement:** loom generates the list into each permission file a client has. The orientation gives every agent the list and says plainly which clients enforce it, so a list that only asks never reads as one that guarantees (P15).
- **The instruction line:** the one-line `CLAUDE.md`, `AGENTS.md` and `GEMINI.md` change with it. `ensure_root_line` matches the old line exactly, so it has to recognise the old line and replace it, or a quilt keeps both.
- **The setting's name** is open.

The list decides which of two ways of contributing applies to a file:

- **Open files** are edited in place, and Review shows what changed (next section).
- **Protected files** are copied and adopted, as today. `loom draft DOC --ai NAME` makes the copy in `.loom/`, where the scanner reads it on purpose as it reads landmarks; the viewer shows it beside its source by `copy_of`; and `loom adopt` takes it in.

The Author keeps everything they have now, at the cost of one line naming their paper. In-place edits to mathematics are also less dangerous than they sound. Acceptance holds hashes of a key's text and its closure, so an agent's edit to an accepted result shows as stale, with its cause, whoever made the edit (P3, P15).

## Review as the meta view

Docs is where the person works. Review is where they see what has changed or is waiting on them, and keep it or throw it away. Its sections, as proposed:

- **Changes to open files** since the person last looked, each kept or undone, with who made it where loom knows.
- **Agent documents** to adopt, and **pulls** from the Overleaf directory to incorporate, as today.
- **Suggestions** waiting to be applied, and **library proposals** waiting to be verified.
- **Acceptance** of the mathematics, kept apart from the rest. "Accept" means only that a key's mathematics is right; keeping an edit gets a verb of its own (K7).
- **Sessions, History and Problems,** as today.

Pulls stay in Review for as long as sync does (see "Overleaf: backing off").

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

This part adds nothing. It hands the person the Overleaf directory now, and may later hand them the syncing too.

### Now: sync works in a directory the person names

The person makes a directory, clones their Overleaf project's git repository into it, and names it to loom with `loom sync init DIR` (the author's choice, 2026-10-30). Loom stops cloning into `.loom/workspace/`. Everything else in sync carries on as it works today: publish, fetch, review in Incoming, and incorporate, with loom running git in that directory as it runs it in its clone now.

Running git in a directory the person owns is safe with the existing machinery, because of how it already works. Publishing builds its commit with a temporary index (`GIT_INDEX_FILE`, `hash-object`, `commit-tree`) and moves only loom's own ref, `refs/loom/publication`; fetching moves only `refs/loom/incoming/*`. Neither touches the directory's working tree or its checked-out branch. `sync publish --push` sends the publication, so after a push the person's own branch lags the remote until they pull.

What changes in the code is small:

- **`configure`** (`sync.py:296`) checks the named directory (a git repository, with the Overleaf project as a remote) instead of cloning, and never replaces or removes it. Today it removes an existing clone and clones again, which is right only for a directory loom owns.
- **`workspace()`** (`sync.py:174-186`), through which every git call but the clone already goes, returns the directory the sync record names instead of the constant `WORKSPACE`.
- **The guards stay:** the directory may not be the quilt's own repository, nor hold a quilt.
- **Every tree walker skips the directory:** the scanner (`skipped_dirs`, `scan/scan.py:139-141`), the watcher, section drafts' context and the importer's mirror. Inside the quilt, the directory holds copies of the quilt's own sources, so scanning it would define every id twice and leave every key conflicted. Today's clone escapes that only because `.loom/` is skipped.
- **The `.loom/workspace/` lines** in `gitignore.py` and the init asset go.

Sync keeps following the documents it publishes. When documents may live anywhere (phase 2) and compile from their own directory (phase 3), its master rule and its projection change with them.

### Later: backing off fully

Once a document can live in the Overleaf directory itself and compile from it there, the person can work in that directory directly, pulling and pushing themselves. Loom shows it like any other directory, and the paper compiles in loom as it does on Overleaf. Sync then has nothing left to project. Whether to delete it at that point is a later decision, and the rest of this section is what deleting it would mean.

**What would go,** about 2,700 lines:

- `.loom/workspace/`, loom's own clone, and `loom sync` with `init`, `documents`, `publish`, `fetch` and `incorporate`: `sync.py` and `cli/sync.py`, and `loom/tests/unit/test_sync.py`.
- The source projection, and the review origins kept for pulls (the `pull:` rows of `.loom/review-origins.json`).
- Pulls in Review's Incoming: `attach_incoming` and its helpers in `render/incoming.py`, `prose_sections` and `attach_prose` in `render/prose_changes.py`, and the viewer's `IncomingPull.svelte` and `m.incoming` branches.
- The write API's `sync-preview` and `sync-incorporate`, and the manifest's `incoming` and `kind: "workspace"` fields.
- The invariant "Sync never writes to the quilt's own repository", since loom would then run no git that writes. `sync publish --push` and `sync incorporate` would leave the list of the author's acts.

**What would stay:** `SyncError` would be renamed to an error of incorporation, since adoption raises it at 93 sites; `incorporation_review.py`, `review_origins.py` and `IncomingMath.svelte` keep their adoption halves.

What each job of the projection would become:

| job | today | after |
|---|---|---|
| keeping loom's files out of Overleaf | the projection copies only the sources | loom's files are in `.loom/`, and the macros are a block in the preamble |
| paths | documents compile from the quilt root, Overleaf compiles from the project's root | both compile from the document's directory |
| coauthors' changes reviewed before they land | Incoming, then `sync incorporate`, which stamps first | lost: `git pull` writes them; every accepted key a coauthor changed shows as stale with its cause, and git keeps the old text |
| a landmark of what was published | `publish` stamps each document | `loom stamp` when the person wants one, or their commits |
| a coauthor's rename | recorded as a move | `document-gone`, with `loom mv` as its fix |
| agents and the paper | agents never wrote the author's files | the deny list: protect the paper's directory, and agents work on copies |

**The loss, stated plainly:** with sync deleted, loom would no longer review coauthors' changes before they land. Nothing unchecked would look checked all the same, because staleness is computed from the text (P3, P15), and loom would write no author file in any of it (P7). DR-105's "a quilt is not a repository unless the author asks" would then hold more firmly than before, since loom would write to no repository at all.

**A nested repository,** now and later. If the quilt is itself a git repository and the Overleaf directory sits inside it, that directory is a repository inside the quilt's, and a coauthor who clones the quilt does not get the paper unless the person makes it a submodule. That choice is the person's; loom does not need to care.

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
- **Frozen records that become history:** DR-132's placement rule, DR-23's masters directory and compile from the root, and DR-28's `loom.sty` at the root.
- **The interface:** documents are named by path in the manifest and the viewer's routes; `masters[].directory` goes; a file item kind arrives.
- **Documents that change:**
  - `docs/design/`: `model.md` (the quilt, documents, the viewer's frame, coauthors), `agents.md` (what an agent may write) and `invariants.md` (sync's git runs only in the directory the sync record names, where today it says loom's own clone);
  - `docs/specs/`: `source-contract.md` §1, `manifest.md` (§1, §2, §2a), `write-api.md` (`adopt-start`'s destination), `diagnostics.md` (the drafting-directory codes, `loom.sty`'s), `dialect.md` §3 (frames belong to file items) and `fixture.md`;
  - the init assets, `loom upgrade` and `loom doctor`.
- **A possible principle,** for the author to decide: *loom hosts the project; it does not shape it.* A layout, a medium or a way of working is the person's, and a feature that works only when the person organises their work loom's way needs a reason.

## Found along the way

- **A page in the viewer's origin can act as the author.** `GET /_api` returns the write token with no origin check, and `/build/*` and `/digests/storage/*` are served from the viewer's origin with a type guessed from the file's extension. Agents may write under `build/`. So an agent can write `build/SESSION/x.html`, link it in a transcript message, and the person's click opens a page that reads the token and posts `review-finish` with no author, which accepts as the author, past K5; `review-decision` and `review-finish` also lack the agent check the other author acts have (`render/api.py:380-389`). A fetched paper's source holds files nobody at loom wrote, and is served the same way. This holds today, before anything here is built, and is its own task: serve everything that is not the viewer's bundle under `Content-Security-Policy: sandbox`, check the origin on `GET /_api`, and give the review endpoints the agent check. It comes before any phase that shows HTML.
- **A moved quilt loses its agents.** `.mcp.json`, `.codex/config.toml`, `.gemini/settings.json` and `.cursor/mcp.json` in quant each start the server with `--quilt /Users/isaac/notes/quilts/quant`, the quilt's old absolute path. The quilt now lives at `~/quilts/quant`. Running `loom upgrade` (or `loom ai init`) there rewrites the four files, and `loom doctor` already notices that they differ. Dropping `--quilt` is right for clients that start the server inside the project and wrong for those configured outside it, so it is decided per client.
- **`[quilt] history` is a setting four copies ignore** (listed under "Who owns the layout").
- **`loom init`'s summary of the ignore file is stale:** it still says `refs/**/paper.pdf` (`cli/quilt.py:122-125`).
- **No way to propose an edit to a file that is not LaTeX.** Asked to merge new topics into quant's `syllabus.md`, the agent wrote `syllabus.proposed.md` and a merge script in its session, asked for approval in chat, and then applied the change. Edit in place, with Review afterwards, is the general answer.
- **The person's one file sits outside everything the viewer shows:** `syllabus.md`, at quant's root among loom's entries.

## Open questions

**Answered by the code:**

- **`loom new`'s destination:** `nodes/<id>.tex` in the default document's directory, so `\input{nodes/<id>}` keeps working relative to the document; `--to` names another.
- **An agent copy beside its source:** by `copy_of`, which the manifest already publishes from the history.
- **A person's Markdown with raw HTML:** escaped, as it is in pages and messages; raw HTML belongs in HTML files, shown from their own origin.
- **Ignoring:** the scanner reads only `.tex` files, so an ignore file would matter mainly to the viewer's tree, and there the person's own `.gitignore` already says what they count as noise. `% !LOOM ignore` stays the scanner's declaration.

**Decided by the author:**

- **How a document is named:** by its path without `.tex`, kept as a path, not flattened to `paper-main`, which would let `a-b/c.tex` and `a/b-c.tex` collide.

**Raised by the code, for the author:**

1. **The front door's setting name.** `home` is a candidate.

**Still open:**

2. Where Review's old text comes from (the four options above).
3. Notebooks: rendered read-only, or only opened in their application.
4. How a link names an application, and whether Anki on the desktop has a URL scheme.
5. Whether a discussion quote and a fleeting note are one mechanism.
6. The research state's default place: `.loom/`, or the root.
7. The deny list's setting name.
8. Whether to delete sync once a document can live and compile in the Overleaf directory itself.

## Phases

Each phase is checked against two quilts. In relloc, the Author must lose nothing they have now. In quant, the person and their agent must be able to build whatever they choose without loom getting in the way. The security fix in "Found along the way" is its own task and lands before phase 6.

0. **One owner for loom's paths.** A module holds every path loom uses, and the forty modules that encode the layout read it; nothing changes in behaviour, and the four copies that ignore `[quilt] history` are fixed. Every later phase then moves a path in one place.
1. **Overleaf: the person names the sync directory.** `loom sync init DIR` checks the person's clone instead of making one, `workspace()` returns it, every tree walker skips it, and `.loom/workspace/` goes; the rest of sync is unchanged.
2. **Documents anywhere, named by path.** One master rule in place of seven, sync's among them; the path, kept as a path, as the name through the build directory, fragments, the `.aux` lookup, the manifest and the viewer's routes; `masters[].directory` replaced by `copy_of`. Most of the fixture churn falls here: the 69 loom test files, the 16 fixture quilts, the spec fixture, and about 290 lines of the viewer's tests.
3. **Own-directory compile and the macro block.** A per-document base through `compile_tex` and the resolvers; landmarks and copies compile from their source's directory; sync's projection compiles from the document's directory; `new`, atomize, fork and import write relative to the document; section drafts take their context from the document's directory; the macro block replaces `loom.sty`. After this phase a person can work in the Overleaf directory directly, and whether to delete sync becomes a decision of its own (open question 8).
4. **Loom's files into `.loom/`.** `digests/`, `annotations/`, `reference-notes.jsonl`, `ai/`, `build/` and `retired/` move, which after phase 0 is a change of constants; `loom init` writes the config, the tutorial README and `.loom/`; the root `.gitignore` shrinks.
5. **Agents.** The deny list, its generation into each client and its statement in the orientation and the instruction line; agent copies in `.loom/`, read as landmarks are; agent documents written from scratch removed.
6. **The viewer.** The file item kind, Docs as the project's tree, the front door, Markdown documents, HTML in its frame from its own origin, and links that open other applications.
7. **Review and quoting.** Review as the meta view, and quoting any shown thing into a discussion. This waits until the open questions about the old text and about notes are answered.

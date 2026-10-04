# 3. Vocabulary

This glossary is normative. Every chapter, the specifications, the CLI help, the README, and the orientation document use these words with these meanings. A term not listed here is not a term of the system. Withdrawn terms are listed at the end so that older notes can be read.

All entries are **[decided]** unless marked.

## 3.1 Products

- loom : the tool. A Python command-line program and library. Distribution `loomtex`, command `loom`.
- arras : the viewer. A static Svelte bundle that reads a build directory conforming to the interface. Serves nothing itself; served by loom or any static server.
- quilt : a directory satisfying loom's assumptions. One paper, or one library of digests. Marked by `config.toml` at its root.
- workspace : the developer's directory `loom-arras/`, holding clones of the two tool repositories, the shared documentation, and uncommitted fixtures.

## 3.2 Files and directories of a quilt

- master : a `.tex` file containing `\documentclass`, located in the drafting directory or the agent's drafting directory. Compiled as a document. Addressed by path. The root of an inclusion tree. Also called a live document.
- drafting directory : the directory named by `config.toml [quilt] drafting`, by default `drafting/`. Every file in it with `\documentclass` is a master, and every one is live. Read as `drafts` in a quilt written before 0.9.
- agent's drafting directory : the directory named by `config.toml [quilt] drafting_ai`, by default `drafting-ai/`. Holds the documents the person and an agent both edit: live, and never reviewed, accepted or published (4.4). The one place outside its session an agent may write a document.
- agent document : a document in the agent's drafting directory, whether drafted from a working document by `loom draft` or written there by the agent from scratch (DR-330-ikmartin). One drafted from a working document says so where it matters: "drafted from drafting/main.tex".
- landmark : a document's flat text as it stood at a step, kept in that step's directory under `.loom/history/`: the paper as received, kept by `loom import`, or a drafting document with its ids and `\usepackage{loom}`, kept by `loom stamp DOCUMENT -m NAME` (17.9). Named by the slug of its message (`widgets-v3`), its step, or `DOC@STEP`. Never scanned, so nothing in it defines a node; shown in arras as a document; `loom history show` prints it and `loom history restore` starts a working document from it.
- live : a property of a document, not of a file: a document is live when it sits in the drafting directory and no conversion has recorded that its output superseded it. Only live documents define the nodes they hold inline.
- superseded : a document a conversion (`atomize`, `linearize`) replaced, recorded in the history. It defines nothing until `loom live` says otherwise.
- default master : the master named by `config.toml [quilt] main`.
- spine : a file consisting of prose, sectioning, and inclusion lines, produced by `atomize`. Not a distinct kind to the scanner; the word is descriptive.
- `nodes/` : the directory `loom new` and `atomize` write node files to. A convention, not a rule.
- `digests/` : the directory of digests, with loom's store of other people's documents under `digests/storage/`, named by identifier. `refs/` is the author's seed space: the PDFs and `.bib` files they drop in for loom to read (8.16), and is gitignored.
- `ai/` : the optional AI layer: `orientation.md`, `rules.md`, `formatting.md`, `modes/`. Sessions live in `.loom/sessions/`.
- `.loom/` : loom's own durable data: `state.toml` (the acceptance ledger) and `history/` (the history ledger, the step directories, and the content-addressed text store).
- `retired/` : where `atomize --retire` moves a converted file at the author's request. Never scanned.
- `build/` : everything derivable. Gitignored. Deletable at any time.
- `loom.sty` : the vendored LaTeX package providing the three macros. Lives at the quilt root.
- user config : `~/.config/loom/config.toml`. Per person, not per quilt. Holds `[author] name`.

## 3.3 Nodes and identity

- node : a sectioning unit or a theorem-like environment. Has an id if its first label is id-shaped, otherwise a qualified key. May include other nodes.
- id : the permanent identifier of a node, of the form `<prefix>-<local>`. For nodes made by `loom new`: prefix chosen by the author, local four uppercase base-36 characters (`rl-0004`). For digest nodes: the citekey as prefix and the paper's own label as local (`Man12-thm-4.1`).
- id-shaped : a label matching the id grammar (Chapter 5).
- derived id : the id of a node an agent document defines, `zk-0001-ai` for the person's `zk-0001`: the counterpart is read from the id by dropping the suffix (5.3.1). An id to the scan, never versioned or accepted.
- prefix : the part of an id before the first hyphen. Chosen by the author per quilt (default in config) or per command (`--prefix`). Alphanumeric, no hyphens.
- alias : any label on a node other than its id. Multiple `\label`s in one environment are legal LaTeX; loom resolves all of them to the node.
- tag : a thematic label attached to a node by a `% !LOOM tags:` directive (`algebraic-geometry`). Any number per node. Never an identifier.
- taxon : the kind of a node: the display name declared by `\newtheorem` (or `\declaretheorem`) for a theorem-like environment; `Section`, `Subsection`, and so on for sectioning units; `Proof` for a labelled proof.
- style class : amsthm's `plain`, `definition`, or `remark`, read from the `\theoremstyle` in force when the environment was declared. It controls presentation, not proof obligation.
- basis : the reason a theorem-like block may be relied on: `expository`, `local-proof`, `cited-result`, `assumption`, or `open-claim`; `unclassified` means the drafting scan needs the author's choice. `expository` covers definitions, notation, and explanatory remarks or comments that make no claim requiring mathematical justification. A remark or comment with a claim and its justification inline may declare `local-proof`; its acceptance covers the entire block. The author may declare a basis with `% !LOOM basis:` inside the block.
- version : the text a key had at a step, stored in that step's directory and addressed `rl-0001@3`.
- address : a key and a step, `rl-0001@3` or `rl-0001@paper-v2`; the step may be named by number or by the name of the landmark it kept.
- retired id : an id the history has recorded and no live document defines. Never allocated again.
- conflicted : the state of an id two live files both define. It has no text: loom reports both and chooses neither.
- key : the unit the ledger accepts and annotations target: a statement (its id) or a proof (`<id>/proof`, `<id>/proof/2`, ..., or a labelled proof's own id). Equations and masters are also annotation targets but never ledger keys.
- qualified key : the internal address of something without an id: `rl-0004#eq:main` for an equation, `drafting/main.tex#sec:setup` for an untagged section.
- region : the span of source text belonging to a node, a proof, or a labelled equation.
- own text : a node's region minus the regions of its children. Every character of the quilt belongs to exactly one node's own text (the master owns the preamble and top-level prose).
- digest node : a node of a cited work's digest — a `plain` node with no proof whose title carries the citation and the locator. **[decided]** The term is *digest node*, said from what it is rather than from where it is not; a quilt's own nodes are **authoring nodes** where the two must be told apart (DR-205).

## 3.4 Structure

- inclusion : the relation "A's region contains B's region", arising from `\input`, `\nest`, `\include`, and sectioning nesting. Forms a tree per master.
- inclusion tree : the tree rooted at a master.
- reached : a node or file is reached by a master when it lies in that master's inclusion tree.
- loose : reached by no master. A computed property, never a directory.
- level shift : the number of `\nest` wrappers between a master and a file; added to the levels of the file's sectioning commands.
- edge : a dependency: from a region (statement or proof) to a node, arising from `\ref`, `\eqref`, `\cref`, `\autoref`, `\uses`, or a matched `\cite[postnote]`. Classified as statement-edge or proof-edge by the region it occurs in.
- closure : the transitive statement-dependencies of a key.
- closure document : a standalone document for a key: the master's preamble, `\usepackage{loom}`, the statements of the closure in dependency order, then the key's own text with inclusions expanded.

## 3.5 Review

- ledger : `.loom/state.toml`. Holds acceptance rows and nothing else. Written only by `loom accept`. Never edited.
- acceptance row : one entry in the ledger: key, author, date, hash of the key's text, hashes of the closure's statements and the preamble closure, references to snapshots.
- snapshot : the normalized text of a key or preamble at the time of an acceptance, stored content-addressed under `.loom/history/texts/`, the same store the versions use. What lets a stale acceptance be explained with a diff.
- review record : one session's annotations as they now stand, replayed from `annotations/log.jsonl`. Not a file: the log is the only store, written only by `loom annotate` and by `loom library verify` and `discard` on a citation suggestion.
- annotation : the one record of review, and the one noun for it in commands, the viewer and the documents: id, author (person or agent), session, target key, target hash, selector, `in` (the document a claim about a node is read in, or none), kind (one of five: objection, suggestion, question, citation, note), severity, body, status, reply-to. Written by `loom annotate`; listed by `loom ai annotations`. A note is one of its kinds (7.2), never the record itself.
- selector : the text-quote selector: the exact quoted text with prefix and suffix context, resolved within the target's own text.
- detached : an annotation whose selector no longer matches its target's current text.
- state : a computed word for a key: `draft`, `accepted`, `incomplete`, with `stale` as a modifier on `accepted`.
- stale : an acceptance row exists whose recorded hashes do not all match the current text.
- fresh : not stale.
- proved : a computed display state for a node: statement accepted and at least one proof accepted, none stale, no `\incomplete`.
- settled : proved, and every node in the closure settled.
- settled (of an annotation) : resolved or withdrawn, marked by hand and never by being read; not drawn at rest, and shown faint by the settled control (15.3.1).
- discard : marking a session ignored so that its annotations vanish from every view, and closing it (`loom ai discard`). Reversible. Never deletes.
- withdrawn : of an annotation, discarded on its own (`loom annotate --discard ID`) or with its session. The word a person reads, in the CLI, the viewer and this book; the log and the manifest say `discarded` (DR-330-ikmartin).

## 3.6 Digests

- digest : a LaTeX file under `digests/` holding one cited paper's results as digest nodes under the paper's outline, with a provenance header.
- extraction : producing a digest mechanically from the reference paper's LaTeX source (`loom library update`'s extract step).
- ingest : the AI mode in which an agent produces or completes a digest from a PDF, or checks an extracted digest for missing dependencies.
- postnote : the optional argument of `\cite`, as in `\cite[Theorem 4.1]{Man12}`.
- postnote edge : an edge created by matching a postnote against a digest node's locator.
- locator : the reference's own address for a result, recorded in the digest node's title: `Theorem 4.1, p. 12`.
- macro block : a `% !LOOM begin macros` ... `% !LOOM end macros` region in a digest holding the reference paper's macro definitions, applied inside a TeX group wherever the digest's text is used.
- Library : the view of a quilt's cited works as **whole documents** rather than as loose digest nodes — a work is one thing one opens, reads and annotates. **[decided]** It is where `/references` and `/digest` fold together (DR-206).
- work : one cited paper, named by its global identifier rather than by a citekey, with whatever the store holds for it — a PDF, its LaTeX source, its page text, its digest.
- unreadable : an author's standing claim that a work has no document to hold at all, recorded in `digests/unreadable.json`. Declared and never inferred, because nothing in a bibliography entry says so.
- library : the papers a quilt cites and what loom knows of them — their documents in the store, their digests, the results proposed and verified, and the relations asserted between results — and `loom library`, the commands that keep it (Chapter 8, DR-331-ikmartin). "Reference layer" is the same thing seen from the store's side.
- relation : a typed link between two results (`same-notion`, `generalises`, `specialises`, `depends-on`, `contradicts`), with its reason, asserted by `loom library relate` and never checked or citable.
- library quilt : a quilt with no masters, holding only digests and the store. The place digests are kept once per paper.

## 3.7 Build and interface

- build directory : `build/` after `loom build`: fragments, `manifest.json`, derived files, rendered SVGs, compiled outputs.
- fragment : one HTML file in the dialect, per node and per master.
- dialect : the constrained semantic HTML that arras accepts (`specs/dialect.md`).
- manifest : `build/manifest.json`, the graph and all non-textual data (`specs/manifest.md`).
- diagnostic : an entry in the manifest's diagnostics list: severity, code, message, locations, keys.
- reserved code : a diagnostic code defined by the interface for any node-based publisher.
- publisher code : a namespaced diagnostic code (`loom:unattached-proof`) defined by one publisher.
- thread : the interface's name for a discussion: messages, attachments, targets. A session publishes as a thread.
- Authoring View : the quilt's own document and nodes — what the author is writing. **Library View** is the same frame turned on a cited work. The split, the panel and the placements are the same machinery in both; what differs is whose text is in the content pane.
- split view : content on one side, discussion on the other, one divider between them, with one ratio for the whole app.
- placement : where an opened annotation stands — `floating` over the text or `inline` in the flow, the latter in the Authoring View alone; also the field of a suggestion that says where its text goes (`replace`, `after`, `before`).
- travel : moving between the panes on a double-click: a brief scroll, then a flash on what was arrived at.
- write API : the HTTP form of loom's record-writing commands, for a browser. Carries a token, an `Origin` check and a JSON content type (DR-203).
- runner : an external command that turns one prompt into one response with no interactive session. Specified and declined; loom prepares an agent's context and records what it did, and does not supervise the process (WQ-15).

## 3.8 AI layer

- orientation document : `ai/orientation.md`, the file that tells an agent what a quilt is and how to work in it. Printed with live state by `loom ai orient`.
- session : a stretch of work on a quilt, which a person and an agent may share; one directory under `.loom/sessions/`, named by a stable id and carrying a title the author may change. Re-enterable, not tied to a mode, and what an annotation belongs to. **[decided]** It replaces *run*, and the separation it makes is that the **author** is who wrote a thing and the **session** is where it belongs (DR-199).
- round : the span between a session opening or resuming and its next close or resume; what "changed since last time" is measured from.
- inbox : a session's append-only message log, read and never consumed. A **broadcast**, not a queue with assignment: every attached reader sees everything and nobody is handed a task.
- attached : listening to a session, recorded by a heartbeat. A stale heartbeat means detached.
- mode : one of the review procedures (audit, referee, review, simplify, question, quick, draft, ingest, brainstorm) as a prompt template with input and output contracts, under `ai/modes/`.
- application : one use of a mode on one target inside a session, producing named output files in the session's directory.
- `run.log` : automatic log of every loom command invoked with `--session`, in the session's directory; `loom annotate` adds the annotation it made or changed after an arrow. A session's What it did is this log.
- transcript : a session's conversation, which is its inbox: every message the person and the agent said, in order, and nothing loom wrote. The agent writes its account of the work there with `loom session say`; there is no separate journal.
- promote : withdrawn (DR-173). Nothing copies what an agent wrote into the quilt: a digest is made by `loom library update` and checked by ingest mode, and a drafted node is previewed by the author and pasted by them, taking an id from `loom id --next`.
- agent : the interactive program a person points at a quilt (Claude Code, Codex). Never a dependency.

## 3.9 Operations

- atomic format : a file written around inclusion lines, with each node in a file of its own.
- linear format : a file written as one document, with its environments in place. Neither is rigorous; they name the two shapes loom's conversions move between.
- import : bringing a paper into a quilt, with its styles, bibliography and figures at the root: the paper as received, flattened, is kept as a landmark in the history, and the working document is drafted from it at once, with `\usepackage{loom}` and an id on every node.
- draft : making an agent document from a live drafting document: a flat copy with derived ids in the agent's drafting directory, recorded as a `copy` step (17.7).
- stamp : recording a step: every key whose text has moved since the last one, quilt-wide; given a document, only the keys it reaches, and the document's flat text kept as a landmark.
- restore : writing a new working document in the drafting directory from a landmark, with `\usepackage{loom}` and an id on every node that has none (17.9).
- fork : giving a document its own copy of a node under a new id, as a patch the author applies.
- revert : printing the patch that puts a recorded version's text back in place of the head's.
- live : making a superseded document define its nodes again.
- move : recording that a drafting document now has another path, renaming the file when it is still where it was (`loom mv`). Every record naming the document follows it.
- linearize : flattening a document, every inclusion expanded in place with `\nest`'s level shift applied, and the reverse of atomize.
- atomize : moving each node of a file into its own file, writing a spine to a named destination. Never in place; the history records that the spine superseded the source.
- step : a numbered, directory-creating event in the history: an import, a stamp, or a draft. Numbered once over the whole quilt.
- identity test : the compiled output (`pdftotext`) of a document must be unchanged by import, atomize, inline, or linearize.
- downstream : the report of everything downstream of a node: transitive dependents, inclusion sites, ledger rows, annotations (`loom downstream ID`).
- publish (verb) : writing the build directory. The command is `loom build`.

## 3.10 Withdrawn terms

The following words were used during design and are not terms of the system. Do not use them in code, docs, or CLI text.

- external node : now digest node (DR-205). The old term said what a node was *not* part of, which stopped being the interesting fact once the Library made a cited work a thing one reads.
- run : now session (DR-199). A run was the agent's alone; a session is shared, and the author of a thing is recorded separately from the place it belongs to.
- tag (as identifier) : now id. "Tag" means a thematic label.
- patch, thread (as node or edge) : now node and edge. "Thread" survives only as the interface's word for a discussion.
- map : now digest.
- math-aid, mathaid : the working label before naming.
- tutte : the viewer's earlier name; now arras.
- `sections/` : no dedicated directory; section node files live in `nodes/`.
- `drafts/` : the pre-0.9 name of the drafting directory. Still read from an old `config.toml`, with a warning; never written.
- `assemble` : withdrawn; `linearize` flattens a document.
- `inline` : withdrawn; it flattened a copy without superseding its source, so every id was defined twice (DR-326-ikmartin); `linearize` is the reverse of atomize.
- expanded format, assembled format : now linear format.
- work, bench, revise : considered and rejected as verbs; the pair is atomize and linearize, and the passage between a working document and a landmark is stamp and restore.
- canon directory, canon document, `canonize` : withdrawn; a landmark is kept in its step by `loom stamp DOCUMENT -m NAME`, and `loom history show --plain` prints it without loom. The interface still names a landmark's manifest entry, route and fragment `canon` (specs/manifest.md §2).
- `--ignore-src` : withdrawn from `atomize`; the history records that the output superseded the input, and `--retire` moves it.
- `loose/`, `attic/`, `archive/` : not loom directories; an author may use any of them, and `% !LOOM ignore` handles a file that must not be scanned.
- sidecar, `block.toml` : no per-node metadata files exist.
- `reviewed` (as a state) : not a state; reviews are facts and counts.
- `impact`, `deps --closure` vs `closure`, `dependents`, `resolve`, `ai finish`, `ai resume`, `ai list`, `ai restore`, `digest export`, `state set`, `state refresh`, `ref use`, `bundle --for-review`, `\blocker`, `\block`, `% !LOOM begin preamble` : withdrawn commands and syntax; see the CLI reference for what replaced each.
- `map.toml`, `map.md` : withdrawn digest form.
- `loom refs`, `loom digest` : withdrawn groups; `loom library` holds their commands (DR-331-ikmartin, 12.11).
- `unravel`, `reach`, `pop` : withdrawn names for `loom downstream` (DR-330-ikmartin).
- AI draft, AI copy, agent copy : withdrawn names for an agent document (DR-330-ikmartin).
- bundle (of a key) : now closure document (DR-330-ikmartin); "bundle" still names the viewer's built files.
- comment, finding : withdrawn as names for the record (DR-292-ikmartin); it is an annotation, whatever its kind. `loom comment` is `loom annotate`, `loom ai findings` is `loom ai annotations`, `loom refs note` is `loom library verify` and `discard` on the suggestion's id, and the write API's `comment` and `refs-note` are `annotate` and `library-cite`.
- `--proofs` on `\nest`, `section-nesting` directive : withdrawn; `\nest` is per-site.

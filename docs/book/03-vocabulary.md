# 3. Vocabulary

This glossary is normative. Every chapter, the specifications, the CLI help, the README, and the orientation document use these words with these meanings. A term not listed here is not a term of the system. Withdrawn terms are listed at the end so that older notes can be read.

All entries are **[decided]** unless marked.

## 3.1 Products

- loom : the tool. A Python command-line program and library. Distribution `loomtex`, command `loom`.
- arras : the viewer. A static Svelte bundle that reads a build directory conforming to the interface. Serves nothing itself; served by loom or any static server.
- quilt : a directory satisfying loom's assumptions. One paper, or one library of digests. Marked by `config.toml` at its root.
- workspace : the developer's directory `loom-arras/`, holding clones of the two tool repositories, the shared documentation, and uncommitted fixtures.

## 3.2 Files and directories of a quilt

- master : a `.tex` file containing `\documentclass`, located in the masters directory. Compiled as a document. Addressed by path. The root of an inclusion tree.
- masters directory : the directory named by `config.toml [quilt] drafts`, by default `drafts/`. Every file in it with `\documentclass` is a master.
- default master : the master named by `config.toml [quilt] main`.
- spine : a file consisting of prose, sectioning, and inclusion lines, produced by `atomize`. Not a distinct kind to the scanner; the word is descriptive.
- `nodes/` : the directory `loom new` and `atomize` write node files to. A convention, not a rule.
- `refs/` : the directory of digests. `refs/pdf/` holds PDFs and is gitignored.
- `comments/<author>/` : human review records.
- `ai/` : the optional AI layer: `orientation.md`, `modes/`, `runs/`.
- `.loom/` : loom's own durable data: `state.toml` (the ledger) and `snapshots/`.
- `build/` : everything derivable. Gitignored. Deletable at any time.
- `loom.sty` : the vendored LaTeX package providing the three macros. Lives at the quilt root.
- user config : `~/.config/loom/config.toml`. Per person, not per quilt. Holds `[author] name`.

## 3.3 Nodes and identity

- node : a sectioning unit or a theorem-like environment. Has an id if its first label is id-shaped, otherwise a qualified key. May include other nodes.
- id : the permanent identifier of a node, of the form `<prefix>-<local>`. For nodes made by `loom new`: prefix chosen by the author, local four uppercase base-36 characters (`rl-0004`). For digest nodes: the citekey as prefix and the paper's own label as local (`Man12-thm-4.1`).
- id-shaped : a label matching the id grammar (Chapter 5).
- prefix : the part of an id before the first hyphen. Chosen by the author per quilt (default in config) or per command (`--prefix`). Alphanumeric, no hyphens.
- alias : any label on a node other than its id. Multiple `\label`s in one environment are legal LaTeX; loom resolves all of them to the node.
- tag : a thematic label attached to a node by a `% !LOOM tags:` directive (`algebraic-geometry`). Any number per node. Never an identifier.
- taxon : the kind of a node: the display name declared by `\newtheorem` (or `\declaretheorem`) for a theorem-like environment; `Section`, `Subsection`, and so on for sectioning units; `Proof` for a labelled proof.
- style class : amsthm's `plain`, `definition`, or `remark`, read from the `\theoremstyle` in force when the environment was declared. `plain` nodes owe a proof.
- key : the unit the ledger accepts and annotations target: a statement (its id) or a proof (`<id>/proof`, `<id>/proof/2`, ..., or a labelled proof's own id). Equations and masters are also annotation targets but never ledger keys.
- qualified key : the internal address of something without an id: `rl-0004#eq:main` for an equation, `drafts/main.tex#sec:setup` for an untagged section.
- region : the span of source text belonging to a node, a proof, or a labelled equation.
- own text : a node's region minus the regions of its children. Every character of the quilt belongs to exactly one node's own text (the master owns the preamble and top-level prose).
- external node : a `plain` node with no proof whose title contains a citation. Digests consist of these.

## 3.4 Structure

- inclusion : the relation "A's region contains B's region", arising from `\input`, `\nest`, `\include`, and sectioning nesting. Forms a tree per master.
- inclusion tree : the tree rooted at a master.
- reached : a node or file is reached by a master when it lies in that master's inclusion tree.
- loose : reached by no master. A computed property, never a directory.
- level shift : the number of `\nest` wrappers between a master and a file; added to the levels of the file's sectioning commands.
- edge : a dependency: from a region (statement or proof) to a node, arising from `\ref`, `\eqref`, `\cref`, `\autoref`, `\uses`, or a matched `\cite[postnote]`. Classified as statement-edge or proof-edge by the region it occurs in.
- closure : the transitive statement-dependencies of a key.
- bundle : a standalone document for a key: the master's preamble, `\usepackage{loom}`, the statements of the closure in dependency order, then the key's own text with inclusions expanded.

## 3.5 Review

- ledger : `.loom/state.toml`. Holds acceptance rows and nothing else. Written only by `loom accept`. Never edited.
- acceptance row : one entry in the ledger: key, author, date, hash of the key's text, hashes of the closure's statements and the preamble closure, references to snapshots.
- snapshot : the normalized text of a key or preamble at the time of an acceptance, stored content-addressed under `.loom/snapshots/`. What lets a stale acceptance be explained with a diff.
- review record : an `annotations.json` file under a run directory or a comments directory, written only by `loom comment`. Contains annotations.
- annotation : one comment: id, author (person or run), target key, target hash, selector, kind, body, status, reply-to.
- selector : the text-quote selector: the exact quoted text with prefix and suffix context, resolved within the target's own text.
- detached : an annotation whose selector no longer matches its target's current text.
- state : a computed word for a key: `draft`, `accepted`, `incomplete`, with `stale` as a modifier on `accepted`.
- stale : an acceptance row exists whose recorded hashes do not all match the current text.
- fresh : not stale.
- proved : a computed display state for a node: statement accepted and at least one proof accepted, none stale, no `\incomplete`.
- settled : proved, and every node in the closure settled.
- discard : marking a run or comment session ignored so that its annotations vanish from every view. Reversible. Never deletes.

## 3.6 Digests

- digest : a LaTeX file under `refs/` holding one cited paper's results as external nodes under the paper's outline, with a provenance header.
- extraction : producing a digest mechanically from the reference paper's LaTeX source (`loom digest extract`).
- ingest : the AI mode in which an agent produces or completes a digest from a PDF, or checks an extracted digest for missing dependencies.
- postnote : the optional argument of `\cite`, as in `\cite[Theorem 4.1]{Man12}`.
- postnote edge : an edge created by matching a postnote against a digest node's locator.
- locator : the reference's own address for a result, recorded in the external node's title: `Theorem 4.1, p. 12`.
- macro block : a `% !LOOM begin macros` ... `% !LOOM end macros` region in a digest holding the reference paper's macro definitions, applied inside a TeX group wherever the digest's text is used.
- library quilt : a quilt with no masters, holding only `refs/`. The place digests are kept once per paper.

## 3.7 Build and interface

- build directory : `build/` after `loom build`: fragments, `manifest.json`, derived files, rendered SVGs, compiled outputs.
- fragment : one HTML file in the dialect, per node and per master.
- dialect : the constrained semantic HTML that arras accepts (`specs/dialect.md`).
- manifest : `build/manifest.json`, the graph and all non-textual data (`specs/manifest.md`).
- diagnostic : an entry in the manifest's diagnostics list: severity, code, message, locations, keys.
- reserved code : a diagnostic code defined by the interface for any node-based publisher.
- publisher code : a namespaced diagnostic code (`loom:unattached-proof`) defined by one publisher.
- thread : the interface's name for a discussion: messages, attachments, targets. A run publishes as a thread.
- write API : the HTTP form of loom's record-writing commands, for a browser. Specified, deferred.
- runner : an external command that turns one prompt into one response with no interactive session. Specified and declined; loom prepares an agent's context and records what it did, and does not supervise the process (WQ-15).

## 3.8 AI layer

- orientation document : `ai/orientation.md`, the file that tells an agent what a quilt is and how to work in it. Printed with live state by `loom ai orient`.
- run : one chat thread with an agent; one directory under `ai/runs/`. Re-enterable. Not tied to a mode.
- mode : one of the review procedures (audit, referee, simplify, question, quick, draft, ingest) as a prompt template with input and output contracts, under `ai/modes/`.
- application : one use of a mode on one target inside a run, producing named output files in the run directory.
- `run.log` : automatic log of every loom command invoked with `--run`, in the run directory.
- `thread.md` : voluntary journal the agent appends to, in the run directory.
- promote : copying a draft node or a digest from a run directory into the quilt (`loom ai promote`), allocating or checking its id, then linting.
- agent : the interactive program a person points at a quilt (Claude Code, Codex). Never a dependency.

## 3.9 Operations

- import : copying a paper and everything it reaches into a quilt, inserting ids into the copies, changing nothing else.
- atomize : moving each node of a file into its own file, writing a spine to a named destination. Never in place.
- inline : the reverse of atomize, to a named destination.
- identity test : the compiled output (`pdftotext`) of a master must be unchanged by import, atomize, or inline.
- unravel : the report of everything downstream of a node: transitive dependents, inclusion sites, ledger rows, annotations. Aliases `downstream`, `reach`, `pop`.
- publish (verb) : writing the build directory. The command is `loom build`.

## 3.10 Withdrawn terms

The following words were used during design and are not terms of the system. Do not use them in code, docs, or CLI text.

- tag (as identifier) : now id. "Tag" means a thematic label.
- patch, thread (as node or edge) : now node and edge. "Thread" survives only as the interface's word for a discussion.
- map : now digest.
- math-aid, mathaid : the working label before naming.
- tutte : the viewer's earlier name; now arras.
- `sections/` : no dedicated directory; section node files live in `nodes/`.
- `drafts/` (as a loose-files directory) : no such directory; loose is computed. `drafts/` is the masters directory.
- `loose/`, `attic/`, `archive/` : not loom directories; an author may use any of them, and `% !LOOM ignore` handles a file that must not be scanned.
- sidecar, `block.toml` : no per-node metadata files exist.
- `reviewed` (as a state) : not a state; reviews are facts and counts.
- `impact`, `deps --closure` vs `closure`, `dependents`, `resolve`, `ai finish`, `ai resume`, `ai list`, `ai restore`, `digest export`, `state set`, `state refresh`, `ref use`, `bundle --for-review`, `\blocker`, `\block`, `% !LOOM begin preamble` : withdrawn commands and syntax; see the CLI reference for what replaced each.
- `map.toml`, `map.md` : withdrawn digest form.
- `--proofs` on `\nest`, `section-nesting` directive : withdrawn; `\nest` is per-site.

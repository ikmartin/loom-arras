# The model

What loom works with: the quilt, its documents, the nodes and graph read from them, the history, review and trust, annotations, the library of other people's work, notes, sessions, and the viewer that shows all of it. Formats are in `docs/specs/`; commands are in `loom --help`. This file says what the things are and why.

## The quilt

A quilt is a research project in a directory marked by a `config.toml` with a `[quilt]` table; every command finds it by walking up from the current directory. It may hold several documents, one, or none at all. A paper with a talk beside it is a quilt; so is a reading project with no draft, made of the papers and books someone is learning from.

What lives where:

- **The author's sources:** documents, node files, style files, the bibliography and figures, wherever the author keeps them. Style files sit at the root, because documents compile from the root (P12).
- **`drafting/`** holds the author's live documents, and **`drafting-ai/`** holds documents the author and an agent both edit (below). Both names are settings.
- **`digests/`** holds digests of cited works and loom's store of their documents. **`refs/`** is the author's drop folder for PDFs and `.bib` files, which loom reads and never writes. **`notes/`** is the author's own reference material, which loom never scans or writes.
- **`.loom/`** holds loom's durable records: the acceptance ledger, the history, sessions. **`annotations/log.jsonl`** is the annotation log. **`build/`** is everything derivable and can be deleted at any time.

Every `.tex` file is scanned except under `build/`, `.loom/`, `refs/`, `notes/`, `digests/storage/`, the history and tooling directories, and files whose first twenty lines say `% !LOOM ignore`. Nothing is inferred from where a file sits (P5); the exclusions are exclusions, not inferences.

**Open.** A quilt today assumes a paper in places: `loom init` writes an article skeleton, `status` counts "keys of yours", and an empty `drafting/` is reported as a problem. For the Learner, a quilt with only works and notes must be complete and unremarkable (not built yet, see [README](README.md#decided-not-yet-built)).

## Documents

A **document** is a `.tex` file with `\documentclass` in `drafting/` or `drafting-ai/`. Every one is **live**: scanned, compiled, rendered and reviewable. There is no list of documents; the directory is the list. A document compiles from the quilt root, and a node it reaches is numbered from that document's own compile.

An **agent document** lives in `drafting-ai/`. It is a flat copy of one of the author's documents, made by `loom draft DOC --ai NAME`, with every id it defines derived (`rl-0004-ai` for `rl-0004`) so it can never collide with the author's. The copy records the version of each node it began from, so loom can say when the author's side has moved past it (`loom ai drafts`) and refresh it (`loom ai refresh`). Nothing in an agent document is accepted or published. Taking its changes back is `loom adopt`, the author's act: it previews the changes, lets the author choose node by node, stamps the working document first, and then writes (P7). **Open.** An agent document drafted from none of the author's (a survey, a section to be placed later) is refused today; see WQ-57.

A **landmark** is a document as it stood at a moment worth returning to: the paper as received by `loom import`, or a working document kept by `loom stamp DOC -m NAME`. It lives in the history, is never scanned, and so defines nothing and collides with nothing. `loom history show` prints it and `loom history restore` starts a new working document from it.

A conversion (`atomize`, `linearize`) records that its output **superseded** its input, which stops being scanned until `loom live` says otherwise. `loom mv` records a document's move, and every record naming it by path follows the move when it is read, without being rewritten.

## Nodes and the graph

A **node** is a theorem-like environment (declared by `\newtheorem`) or a section. It becomes addressable when its first label is id-shaped, `<prefix>-<local>` such as `rl-0004`; `loom id` prints the patch that adds one. Other labels on the same node are aliases. A **key** is what review is about: a statement (its id) or a proof (`rl-0004/proof`, `rl-0004/proof/2`).

An id is **defined once**. A file may be included by several documents, and its nodes then appear in each, numbered by each. But when an id is defined twice, by two files or within one, the key is **conflicted**: it has no text, loom reports both definitions and chooses neither, and `loom fork` gives one of them a fresh id. Loom never picks a winner, because any rule for picking one would let one definition's acceptance and annotations silently apply to another's text. An id that history has recorded is never allocated again.

**Edges** are read from what the author writes: `\ref` and its relatives, `\cite[Theorem 4.1]{key}` when a digest of that work has the result, and `\uses{…}` for a dependency the text does not name. The **closure** of a key is everything its statement depends on, transitively; `loom source KEY --closure` prints it as the exact context for reading, reviewing or drafting that key. A node no document reaches is **loose**, which is computed, never a directory. `% !LOOM see: ID` links two nodes for the reader and is never a dependency.

Two markers carry mathematical status in the source: `\incomplete{…}` marks a statement or proof as not finished, and `% !LOOM basis:` declares why a block may be relied on (a local proof, a cited result, an assumption, an open claim, or exposition). The exact rules are `docs/specs/source-contract.md`.

## History

The history (`.loom/history/`) records what loom was told, at the moments it was told: never on save, and never a claim about the filesystem (P13). A **step** is an import, a stamp, or the copy behind an agent document, numbered once across the quilt. A stamp records every key whose text moved since the last step; given a document, it also keeps that document as a landmark. A key's text at a step is a **version**, addressed `rl-0001@3` or `rl-0001@submitted`.

`loom revert KEY@N` prints the patch that puts a version back and records nothing, since the head's text says whether it was applied. `loom fork` gives one document its own copy of a node under a new id. Every divergence between the record and the files (an edited landmark, a missing step, an unreadable ledger, a step interrupted before it was recorded) is reported with the command that resolves it, and nothing stops a build. No step is recorded beside an interrupted one: every command that records a step refuses until its directory is removed.

## Review and trust

Two kinds of record say what has been looked at, and they never mix.

**Acceptance** is the author's claim that a key's mathematics is right. `loom accept` appends a row to the ledger (`.loom/state.toml`) holding hashes of the key's text, of every statement in its closure, and of the preamble, with snapshots of that text. Only the author accepts; an agent is refused whatever name it gives (`agents.md`). From the ledger and the current text, every key's state is **computed** (P3):

- `incomplete` when it contains `\incomplete`, whatever else is true;
- `accepted` when the latest row's hashes still match;
- `accepted, stale` when something has moved, with each cause named: its own text, a dependency (directly or through another), the preamble, its basis, or the document it was accepted in. `loom status --explain KEY` shows the diff;
- `conflicted` when two live files define it;
- `draft` otherwise.

On top of these, `proved` and `settled` are display states: a statement is proved when it and a proof are freshly accepted, and settled when everything it depends on is settled too. A cited result is a settled leaf by attribution.

Acceptance is personal: each reviewer's latest rows are their own, and a coauthor's acceptance never accepts for you. In the viewer, Review queues what needs looking at in dependency order; marking a block OK is pending until **Finish review** records the acceptances together, and overlooking a block never accepts it.

**Verification** is a different claim: that loom's copy of someone else's result is faithful to their paper. `loom library verify` records it, only the author can make it, and it settles nothing mathematical (below).

**Annotations** are the other kind of record: what anyone, person or agent, says about the text (next section). Annotations never change a state; a key with forty open objections and a fresh acceptance is accepted.

## Annotations

An annotation is the one record of review, written only by `loom annotate` and appended to `annotations/log.jsonl`. It has an author (a person, or an agent naming itself), a session, a target, and one of five kinds:

| kind | for |
|---|---|
| objection | something that must change |
| suggestion | something that could change, often with proposed text |
| question | something the writer could not decide |
| citation | a work worth citing |
| note | an explanation or aside that asks nothing |

Objections and suggestions carry a severity. A suggestion may carry a payload, the proposed text, and a placement (replace, after, before); the author reads it beside what it would replace and applies it if they want it.

A **target** is a key, a labelled equation, a whole document, or a page of a cited work. An annotation on text is anchored by a quote: the exact words, with a little context before and after, resolved inside the target's own text, so moving text between files never moves an annotation. When the quoted words are gone, the annotation is **detached**: never deleted, never drawn at a guessed place (A3), listed with its quote. An annotation is **settled** when someone resolves or withdraws it; settled annotations are hidden until the reader asks for them (A6). A re-check edits its own earlier finding rather than replying to itself.

How an annotation is drawn is the A set of `principles.md`: hue for its kind, weight for its severity, shape for what it is attached to, and a mark never splits a formula.

**Open.** Annotations can target only addressable things today. Something said about an untagged statement, or about an open problem that is not yet a node, has nowhere to go; notes (below) are meant to close this gap.

## The library

The library is the works a quilt reads and cites, and what loom knows of them. A **work** is one paper or book, named by a global identifier (a DOI, an arXiv id), with whatever loom's store holds for it: its PDF, its LaTeX source, its page text, its digest. `loom library update` gathers the bibliography, fetches what it may (only when the quilt allows the network, which an agent cannot grant), and maps pages.

A **digest** holds a work's results as digest nodes, each a statement verbatim with its locator (`Theorem 4.1, p. 12`), so that `\cite[Theorem 4.1]{Man12}` becomes an edge to a result someone can read and check. A digest's results are results whether or not any document declares their environments: each declares its own from its locator, so a quilt of digests alone already has them. A digest is **extracted** mechanically from the work's LaTeX source; nothing is typed from a PDF. For a work with only a PDF, an agent or person **proposes** a result with `loom library propose`, and loom refuses a quotation that is not on the page it names. Proposals wait in a file nothing inputs until the author verifies them, and citing one makes no dependency: the citation is reported, and verifying the proposal makes it one. A result's state is computed: extracted, proposed, verified, or discarded. A proposal whose quotation passed the page check is checked, never verified, and only the author verifies (P15).

A **relation** links two results (same notion, generalises, specialises, depends on, contradicts) with a reason. It is an assertion, never checked and never citable, and it is how connections between works are recorded and found from either end. A note on a page of a work (`loom annotate CITEKEY --page N --quote …`) says something about what is there.

The details are `docs/specs/digests.md`.

**Open.** The library is organised around what a draft cites: the bibliography is gathered from landmarks, fetching follows a work's own references, and uncited works are demoted. The Learner reads works nobody cites yet, so a work that is read must be as first-class as one that is cited (not built yet, see [README](README.md#decided-not-yet-built)).

## Notes

*Not built yet* (see [README](README.md#decided-not-yet-built)). This section is the design as currently decided.

A **note** is something a person or an agent wants to remember about the mathematics: an explanation of a definition, an example, a question, an attempt, a claim and its evidence, a dead end and why it failed, a connection between two works. Notes are how exploration and learning leave a trace.

- **Capture costs one gesture** (P14). A note needs only its text. Its kind defaults to note, and its target to what the viewer has selected, else the session; an agent may set either. Loom infers nothing, since it has no model.
- **A note attaches to anything:** a key, a digest result, a page of a work, an `\incomplete` step, an open problem, or the session alone, to be filed later. It is found from what it is attached to.
- **Notes are fleeting by default.** A note fades after a while unless it is kept or something durable links to it. Fading is computed from age and links (P3): a faded note is hidden by default, shown with one toggle, found by search, and never deleted from the log. Nothing announces it.
- **Claims carry their evidence.** A note that claims something says how far it has got (conjectured, tested on examples, sketched, proved here, refuted), and every step past conjectured names its evidence. Who linked the evidence is shown, because a link is itself a claim (P15). Evidence is asked for when a note is promoted, not when it is taken.
- **What is worth keeping becomes durable.** A note that has proved its worth is promoted: to a node in a document of the author's (a problem, a lemma, a definition restated in their own words), or kept as a durable note linked to the mathematics it concerns. Promotion is where care is asked for.
- **Open problems are nodes.** A question the Explorer is working on is a `question` or `conjecture` environment in a research document, with an id, edges and a computed status, and the attempts and dead ends about it attached as notes. An agent proposes one as a node in an agent document.

Notes are records loom writes (P1, P2), through one command, and share the annotation log's machinery: append-only events, authors, sessions. They are a separate kind of record, because "resolved" means the text was fixed and "refuted" or "proved" means something else.

**Open.** Where durable notes in the author's own words live (as nodes in a notes document, or as kept notes); how long a fleeting note lasts by default; and how a note cites a script by path and hash, until loom can run code.

## Sessions and transcripts

A **session** is a stretch of work, which a person and agents may share. Everything written in it records the session it belongs to and the author who wrote it, so the session is the audit trail: `run.log` lists every loom command run in it, and its directory holds what an agent hands the author (drafts, diffs, reports).

Sessions are not what work is organised around. Work collects around the mathematics: annotations and notes are found from what they are about, whichever session wrote them.

A session's **transcript** is what its participants wrote deliberately with `loom session say`, not a copy of a conversation held in an agent app. An agent writes it so that someone coming back later sees the main points of the discussion, what was decided or found, what is still open, and links to everything durable that came of it. The viewer shows a transcript beside the documents it refers to, its links live, like a long-running annotation.

The viewer's chat composer and agent launching are retired (not built yet, see [README](README.md#decided-not-yet-built)): conversations happen in agent apps, which own the model, the streaming, interruption and permissions.

## The viewer

Arras shows what loom publishes and lets a person read and decide: read documents and works, follow links between them, see annotations and notes where they belong, review and accept, verify library results. It writes nothing itself; every write goes through a control the publisher advertises, and only when the publisher serves it (P11). It works offline, from a static build, on any host.

The principles that govern it are the V and A sets. In short: open on the thing itself, show less, claim only what is known, and never lose the thing you followed a link from.

A redesign is being settled (not built yet, see [README](README.md#decided-not-yet-built)): the left panel shows the quilt's content, documents and works alike, sized by what exists; there is a Library view; Review is a place; Home and the icon strip go.

Things are shown where they live (V7): a statement in a document that holds it, a cited result on its work's page, an annotation on the words it marks. A result included in several documents opens in the one the link stands in, else one on screen, else the one looked at last; a result in no document, or a work with no PDF, is the one case for a view of its own.

## Coauthors

Coauthors clone the quilt. Sources, the history, annotations and digests are shared; `build/`, `refs/` and personal settings are not, and identity is never stored in the quilt. Acceptance is per reviewer. Two coauthors who allocate the same id on separate branches get a conflicted key after the merge, which `loom fork` resolves. A coauthor who works in Overleaf edits a document workspace that `loom sync` exchanges with the quilt: fetched changes are reviewed and incorporated by the author, who stamps each document first (P7).

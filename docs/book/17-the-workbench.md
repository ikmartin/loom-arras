# 17. The workbench

Chapter 6 brings a paper in; Chapter 7 records what has been reviewed. This chapter is about the third thing a paper has: a history. It specifies the two states a document is in, the record loom keeps of the passage between them, how a key's text at a past moment is named and read back, and what loom does when the record and the files disagree.

## 17.1 The two states

**[decided]** A document is either being worked on or fixed as a landmark, and where it sits says which.

- The **drafting directory** (`[quilt] drafting`, by default `drafting/`) holds the documents being worked on. Every one of them is live: it defines the nodes it holds inline, it is a master, it is scanned, compiled, rendered and reviewed. This is where the author writes.
- A **landmark** is a document's flat text kept in a step's directory in the history (17.2): the paper as received, kept by `loom import`, or a working document as it stood, kept by `loom stamp DOCUMENT -m NAME` (17.9). Each is one flat file, every inclusion expanded in place, nothing to resolve. It is never scanned, so it defines nothing and can never collide with the working text it came from. Arras shows it as a document; `loom history show --plain` prints it with `loom.sty`'s macros inline, so that it compiles where loom.sty is not.

**[decided]** Placement is the declaration, not a property loom computes. A file cannot say whether it is being worked on; the directory can. This is the same answer the masters directory has always given (1.3, sign 10), and the rejected alternative — a list of live files somewhere — is a second source of truth (sign 4).

**[decided]** The passage between the two states is what leaves a trail. `loom stamp DOCUMENT -m NAME` keeps a landmark and records, at that moment, what every key the document reaches was. `loom history restore` starts a working document in the drafting directory from a landmark. Everything in this chapter exists so that the sentence "what did this lemma say when we submitted?" has an answer that does not depend on the quilt being in version control.

**[decided]** P13 governs every check here: *loom verifies what it can, reports what diverges, repairs nothing, and never blocks work.* The head is always the files on disk. The history is a log of what loom was told, never a claim about the filesystem.

## 17.2 The record

**[decided]** The history lives under `.loom/history/`, hidden, beside the acceptance ledger:

```
.loom/
  state.toml                   the acceptance ledger (7.2)
  history/
    ledger.jsonl               one JSON object per line, appended only
    0001-paper/                an import: the paper as received, its landmark
      paper.tex
    0002-paper-v1/             a stamp given a document: its landmark, the preamble, one file per key that moved
      paper-v1.tex
      preamble.tex
      rl-0001.tex
      rl-0001.proof.tex
    0003-stamp-referee-points/ a stamp without one: the keys that moved
      rl-0004.tex
    texts/                     content-addressed text: snapshots, versions, anchors
      3f9a....tex
```

**[decided]** `texts/` is one store, shared by acceptance snapshots (7.2.2), by anything a version points at, and by the anchors of Chapter 0.10 when they arrive. Files in it are named by the sha256 of their normalized text, so identical text is stored once and nothing is ever overwritten.

**[decided]** The history is not a backup and does not try to be. It holds the text of a key at the moments loom was told to record one, the document as it stood at each of those moments, and the preamble that compiled them. It does not hold the files in between, and it does not hold anything about a file the quilt does not define a key in.

**[decided]** `[quilt] history` names the directory and defaults to `.loom/history`. `loom init` does not write the key: a quilt that never moves its record does not need a line saying where it is.

## 17.3 Three tiers

**[decided]** Three kinds of thing are recorded, and only three:

1. **Landmarks** — steps that keep a document's text: `loom import` (the paper arrives, before it has ids, so no key is recorded) and `loom stamp DOCUMENT -m NAME` (a working document as it stands, with every key it reaches that moved). A landmark is what an author points at later: *the submitted version*.
2. **Stamps** — the recording without a document: `loom stamp -m "Referee points"` records every key whose text has moved since the last step and keeps no document. A stamp is a step in the numbering as a landmark is, and so is the copy step of `loom draft --ai` (17.7.1).
3. **Anchors** — named positions inside a text, used by annotations. Defined in the annotation plan (0.10) and not in this chapter.

**[decided]** Nothing is recorded on save. Loom does not watch the filesystem for the purpose of recording history, and a quilt that nothing was imported into, stamped, or copied for an agent has an empty ledger and works exactly as it did before this chapter existed.

## 17.4 Numbering and addresses

**[decided]** Steps are numbered once over the whole quilt, `0001`, `0002`, `0003`, whether the step kept the paper, the talk, or no document at all. There is no per-node counter: two nodes numbered independently cannot be placed on one time axis, and the question a history answers — *what did the quilt look like then* — is about a moment, not about a node.

**[decided]** A **version** is addressed `rl-0001@3`: the text key `rl-0001` had at step 3. The step may be named instead of numbered, by its name — the landmark it kept, `rl-0001@paper-v2`, or a stamp's `rl-0001@stamp-referee-points`. A proof is addressed like any other key: `rl-0001/proof@3`.

**[decided]** A key that did not move at a step has no file in that step's directory, and `rl-0001@3` then means the version it still had, carried forward from the step that last recorded it. Gaps are meaningful: they say the text did not change.

## 17.5 Keys and versions

**[decided]** Versions are per key — a statement by its id, a proof by `<id>/proof` or its own id — because that is the unit acceptance, hashing and annotation already use (3.3). Sections and qualified keys are never versioned: a section's text is its prose between its children, and a landmark holds the document itself, which says the same thing better.

**[decided]** A proof's version records the statement version it stood against, as `of: rl-0001@2`. Three cases follow from it, and telling them apart is why the field exists: the statement changed and the proof did not; the proof changed and the statement did not; both changed together.

**[decided]** Each step records the preamble that compiled it, as a hash and a copy, when it differs from the last one recorded. A version's text is only meaningful with the macros that were in force.

**[decided]** A version's text is the key's **raw own text**, comments and directives included, with a `% !LOOM child: KEY` marker where each child was cut out (5.13). Restoring it materializes those markers from the head's current children, so a version is exact when its children still exist and is refused when one does not. This is the price of storing a node once rather than storing every node's full subtree at every step, and it is stated so that nobody is surprised by it.

## 17.6 The ledger line

**[decided]** Every event is one line of `ledger.jsonl`. Common fields: `when` (ISO 8601 UTC), `actor` (the author's name, or `null` — a record of what loom was told never refuses for want of a name), `action`. Steps add `step` and `dir`.

| action | what else the line carries |
|---|---|
| `import` | `from` (the paper's name and hash), `landmark` (the file the step keeps), `to` (that file and its hash), `inlined`, `drafted` (the working document's path and hash, and how many ids it took), `froze` (empty), `preamble` |
| `stamp` | `message`, `in` (the document given, or null), `froze` (key to hash), `of`, `removed`, `restored`, `preamble`; given a document, also `landmark`, `to`, `reaches` (17.9) |
| `copy` | `from` (the source document), `to` (the agent's copy), `bases` (each derived key to `{key, step, hash}`: its plain key, the step whose version is its base, that version's hash), `froze`, `of`, `restored`, `preamble` |
| `restore` | `from` (`{landmark, step}`), `to` (the new document's path and hash), `ids` (how many were inserted) |
| `atomize` | `from`, `to`, `keys`, `superseded`, `retired` |
| `linearize` | `from`, `to`, `superseded`, `forks`, `kept` |
| `fork` | `new`, `from` (id, step, hash), `in`, `to` |
| `revert` | `key`, `step`, `hash`, `in` |
| `live` | `path` |
| `move` | `from`, `to`, `moved` (whether loom renamed the file), `via` (`"sync"` when an incorporated pull recorded it, else absent) |

**[decided]** The line is written **last**, after the step's directory and every file in it. A step that was interrupted leaves a directory the ledger does not name, which `loom history verify` reports and nothing reads.

## 17.7 `loom draft`

**[decided]** `loom draft` has one job, the copy across the border into the agent's drafting directory (17.7.1). Starting a working document from an old version of one is `loom history restore` (17.9).

### 17.7.1 The copy across the border

**[decided]** `loom draft DOC --ai NAME [--json]` copies a live document of the drafting directory into the agent's drafting directory (4.4) as `NAME`, for the person and an agent to edit together. It is the author's command; an agent cannot run it (11.8).

- **The copy is flat**: every inclusion expanded, as `loom linearize` expands them, so an agent edits one file and never the person's node files through an `\input`.
- **Every label the copy defines is derived** — an id becomes its derived id (`dm-0001` → `dm-0001-ai`, 5.3.1), and any other label takes the same suffix (`eq:fix` → `eq:fix-ai`), since labels are claimed quilt-wide — and every reference to one of them is rewritten. A reference to a label the copy does not define is left as it is.
- **One copy per document.** A second copy of the same document is refused, naming the first; so is a `NAME` that exists or whose stem another live document has.
- **A `copy` step records what each node began from.** It freezes, as a stamp does, every key the document reaches whose text no step records yet, so that every **base** is a version loom can read back; the line maps each derived key to its base, `dm-0002-ai` → `dm-0002@1`. The step keeps the source's flat text under the source's own file name, which is what the prose between nodes and the preamble are later compared against. A copy's bases are read from its `copy` line, the copy's path followed across moves; the manifest carries a copy's `copy_of` and each derived node's `base`.

**[decided]** **A copy is stale** when the person's side has moved past it: a node it was based on changed mathematically since its base — a display name alone is no change (5.13) — or left the source, or the source's prose between nodes, or its preamble, is not what the copy step recorded. Comment lines are no prose. `loom ai drafts [--json]` lists each copy, its source, and what moved; an agent checks it before a large instruction on a copy and suggests refreshing a stale one rather than working against text the person has since changed (Appendix D).

## 17.8 `loom stamp`

**[decided]** `loom stamp [DOCUMENT] -m MESSAGE [--json]` records a step. A message is required, as for a commit: a step nobody named is a step nobody can ask for.

**[decided]** Without DOCUMENT, the stamp records every key whose text has moved since the last step, quilt-wide, and keeps no document; its directory is `NNNN-stamp-<slug>`, the slug of the message. It refuses when nothing has moved, naming the last step.

**[decided]** Given DOCUMENT, a live document of the drafting directory, the stamp records only the keys that document reaches, and keeps the document's flat text as a landmark named by the message (17.9). It is recorded even when no key has moved, since the landmark is worth keeping on its own.

Example: an author with a paper and a talk runs `loom stamp drafting/talk.tex -m "Talk v1"` before giving the talk. The talk's keys that moved are recorded and the paper's are not, because they did not; the landmark `talk-v1` keeps the talk as given.

**[decided]** Stamping changes no acceptance and no review. A landmark is not a review, and Chapter 7's states are untouched by it.

## 17.9 Landmarks

**[decided]** A landmark is how a document stood at a moment worth returning to. Two steps keep one: `loom import`, whose landmark is the paper as received (6.2), and a stamp given a document (17.8). No other step does: a stamp without a document records keys only, and the copy step of `loom draft --ai` keeps its source's text to compare against later (17.7.1), not as a landmark.

**[decided]** A stamp's landmark is the document's **loom form**: flattened as `loom linearize` flattens (17.13), with `\usepackage{loom}` and its ids, so that a working document can be drafted from it again. It is kept as `<name>.tex` in the step's directory `NNNN-<name>/`, where `<name>` is the slug of the message (`-m "Widgets v3"` gives `widgets-v3`), and the line carries `landmark` (that file), `to` (that file and its hash), `in` (the document) and `reaches` (the keys the document reaches). An import's landmark is the paper as received, with neither the package line nor ids, named by the slug of the paper's file name (`draft3`).

**[decided]** A landmark is named by its name (`widgets-v3`), by its step's number (`5` or `0005`), or as `DOC@STEP`, the document's stem and the step (`main@5`). A name is used once: `stamp` refuses a name a landmark already has. It also refuses a DOCUMENT that is not live in the drafting directory, and one that reaches a conflicted id (5.3.5), because a landmark needs one text per key.

**[decided]** `loom history show LANDMARK [--plain] [--json]` prints a landmark's text as its step kept it. `--plain` prints it without loom: `\usepackage{loom}` replaced by the package's macros in a marked block (17.13), so the paper compiles on its own where loom.sty is not — the text a journal or arXiv is sent.

**[decided]** `loom history restore LANDMARK --to FILE [--json]` writes FILE, a new working document directly in the drafting directory, from a landmark: the package line in place of any macro block and an id on every node that has none (6.3). It refuses a FILE that exists and a landmark whose text cannot take ids as it stands, naming the lines. It is the author's command; an agent cannot run it (11.8). It appends a `restore` line: `from` (the landmark and its step), `to` (FILE and its hash) and `ids` (how many were inserted). A restored document defines the ids its landmark carried, so while the document it was stamped from is still live, those ids are conflicted (5.3.5); `restore` says so, and `loom fork` or retiring one of the two documents resolves each.

**[decided]** A landmark lives in the history, which the scan never enters (4.1), so it defines nothing and never collides with the working text it came from. The build renders each landmark as a document of its own (9.3), and the quilt's bibliography is gathered from the landmarks (8.15). When no live document is left in the drafting directory, `loom:no-live-document` offers `loom history restore <newest landmark> --to <drafting>/main.tex`.

## 17.10 `loom fork`

**[decided]** `loom fork ID --in DOCUMENT [--from @N] [--as ID2] [--json]` gives one document its own copy of a node under a new id. The text comes from the head, or from a recorded version with `--from`. The new id is allocated as `loom new` allocates one, or named with `--as`.

**[decided]** What it writes depends on how the document holds the node. When the document includes a node file, loom writes `nodes/<ID2>.tex` and prints the patch that points the document's inclusion at it. When the document defines the node inline, loom prints the patch and writes nothing. References to the old id **inside that document** are rewritten in the patch; references anywhere else are left alone and reported, because whether they should follow the fork is a mathematical question.

**[decided]** The ledger records the ancestry: `{new, from: {id, step, hash}, in}`. Provenance is a line in the record, never a prefix in the id, which would go on saying "this was forked" long after it stopped mattering.

**[decided]** Annotations are not copied. An objection to the paper's lemma is not automatically an objection to the talk's.

## 17.11 `loom revert`

**[decided]** `loom revert KEY@N` prints the patch that puts the recorded text back in place of the head's. It materializes the version (17.5) and never points at it: after the patch is applied the file holds that text, and nothing in the quilt refers to a version to find out what a node says.

**[decided]** Applying the patch is the author's act, as it is for `atomize --key` and `loom id`. Loom prints; the editor applies.

## 17.12 Superseded documents and `loom live`

**[decided]** A conversion knows with certainty that its output replaced its input. `loom atomize` and `loom linearize` record it: the ledger line names the file in `superseded`, and from that moment the file is not scanned, defines nothing, and is not a master. `loom:superseded-file` (info, subject `record`) says so once per file, with `loom live FILE` as its fix.

**[decided]** This is the only inertness loom declares by itself. Everything else in the drafting directory is live. `% !LOOM ignore` remains the author's way to say the same thing about a file loom did not produce (4.9).

**[decided]** `loom live FILE` appends a line that makes the file live again. Nothing is moved and nothing is edited; the record simply says the conversion no longer stands.

**[decided]** `atomize --retire` moves the input into `retired/` instead, which is not scanned either. It is opt-in because loom moves an author's file only when asked (4.8), and it exists because an author who has finished with a file would rather it were out of the way than inert in place.

**[decided]** **Where a document is now** is the history's to say (DR-297-ikmartin). A conversion's line records a move: `linearize` from its `from` to its `to`, `atomize` from each path in `from` to the path at the same place in `to`. So does a `move` line, from its `from` to its `to`, whether `loom mv` renamed the file, recorded a rename made elsewhere, or an incorporated pull found a collaborator's exact rename (4.4, 4.6, DR-298-ikmartin); a `move` line also makes its `to` a document of its own again, neither superseded nor leading anywhere, since a document now stands there. A path that is a live document is itself. Otherwise the latest line that moved it names its successor, and a later `live` line makes it its own again; the walk follows successors until it reaches a live document, and a path with no successor that is not live is gone. `retired/` is never a successor: `atomize --retire` sends the document to its spine like any atomize, and the retired copy is not a document. Every record that names a document by path is resolved this way whenever it is read and never rewritten: an acceptance row's `master` (7.3), an annotation's `in` and a whole-document target (7.4.2, 7.5.4), and the sync record's main and selected documents (4.6). `loom live` therefore undoes a move for everything that follows it.

## 17.13 `loom linearize`

**[decided]** `loom linearize SPINE --to FILE [--fork | --keep-shared] [--no-check]` writes FILE: SPINE with every `\input`, `\include` and `\nest` of a `.tex` file expanded in place, `\nest`'s level shift applied to what it brings in, and every comment and directive kept. It is the whole-document counterpart of `inline`, which reverses one atomization (6.6), and it replaces `loom assemble`, which did the same thing and knew nothing about identity.

**[decided]** A node is defined once and included many times (5.3.5). Inlining a node file that another live document also includes would define that node twice, so `linearize` refuses, names the nodes and both documents, and offers two continuations:

- `--fork` gives this document its own copy of each shared node under a new id, and prints the mapping.
- `--keep-shared` leaves those inclusions as inclusions and writes the reason above each: `% !LOOM shared: nodes/rl-0001.tex is also included by drafting/talk.tex -- `loom fork rl-0001 --in drafting/paper-flat.tex` to split`. The result is not flat, and the comment says why, so that the next reader does not "fix" it.

**[decided]** `loom history show --plain` prints a landmark with `loom.sty`'s macros inline, between `% !LOOM begin loom-macros` and `% !LOOM end loom-macros`, in place of `\usepackage{loom}`. `\uses` and `\incomplete` survive into the plain text, the file compiles where loom.sty is not, and `\providecommand` makes the block harmless in a quilt that also loads the package. Drafting from a text that carries the block, by `loom import` or `loom history restore`, swaps it back for the package line (6.3).

## 17.14 Retired ids, recovery and reuse

**[decided]** An id the history has recorded is never allocated again. The allocator consults, on every call, the ids visible in the source, the acceptance ledger, the annotations, git history where there is any, **and the history ledger and its step directories** (5.3.2). A **retired id** is one the history holds and no live document defines.

**[decided]** A file that appears again under a retired id is one of two things, and loom tells them apart by content:

- Its text is one the history recorded for that id: the node is **recovered**. `loom:node-recovered` (info) says so, and the next step records it as restored. This is what `loom revert` produces by construction.
- Its text is one the history never recorded: the id has been **reused**. `loom:id-reused` (error) says so and offers two fixes — take a fresh id for a new node, or record a stamp if it really is the old node revised.

**[decided]** Deletion is absence. A node whose file is gone and whose inclusion is gone is removed; the next step records it in `removed`, and the versions of it stay where they were.

## 17.15 When the record and the files diverge

**[decided]** Four things can be found, and each is reported with the commands that would resolve it. None of them stops a build.

| code | severity | what it means |
|---|---|---|
| `loom:history-edited` | error | a version file, a preamble, or a step's document — a landmark, or a copy step's source — does not hash to what the ledger recorded. |
| `loom:history-missing` | error | a step directory or one of its files is gone. |
| `loom:history-corrupt` | error | a line of the ledger cannot be read, or a step number does not follow the last. |
| `loom:dangling-ancestry` | warning | a `fork`, `revert`, `restore` or `copy` line names a step, a landmark or a version the history no longer resolves. |

**[decided]** A ledger that cannot be read in full is reported as `loom:history-corrupt` on every scan, because every reading of the history depends on it. The rest are checked by `loom lint` and `loom history verify`, which walk every step directory, because a quilt with fifty steps should not re-read them on every keystroke of `loom serve`.

## 17.16 Reading the record

**[decided]** `loom history` prints the steps and the events between them, one per line: the number, the action, the date, the name and message of a step, and how many keys it recorded. `loom history KEY` prints that key's versions, each with its hash and the step that recorded it, and says whether the head is one of them. `loom history show` and `loom history restore` read a landmark (17.9).

**[decided]** `loom history verify` walks every step directory against the ledger and reports the divergences of 17.15; it exits 1 on any error. `loom lint --nodes` is the other reading: one block per node id, carrying what is wrong with that node's identity — conflicted, unreachable, referenced but absent, reused, recovered — and then the superseded files. It is the hygiene report for the rule of 5.3.5.

## 17.17 A worked timeline

The synthetic quilt (14.3) carries one, produced by the commands themselves:

| step | when | what |
|---|---|---|
| `0001-widgets-v1` | 09-13 | `stamp drafting/main.tex -m widgets-v1` keeps the first landmark; every key the paper reaches is recorded as first written |
| — | 09-14 | `accept` records six keys; the author then rewrites the definition, and its dependents go stale |
| `0002-stamp-referee-points` | 09-15 | `stamp -m "Referee points"` records the definition that moved, and three keys the first landmark did not reach: a loose lemma and the digest's two results |
| — | 09-15 | `fork` gives the talk its own copy of a proposition; the author applies the patch |
| `0003-widgets-v2` | 09-15 | the second landmark; no key the paper reaches has moved, so it records the document alone |
| — | 09-15 | an edit, then `revert` puts the recorded text back: the head is again the text of `@1` |
| `0004-stamp-talk-prepared` | 09-15 | `stamp -m "Talk prepared"` records the talk's own copy, the only keys that moved |
| `0005-widgets-v3` | 09-15 | a lemma is dropped and the third landmark records it as removed; its id is retired |
| `0006-copy-aidoc` | 09-16 | `draft drafting/main.tex --ai aidoc.tex` copies the paper for an agent (17.7.1) |

**[decided]** The quilt is generated by `loom/scripts/gen_quilts.py`, which runs exactly these commands under a fixed clock, so the record is made the way an author's is and a test can prove the checked-in copy is what the commands write.

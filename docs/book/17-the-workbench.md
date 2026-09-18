# 17. The workbench

Chapter 6 brings a paper in; Chapter 7 records what has been reviewed. This chapter is about the third thing a paper has: a history. It specifies the two states a document is in, the record loom keeps of the passage between them, how a key's text at a past moment is named and read back, and what loom does when the record and the files disagree.

## 17.1 The two states

**[decided]** A document is either being worked on or fixed as a landmark, and where it sits says which.

- The **drafting directory** (`[quilt] drafting`, by default `drafting/`) holds the documents being worked on. Every one of them is live: it defines the nodes it holds inline, it is a master, it is scanned, compiled, rendered and reviewed. This is where the author writes.
- The **canon directory** (`[quilt] canon`, by default `canon/`) holds the landmarks. Each is one flat, self-contained file: every inclusion expanded in place, `loom.sty`'s macros carried inline, nothing to resolve. It compiles on its own in an empty directory. It is never scanned, so it defines nothing and can never collide with the working text it was copied from. Arras shows it as a document.

**[decided]** Placement is the declaration, not a property loom computes. A file cannot say whether it is being worked on; the directory can. This is the same answer the masters directory has always given (1.3, sign 10), and the rejected alternative — a list of live files somewhere — is a second source of truth (sign 4).

**[decided]** The passage between the two states is what leaves a trail. `loom canonize` writes a landmark and records, at that moment, what every key in the quilt was. `loom draft` copies a landmark back into the drafting directory to work on. Everything in this chapter exists so that the sentence "what did this lemma say when we submitted?" has an answer that does not depend on the quilt being in version control.

**[decided]** P13 governs every check here: *loom verifies what it can, reports what diverges, repairs nothing, and never blocks work.* The head is always the files on disk. The history is a log of what loom was told, never a claim about the filesystem.

## 17.2 The record

**[decided]** The history lives under `.loom/history/`, hidden, beside the acceptance ledger:

```
.loom/
  state.toml                   the acceptance ledger (7.2)
  history/
    ledger.jsonl               one JSON object per line, appended only
    0001-paper/                a step: the document as written, and one file per key
      paper.tex
      preamble.tex
      rl-0001.tex
      rl-0001.proof.tex
    0003-stamp-referee-points/
      rl-0004.tex
    texts/                     content-addressed text: snapshots, versions, anchors
      3f9a....tex
```

**[decided]** `texts/` is one store, shared by acceptance snapshots (7.2.2), by anything a version points at, and by the anchors of Chapter 0.10 when they arrive. Files in it are named by the sha256 of their normalized text, so identical text is stored once and nothing is ever overwritten. `loom upgrade` moves a pre-0.9 `.loom/snapshots/` into it; every hash still resolves, which is why the move is safe.

**[decided]** The history is not a backup and does not try to be. It holds the text of a key at the moments loom was told to record one, the document as it stood at each of those moments, and the preamble that compiled them. It does not hold the files in between, and it does not hold anything about a file the quilt does not define a key in.

**[decided]** `[quilt] history` names the directory and defaults to `.loom/history`. `loom init` does not write the key: a quilt that never moves its record does not need a line saying where it is.

## 17.3 Three tiers

**[decided]** Three kinds of thing are recorded, and only three:

1. **Steps** — the events that create a directory and a version of every key that moved: `loom import` (the paper arrives) and `loom canonize` (a landmark is written). A step is what an author points at later: *the submitted version*.
2. **Stamps** — the same recording without a landmark: `loom stamp -m "Referee points"` records every key whose text has moved since the last step and writes no document. A stamp is also a step in the numbering; it differs in that no canon file is written.
3. **Anchors** — named positions inside a text, used by annotations. Defined in the annotation plan (0.10) and not in this chapter.

**[decided]** Nothing is recorded on save. Loom does not watch the filesystem for the purpose of recording history, and a quilt that is never canonized or stamped has an empty ledger and works exactly as it did before this chapter existed.

## 17.4 Numbering and addresses

**[decided]** Steps are numbered once over the whole quilt, `0001`, `0002`, `0003`, whether the step canonized the paper, the talk, or nothing at all. There is no per-node counter: two nodes numbered independently cannot be placed on one time axis, and the question a history answers — *what did the quilt look like then* — is about a moment, not about a node.

**[decided]** A **version** is addressed `rl-0001@3`: the text key `rl-0001` had at step 3. The step may be named instead of numbered, by the landmark it wrote: `rl-0001@paper-v2`. A proof is addressed like any other key: `rl-0001/proof@3`.

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
| `import` | `from` (the paper's name and hash), `to` (the canon path and hash), `inlined` |
| `canonize` | `message`, `document`, `live`, `from`, `to`, `froze` (key to hash), `of`, `reaches`, `removed`, `restored`, `preamble`, `parent` |
| `stamp` | `message`, `in` (a document, or null), `froze`, `of`, `removed`, `restored`, `preamble` |
| `draft` | `from` (canon path, hash, step), `to`, `ids`, `moved` |
| `atomize` | `from`, `to`, `keys`, `superseded`, `retired` |
| `linearize` | `from`, `to`, `superseded`, `forks`, `kept` |
| `fork` | `new`, `from` (id, step, hash), `in`, `to` |
| `revert` | `key`, `step`, `hash`, `in` |
| `live` | `path` |

**[decided]** `parent` says which step this one continues: `{step, how: "declared"}` when the author said so or a `draft` line recorded where the document came from, `{step, how: "inferred", matched, of}` when loom matched key hashes against the recorded states, and `{how: "unknown"}` when nothing was shared. A history is a log, not a graph the author maintains; the parent is loom's best reading of it and says which it is.

**[decided]** A run is referenced by its directory name, which is its id (11.4). Nothing in the history refers to a run by any other name.

**[decided]** The line is written **last**, after the step's directory and every file in it. A step that was interrupted leaves a directory the ledger does not name, which `loom history verify` reports and nothing reads.

## 17.7 `loom draft`

**[decided]** `loom draft CANON [--to FILE] [--no-ids] [--fix-anchoring] [--prefix P] [--no-check] [--yes]` copies a canon document into the drafting directory as a working document. It inserts the two things a working document needs and a landmark must not carry: `\usepackage{loom}` in place of the macro block (17.13), and an id on every node that has none (6.3). The canon document is not touched.

**[decided]** The copy is live because of where it sits. The ledger line records where it came from, including the step, so that the landmark it continues is known without the author saying so.

**[decided]** When the canon file's text is not the text its step recorded, `draft` says so (`loom:canon-edited`) and drafts from the file as it is. The head is always the files on disk.

## 17.8 `loom canonize`

**[decided]** `loom canonize DOCUMENT [--to FILE] -m MESSAGE [--no-check] [--parent N] [--json]` writes DOCUMENT as one flat, self-contained canon file and records a step. A message is required, as for a commit: a landmark nobody named is a landmark nobody can ask for.

**[decided]** The command is document-scoped and the step is quilt-scoped. The canon file is one document; the step records every key in the quilt whose text has moved, and names separately the keys the document reaches (`reaches`). An author with a paper and a talk canonizing the paper has recorded the talk's nodes too, because they were part of the quilt at that moment, and can see which belonged to the paper.

**[decided]** `canonize` refuses a document that reaches a conflicted id (5.3.5) or an environment that spans files: a landmark needs one text per key. It warns, records `live: false`, and proceeds for a document that is superseded, ignored, or outside the drafting directory, because recording what such a file was is harmless and refusing would be an obstruction.

**[decided]** Canonizing changes no acceptance and no review. A landmark is not a review, and Chapter 7's states are untouched by it.

**[decided]** `canonicalize` and `canonise` run `canonize` and print `canonicalize → canonize` on the way. A silent alias teaches the wrong name.

## 17.9 `loom stamp`

**[decided]** `loom stamp -m MESSAGE [--in DOCUMENT] [--json]` records a step with no canon file: every key whose text has moved since the last step, quilt-wide, or only those one document reaches with `--in`. It refuses when nothing has moved, naming the last step.

Example: an author with a paper and a talk stamps `--in drafting/talk.tex` after a morning on the slides, and the paper's keys are not recorded as having changed, because they did not.

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

**[decided]** `atomize --retire` moves the input into `retired/` instead, which is not scanned either. It is opt-in because moving an author's file is the one thing 4.8 otherwise forbids, and it exists because an author who has finished with a file would rather it were out of the way than inert in place.

## 17.13 `loom linearize`

**[decided]** `loom linearize SPINE --to FILE [--fork | --keep-shared] [--no-check]` writes FILE: SPINE with every `\input`, `\include` and `\nest` of a `.tex` file expanded in place, `\nest`'s level shift applied to what it brings in, and every comment and directive kept. It is the whole-document counterpart of `inline`, which reverses one atomization (6.6), and it replaces `loom assemble`, which did the same thing and knew nothing about identity.

**[decided]** A node is defined once and included many times (5.3.5). Inlining a node file that another live document also includes would define that node twice, so `linearize` refuses, names the nodes and both documents, and offers two continuations:

- `--fork` gives this document its own copy of each shared node under a new id, and prints the mapping.
- `--keep-shared` leaves those inclusions as inclusions and writes the reason above each: `% !LOOM shared: nodes/rl-0001.tex is also included by drafting/talk.tex -- `loom fork rl-0001 --in drafting/paper-flat.tex` to split`. The result is not flat, and the comment says why, so that the next reader does not "fix" it.

**[decided]** A canon document carries `loom.sty`'s macros inline, between `% !LOOM begin loom-macros` and `% !LOOM end loom-macros`, in place of `\usepackage{loom}`. `\uses` and `\incomplete` survive into the landmark, the file compiles where loom.sty is not, and `\providecommand` makes the block harmless in a quilt that also loads the package. `loom draft` swaps the block back for the package line.

## 17.14 Retired ids, recovery and reuse

**[decided]** An id the history has recorded is never allocated again. The allocator consults, on every call, the ids visible in the source, the acceptance ledger, the annotations, git history where there is any, **and the history ledger and its step directories** (5.3.2). A **retired id** is one the history holds and no live document defines.

**[decided]** A file that appears again under a retired id is one of two things, and loom tells them apart by content:

- Its text is one the history recorded for that id: the node is **recovered**. `loom:node-recovered` (info) says so, and the next step records it as restored. This is what `loom revert` produces by construction.
- Its text is one the history never recorded: the id has been **reused**. `loom:id-reused` (error) says so and offers two fixes — take a fresh id for a new node, or record a stamp if it really is the old node revised.

**[decided]** Deletion is absence. A node whose file is gone and whose inclusion is gone is removed; the next step records it in `removed`, and the versions of it stay where they were.

## 17.15 When the record and the files diverge

**[decided]** Five things can be found, and each is reported with the commands that would resolve it. None of them stops a build.

| code | severity | what it means |
|---|---|---|
| `loom:canon-edited` | warning | a canon document is not the text its step recorded. The step keeps its own copy; the fixes are to restore it or to work on it as a draft. |
| `loom:history-edited` | error | a version file, a preamble, or a step's document copy does not hash to what the ledger recorded. |
| `loom:history-missing` | error | a step directory or one of its files is gone. |
| `loom:history-corrupt` | error | a line of the ledger cannot be read, or a step number does not follow the last. |
| `loom:dangling-ancestry` | warning | a `fork`, `revert`, or `draft` line names a step or a version the history no longer resolves. |

**[decided]** `loom:canon-edited` is checked on every scan, because it costs one hash per canon document and the answer matters to `draft`. The rest are checked by `loom lint` and `loom history verify`, which walk every step directory, because a quilt with fifty steps should not re-read them on every keystroke of `loom serve`.

## 17.16 Reading the record

**[decided]** `loom history` prints the steps and the events between them, one per line: the number, the action, the date, the name and message of a step, and how many keys it recorded. `loom history KEY` prints that key's versions, each with its hash and the step that recorded it, and says whether the head is one of them.

**[decided]** `loom history verify` walks every step directory against the ledger and reports the divergences of 17.15; it exits 1 on any error. `loom lint --nodes` is the other reading: one block per node id, carrying what is wrong with that node's identity — conflicted, unreachable, referenced but absent, reused, recovered — and then the superseded files. It is the hygiene report for the rule of 5.3.5.

**[decided]** `loom upgrade` brings a quilt written before 0.9 to this layout: `.loom/snapshots/` moves into `history/texts/`, and `[quilt] drafts` is renamed `drafting` in `config.toml` with nothing moved on disk. Both are idempotent.

## 17.17 A worked timeline

The synthetic quilt (14.3) carries one, produced by the commands themselves:

| step | when | what |
|---|---|---|
| `0001-widgets-v1` | 09-13 | `canonize` writes the first landmark; every key is recorded as first written |
| — | 09-14 | `accept` records six keys; the author then rewrites the definition, and its dependents go stale |
| `0002-stamp-referee-points` | 09-15 | `stamp` records the one key that moved |
| — | 09-15 | `fork` gives the talk its own copy of a proposition; the author applies the patch |
| `0003-widgets-v2` | 09-15 | `canonize` writes the second landmark, freezing the fork with everything else |
| — | 09-15 | an edit, then `revert` puts the recorded text back: the head is again the text of `@1` |
| `0004-stamp-talk-prepared` | 09-15 | `stamp --in drafting/talk.tex` records the talk's own copy and nothing else |
| `0005-widgets-v3` | 09-15 | a lemma is dropped and the third landmark records it as removed; its id is retired |

**[decided]** The quilt is generated by `loom/scripts/gen_quilts.py`, which runs exactly these commands under a fixed clock, so the record is made the way an author's is and a test can prove the checked-in copy is what the commands write.

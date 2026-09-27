# AI drafting: a study

A design for documents that a person and an agent both edit, worked out with the author on 2026-09-26, to be built as plan 0.17. Plan 0.16 comes first and fixes the record defect of §4, on which this depends. It replaces the nested-quilt design of [WQ-24](../work-queue/WQ-24-ai-quilt.md), takes the fork-and-merge half of [WQ-29](../work-queue/WQ-29-node-manager.md) and the apply step of [WQ-33](../work-queue/WQ-33-the-proposed-document.md), and folds `canon/` into the history.

Part one is the settled design. Part two is the adoption analysis that produced its central decision, kept whole because the plan that builds this and the book chapter that documents it must both carry it. Part three is what is still open, part four what the design touches.

**A requirement on the documentation.** When this is built, the book's account of it carries worked examples in the manner of §6 and §8 below — a named document followed from copy to adoption, and the four cases of §8.1 with what each mode does to them. Plan 0.17 carries §8 in full.

## Part one: the design

### 1. Two directories and a border

- **`drafting/` holds the documents only the person edits.** It is what the quilt is: what Review tracks, what `loom accept` records, what Overleaf sync publishes.
- **`drafting-ai/` holds the documents the person and an agent both edit.** Nothing there is reviewed or accepted while it changes, and nothing there is published: Overleaf sync never selects a document from it.
- **Each has its own setting.** `[quilt] drafting` (default `drafting`) and a new `[quilt] drafting_ai` (default `drafting-ai`). The second is a setting and not derived from the first, so that renaming one directory without the other is a visible mismatch in the config rather than a silent change of meaning.
- **`drafting-ai/` is a directory of the author's content, not of loom's.** It is not under `ai/`, which holds the agent layer's templates that `loom upgrade` refreshes and the managed gitignore reaches into, and which the scan excludes whole (book 4.1.2). The scan reads `drafting-ai/` as a second drafting directory, and its documents are live in the same sense.
- **The border is the permission file.** An agent's `.claude/settings.json` allows `Edit` under `.loom/sessions/` and `build/` today and nowhere else; adding `drafting-ai/**` is the whole of an agent's write access to documents.
- **A document crosses the border by copying.** Both copies are live at once, which is the point: the person keeps writing in `drafting/` while an agent works in `drafting-ai/`.
- The pairing reads the same at both levels: `zk-0001-ai` is defined in `drafting-ai/`. Paths inside a document are root-relative (book 4.4.4), so where the directory sits changes no `\input`.

### 2. Identity: a derived id per copy

Two live documents may not define one id (`duplicate-id`, book 5.3), so a copy cannot keep its ids. Every node the copy defines takes a **derived id**: `zk-0001` in `drafting/draft1.tex` is `zk-0001-ai` in `drafting-ai/aidoc.tex`.

- **The pair is in the id.** `zk-0001-ai` names its counterpart whatever either file is called and wherever it moves, found by stripping a suffix rather than by a lookup table.
- **References to the person's nodes stay plain.** An agent's document may cite `zk-0005`, which it did not copy. The person's documents never cite a `-ai` id; lint refuses it.
- **The setting is `drafting_ai`** (§1).
- **A node the agent writes takes a number from the person's allocator** and wears the suffix: `zk-0012-ai`. The number is reserved, so on adoption it becomes `zk-0012` with no collision. There is one id space. The allocator's pattern already sees `zk-0001` inside `zk-0001-ai`; the scanner, lint and arras learn that the suffixed form is derived.
- **A derived id cannot be accepted.** `loom accept` refuses it; acceptance belongs to the node it becomes.
- **One agent copy per document.** `loom draft DOC --ai` refuses when a copy of DOC exists, naming it. Different agents work in the same copy one after another, which is the common case; nothing fills `drafting-ai/` with copies. If several simultaneous copies are ever wanted — comparing versions side by side — the suffix numbers them in base 36 (`-ai-01` … `-ai-0Z`, `-ai-10` … `-ai-ZZ`), and that is added only if it is both simple to build and simple to use.

`loom fork` already gives a file its own copy of a node under a new id with its references rewritten; the copy is that operation over every node of a document, with a derived id in place of a fresh one.

### 3. The copy is flat, and each node records its base

`loom draft drafting/draft1.tex --ai aidoc.tex` writes `drafting-ai/aidoc.tex`:

- **Flat**, every inclusion expanded as `loom inline` does. An atomized document's node files are the person's; a copy of the spine alone would leave an agent editing them through `\input`.
- **Every defined id derived**, and the references to them rewritten.
- **A base per node**, recorded as one history line: `zk-0001-ai` began from `zk-0001@3`, and so on for each node. The base is what makes both copies safe to edit at once, since it is what tells a later merge who changed what.

### 4. History between documents

**Identity and history belong to nodes.** A node's versions are `key@N`. A document is a spine — a path whose reach the scan recomputes each time — with no identity of its own; the history names documents only at events, a landmark saying which document it froze and a conversion recording `from`, `to` and what it superseded.

- **No link between `draft1.tex` and `aidoc.tex` is needed.** The correspondence is in the ids, and the base is per node and names keys, not files, so either document may be renamed or moved without losing anything.
- **Records that name a document by path are the exception, and they are a defect today, independent of this design.** An acceptance row records the document it was compiled against (`--master`, DR-298-luisa) and an annotation may record the document it is read in (`in`, DR-291-ikmartin). Freshness looks up the recorded document's preamble (`records/store.py:125`); a document that is gone — superseded by a conversion, or renamed by hand — has none, and every row accepted against it reports `preamble-changed`. Such records must follow a document across the conversions that record `from` and `to`, and a hand rename needs either a `loom` command for it or detection by content. This is fixed first, as plan 0.16: it was confirmed on 2026-09-26 by accepting `dm-0001` in a copy of the demo quilt and linearizing `drafting/main.tex`, after which `dm-0001` was stale with `preamble-changed` though neither its text nor the preamble had moved.

### 5. Staleness and refreshing

After an adoption the agent's copy stays, and the adoption is recorded in the history as a step naming the copy and what was taken. A copy is **stale** when the person's side has moved past a node's base: a node's text, the document's text between its nodes, or the preamble.

- `loom ai drafts` lists each agent document with, when stale, what moved on the person's side.
- The orientation tells an agent to check before a large instruction: a stale copy is flagged, and the agent suggests refreshing it before starting.
- **Refreshing is adoption in the other direction.** Both people edit the copy, so replacing it would discard what was written there since the base; the person's changes are merged in under the same contract as §7, conflicts shown, and the bases move forward.

### 6. The workflow, as the author first posed it

The scenario that framed the question of how the two documents relate:

1. `draft1.tex` is copied into the agent's directory with `loom draft draft1.tex --ai aidoc.tex`, which creates `aidoc.tex` identical to `draft1.tex` except that every node carries the `-ai` suffix.
2. The person and an agent both edit `aidoc.tex`; `draft1.tex` is not touched.
3. `loom adopt aidoc.tex draft2.tex` puts a copy of `aidoc.tex` in `drafting/`, suffixes kept.
4. Review is used to take or reject changes, and after it the taken nodes become the new head.

Steps 1 and 2 stand. Steps 3 and 4 raised the question of what happens to `draft1.tex`, which §8 answers; the same scenario under the settled design is §8.5.

### 7. Adoption writes where each node lives, and says so

`loom adopt aidoc.tex` treats the agent's copy as an incoming revision of the documents and node files its nodes came from, as Review's Incoming view treats a collaborator's pull (§8.4). It is reviewed node by node in that view, each changed node beside its counterpart and its base, with take and keep and a lazy take-all, and nothing is written until the review is finished.

- **In arras, Finish writes in place**, under Incorporate pull's contract: the exact change is shown first, it is refused while an affected file has uncommitted edits, a conflict stops it before any file changes, and it is committed as one commit.
- **At the command line, it writes a patch.** `loom adopt` prints (or with `--to` writes) the patch and applies nothing; the person applies it with `git apply`. This is how `loom revert` and `loom id` already work.
- Either way the history records each taken node's new version, and the copy's bases move forward.
- **Loom is not an editor.** It writes the person's files only where a change is exact and was reviewed, and it always shows what it is about to write. That is the whole of the exception.

### 8. The adoption analysis

#### 8.1 The fact that decides it, and four examples

A node's text lives in exactly one file: inline in a live document, where only that document can show it, or in a node file (`nodes/zk-0001.tex`), which any number of documents can `\input`. "The adopted version becomes the head" means that one file comes to hold the new text; what happens to `draft1.tex` is a question about where each adopted node lives.

- **E1, a revision.** A single-file paper `draft1.tex` defines every node inline. An agent rewrites section 2 in its copy, and the person wants the paper improved.
- **E2, a shared lemma.** `main.tex` and `talk.tex` both `\input nodes/zk-0003.tex`. An agent improves the lemma in its copy of `main`, and the person wants both documents to have it.
- **E3, a derivative.** The person asks for a talk version of the paper. The copy cuts proofs and shortens lemmas, and the person wants a new document with the paper left alone.
- **E4, more than one document defines the nodes.** `part1.tex` and `part2.tex` each define nodes inline. In its copy of `part1`, an agent pulls in a lemma from `part2`: `zk-0040-ai`, where `zk-0040` is inline in `part2`.

#### 8.2 Four candidate resolutions

- **S1, supersede every definer.** The adopted document replaces every file that defined a node it took.
- **S2, supersede only the source.** It replaces `draft1`; nodes defined elsewhere become new ids in it.
- **S3, incorporate into the nodes' homes.** The agent's copy is an incoming revision: each taken node's text goes where that node lives, and the changes between nodes go into `draft1`. No new document.
- **S4, a new independent document.** Changed and new nodes take fresh ids, recorded as forks of their originals; nothing of the person's is touched.

#### 8.3 Each resolution against each example

| | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| **E1 revision** | works, but the paper is renamed every round (`draft2`, `draft3`, …), the default document moves, and every record naming `draft1` breaks (§4) | as S1 | **works**: `draft1` keeps its name, and nothing needs to follow a rename | wrong: a duplicate paper, and its acceptances lost |
| **E2 shared lemma** | **breaks `talk.tex`**: the lemma's file is superseded out from under it | splits the lemma: the paper gets the new text, the talk keeps the old | **works**: the node file changes, and both documents see it | wrong: the improvement goes nowhere |
| **E3 derivative** | **retires the paper** unless the person declines | as S1 | **wrong**: applies the talk's cuts to the paper | **works** |
| **E4 several definers** | **supersedes all of `part2`** to take one lemma | duplicates the lemma under two ids | needs a definition moved between documents | works, as a copy rather than a move |

#### 8.4 Critique

- **S1 and S2 were the first proposal, and nothing favours them.** S3 handles E1 as well and E2 better; S1 and S2 fail E2 and E4 and bring the stale-record defect of §4 into every adoption. They were borrowed from `linearize`, whose output genuinely replaces its inputs; adoption is not that once a node is shared or defined elsewhere. Superseding a document stays what it is today: the person's deliberate act, never a side effect.
- **S3 is how loom already treats a collaborator.** Review's Incoming view already reviews an incoming revision block by block, with comparisons, and Incorporate pull writes it into the person's files under a contract: the exact revision, refused over uncommitted edits, stopped by a conflict before anything changes, committed. An agent is a collaborator and its copy is an incoming revision. S3 also removes the need for step 3 of §6: nothing is copied into `drafting/` to be reviewed, so neither a `draft2` nor stripping its labels in place is needed.
- **S3's cost** is that it writes the person's files, a larger exception than stripping labels in a file loom made; its precedent is Incorporate pull, which the author accepted. The text between nodes — prose, order — is merged as text and can conflict, as a pull's source diffs can.
- **S3 is wrong for E3 and S4 is wrong for E1.** They are different intentions — a new version of this, and a new document from this — and loom cannot tell them apart, so the person names which.
- **E4 is a move.** A node can appear in two documents only as a node file, so pulling `part2`'s inline lemma into `part1` moves a definition. That is the node manager's work ([WQ-29](../work-queue/WQ-29-node-manager.md)), not adoption's.

#### 8.5 Final recommendations

1. **Adoption never supersedes.** Retiring `draft1` stays the person's separate, explicit act.
2. **`loom adopt aidoc.tex` is a new version of the documents it came from** (E1, E2): §7. Finish writes each taken node's text to its home, inline in `draft1` or in a node file; merges the changes between nodes into `draft1`; adds new nodes (`zk-0012-ai` as `zk-0012`) where the copy placed them; removes deleted nodes from the document, their node files staying since loom never deletes. Arras writes it in place under Incorporate pull's contract; the command line writes a patch.
3. **`loom adopt aidoc.tex --as drafting/talk.tex` is a new document** (E3). Changed and new nodes take fresh ids recorded as forks; unchanged nodes that live in node files are shared by `\input`, and unchanged inline ones are forked too. Nothing of the person's changes.
4. **A taken node defined in a document other than the copy's source** (E4) is offered only as a fork, with the reason shown; moving definitions waits for the node manager.
5. **Records that name a document follow it across a rename** (§4), whatever else is decided.

The scenario of §6 under these recommendations: steps 1 and 2 as posed; then `loom adopt aidoc.tex` opens the copy's changes in Review's Incoming view; the person takes some nodes and keeps others; Finish writes the taken texts into `draft1.tex` (in arras) or prints the patch (at the command line); `zk-0001@4` is recorded for each taken node; `draft1.tex` keeps its name and acceptances, and `aidoc.tex` stays with its bases moved forward. Had the person wanted a talk rather than a revision, step 3 is `loom adopt aidoc.tex --as drafting/talk.tex`.

### 8.6 What adoption does to annotations and deletions

- **Open annotations follow the text the person takes.** An open annotation on a node the person takes moves with it, by an event appended to the log, re-anchored against the adopted text — identical once the suffix is stripped, so its quote and recorded version hold (DR-284-ikmartin). An annotation on a node the person keeps stays on the copy, and settled annotations stay on the copy either way. The adoption review shows each node's open annotations beside its take and keep. The alternatives were weighed and refused: staying on the copy hides an open objection from the text it is about (A3); closing treats a file operation as an answer; copying gives one record two marks (A2).
- **A node the agent deleted is a change like any other**, offered as take or keep. Taken, it leaves the document and its node file stays, since loom never deletes; kept, the person's node stays where it is.

### 9. Arras

- **The side panel's Documents section** lists `drafting-ai/` as a subsection under the Working Drafts subsection. They are documents like any other there: arras edits nothing, so there is nothing to mark read-only, and the two directories differ only in who may edit them.
- **Compare**, a control that puts two open tabs side by side in comparison: corresponding nodes linked and scrolled together, differences marked with Review's change highlighting, a hover on one lighting its partner. Nodes correspond when they share an id (`main.tex` and `talk.tex`), when one is the other's `-ai` copy, or when they are two versions of one key (a landmark against today). It serves any two versions, not only an agent's copy; reading side by side needs nothing, since an agent's document opens as a tab like any other.
- **Review** never gives a `drafting-ai/` document a tab and never lists a derived id; an adoption appears in the Incoming view (§7).

### 10. Canon folds into the history

- **Canonizing and stamping become one act.** A stamp records every key whose text moved; canonizing does the same and also writes a flat copy of the document to `canon/`. A step can already store a document's flat text (`write_step` takes `document_text`, and canonize passes it), so a stamp that stores it makes the canon file derived. What remains is `loom stamp [DOC] -m "name"`, and a named stamp is a landmark; the flat text of any landmark is printed on demand (`loom history show main@3`).
- **The panel's Canon subsection becomes a history view** ([WQ-25](../work-queue/WQ-25-history-view.md)).
- **`loom init --from paper.tex` stamps the paper as received and drafts it at once**: the first landmark is the original, and the working copy with `\usepackage{loom}` and an id on every node is written to `drafting/`. `loom import` does the same in an existing quilt. A person who instead copies a paper into `drafting/` by hand has no landmark of the original until they stamp one; that is theirs to do.
- **`draft` loses its everyday job and takes a new one.** Nobody drafts from canon to keep working, because the working document already exists; starting a new document from an old version, rare, is `loom history restore main@3 --to talk.tex`. `draft` becomes the copy across the border: `loom draft DOC --ai NAME`.

## Part three: open questions

1. **The scope of plan 0.16 (§4).** Settled on 2026-09-26:
   - **Records are resolved when read, never rewritten.** A record keeps the path it was written with; whenever loom reads one it follows the history's chain of moves (a conversion's `from` and `to`, and any recorded rename) to the document's current path. The ledger stays append-only and `loom live` undoes a move for free.
   - **A record whose document is gone, with nothing saying where, has its own cause**: the key reads stale with "the document it was accepted in is gone", naming the path and the fix, and `loom lint` reports it once for all such rows, instead of `preamble-changed`.
   - **`loom mv OLD NEW`, author-only.** When `OLD` exists it moves the file and records the move, as `atomize --retire` already moves a file; when `OLD` is gone and `NEW` exists it records a rename already made in an editor, with git, or anywhere else. Moving the default document also moves `[quilt] main`, as conversions do. Its use is rare, so the "document is gone" diagnostic names the exact command as its fix, and arras offers it there. Recording only, the first proposal, was two steps and easy to forget.
   - **An Overleaf pull records exact renames**: a drafting document deleted and an identical one added in the same pull is recorded as a move, so a collaborator's rename needs no command. The pull diffs with `--no-renames` today (`sync.py:166`).
   - **What follows the document**, from the scenario table the author approved:

     | record | follows | why |
     |---|---|---|
     | acceptance rows' `master` | yes | the defect that started this |
     | annotations' `in` | yes | an annotation read in a document stays drawn there |
     | annotations whose target is a whole document | yes | otherwise they detach and vanish |
     | `.loom/source-sync.json`'s main and selected documents | yes | otherwise sync refuses until the file is edited by hand |
     | `loom accept --stale` | fixed | it re-accepts against the vanished document with an empty preamble, and the key never becomes fresh |
     | the Review queue's saved decisions | no change | they are checked against the current default document, which conversions already move; a preamble that really changed should still invalidate them |
     | annotations carried in a session's packets | no change | they are copies of what was sent, not live references |

## Part four: what it touches

- **loom:** the config (`drafting_ai`); the scan (a second drafting directory whose documents define derived ids); the allocator and lint (derived ids; no `-ai` citation from `drafting/`); `accept` (refuses derived ids); `draft --ai`, `adopt`, `adopt --as`, `ai drafts`; `stamp`, `canonize`, `init --from`, `import`, `history show` and `history restore` (§10); the history ledger (bases, adoptions); the manifest (a document's directory, a node's derived pair); records that follow documents (§4); Overleaf sync's selection (never `drafting-ai/`); the agent permission file and the orientation.
- **arras:** the panel's Documents section; Compare; the Incoming view's adoption source and its Finish; the Canon subsection's replacement.
- **the book:** chapters 3, 4, 5, 7, 10, 11, 12 and 15, with the worked examples required above; a decision record for each of §1, §2, §7, §8.5 and §10, and one for the record-following fix.
- **the queue:** WQ-24 closes into this; WQ-29's fork and merge and WQ-33's apply step are absorbed; WQ-25 inherits the landmarks.

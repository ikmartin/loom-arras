# 7. Review

This chapter specifies how decisions about a quilt are recorded and how the tool reports their current standing. The model has two kinds of record and no stored state: acceptance rows in the ledger, written only by a human through `loom accept`; and review records, files of annotations written only by `loom comment`, by humans and agents alike. Every word the viewer shows is computed from those records and the current text.

## 7.1 The model in one paragraph

**[decided]** A key (a statement or a proof, 3.3) has two kinds of history. Someone reviews it and leaves annotations, which loom writes into a review record together with the hash of the text that was reviewed. The author accepts it, which loom writes into the ledger together with the hashes of the key's text and of everything it depends on, and snapshots of that text. On every query, loom compares the recorded hashes with the current text and reports the key as draft, accepted, accepted-stale, or incomplete, and reports the reviews as facts: who looked, when, how many comments are open. Nothing ever writes a state word.

## 7.2 The ledger

### 7.2.1 File

**[decided]** `.loom/state.toml`. Committed. Written only by `loom accept`, only by appending. Never edited by any command; never edited by hand (the file's header says so). Format:

```toml
# .loom/state.toml -- written by `loom accept`. Do not edit.
schema = 1

[[accept]]
key = "rl-0004"
author = "Markas Hecht"
date = 2026-09-16T14:02:11Z
text = "sha256:9b1c4e..."          # hash of the key's normalized own text
preamble = "sha256:77aa02..."      # hash of the master's preamble closure
master = "drafting/main.tex"         # the master whose preamble was hashed
[accept.closure]                   # hashes of every statement in the closure
"rl-0002" = "sha256:3c0e91..."
"rl-0001" = "sha256:1f2d7b..."
"Man12-thm-4.1" = "sha256:aa10c3..."

[[accept]]
key = "rl-0004/proof"
author = "Markas Hecht"
date = 2026-09-16T14:02:11Z
text = "sha256:5d2f..."
preamble = "sha256:77aa02..."
master = "drafting/main.tex"
[accept.closure]
"rl-0004" = "sha256:9b1c4e..."
"rl-0002" = "sha256:3c0e91..."
"rl-0012" = "sha256:b8e0..."
```

Rules:

1. **[decided]** Rows are appended; the latest row for a key is its current acceptance; earlier rows are history. Nothing is ever removed.
2. **[decided]** `closure` lists every statement the key depends on transitively (5.7.2) with the hash of each statement's own text at acceptance time. For a proof key, the closure includes its own statement.
3. **[decided]** `preamble` is the hash of the preamble closure (5.13) of the default master at the time of acceptance, which is the master named in `master` (settled at M3).
4. **[decided]** `author` comes from the resolution order in 4.3; the row is refused without one.
5. **[decided]** `schema = 1`; a future loom migrates on `loom upgrade`.
6. **[decided]** Git merges of concurrent appends to different keys are clean; concurrent acceptances of the same key produce a textual conflict either resolution of which is consistent, since both rows are valid.

### 7.2.2 Snapshots

**[decided]** `.loom/history/texts/<hex>.tex`, where `<hex>` is the SHA-256 of the file's contents, which is the normalized own text of a key or the normalized preamble closure. Written by `loom accept` for the key's text, its preamble, and every statement in its closure. Content-addressed, so identical text is stored once and a snapshot is never overwritten or deleted. Committed. They exist so that a stale acceptance can be explained with a diff without git.

## 7.3 `loom accept`

**[decided]** `loom accept KEY [KEY ...] [--proofs] [--stale] [--author NAME] [--force] [--yes]`

1. For each key: compute the current hashes; write one row and the snapshots; print `accepted <key> (<Taxon>) by <author> <date>` per row, then how many snapshots were written and how many were already present.
2. `--proofs`: for each statement key given, also accept all its attached proofs.
3. `--stale`: accept every key currently in state accepted-stale, after printing the list with its causes and asking for confirmation on a terminal (`--yes` skips; without a terminal `--yes` is required). This is the command for "I have read the diffs and nothing is affected".
4. Refusals: no author name (exit 2); a key that does not exist or is not a statement or proof (exit 2); a key with `\incomplete` in it (exit 1; `loom accept` will not accept an incomplete key; remove the mark first); a default master that does not compile (exit 1), since numbers and preamble are then unknown. **[decided]** The compile check is cheap: the master is recompiled only when its PDF under `build/` is older than some scanned file, and `--force` skips the check (settled at M3).
5. Never enforced: that the closure is accepted. An author may accept a proof whose lemmas are drafts; the viewer shows that honestly through the derived states (7.6.3).

Example:

```
$ loom accept rl-0004 --proofs
accepted rl-0004 (Lemma)                         by Markas Hecht  2026-09-16
accepted rl-0004/proof (Proof)                   by Markas Hecht  2026-09-16
snapshots: 5 written, 2 already present
```

## 7.4 Review records

### 7.4.1 The log

**[decided]** Every review event is one line of `annotations/log.jsonl` at the quilt root, appended and never rewritten. A *record* is what replay produces: one run's or one author's annotations as they now stand. There is no file per run and none per author; a line that cannot be read is reported as `loom:foreign-annotations` (warning) and skipped, and the rest of the log still loads.

**[decided]** The columns, spelled as they are written. An event carries `id`, `event`, `when`, `author`, `kind` (`human` | `agent`), `run`, and then whatever its event needs: a `created` or `replied` event carries `target`, `against`, `anchor`, **`annotation_kind`** (one of `objection`, `suggestion`, `question`, `ok`, `citation`), `severity`, `body`, `payload`, `placement`, and **`reply_to`** on a reply; a later event carries the `id` it acts on. The underscores are not decoration: an earlier draft of the design wrote `annotation-kind` and `reply-to` with hyphens, and a log written from that spelling lost its kind and its parent on every line.

**[decided]** Four things make a line foreign rather than merely unusual, and each is reported as `loom:foreign-annotations` with its line number: it is not JSON; it is JSON that is not a review event; its `annotation_kind` is not one of the five; its `id` is not of the form `a-YYYY-MM-DD-NNNN`; or it replies to an annotation the log does not contain. **None of these is corrected.** An unknown kind is published as written, because `kind` is an open string a viewer must tolerate from any publisher — what is wrong is the silence, not the value. The id is checked because it becomes a DOM id and a URL fragment, and would become a filename the first time anything stored one per annotation. A reply whose parent is absent is reported because it is otherwise in the record and on no page: not a finding, because it answers one, and under no finding, because the one it answers is not there.

**[decided]** The events are `created`, `replied`, `edited`, `resolved` and `discarded`, and an annotation's current state is their replay. `edited` supersedes a body: the earlier one stays in the log, one current body is shown. That is what lets a re-check restate a finding that still stands instead of replying to itself, which is how a single finding used to end up wearing one copy per pass.

**[decided]** `run` and `author` are separate columns, so "everything from this run" and "everything any agent said about `rl-0002`" are both filters rather than string parsing. A run's record is keyed by its directory; a person's by `comments/<author-slug>/<YYYY-MM-DD>`, because "what the author said on the 16th" is a session a reader looks for where everything one person has ever written is not. The slug is the name lowercased with every run of other characters replaced by a hyphen.

**[decided]** Two people appending in parallel merge as two lines, which is why this is JSONL and not a database, and the reason the log is written by `loom comment` and `loom refs note` alone.

### 7.4.2 Schema

**[decided]**

```json
{
  "schema": 1,
  "discarded": false,
  "annotations": [
    {
      "id": "a-2026-09-16-0007",
      "author": {"kind": "run", "id": "2026-09-16T14-02-referee"},
      "created": "2026-09-16T14:31:08Z",
      "target": {"key": "rl-0004/proof", "hash": "sha256:5d2f..."},
      "selector": {
        "exact": "the inclusion is open by the rigidity lemma",
        "prefix": "decomposes as $M^T_Z \\times_{\\mathcal Y^T} Z^T$ and ",
        "suffix": ", so the residue of"
      },
      "kind": "objection",
      "body": "No rigidity lemma exists in the quilt. Either add one or cite the source.",
      "status": "open",
      "in_reply_to": null
    }
  ]
}
```

Fields:

- `id`: `a-<date>-<nnnn>`, unique within the quilt; **[decided]** the counter runs over every review record in the quilt, not per file (DR-60).
- `author.kind`: `run` or `person`; `author.id`: the run directory name or the person's name.
- `target.key`: a key, an equation's qualified key, or a master path (7.5.4). `target.hash`: the hash of the target's own text when the annotation was written.
- `selector`: null for an annotation on the whole target; otherwise the text-quote selector (7.5).
- `kind`: `objection`, `suggestion`, `question`, `ok`, `citation`.
- `body`: Markdown; the manifest carries it rendered as CommonMark.
- `severity`: **[decided]** `major`, `moderate` or `minor`, grading the *fault a finding names* rather than the enthusiasm of the suggestion — a grammar note is minor because the fault is small. Required by review mode, where every item is grouped by it; optional elsewhere, and absent where nothing is wrong.
- `payload`: **[decided]** text the annotation proposes — a proof, a paragraph, a rewritten passage — with `placement` (`replace`, `after`, `before`) as a hint for where a viewer shows it relative to the anchor. Everything is preview and copy: the author reads it and pastes it where they decide, and nothing in loom applies one.
- `status`: `open`, `resolved` or `discarded`.
- `in_reply_to`: an annotation id or null.
- `discarded`: **[decided]** an event, set by `loom ai discard` against a whole run or session, or against one annotation; a discarded record's annotations are hidden everywhere. Nothing is deleted and `--undo` reverses it.

### 7.4.3 `loom comment`

**[decided]** `loom comment TARGET "message" [--quote TEXT] [--kind objection|suggestion|question|ok] [--run DIR | --author NAME] [--reply ID] [--resolve ID] [--batch]`

1. `TARGET` is a key, an equation's qualified key, or a master path. It must exist.
2. `--quote TEXT`: the annotation anchors to `TEXT`, which must occur exactly once in the target's own text (whitespace-normalized). Zero occurrences: exit 1 with "quote not found in TARGET". More than one: exit 1 with "quote is ambiguous (n occurrences); give a longer quote". Loom extracts prefix and suffix itself, **[decided]** 32 characters each, clipped at the target's boundaries (settled at M3).
3. `--kind` defaults to `objection` when a message is given and to `ok` when none is; `ok` records that the author read the target and found nothing, and may carry a message.
4. `--run RUN`: author is the run, named by its directory; the command is also appended to `RUN/run.log`. **[decided]** `RUN` is a run's name, a prefix of one, or its path, resolved as 11.4 describes, and defaults from `LOOM_RUN` so an agent inside a run need not pass it. Otherwise `--author NAME` or the resolution order of 4.3. `--run` and `--author` together are refused.
5. **[decided]** `--edit ID` supersedes an annotation's body, and is what a re-check uses on a finding that still stands. A reply is dialogue; an edit is restatement. `--severity`, `--payload` and `--placement` carry the fields of 7.4.2.
5. `--reply ID`: `in_reply_to` set; `target`, its hash, and the selector are copied from the parent, so the reply is anchored where the parent is; the kind defaults to `question`; no `TARGET` is needed.
6. `--resolve ID`: sets the parent's `status` to `resolved` and, if a message is given, records it as a reply with status `resolved` (kind `ok` unless given). **[decided]** Resolution is an edit to an existing annotation's `status` field, the one field loom rewrites in place; it is loom's file.
7. `--batch`: read JSON lines from stdin, each an object with the keys `target`, `message`, `quote`, `kind`, `reply`, `resolve`, so an agent can write many comments in one process; all go into the same record, and an error names its line number.
8. Every annotation records `target.hash` at the moment of writing.

Examples:

```
$ loom comment rl-0004/proof "This needs the rigidity lemma." \
    --quote "the inclusion is open" --run ai/runs/2026-09-16T14-02-referee
a-2026-09-16-0007  rl-0004/proof  objection  (2026-09-16T14-02-referee run)

$ loom comment rl-0004 --kind ok
a-2026-09-16-0008  rl-0004  ok  (Tom Graber)

$ loom comment rl-0004/proof --resolve a-2026-09-16-0007 "Added rl-0019 (rigidity)."
resolved a-2026-09-16-0007
```

## 7.5 Selectors

### 7.5.1 Model

**[decided]** The text-quote selector of the W3C Web Annotation model: `exact`, `prefix`, `suffix`. Resolved inside the target's own text, never against a file path or line numbers. Consequences: moving text between files (`atomize`, `inline`) does not touch an annotation; an edit elsewhere in the same file cannot shift an anchor.

### 7.5.2 Resolution

**[decided]** To place an annotation against the current text: search the target's own text for `exact`; if it does not occur, search again with whitespace normalized; if it still does not occur, the annotation is detached; if it occurs once, done; if several times, choose the occurrence whose surroundings best match `prefix` and `suffix` (longest common suffix of prefix plus longest common prefix of suffix).

### 7.5.3 Detached annotations

**[decided]** A detached annotation is still shown, in a separate list on the target's page and in the run or comment session, with its quoted text, marked detached. It is never deleted. An annotation whose target no longer exists is detached as a whole (7.9). `loom:detached-annotation` (info) is reported with a count per key, by `loom lint` and `loom check` as well as in the manifest (DR-61). Detached annotations are the natural candidates for `--resolve`.

### 7.5.4 Targets

**[decided]** Annotations may target: a key; a labelled equation (qualified key); a master (path), whose own text is the region. They may not target rendered-only content, LaTeX comments, the preamble, or a span crossing a node boundary (`loom comment` refuses a quote that crosses out of the target's own text).

## 7.6 Computed states

### 7.6.1 Per key

**[decided]** For a key with current text hash H, current closure hashes C, and current preamble hash P:

- `incomplete` if the key's text contains `\incomplete`. Overrides everything below.
- `accepted` if the latest acceptance row for the key has `text = H`, `preamble = P`, and `closure` equal to C on every entry, and no closure entry names a node that no longer exists.
- `accepted, stale` if a latest row exists but some recorded hash differs from the current one, or a closure node was removed.
- `draft` otherwise (no row).

### 7.6.2 Stale causes

**[decided]** When a key is stale, loom names the cause, and there are exactly these:

1. `own-text-changed`: `text` differs. Diff: snapshot of the accepted text against the current own text.
2. `dependency-changed <id>`: a closure entry's hash differs. Diff: snapshot of that statement against its current text. Several may apply; all are listed.
3. `dependency-removed <id>`: a closure entry names a node no longer defined.
4. `preamble-changed`: `preamble` differs. Diff: preamble snapshot against current.
5. `dependency-added <id>`: the current closure contains a node not in the recorded closure (which implies `own-text-changed`, since a new edge means new text, or `dependency-changed` upstream). Listed for clarity.

`loom status --explain KEY` prints the key with its state, the file that holds it, its open comment counts and detached count, and each cause with the date of the changed file and the unified diff (`accepted/<id>` against `current/<id>`); `loom build` writes the same diffs under `build/diffs/`, and the review panel shows them (settled at M3).

### 7.6.3 Derived node states

**[decided]** Display only, never written:

- `proved`: statement accepted (fresh) with no `\incomplete`, and, for a node that owes a proof (plain style and not external), at least one attached proof accepted (fresh) with no `\incomplete`. Definition- and remark-style nodes and external nodes owe no proof and are proved by acceptance alone, so they can be settled and so can what depends on them (DR-59).
- `settled`: proved, and every node in the statement's closure and in the closure of each fresh accepted proof is settled. External nodes count as settled. **[decided]** A dependency cycle is reported as `loom:dependency-cycle` (warning) and nothing on it is settled (verified at M3; 5.9.4 covers inclusion cycles).

### 7.6.4 Review facts

**[decided]** Beside the state, for each key, loom reports: the latest review (author, date) whose `target.hash` equals the current text; the latest review of any older text; counts of open annotations by kind, counting top-level annotations with status `open` and a kind other than `ok`, excluding discarded records; the number of detached annotations. These are facts, not states. A key with forty open comments and an acceptance row is `accepted`.

## 7.7 `loom status`

**[decided]** Prints every key as `<key> (<Taxon>)` with its state, the cause if stale (with the date of the changed file), review facts, and its `\incomplete` text if any; then a summary line counting stale of accepted, draft, incomplete, loose, proved, and settled keys. Filters: `--stale`, `--draft`, `--incomplete`, `--loose`, `--master PATH`, `--tag TAG`, `--unmatched-cites`, `--undigested`, `--retired`, `--runs`; `--explain KEY`; `--json`, which also carries each key's closure and the masters reaching it. It never exits nonzero; `loom check` is the command that fails.

`loom status --stale` on the synthetic quilt (14.3) at M3:

```
$ loom status --stale
sy-0001 (Definition)   accepted, stale   own-text-changed (2026-09-16)            1 open question; 1 detached
sy-0002 (Lemma)        accepted, stale   dependency-changed sy-0001 (2026-09-16)  1 open question
sy-0004 (Proof)        accepted, stale   dependency-changed sy-0001 (2026-09-16)  reviewed clean (The synthetic quilt, 2026-09-16)
sy-0005 (Proof)        accepted, stale   dependency-changed sy-0001 (2026-09-16)
sy-0002/proof (Proof)  accepted, stale   dependency-changed sy-0001 (2026-09-16)
5 stale of 6 accepted; 21 draft; 1 incomplete; 6 loose; 0 proved, 2 settled
```

## 7.8 Discard

**[decided]** `loom ai discard RUN` appends a `discarded` event naming the run (and sets `discarded = true` in `RUN/run.toml` when present, Chapter 11); every annotation in it disappears from the panel, the margins, and every count; the directory remains. `--before DATE` (records whose earliest annotation predates the date), `--author NAME`, `--target KEY` discard every run or comment session matching; `--undo` reverses. Comment sessions are discarded the same way, by `--author`. Discard is a flag, never a deletion, and never touches the ledger.

Two further defences against garbage: annotations carry kinds, and the panel filters by kind; and no annotation creates an obligation, since states never depend on annotation counts.

## 7.9 Deletion and retirement

**[decided]** Loom never deletes a node; the author does. What loom does:

- `loom unravel ID` (aliases `downstream`, `reach`, `pop`) prints, before the fact, the transitive dependents, every reference and inclusion site, ledger rows, and annotations attached to the id.
- `loom delete` (aliases `rm`, `remove`) prints `loom will not delete your notes; do this yourself with rm. Run loom unravel <ID> to see the consequences first.` and exits 1.
- After deletion, lint reports dangling references (`dangling-link`), missing inputs (`missing-include`), and `loom:retired-ledger-key` (info) for ledger rows whose key no longer exists (DR-61); `status --retired` lists retired keys with the date of their last acceptance; annotations targeting them are detached at the target level.
- Dependents whose closure recorded the deleted id become stale with cause `dependency-removed`.
- The recommended alternative to deletion is to make the node loose: remove its inclusion line. Everything about it survives, marked loose.
- A refuted candidate is handled the same way: its `\input` line is removed, its body gains a sentence naming the run and the counterexample, and a tag of the author's choosing may mark it for filtering; no tag has special meaning.
- Merging is aliasing (5.4.5); splitting is new ids for the pieces; renaming is not an operation.

## 7.10 Positional proof keys

**[decided]** Deleting or reordering unlabelled proofs renames the survivors' keys. `status` reports, for any acceptance row whose recorded `text` hash equals the current text of a differently keyed proof of the same statement, "acceptance recorded under `<old key>`; re-accept to confirm"; lint and check report the same as `loom:previous-key-match` (info) (DR-61), and the review panel shows it. Prevention: lint suggests labels whenever a node has more than one unlabelled proof (`loom:positional-proof-key`, info).

## 7.11 Worked timeline

Day 1. The author writes `nodes/rl-0004.tex`, a lemma with its proof. `status`: both keys `draft`, never reviewed.

Day 1. `loom ai start referee-rl-0004`; in the run, the agent runs `loom source rl-0004 --closure`, reads it, and issues three `loom comment --run ...` calls: one objection on a hypothesis in the statement, two on the proof. `status`: statement `draft, 1 open objection (run, today)`; proof `draft, 2 open objections`. The node page shows three margin marks.

Day 2. The author fixes the proof. Its hash changes; the two proof annotations no longer find their quotes and show as detached. The author asks the agent to look again; it issues `loom comment rl-0004/proof --kind ok --run ...`. `status`: proof `draft, reviewed clean (run, today), 2 detached`.

Day 3. The author decides the hypothesis objection is wrong, runs `loom comment rl-0004 --resolve a-...-0001 "The hypothesis is stated in rl-0002."`, and `loom accept rl-0004 --proofs`. Both keys `accepted`; the node `proved`.

Day 9. The author edits Definition `rl-0002`, which `rl-0004`'s statement uses. `status --stale` lists `rl-0004` and `rl-0004/proof` with `dependency-changed rl-0002`; `status --explain rl-0004` shows the diff of the definition. The author reads it, decides nothing is affected, and runs `loom accept --stale`. Two new rows; both keys `accepted` again.

**[decided]** The timeline runs as one test (`test_timeline_7_11`) on the demo quilt, and the synthetic quilt's shipped records were produced by running these commands on a copy, then editing the definition and deleting the retired lemma (settled at M3).

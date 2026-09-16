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
master = "drafts/main.tex"         # the master whose preamble was hashed
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
master = "drafts/main.tex"
[accept.closure]
"rl-0004" = "sha256:9b1c4e..."
"rl-0002" = "sha256:3c0e91..."
"rl-0012" = "sha256:b8e0..."
```

Rules:

1. **[decided]** Rows are appended; the latest row for a key is its current acceptance; earlier rows are history. Nothing is ever removed.
2. **[decided]** `closure` lists every statement the key depends on transitively (5.7.2) with the hash of each statement's own text at acceptance time. For a proof key, the closure includes its own statement.
3. **[decided]** `preamble` is the hash of the preamble closure (5.13) of the master named in `master`; **[assumed]** the default master at the time of acceptance.
4. **[decided]** `author` comes from the resolution order in 4.3; the row is refused without one.
5. **[assumed]** `schema = 1`; a future loom migrates on `loom upgrade`.
6. **[decided]** Git merges of concurrent appends to different keys are clean; concurrent acceptances of the same key produce a textual conflict either resolution of which is consistent, since both rows are valid.

### 7.2.2 Snapshots

**[decided]** `.loom/snapshots/<hex>.tex`, where `<hex>` is the SHA-256 of the file's contents, which is the normalized own text of a key or the normalized preamble closure. Written by `loom accept` for the key's text, its preamble, and every statement in its closure. Content-addressed, so identical text is stored once and a snapshot is never overwritten or deleted. Committed. They exist so that a stale acceptance can be explained with a diff without git.

## 7.3 `loom accept`

**[decided]** `loom accept KEY [KEY ...] [--proofs] [--stale] [--author NAME]`

1. For each key: compute the current hashes; write one row and the snapshots; print the row's key and date.
2. `--proofs`: for each statement key given, also accept all its attached proofs.
3. `--stale`: accept every key currently in state accepted-stale, after printing the list and asking for confirmation on a terminal (`--yes` skips). This is the command for "I have read the diffs and nothing is affected".
4. Refusals (exit 2): no author name; a key that does not exist; a key with `\incomplete` in it (`loom accept` will not accept an incomplete key; remove the mark first); a key whose master does not compile, **[assumed]** since numbers and preamble are then unknown (`--force` overrides).
5. Never enforced: that the closure is accepted. An author may accept a proof whose lemmas are drafts; the viewer shows that honestly through the derived states (7.6.3).

Example:

```
$ loom accept rl-0004 --proofs
accepted rl-0004          (Lemma 3.4)  by Markas Hecht  2026-09-16
accepted rl-0004/proof                  by Markas Hecht  2026-09-16
snapshots: 5 written, 2 already present
```

## 7.4 Review records

### 7.4.1 Files

**[decided]** A review record is a JSON file named `annotations.json` in one of two places:

- `ai/runs/<run>/annotations.json` for annotations written inside a run (author is the run);
- `comments/<author>/<YYYY-MM-DD>.json` for annotations by a person, one file per author per day.

Both are written only by `loom comment`. The scanner finds them by these paths; nothing else is a review record. **[decided]** The directory names are part of the contract: `comments/` and `ai/runs/` are the two places, so the core model depends on the file schema, not on the AI layer's existence.

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

- `id`: `a-<date>-<nnnn>`, unique within the quilt; **[assumed]** the counter is per file.
- `author.kind`: `run` or `person`; `author.id`: the run directory name or the person's name.
- `target.key`: a key, an equation's qualified key, or a master path (7.5.4). `target.hash`: the hash of the target's own text when the annotation was written.
- `selector`: null for an annotation on the whole target; otherwise the text-quote selector (7.5).
- `kind`: `objection`, `suggestion`, `question`, `ok`.
- `body`: Markdown.
- `status`: `open` or `resolved`.
- `in_reply_to`: an annotation id or null.
- `discarded` at file level: set by `loom ai discard` on run records and by the same command on comment sessions; a discarded file's annotations are hidden everywhere.

### 7.4.3 `loom comment`

**[decided]** `loom comment TARGET "message" [--quote TEXT] [--kind objection|suggestion|question|ok] [--run DIR | --author NAME] [--reply ID] [--resolve ID] [--batch]`

1. `TARGET` is a key, an equation's qualified key, or a master path. It must exist.
2. `--quote TEXT`: the annotation anchors to `TEXT`, which must occur exactly once in the target's own text (whitespace-normalized). Zero occurrences: exit 1 with "quote not found in TARGET". More than one: exit 1 with "quote is ambiguous (n occurrences); give a longer quote". Loom extracts prefix and suffix itself, **[assumed]** 32 characters each, clipped at the target's boundaries.
3. `--kind` defaults to `objection` when a message is given and to `ok` when `--kind ok` is given with no message; `ok` records that the author read the target and found nothing.
4. `--run DIR`: author is the run; the record is `DIR/annotations.json`; the command is also appended to `DIR/run.log`. `--author NAME` or the resolution order of 4.3 otherwise; the record is `comments/<author>/<date>.json`.
5. `--reply ID`: `in_reply_to` set; `target` copied from the parent; the reply is anchored where the parent is.
6. `--resolve ID`: sets the parent's `status` to `resolved` and records a reply body if a message is given. **[decided]** Resolution is an edit to an existing annotation's `status` field, the one field loom rewrites in place; it is loom's file.
7. `--batch`: read JSON lines from stdin, each an object with the fields of a single call, so an agent can write many comments in one process.
8. Every annotation records `target.hash` at the moment of writing.

Examples:

```
$ loom comment rl-0004/proof "This needs the rigidity lemma." \
    --quote "the inclusion is open" --run ai/runs/2026-09-16T14-02-referee
a-2026-09-16-0007  rl-0004/proof  objection  (run 2026-09-16T14-02-referee)

$ loom comment rl-0004 --kind ok
a-2026-09-16-0008  rl-0004  ok  (Tom Graber)

$ loom comment rl-0004/proof --resolve a-2026-09-16-0007 "Added rl-0019 (rigidity)."
resolved a-2026-09-16-0007
```

## 7.5 Selectors

### 7.5.1 Model

**[decided]** The text-quote selector of the W3C Web Annotation model: `exact`, `prefix`, `suffix`. Resolved inside the target's own text, never against a file path or line numbers. Consequences: moving text between files (`atomize`, `inline`) does not touch an annotation; an edit elsewhere in the same file cannot shift an anchor.

### 7.5.2 Resolution

**[decided]** To place an annotation against the current text: search the target's own text for `exact`; if it occurs once, done; if several times, choose the occurrence whose surroundings best match `prefix` and `suffix` (longest common suffix of prefix, longest common prefix of suffix); if none, retry with whitespace normalized; if still none, the annotation is detached.

### 7.5.3 Detached annotations

**[decided]** A detached annotation is still shown, in a separate list on the target's page and in the run or comment session, with its quoted text, marked detached. It is never deleted. Lint reports `loom:detached-annotation` (info) with a count per key. Detached annotations are the natural candidates for `--resolve`.

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
5. `dependency-added`: the current closure contains a node not in the recorded closure (which implies `own-text-changed`, since a new edge means new text, or `dependency-changed` upstream). Listed for clarity.

`loom status --explain KEY` prints the causes with diffs; the review panel shows the same.

### 7.6.3 Derived node states

**[decided]** Display only, never written:

- `proved`: statement accepted (fresh) and at least one attached proof accepted (fresh), and no `\incomplete` in the statement or that proof.
- `settled`: proved, and every node in the statement's closure and the accepted proof's closure is settled. External nodes count as settled. **[assumed]** A cycle in closures cannot occur (5.9.4 applies to inclusion; dependency cycles are reported as `loom:dependency-cycle`, warning, and break settledness).

### 7.6.4 Review facts

**[decided]** Beside the state, for each key, loom reports: the latest review (author, date) whose `target.hash` equals the current text; the latest review of any older text; counts of open annotations by kind (excluding discarded records); the number of detached annotations. These are facts, not states. A key with forty open comments and an acceptance row is `accepted`.

## 7.7 `loom status`

**[decided]** Prints every key with its state, the cause if stale, review facts, `\incomplete` text if any, and whether the default master reaches it; a summary line; and the filters `--stale`, `--draft`, `--incomplete`, `--loose`, `--unmatched-cites`, `--undigested`, `--retired`, `--runs`; `--explain KEY`; `--json`. It never exits nonzero; `loom check` is the command that fails.

Illustrative output:

```
$ loom status --stale
rl-0004        Lemma 3.4   accepted, stale   dependency-changed rl-0002 (9 Sep)
rl-0004/proof              accepted, stale   dependency-changed rl-0002 (9 Sep)
rl-0007        Prop. 4.2   accepted, stale   own-text-changed (12 Sep); 2 open objections
3 stale of 41 accepted; 0 draft; 2 incomplete; 4 loose
```

## 7.8 Discard

**[decided]** `loom ai discard RUN` sets `discarded = true` in `RUN/annotations.json` (and in `RUN/run.toml`, Chapter 11); every annotation in it disappears from the panel, the margins, and every count; the directory remains. `--before DATE`, `--author NAME`, `--target KEY` discard every run or comment session matching; `--undo` reverses. Comment sessions are discarded the same way, by path (`loom ai discard comments/tom/2026-09-16.json`). Discard is a flag, never a deletion, and never touches the ledger.

Two further defences against garbage: annotations carry kinds, and the panel filters by kind; and no annotation creates an obligation, since states never depend on annotation counts.

## 7.9 Deletion and retirement

**[decided]** Loom never deletes a node; the author does. What loom does:

- `loom unravel ID` (aliases `downstream`, `reach`, `pop`) prints, before the fact, the transitive dependents, every reference and inclusion site, ledger rows, and annotations attached to the id.
- `loom delete` (aliases `rm`, `remove`) prints `loom will not delete your notes; do this yourself with rm. Run loom unravel <ID> to see the consequences first.` and exits 1.
- After deletion, lint reports dangling references (`dangling-link`), missing inputs (`missing-include`), and `loom:retired-ledger-key` (info) for ledger rows whose key no longer exists; `status --retired` lists retired keys with their last snapshot; annotations targeting them are detached at the target level.
- Dependents whose closure recorded the deleted id become stale with cause `dependency-removed`.
- The recommended alternative to deletion is to make the node loose: remove its inclusion line. Everything about it survives, marked loose.
- Merging is aliasing (5.4.5); splitting is new ids for the pieces; renaming is not an operation.

## 7.10 Positional proof keys

**[decided]** Deleting or reordering unlabelled proofs renames the survivors' keys. `status` reports, for any acceptance row whose recorded `text` hash equals the current text of a differently keyed proof of the same statement, "acceptance recorded under `<old key>`; re-accept to confirm", and the review panel shows the same. Prevention: lint suggests labels whenever a node has more than one unlabelled proof (`loom:positional-proof-key`).

## 7.11 Worked timeline

Day 1. The author writes `nodes/rl-0004.tex`, a lemma with its proof. `status`: both keys `draft`, never reviewed.

Day 1. `loom ai start referee-rl-0004`; in the run, the agent runs `loom bundle rl-0004`, reads it, and issues three `loom comment --run ...` calls: one objection on a hypothesis in the statement, two on the proof. `status`: statement `draft, 1 open objection (run, today)`; proof `draft, 2 open objections`. The node page shows three margin marks.

Day 2. The author fixes the proof. Its hash changes; the two proof annotations no longer find their quotes and show as detached. The author asks the agent to look again; it issues `loom comment rl-0004/proof --kind ok --run ...`. `status`: proof `draft, reviewed clean (run, today), 2 detached`.

Day 3. The author decides the hypothesis objection is wrong, runs `loom comment rl-0004 --resolve a-...-0001 "The hypothesis is stated in rl-0002."`, and `loom accept rl-0004 --proofs`. Both keys `accepted`; the node `proved`.

Day 9. The author edits Definition `rl-0002`, which `rl-0004`'s statement uses. `status --stale` lists `rl-0004` and `rl-0004/proof` with `dependency-changed rl-0002`; `status --explain rl-0004` shows the diff of the definition. The author reads it, decides nothing is affected, and runs `loom accept --stale`. Two new rows; both keys `accepted` again.

## Open questions

- Whether the ledger should record the arras or loom version. **[assumed]** `schema` only.
- Whether `--kind ok` should be allowed with a message ("read carefully; fine"). **[assumed]** Yes; the kind is what matters.
- Whether a person's comment sessions should be one file per day or one per session started explicitly. **[assumed]** Per day; simplest, and git-mergeable.
- Whether acceptance should be refused when the master does not compile. **[assumed]** Refused with `--force` to override; revisit if it annoys.
- How arras displays a key with both an acceptance and many detached annotations. **[deferred]** to the arras chapter's badge rules.

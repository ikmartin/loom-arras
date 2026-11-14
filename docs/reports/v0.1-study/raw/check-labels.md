# Check: any `\label` a stable key, and a file-wide quote search before "gone"

Tested at 71621877 on scratch copies of seven papers, with a prototype in a separate clone. The claim under test (INST-11, register S7): treat any `\label` as a stable key, and before calling an annotation gone search the whole file for its quoted words; plus the requirement from SAFE-4 that a key named by place never lands silently on another block.

**Verdict: not safe as proposed; safe with changes.** Label keys are a large gain. The file-wide quote search makes things worse: it puts records on the wrong block more often than today's code does (255 against 160 of 4,693 record placements), and it puts six times as many suggested edits in the wrong block (43 against 7), which Keep would then write into the wrong text. The design that is safe adds three things the audit did not mention. First, every record must store where its block stood among its neighbours, and whether another block reads like it. Second, any block found by its text must be checked against that record. Third, a quote may place a record on its own only where that quote stood once in the whole quilt. On the same 4,693 placements that design put 15 on the wrong block, all of them whole-block notes on a label that a co-author had reused for a different statement. With label keys also checked against the text (verify mode), it put none on the wrong block. Effort is about 4-5 coding-agent sessions, against the audit's 2-3 days.

Prototype: `spikes/labels.patch` (applies to 71621877; the code changes plus the harness under `loom/scripts/spikes/labels/`). Scratch work: `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/check-labels/` (`runs/summary.txt` holds the full tables).

| # | finding | weight |
|---|---|---|
| KEY-1 | How each kind of piece is keyed today; sections and unattached proofs already use `FILE#label`, statements never do | — |
| KEY-2 | How a record finds its block today: hash first, then the block at its place; the quote is looked for only inside that block | — |
| KEY-3 | In five real papers 92% of pieces are keyed by place; label keys would bring that to 42%. Import adds ids, but the Overleaf mirror does not import | blocks (Overleaf pilot) |
| KEY-4 | Today, under co-author edits: 160 of 4,693 placements are on the wrong block; renaming a file loses everything; SAFE-4 is reproduced | blocks |
| KEY-5 | The audit's file-wide quote search on a miss is not safe: 255 wrong, 43 of them suggested edits | blocks (as proposed) |
| KEY-6 | Label keys with today's lookup: wrong placements fall to 65, but lost ones rise, since a renamed label or file is not followed | hurts |
| KEY-7 | The safe design: 15 wrong (verify mode: 0), 88% right against 63% today; it holds on two papers not used to tune it | — |
| KEY-8 | Restatements and identical blocks are what remains; they need context recorded at filing, which means a change to the record format | blocks (if skipped) |
| KEY-9 | The acceptance ledger, measured: today one inserted theorem moves every row to the wrong theorem, shown stale; label keys fix labelled rows | hurts |
| KEY-10 | Every other kind of record that names a key, case by case | — |
| KEY-11 | Labels in the wild: 81 of 139 acgs labels and 70 of 96 mzk labels contain spaces, which the `quilt:` link grammar cannot carry | hurts |
| KEY-12 | Unit tests: 5 of 158 fail in the prototype, all for intended reasons | — |
| KEY-13 | The design, the order to land it, what it waits for, the files it owns, the size | — |

## Method

**Papers.** Each paper was taken as its author wrote it, not as loom imported it.
- man12: arXiv 0805.2065, `virtual6.tex`.
- acgs: arXiv 1709.09864.
- kpsv: arXiv 2012.12270.
- mzk: arXiv 2605.29265.
- relloc: the author's `draft3.tex`.

Sources come from `tests/fixtures/` in the main checkout; `demos/man12` and `demos/acgs` are already atomized with `man-`/`acgs-` ids, so I used their sources instead. I also used the three LaTeX files of `~/quilts/quant/course/solutions` (quant) and the showcase, which is loom-native and serves as a control. Each copy is a minimal quilt (`config.toml` naming the main file), which is what a read-only Overleaf mirror would be. mzk and relloc were kept back: the design was tuned on the other five and then run once on these two.

**Records.** For each paper the harness (`harness.py`) picks targets spread through the document:
- 3 statements with an ordinary label and 2 with none;
- a proof of a labelled statement and a proof of an unlabelled one;
- up to 3 proofs attached to no statement, and in quant one empty `\begin{proof}[Answer]\end{proof}` among identical twins (the SAFE-4 case);
- a labelled section and an unlabelled one;
- one equation's qualified key;
- prose in the document's body;
- in the showcase, an id-keyed statement.

On each target it files records through loom's own writers (`cli/review.py:_one_comment`, and the event `loom suggest` writes):
- an annotation on a 6-word quote;
- an annotation on the shortest leading 2-3 words that occur once in the block, which is how a person selects;
- a whole-block annotation on most kinds;
- a suggested edit replacing the 6 words.

That gives 159 records on the five tuning papers and 88 on the two held-back ones.

**Edits.** 19 co-author edits, alone and combined, are applied to a fresh copy:
- insert a theorem (with its proof) above;
- insert a section above;
- a light edit (one sentence added inside the block);
- a heavy edit, keeping the quoted words;
- the quoted words themselves rewritten;
- a statement moved, with its proof;
- a section moved;
- a label renamed, with every `\ref`;
- a statement deleted, with its proof;
- the file renamed;
- the file split in two with `\input`;
- insert+light, insert+heavy, move+light, rename-label+light, rename-file+light, split+insert;
- a label reused: the labelled statement deleted and its label put on a new, different statement;
- a duplicate label: a labelled statement restated verbatim, label and all, near the top (LaTeX warns).

The true place of every block and quote is carried through each text operation as an offset.

**Outcome of each record.**
- right: on the true block, at the true words.
- wrong: shown as placed anywhere else. This is the dangerous outcome, since it is silent.
- detached: shown detached, on a key that still names a block.
- lost: its key names nothing now.

Each detached or lost record is split further. It is "honest" when its block or words are really gone, and a "miss" when they still stand. It is "elsewhere" when the key it is shown on now names another block.

Reproduce one paper with `python -I harness.py PAPER OUT OUT.json`. Set `LOOM_PROTO_MODE` to `labels` or `literal`, or `LOOM_PROTO_LABEL=verify`, for the variants, and sum the results with `aggregate.py`. Accept rows for KEY-9 were written with `write_acceptance`, the writer `loom accept` and the unit tests share, on scratch copies; the CLI refuses an agent's shell.

## KEY-1 · How keys are assigned today

| piece | key today | where |
|---|---|---|
| statement with a loom id (`\label{rl-0004}`) | `rl-0004` | `scan/nodes.py:367, 371`; id grammar `scan/labels.py:33-40` |
| statement with an ordinary label (`\label{thm:main}`) | `FILE#theorem:3`: per environment name, per file, in file order; the label becomes an alias | `scan/nodes.py:371, 386` |
| statement with no label | `FILE#theorem:3` | same |
| proof attached to a statement | `STMTKEY/proof`, `/proof/2` (so by place whenever its statement is) | `scan/nodes.py:554` |
| proof attached to nothing | its first label: `FILE#label`; else `FILE#proof:N` among the file's unattached proofs (bc6268c5) | `scan/nodes.py:588-598` |
| section | id; else **`FILE#label` already**; else `FILE#section:N` (`subsection:N`, …) | `scan/nodes.py:423-428` |
| equation | only when labelled: a region `CONTAINERKEY#eqlabel`, so it is by place whenever its container is | `scan/nodes.py:768-775` |
| prose | the own text of its section's key, or of the document (`FILE.tex`, a path followed by `loom mv`) before the first heading | `scan/nodes.py:601-639` |
| Markdown file | not a key: `loom annotate notes/README.md …` gives "no such key"; it can only be linked, `quilt:notes/README.md#heading` | `links.py:97-99`, hand check |

Three details matter for the design.

- A block's hash covers its own text with `% !LOOM child: KEY` markers where its children were (`render/manifest.py:147-181`). So a section's hash changes whenever a child's key renumbers, even when not a word of the section changed.
- A typed ordinary label resolves to the positional key at filing time (`cli/_quilt.py:95-111`). So `loom annotate thm:main` files on `FILE#theorem:3`, and the label is not kept.
- `annotate` and `suggest` freeze the text they were written on (`cli/review.py:405-415`, `cli/suggest.py:122`). So the old text of every record can be recovered, and the design below depends on that.

## KEY-2 · How a record finds its block again today

Annotations (`records/store.py:573-576`) and suggested edits (`home`, `records/edits.py:193-200`) both go through `written_on` (`records/store.py:123-148`):

1. a key with no `#`, a region key, or a record with no `against`: the block the key names;
2. the block at the key, if it still has the record's hash;
3. else the one block of the same file with that hash;
4. else the block the key names now, whatever it holds.

The quote is then looked for only inside that block (`resolve_selector`, `records/selectors.py:215-243`; with in-place changes put back, `store.py:_on_kept`). If it is missing there the record is detached, shown "gone" against the frozen old text (`render/versions.py`). Nothing searches outside the block. Step 4 is SAFE-4: any record whose block both moved and changed, or whose text has twins, falls onto whichever block now holds its place.

## KEY-3 · How common each kind of key is · blocks the Overleaf pilot

Counted by scanning each paper as written (`count_keys.py`).

| paper | statements (labelled / none) | proofs (attached / unattached) | sections (labelled / none) | labelled equations | pieces | keyed by place today | with label keys |
|---|---|---|---|---|---|---|---|
| man12 | 96 (44 / 52) | 30 / 0 | 21 (1 / 20) | 36 of 110 | 147 | 146 (99%) | 83 (56%) |
| acgs | 70 (56 / 14) | 31 / 1 | 74 (29 / 45) | 39 of 42 | 176 | 147 (84%) | 60 (34%) |
| kpsv | 51 (28 / 23) | 7 / 5 | 17 (6 / 11) | 19 of 21 | 80 | 74 (93%) | 39 (49%) |
| mzk | 19 (16 / 3) | 11 / 0 | 10 (4 / 6) | 72 of 161 | 40 | 36 (90%) | 10 (25%) |
| relloc | 40 (28 / 12) | 15 / 2 | 11 (3 / 8) | 11 of 78 | 68 | 65 (96%) | 24 (35%) |
| **five papers** | 276 (172 / 104) | 94 / 8 | 133 (43 / 90) | 177 | 511 | **468 (92%)** | **216 (42%)** |
| quant (3 files) | 0 | 0 / 57 | 19 (0 / 19) | 0 | 76 | 76 (100%) | 76 (100%) |
| showcase (imported) | 19 (17 ids / 2 none) | 7 (ids) | 6 (ids) | 3 | 32 | 2 (6%) | 2 |

So 62% of statements carry an ordinary label and 38% carry none. Every labelled equation sits inside a container keyed by place.

Homework carries no labels at all. Every problem is a `\section*` and every answer an unattached proof, so for quant label keys change nothing, and only the record-side changes (KEY-7, KEY-8) help.

Importing a paper (`loom init --from`, `loom import`) drafts the working document with `\label{PREFIX-XXXX}` on every statement and section that has none (`reshape/canon.py:125-129`, `reshape/ids.py:33-73`). That is why the showcase is 94% id-keyed. A read-only Overleaf mirror does not import (`cuts.md` CUT-5 e), and must not write the person's file (INST-10), so it gets no ids: a pilot's own paper arrives about 92% by place.

## KEY-4 · What happens today under co-author edits · blocks

All seven papers, 247 records per edit (159 tuning, 88 held back), 4,693 placements in all:

| edit | right | wrong | detached | lost |
|---|---|---|---|---|
| insert a theorem above | 245 | 2 | 0 | 0 |
| insert a section above / light edit | 247 | 0 | 0 | 0 |
| heavy edit, quote kept | 229 | 0 | 0 | 18 |
| quoted words rewritten | 47 | 0 | 200 | 0 |
| move a statement | 245 | 2 | 0 | 0 |
| move a section | 231 | 3 | 9 | 4 |
| rename a label | 227 | 0 | 0 | 20 |
| delete a statement | 91 | 25 | 71 | 60 |
| rename the file | 3 | 0 | 0 | 244 |
| split the file | 122 | 0 | 0 | 125 |
| insert + light edit | 76 | 40 | 103 | 28 |
| insert + heavy edit | 72 | 40 | 103 | 32 |
| move + light edit | 90 | 30 | 83 | 44 |
| rename label + light edit | 227 | 0 | 0 | 20 |
| rename file + light edit | 3 | 0 | 0 | 244 |
| split + insert | 122 | 1 | 3 | 121 |
| label reused | 187 | 17 | 43 | 0 |
| duplicate label | 247 | 0 | 0 | 0 |
| **all** | **2958 (63%)** | **160** | **615** | **960** |

Of the 1,575 detached or lost records, 1,195 are misses: their block and words still stand. 301 of them are shown detached on a key that now names another block, which is INST-11's "shown gone against the wrong block's text".

The wrong placements fall into four kinds.

- **Whole-block notes (141 of the 160).** With no quote, nothing checks the block, so step 4 of `written_on` attaches them to the newcomer at the old place. Example: delete man12's `remark:9`, and the note on it now sits on the next remark.
- **Restated theorems.** kpsv restates its main theorem. After insert+light edit, the 6-word quote "Then, there exist no smoothly embedded" resolves in the restatement, which now holds `theorem:11`. Both the annotation and the suggested edit sit there, attached and not flagged.
- **Short selections.** acgs's "together with" and "The stack" resolve in whatever block took the place.
- **SAFE-4, reproduced on quant's `hull_ch1.tex`.** A whole-body suggested edit on an empty `\begin{proof}[Answer]\end{proof}` is placed on another empty answer after an insert above, and again after a move. That accounts for 5 of the 7 suggested edits placed in the wrong block today; the other 2 are kpsv's restatement.

Renaming the file loses everything except the id-keyed showcase record, because the path is part of every key. Insert-above alone works (d0dcd0d9's hash follow), and so does a light edit alone. It is the combination, a pull that adds a theorem and also touches the annotated one, that fails (INST-11's fourth case): only 76 of 247 right.

## KEY-5 · The file-wide quote search as worded is not safe · blocks (as proposed)

Mode `literal` in the prototype does what the claim says: label keys, today's `written_on`, and when the quote is not in the block found, the quote looked for in every block of the file, then the quilt, best by its prefix. Over the same 4,693 placements:

- right rises from 2958 to **3935**, but **wrong rises from 160 to 255**;
- **suggested edits placed in another block rise from 7 to 43**, 38 of them quoted.

The mechanism: a quote is unique inside its block, not in the file. Rewrite the quoted words and the search finds them where they also stand:

- man12's "is taken to be smooth over" occurs twice in the file;
- kpsv's restated theorem holds its twin's words;
- a 2-word selection occurs everywhere;
- in the showcase, rewriting the words of the id-keyed `sh-0006` sends its suggested edit to `sh-0401`, the restatement in `talk.tex`, another document.

By edit: quoted words rewritten gives 47 wrong where today gives 0; delete gives 38; split the file gives 18. The search also "rescues" records whose words really are gone, onto other text.

## KEY-6 · Label keys with today's lookup · hurts

Mode `labels`: statements key as `FILE#label` (the label unique in its file, not shaped like a place key), with `written_on` unchanged.

- Wrong placements fall from 160 to **65**, and right rises to 3103.
- Lost rises from 960 to 1,160: renaming a label makes the key vanish (rename-label: 64 lost, against 20 today), and nothing follows it.
- Renaming or splitting the file is still total loss (3 right of 247).

Label keys are necessary but not enough on their own.

## KEY-7 · The safe design, measured · —

Mode `safe` (the patch's default): one resolver, `follow` in `records/store.py`, for annotations and suggested edits.

- A **stable key** (an id or `FILE#label`) keeps its block while that block still reads as the record was written:
  - the text is unchanged, or the quote stands in it, or it reads at least 0.6 alike word for word, child markers stripped;
  - otherwise, under `trust`, the block keeps the record unless the old text is clearly found in another block; under `verify` the record detaches.
- A **labelled key whose label left its file** (file renamed or split) is followed by the label, through `asm.labels`. A label that stands twice is refused.
- A **key named by place** keeps the block now at that place only when the neighbours recorded at filing still stand at the same distance on both sides.
- Otherwise the old text is looked for:
  - the same text, with twins told apart by their neighbours;
  - else the one block of the same kind reading clearly closest (at least 0.6, ahead of the next by at least 0.1; for a gone id or label key, only with its neighbours or at 0.95 or more);
  - never by likeness when the block had a near-twin at filing.
- **The quote alone** places a record only when it is at least 4 words, stood once in the whole quilt at filing, and stands once now.
- Otherwise the record is **detached**. The block now at the place is never the fallback.

Writers record the context (`place_context`): the nearest unique block on each side and its distance, or the distance to the file's edge; a `twin` flag; and how many blocks the quote stood in. They freeze the neighbours' texts as well.

| variant | right | wrong | detached | lost | of the wrong: suggested edits |
|---|---|---|---|---|---|
| today | 2958 | 160 | 615 | 960 | 7 |
| labels only | 3103 | 65 | 365 | 1160 | 5 |
| literal (the claim) | 3935 | 255 | 200 | 303 | 43 |
| **safe (trust labels)** | **4126 (88%)** | **15** | 339 | 213 | **0** |
| **safe (verify labels)** | 4100 | **0** | 364 | 229 | 0 |

Misses (records detached or lost while their block and words stand) fall from 1,195 today to 145 (trust) or 171 (verify).

Under `safe` the combined edits come right: insert+light edit gives 237 of 247 right with 0 wrong; rename file gives 236; split gives 243. The 15 wrong placements under trust are all whole-block notes on a label that the label-reused edit gave to a different statement. With `verify` they detach, at the cost of 26 fewer right placements: whole-block notes on labelled blocks that were heavily rewritten now detach too.

Held back: mzk and relloc, run once after tuning, give today 51 wrong; labels only, 12; literal, 61; safe, 6 (all label reuse); verify, 0. Cost: resolving kpsv's 48 records takes 0.67 s today and 0.67-0.97 s with the prototype.

There is one regression. The showcase falls from 205 to 192 right, because its two identical lemmas (`nodes/sh-0020.tex` and `sketch.tex`) each sit alone in their file with no unique neighbour. After an insert above, the record cannot tell them apart and detaches. That is honest, but it is a loss.

## KEY-8 · Restatements and identical blocks need context recorded at filing · blocks (if skipped)

Re-finding a block by its content attracts records to a restatement whenever the original changes or goes.

How common near-twins are (another statement reading at least 0.6 alike, `stats.py`):
- man12: 2 of 96 statements;
- acgs: 2 of 70;
- **kpsv: 15 of 51**;
- mzk: 2 of 19;
- relloc: 0 of 40;
- plus quant's identical empty answers, and the duplicate pasted into `hwk1.tex` (sections 1-7 again as 8-14).

The design steps that went wrong on the way to the safe design, all on twins:
- the closest-text match sent kpsv's rewritten `corollary:6` to its restatement `cor:exotica`;
- a search for the quote inside the file found the copy left behind in `hwk1.tex` after the original moved to `hwk1-part2.tex`;
- a single neighbour could not separate runs of empty answers.

Two-sided neighbours, the twin flag and a whole-quilt count of the quote fixed each of these.

Upgrade check (`upgrade.py`): records filed by today's code, which have no context, read by the prototype.
- man12: unchanged (all right).
- kpsv: 8 wrong after deleting statements, with a restatement taking the records.
- quant: its empty answers detach even with nothing edited.

So the context is not optional: it is a change to the record format, recorded at every filing, and existing records need a one-time pass that stamps context wherever the key still holds the record's text.

## KEY-9 · The acceptance ledger, measured · hurts

Rows (`.loom/state.toml`) are keyed by key, with the text hash and the `closure`/`direct` hashes keyed by dependency keys; they are read by exact key (`records/store.py:297`). Accepting 5 statements (3 labelled, 2 unlabelled) and then applying an edit (`ledger.py`):

| edit | today (man12 / kpsv) | label keys, lookup unchanged |
|---|---|---|
| insert above | all 5 rows on the wrong statements, shown "accepted, stale" with a diff between two different theorems; the real ones show draft | the 3 labelled rows stay right and fresh; rows keyed by place still go wrong, stale (man12 2, kpsv 1) |
| insert + light edit | 5/5 wrong (stale) | 3 right (stale, correctly), 2 wrong |
| delete | 5 rows (man12) and 4 (kpsv) on the neighbours, stale | 1 / 2 on neighbours; the rest retired (`loom:retired-ledger-key`) |
| rename a label | rows stay (by place) | 3 rows retired; the statement shows draft (acceptance lost, not misplaced) |
| label reused | 4 / 3 rows on other statements, stale | 4 / 3 on the statement that took the label, stale ("own text changed") |
| duplicate label (verbatim restatement above) | man12: `lemma:3`'s row is **fresh** on the copy; the original is draft | labelled rows retired (both copies lose the label key); man12's 2 rows keyed by place shift onto neighbours, stale; none fresh |
| rename the file | 5 retired | 5 retired |

A fresh row can attach only to identical text, so the ledger cannot silently approve different mathematics. But "accepted, stale" on a statement nobody accepted, with a diff between two different statements, invites a re-accept. Label keys fix labelled rows; rows on statements keyed by place need the same resolver, in verify mode only: a row is a claim about exact text, so it should follow text, never "trust" a label. On upgrade every row on a labelled statement names a positional key that no longer exists, and is retired. The ledger is append-only and written only by `loom accept`, so the author re-accepts; for a pilot's new quilt there is nothing to migrate.

## KEY-10 · Every other kind of record that names a key

| record | upgrade (keys change form) | the author later renames the label | two pieces share an ordinary label | could it attach to the wrong mathematics? |
|---|---|---|---|---|
| annotations (`.loom/annotations/log.jsonl`) | old `FILE#theorem:3` keys of labelled statements no longer exist; found again by exact text (man12, kpsv: all right as filed); without context, twins detach and restatements attract (KEY-8): needs a one-time context pass | key gone → label not found → found by text and neighbours (rename-label: 247/247 right) | neither gets a label key (`label_keyable`); records follow text; duplicate-label 247/247 right | trust mode: whole-block notes on a reused label (15); verify: none |
| suggested edits (`.loom/edits/log.jsonl`) | as annotations; Keep writes, so an edit must be placed only when its block reads as `against` or its quote stands: verify always | as annotations | as annotations | literal: 43; safe: 0. A quote-less body edit on a reused label, under trust, would replace the new statement's body: edits must never use trust |
| acceptance ledger (`state.toml`) | rows on labelled statements retire; the author re-accepts; `closure`/`direct` dependency keys change form, so rows depending on them go stale with dependency-removed/added | row retired; acceptance lost, never misplaced | rows retire while the label is doubled | only as "stale" on other text (KEY-9); fresh only on identical text |
| history steps and versions (`.loom/history`) | per-key versions exist only for id keys without `#` (`history/steps.py:43-50`); `FILE#label` keys stay unversioned, file versions unaffected; snapshots are stored by hash. If keys were bare labels they would become versionable, and a rename would end the chain | file versions unaffected | — | no |
| `last-seen.json` | keyed by key, rewritten every build; renamed keys find no old text, so nothing is frozen for them, which is harmless because annotate and suggest freeze at write time | same | — | no |
| digests of cited papers | every digest label is rewritten as `SLUG-label` (`digest/extract.py:551`), id-shaped for the slug: unaffected | the digest is loom's, regenerated | — | no |
| `\uses` and `\ref` edges | rebuilt every scan from `asm.labels`; only their copies in ledger rows change | edges follow the source | `asm.labels` keeps the first claim quilt-wide (`scan/nodes.py:786-802`), so two documents in one quilt sharing `\label{p1}` send the second's `\ref` to the first's block, an error but resolved anyway (read in code, today's behaviour) | yes, today, for `\ref` across documents that share a label |
| links in transcripts, messages and annotation bodies (`quilt:KEY`) | text, never rewritten. Old `quilt:FILE#theorem:3` links to a now-labelled statement go dead (positional ordinals count labelled blocks too, so the ordinal is not reused) | dead link, refused when shown | resolved to the first claim | **yes, today**: a `quilt:FILE#theorem:3` link silently names whichever theorem is third after a pull. Label keys fix labelled ones; `loom link` should print labels |
| `since` markers (`.loom/since/*.json`) | the stale set names old keys: one noisy "newly stale" report | same | — | today, renumbering reports the wrong keys as newly stale; machine-local, no damage |
| review observations, decisions, origins (`.loom/review-*.json`) | identities include the key: first-seen dates and decisions reset | same | — | no: a decision carries a fingerprint of the block's text and closure (`review_queue.fingerprint`) and applies only while it matches (read in code) |

## KEY-11 · Labels in the wild · hurts

- **Spaces and other characters.** 81 of acgs's 139 labels contain spaces (`Thm: Decomposition`), 14 contain `()[]#%` (`fM(cX_0)`), and 70 of mzk's 96 contain spaces. As keys these break the `quilt:` link grammar: `LINK = …[^)\s]+` stops at a space or `)` (`links.py:19`), and `resolve_key` is given the raw, unquoted string (`links.py:106`). Keys need percent-encoding in links, decoded before lookup.
- **Shapes and duplicates.** Across the five papers, no label had a place key's shape (`lem:2` beside an environment `lem`), no statement's first label was an equation's, and no label was defined twice outside comments. The prototype refuses all three anyway: a label as a key must be the block's own head label, unique in its file, and not shaped `NAME:N`.

## KEY-12 · Unit tests · —

The targeted files, 158 tests, were `tests/unit/scan/{test_nodes,test_conflicts,test_labels_hashing}.py` and `tests/unit/records/{test_carry,test_edits,test_review_commands,test_recorded,test_lastseen,test_hostile_log,test_log_delete}.py`. All 158 pass at 71621877; with the prototype, 5 fail:

- `test_nodes.py::test_env_node_without_id_qualified_key_and_regions`: expects `#lemma:1`; the key is now `#lem:human`. The rule changed on purpose.
- `test_carry.py::test_an_annotation_on_a_key_named_by_place_goes_with_its_block_when_one_is_put_in_before_it` and `test_edits.py::test_an_edit_goes_with_its_block_when_a_block_put_in_before_it_renumbers_the_keys` assert today's "moved and edited stays on the old key". The prototype follows the block instead. The annotation is detached on the right section (its words are gone), and the edit stays placed because its quote still stands. Both tests encode the behaviour INST-11 calls a defect.
- `test_lastseen.py::test_an_edit_under_an_annotation_freezes_the_text_it_was_written_against[default, configured]` counts one frozen text; the prototype also freezes the neighbours' texts.

## KEY-13 · What to build, in what order, and how big

**Build.**

1. **One resolver**, a new `records/locate.py` holding `follow` and `place_context`. It replaces `written_on`, and every reader goes through it:
   - annotations (`store.resolved`);
   - suggested edits (`edits.home`, and so `place`, `taken_how`, Keep);
   - ledger lookups (`key_states`, verify only);
   - `quilt:` links;
   - `since` and the review files.

   Suggested edits and ledger rows always verify; annotations may trust a label, provided the viewer marks "rewritten since you wrote this".
2. **Context in the record.** `annotate`, `suggest`, the API and MCP writers store `context` (two-sided unique neighbours with their distance or the file's edge, `twin`, the quote's quilt-wide count), and freeze the neighbours' texts. A one-time pass stamps it on existing records whose key still holds their text.
3. **The key rule** in `scan/nodes.py`: a statement whose own head label is unique in its file and not shaped like a place key is keyed `FILE#label`. Positional ordinals keep counting every block, so adding a label never renumbers the rest. Sections get the same uniqueness guard; today two sections in one file with the same label would share a key, and the second would merge into the first's record (`scan/nodes.py:430-449`, read in code).
4. **No quote-only search beyond the guarded one** of KEY-7.
5. **Viewer and manifest.** A record the resolver detaches from a key named by place is listed as unplaced, not counted on the block that now holds the place. Lost records (75-141 of them after deletions) need somewhere to be shown, such as a "notes whose text is gone" list per document. `loom link` prints label keys, percent-encoded.
6. **Fast tests.** Port six harness edits to small synthetic papers: insert+edit, rename file, delete with a restatement, empty-answer twins, label reuse, duplicate label. Keep the harness under `loom/scripts/` for real papers.

**Order.** 1 and 2 first. They fix SAFE-4 and INST-11's combined case on today's keys, and quant (no labels at all) gains only from them. Then 3. Then the ledger, links and since behind the same resolver. Then 5. Step 3 alone, without 1 and 2, is safe but loses more records (KEY-6). Do not land the literal quote search at all.

**Waits for.**
- The write-path prototype (SAFE-12): Keep must place through the resolver. Land `follow` as a pure function first and let the write door call it, so the two meet only in `records/edits.py`, which S1/S1b (`body_span`) and the SAFE guards also touch, so one agent at a time.
- The Overleaf mirror (O1), only for the end-to-end trial; the code can land before it, against INST's ordering, because SAFE-4 is in the author's own workflow today.

**Files.**
- `records/store.py` (`written_on` and `resolved`), a new `records/locate.py`;
- `records/edits.py` (`home`, `Edit`), `records/log.py` and `records/annotations.py` (the `context` field);
- `cli/review.py` and `cli/suggest.py` (the writers), the matching paths in `render/api.py` and `mcp/`;
- `scan/nodes.py` (the key rule);
- `links.py`, `since.py`, `review_queue.py`;
- arras: the counts of detached notes and the "rewritten" mark;
- the tests named in KEY-12.

**Size.** About 4-5 coding-agent sessions:
- resolver and context: 1.5;
- key rule and guards: 0.5;
- ledger, links, since and review files through the resolver: 1;
- viewer and manifest changes: 0.5-1;
- fast tests and updating the 5 tests that encode today's behaviour: 1.

The audit's "days (2-3)" covered only the key rule and the quote search; the quote search is the part that should not be built.

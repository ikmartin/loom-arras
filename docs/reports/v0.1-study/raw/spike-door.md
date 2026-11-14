# Spike: the one door (v0.1 study)

A throwaway prototype of SAFE-12's "one door" for every write to a person's file, built to test the register's claim that "the one door makes the faults SAFE found impossible by construction". Built in a shared clone of 71621877 in the scratch directory `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/spike-door` (called `$D` below; the safety study's scratch is `$S` as in `safety.md`). Nothing was merged or pushed; the whole change is `spikes/one-door.patch`. Every measurement below was run against the same seeds and scripts before (`$D/base`, the code at 71621877) and after (the clone).

Verdict: the claim holds for the faults in which loom itself writes twice, loses a write made beside it, or replaces bytes it does not keep, and it is false as stated for the faults in which loom misreads text that someone else wrote. With the door, every write in the prototype's scope keeps its before and after bytes exactly, two writers can no longer interleave, a crash leaves a state the next act settles, and an edit loom wrote is known by record. But SAFE-4, SAFE-8 and three of SAFE-1's five shapes come from loom deciding whether text the person or an agent typed is already the edit, or which block a key names; no record of loom's own writes can know what someone else typed, and the prototype closed those with three changes that are not the door: the taken test looks only at the edit's place, an edit refuses to be written when the words beside its place (a quote's neighbours, or a body's first or last words) changed since it was filed, and a key named by place carries the line above its block. All nine strict expected-failures of the kept test now pass, every reproduction and crash case that ran shows no damage, and the random-sequence harness's damage to text falls from 105 of 200 synthetic sequences (20 without the injected save) to 5, every one of which, traced, is a second Keep refused while a first ran, with nothing lost; on showcase it falls from 29 to 1 and on quant from 12 to 0, the same; on a quilt with Windows line endings Keep and Discard no longer touch a line ending, and what the harness still flags is restore writing versions that `stamp_document` keeps LF-normalised. The one-step undo of Keep gives back the bytes exactly, and 100 random sequences with it among the acts show no damage. Getting there took four rounds of the harness, and two of the faults it found were introduced by the prototype's own rules for making records follow the text, which is itself a finding (DOOR-14). The door costs about 3 ms per write against 0.5 ms, Keep is about 12% slower end to end, and the journal as SAFE-12 describes it (read whole on every act) grows to 0.7 s per act at 50,000 acts, so it needs compaction before it ships.

## Findings at a glance

| id | finding |
|---|---|
| DOOR-1 | Verdict per SAFE finding: the door closes SAFE-2, 3, 5, 10 (for the writers routed) and the loom-wrote-twice shapes of SAFE-1; SAFE-6 and 7 close only with the door's bytes-in, bytes-out rule applied to the text store as well; SAFE-1's typed-in shapes, SAFE-4 and SAFE-8 need separate fixes; SAFE-9 needs the journal plus a new verb; SAFE-11 is half outside |
| DOOR-2 | Measurements: the kept test's 9 expected-failures pass; every reproduction and crash case clean; random-sequence damage 105 → 5 of 200 synthetic sequences, each of the 5 a refused concurrent Keep that lost nothing |
| DOOR-3 | Loom's own tests near the changed code: 444 of 448 pass; the 4 that fail (all pass on 71621877) assert the old behaviour or a registry the new endpoint and doctor item must join; no regression found |
| DOOR-4 | What was built: `writes.py` (465 lines) and 11 changed files; the interface as it ended up and how each caller uses it |
| DOOR-5 | SAFE-12 left out: the door cannot see what others wrote, so "taken" must be judged at the edit's place, with the place's own precondition |
| DOOR-6 | SAFE-12 left out: the scan's view is stale and normalised; the precondition must compare the bytes the plan came from, and every decision must be made again under the lock |
| DOOR-7 | SAFE-12 got wrong: an act id derived from content names a later act like an earlier one when a state recurs; only Keep has a natural id (edit and reopen generation) |
| DOOR-8 | SAFE-12 left out: records must change shape (the kept hash from the plan, `near` and `edge` on created edits, digests of bytes), and half of an act's records cannot be journalled as data |
| DOOR-9 | Lock scope: stamping a version had to move inside the door; the order is publication, writes, then history and logs; the lock is held through rescans |
| DOOR-10 | A bare precondition turns two Keeps at once into a refusal; one re-plan under a fresh scan fixes it |
| DOOR-11 | Cost: 3.1 ms a write against 0.5 ms; Keep 75 to 84 ms median; the journal read whole costs 131 ms per act at 10,000 acts and 741 ms at 50,000 |
| DOOR-12 | Files that are not UTF-8 are refused, not spliced; CRLF files are spliced in their own line endings; the text store itself read CRLF as LF |
| DOOR-13 | The journal belongs in the history directory, not `.loom/writes`, or every quilt's agent permission files change |
| DOOR-14 | One-step undo of Keep: whole file when nothing moved, else the splice; records must follow every act that moves an edit's words, either way, and the prototype's first rules for that wrote an edit twice |
| DOOR-15 | What the anchor precondition costs: a second edit beside the same quote or body edge is refused once the first is kept; a residual false "taken" for a replacement whose text contains its quote |
| DOOR-16 | Smaller gaps: temp files in the person's directory until the next act, `fsync` is not a full flush on macOS, recovery runs only inside an act, adopt and sync keep a second rollback mechanism |
| DOOR-17 | What the real implementation should do differently |
| DOOR-18 | Landing order, what must wait, files to own |
| DOOR-19 | Size: the prototype took about an hour and three quarters; a careful version is 6 to 7 sessions |

## DOOR-1: verdict per SAFE finding

| finding | closed? | by |
|---|---|---|
| SAFE-1 (Keep writes an edit a second time) | yes, all five shapes and the crash window | the door for shapes 3 (two Keeps at once) and 4 (the reopen of a kept edit, now refused, with `change-undo` in its place) and the crash between write and record (journal and recovery); **not the door** for shape 1 (text after `\end{…}` typed in: closed by judging "taken" at the edit's place), shape 2 (short text typed in and touched: closed by the edit's own precondition on the words beside its place, which a body placement had to start recording) and shape 5 (a by-place key moved: closed with SAFE-4) |
| SAFE-2 (a save during Keep lost; two Keeps lose an edit) | yes | the door: one lock across processes, decisions made again under it, the file compared with the text the plan came from, and one re-plan from a fresh scan when it moved (DOOR-10) |
| SAFE-3 (an interrupted write is invisible) | yes | the journal's `begin` before any file, recovery on the next act (finished when every file holds its after bytes, aborted when every file holds its before bytes), unique temp names, and a `loom doctor` line for an act recovery could not settle; temp files of a crash stay until the next act (DOOR-16) |
| SAFE-4 (an edit written into another block) | yes | **not the door**: a created edit on a key named by place records `near`, the line above its block; `written_on` uses it to tell apart blocks with one text and answers "no block" when it cannot. A record change |
| SAFE-5 (restore overwrites a file it does not keep) | yes | the door: the before bytes of every file any act replaces are stored, reached by a document or not |
| SAFE-6 (Keep and restore rewrite bytes outside the edit) | Keep yes; restore partly | the door splices in the file's own text at offsets mapped from the scan's reading, in the file's own line endings, and refuses a file that is not UTF-8 (DOOR-12). Restore still writes a version's text, which `stamp_document` keeps LF-normalised; the prototype puts it back in the file's own line ending, but versions are not byte-exact, so a version of a file with mixed endings cannot give its bytes back |
| SAFE-7 (Discard in a CRLF file corrupts it) | yes | the door reads the file's bytes, and `snapshots.read_raw` now returns the stored text exactly; it read CRLF as LF, so the look's text and the file's were in two different readings (DOOR-12) |
| SAFE-8 (an insertion that reads as taken is never written) | narrowed, not closed | **not the door**: an insertion is taken only when its text stands at its place and the words recorded beside its place no longer do; a replacement whose quote still stands once is never taken. A residual: a replacement whose new text contains its quote and whose words already follow it reads as taken (DOOR-15) |
| SAFE-9 (no one-step undo of Keep) | in the API, not the viewer | a new `change-undo` endpoint through the door writes back exactly the bytes the Keep replaced and opens the edit (and refuses for a Keep that wrote nothing); restore and put-back now open again a kept edit whose written words they take out, found through the journal (DOOR-14). The viewer is untouched, and an edit with short common words can stay recorded kept after a restore took it out |
| SAFE-10 (writes that keep no version) | yes for Keep into an unread file, a conflicted document and Settings; no for the agent layer | the door stores the before bytes whatever `keep_versions` does; Settings go through it and keep their mode. `.claude/settings.json`, `import`, `init --from`, `mv`, `atomize --retire`, `pages.write` and `sync.incorporate` were not routed |
| SAFE-11 (the write API trusts too much) | the path half | `put_back` and `restore` refuse a path outside the quilt; the token readable by an agent is untouched, and is not a write-path question |

## DOOR-2: measurements

**The kept test** (`tests/unit/test_write_safety.py`, copied as the safety study's §6 says): 6 passed, 9 xfailed before; after, all 15 pass, the nine with their markers (`--runxfail`) and after the markers were removed. Nine further tests of the door are in `tests/unit/test_door.py`: undo byte-exact in a CRLF file and keeping again after it, undo after a later edit elsewhere and refused after one inside, the reopen of a kept edit refused, an act killed after its write finished by recovery and never written twice, an act killed before its write aborted, two Keeps at once in two threads, a Latin-1 file refused whole, every write journalled with its bytes, and a restore of "Before keeping" opening the edit again.

**Reproductions** (`$D/repros-before.log`, `$D/repros-after.log`; scripts copied from `safety-harness/repro`, paths pointed at the clone):

| reproduction | before | after |
|---|---|---|
| `r_outside_block typed` | 2 copies | 1 copy (read as taken at its place) |
| `r_outside_block reopen` / `agent` | 3 / 2 copies | the reopen of a kept edit is refused, so the script stops at its next Keep; `$D/repro/r_door_cycle.py` runs Keep, the old reopen (refused), `change-undo`, three times: 1 copy after each Keep, 0 and the bytes exactly as before after each undo |
| `r_race same` | 2 copies | 1 copy; the second Keep is told the edit no longer waits |
| `r_race two` | X lost while recorded kept | both kept, each once (the second re-planned) |
| `r_wrong_block` (quant) | answer to Problem 3 in Problem 2 | in Problem 3 |
| `r_restore_unreached` | paragraph kept nowhere | in the history |
| `r_encoding crlf` / `latin1` | 0 of 3 CRLF kept / ö written as ˆ | 3 of 3 / refused, file untouched |
| `r_crlf_discard` | `\end{proof the`, all CRLF lost | bytes exactly as before |
| `r_phantom_taken` | listed taken, nothing written | listed ready, written |
| `r_unreached_keep` | the whole file before not kept | kept byte-exact |
| `r_put_back_path` | writes outside the quilt | refused |
| `r_section_in_block` | 1 copy | 1 copy |
| `r_adopt` (showcase, `drafting/main-atomic.tex`) | one file changed, before text kept, token refused again | the same, through the door |
| `r_http_cli_race` (real `loom serve` and CLI, 15 trials each) | lost a kept edit in 1/15 (the safety study saw 3/15); wrote one edit twice in 0/15 | lost 0/15; twice 0/15 |
| `r_encoding symlink` | the script fails before any write (its quote does not stand) | the same |

**Crash injection** (`$D/crash/crash.py`, its child pointed at the door's `write_bytes` and the step after the records): before, 2 of 16 cases ended with the edit written twice (after the write, before the record: a short text touched, and text after `\end{remark}`); after, 0 of 16. After a crash after the write the edit is listed taken by the journal; the next act finishes the act (appends the kept record, then `done`, marked `recovered`). After a crash before the rename the edit is listed ready; the next act aborts the act, removes the temp file, and writes once. No crash case left a temp file once the next act had run.

**Random sequences** (`$D/run_harness.sh`: the safety harness unchanged, 35 acts a sequence, the same seeds before and after, in process; `harness/analyze.py` classifies). "Damage" is `analyze.py`'s count (a SAFE-1, 2, 5, 6 or 7 class); "by inspection" is what is left after tracing each such sequence:

| run | sequences | failing, before → after | damage before (without the injected save) | damage after | by inspection |
|---|---|---|---|---|---|
| synthetic, edits tracked | 200 | 188 → 32 | 105 (20) | 5 | 0: three pairs of Keeps at once where the second was refused (its quote went with the first edit, the two clashed, or the file moved) and nothing was lost, two of them kept once on the next press |
| synthetic, every `.tex` CRLF | 40 | 40 → 30 | 40 (40) | 29 | 0 from Keep or Discard (before: CRLF rewritten by 36 Keeps, 25 Keep alls, 12 discards); all 29 are restore of a version, whose text is kept LF-normalised, plus the injected save (below) |
| showcase, edits tracked | 60 | 58 → 11 | 29 (5) | 2 | 0: as synthetic |
| quant, edits not tracked | 30 | 28 → 21 | 12 (3) | 0 | 0; the 21 are the source quilt's `config.toml`, already mode 0600, which the door keeps as it finds it while the harness expects 0644 (14), restores of quant versions that already held the pasted copies SAFE describes (8), and records left kept after a restore (6) |
| synthetic with `change-undo` among the acts (after only) | 100 | — → 13 | — | 0 | 0; no undo left its edit kept or its words in, and no Keep, undo, Keep cycle wrote an edit twice |

By class on synthetic, sequences before → after: recorded kept with its text gone after a restore or undo (SAFE-9) 142 → 19; taken and never written (SAFE-8) 113 → 4; a save lost during Keep (SAFE-2, injected) 94 → 0; `config.toml` mode changed (SAFE-10) 94 → 0; written twice after `\end{…}` (SAFE-1) 10 → 0; written twice after a reopen (SAFE-1) 3 → 0; two Keeps at once (SAFE-2) 8 → 3, all refusals that lost nothing; restore overwrote a file kept nowhere (SAFE-5) 1 → 0; Keep into a conflicted document with no version (SAFE-10) 1 → 0. No sequence after the change has an edit standing twice, an open edit listed ready while its text stands, a person's words lost, or a write whose before bytes are kept nowhere.

What the after runs still flag, traced: an edit left recorded kept after a restore took its words out (the reopen rule is conservative, DOOR-14) or kept without loom writing it; a replacement whose new text contains its quote, and a text a restored version put back, read as taken (DOOR-15); a Keep refused because the file moved (the injected save) or two edits clashed, then pressed again, which the harness reads as a repeat that changed files; a kept replacement whose quote held an earlier kept edit's words, which leaves that edit recorded kept with its words gone (legitimate); and seed 3167, before and after, whose document reaches a conflicted key so The Record kept no "Before keeping" version (the journal holds the bytes, and `change-undo` gives them back). On CRLF, restore writes a version in the file's majority line ending, so a file whose endings the person had mixed loses the mix (13 sequences), and the harness compares a restored CRLF file with the version's LF text (24, the same before); the injected save, made between the landmark and the door's read, replaces bytes that only the normalised landmark holds (4), which is the editor's overwrite, not loom's.

## DOOR-3: loom's own tests

Before: the nine files nearest the change (`test_pending`, `records/test_edits`, `render/test_write_api`, `history/test_acts`, `test_tasks`, `test_config_edit`, `test_looks`, `test_adopt`, `records/test_review_commands`) pass 287 of 287. After, on a wider set of 18 existing files (adding `history/*`, `records/test_carry`, `render/test_pending`, `render/test_versions`, `test_doctor`, `test_paths`, `test_review_queue`, `test_personal_acceptance`), run with two or three workers: 444 of 448 existing tests pass, and the 24 new ones (the kept test and `test_door.py`) pass. The four that fail all pass on 71621877 (checked with the baseline source on `PYTHONPATH`):

- `render/test_write_api::test_every_capability_has_a_case_and_a_row_in_the_spec`: the new `change-undo` endpoint has no row in the spec. A registry asking for documentation, not a regression.
- `test_adopt::test_record_failure_restores_source_and_history`: asserts that a failed adopt leaves the history directory exactly as it was; now it holds `writes.jsonl` and `writes.lock`, the journal of the attempt (begun, then aborted at the next act). The old behaviour asserted; the assertion should exclude the journal.
- `test_doctor::test_the_demo_is_ok_in_every_quilt_item` and `::test_the_text_report_lines_up`: both pin the exact set and count of doctor items, and the prototype adds one (`writes`). The old behaviour asserted.

Two failures seen on the way were real and were fixed: placing the journal under `.loom/writes` failed `test_paths` (every `.loom` path must be protected or an agent's place) and, once added to the protected table, changed the agent permission files so that the demo's shipped `.claude/settings.json` no longer matched (DOOR-13); and a `kept` record without its key hash failed `records/test_edits` (DOOR-8). `test_edits::test_an_edit_goes_with_its_block_when_a_block_put_in_before_it_renumbers_the_keys` caught a first version of the `near` rule that refused a block whose text was unique; the rule now asks `near` only when the text cannot decide.

## DOOR-4: what was built

New: `loom/src/loom/writes.py` (465 lines), `loom/tests/unit/test_door.py` (166), and the kept test `loom/tests/unit/test_write_safety.py` (408, markers removed). Changed (added/removed lines): `pending.py` 207/68, `history/acts.py` 83/26, `records/edits.py` 69/34, `render/api.py` 29/1, `tasks.py` 28/24, `records/store.py` 21/5, `doctor.py` 18/0, `adopt.py` 17/5, `config_edit.py` 9/1, `cli/suggest.py` 10/0, `records/snapshots.py` 3/2. Production code: 959 lines added, 166 removed.

The door as it ended up:

    with writes.act(root, history_dir, kind, act_id, actor) as w:   # takes <history>/writes.lock, then recovers
        if w.previous is not None: return w.previous["answer"]       # this act id is done already
        text = w.text(rel)                  # bytes under the lock, decoded UTF-8 or WriteRefused("not-utf8")
        w.expect(rel, planned, newlines=True)   # WriteRefused("changed") unless the file reads as the plan's text
        new, made = writes.splice(text, [(a, b, words)])   # scan offsets mapped to the file's own, its line ending kept
        w.replace(rel, new.encode(), made)  # staged; the splices are kept for an undo
        w.edits.append("e-…:0")             # what this act wrote, by record
        w.log(".loom/edits/log.jsonl", {...})    # a record line, journalled, replayed by recovery
        w.then(fn)                          # a follow-up after the files (rescans, looks, carries), not replayed
    # on exit: store before and after bytes (texts/<sha>.md, .bin if not UTF-8) -> journal begin
    #          -> each file: unique temp beside it, fsync, mode kept, os.replace -> record lines -> follow-ups -> journal done
    # an act that changes no file writes no journal line; its record lines are still appended

Beside it: `writes.undo(root, history, act_entry, act_id, actor, only=…, records=…, look=…)`, `writes.written_edits(root)` (every `<edit>:<generation>` loom wrote, by the journal and, for an unsettled act, by the file's bytes), `writes.last_act`, `writes.unfinished`, `writes.recover`, `writes.fresh_id`, `writes.store`/`fetch`/`digest`.

How each caller uses it:

- **Keep** (`pending.keep`): in-place changes go into the look as before. For suggested edits, one act per request named `keep:<edit>:<generation>+…`. Under the lock: the edit log is read again, edits loom already wrote (by the journal) and edits no longer open are dropped, which to write is decided again (the list was made before the lock, DOOR-6), placed with `compose`, the "Before keeping" landmark stamped, then each file read, compared with the scan's text, spliced, and a `kept` line per edit journalled with the key hash computed from the plan. The rescan, the record of edits kept without writing (taken), the resolution of answered annotations, the look's absorb and the carry run as follow-ups. The API's `_change` re-plans once from a fresh scan for edits refused "changed".
- **Discard** of an in-place change (`pending.discard`): one act per file with a unique id; the file read under the lock must equal the text the change was cut from (`look_texts`' now), then the look's old words are spliced back exactly; the ledger's `undo` line, with digests of bytes, is a follow-up.
- **Undo of Keep** (`pending.unkeep`, endpoint `change-undo`): finds the keep act that wrote `<edit>:<generation>` and runs `writes.undo` for that edit only, with the `reopened` line journalled; the look follows when it held the act's after text. The old `change-discard {undo: true}` refuses a kept edit.
- **Restore** (`history.acts.restore`): the landmark is stamped first as before; one act writes every file of the version whose text differs, in the file's own line ending; the `restore` ledger line and the reopening of kept edits whose text the restore took out are follow-ups. The refusal "its text now cannot be kept first" is gone, since the door keeps it whatever.
- **Put back** (`history.acts.put_back`): the stored bytes are written back through an act, the path contained; reopening as for restore.
- **Tick** (`tasks.tick`): the read, the stale check and the write in one act; the look and the `tick` ledger line are follow-ups.
- **Settings** (`config_edit.set_values`): one act, `expect` against the text read, mode kept, before bytes stored.
- **Adopt** (`adopt.incorporate`): the overlay is written by one act with `expect` per file the scan read; `finish()` (history step, review origins) is its follow-up; adopt's own snapshot rollback stays around it (DOOR-16).
- **The taken test and placement** (`records/edits.py`): `place(…, context=True)` refuses an insertion whose words beside the quote, or whose body's first or last words (`edge`, written by `cli/suggest.py` for a body placement), changed since filing; `taken_how` judges an insertion at its place, and a replacement whose quote stands once as not taken; `records.edits.apply`, dead since CORE-5, is deleted. `records/store.written_on` takes `near`; `cli/suggest.py` writes it for a key named by place.
- **Doctor**: a `writes` item lists acts recovery could not settle.

Not routed: `sync.incorporate`, `mv`, `atomize --retire`, `reshape/importer.set_main_forced`, `reshape/canon.apply_import`, `init --from`, the agent layer's writers, `pages.write`, and the new-file writers.

## DOOR-5: the door cannot see what others wrote

SAFE-12 traces SAFE-1 to "the text test standing in for a record of the write" and expects the record to replace it. It does where loom wrote the text: a crash between write and record, two Keeps at once, a Keep sent again, the reopen of a kept edit. But the kept test's two SAFE-1 cases, and 14 of the 24 harness sequences SAFE counted as written twice, are text the person typed in (or an agent wrote in place) while the edit was open: loom wrote nothing, so there is no record, and the only evidence is the text. The prototype therefore keeps a text test and makes it narrow and local: an insertion is taken only when its words stand right at its place (after the quote for `after`, before it for `before`; at the foot or head of the body for a body placement), and only when the words the selector recorded beside the quote at filing no longer stand there (so a phrase that already sat next to the quote is not mistaken for the edit, which was the harness's main SAFE-8 shape). For a short text typed in and then touched (SAFE-1 shape 2), no text test can recognise it; the prototype refuses instead: `place` raises Unplaced when the recorded neighbour of the quote changed since filing, so the edit is listed unplaced ("the words after the text … quotes changed since it was suggested, so it is not written in blind") and Keep writes nothing. A selector records a quote's neighbours already; a body placement ("after the body", no quote) recorded nothing, and the harness found the same shape there once the quoted case was closed (showcase seed 3031: a three-word suggestion at the foot of a body, typed in, worked inside, then written a second time by Keep), so a created edit at the head or foot of a body now records the body's first or last 32 characters (`edge`), checked the same way. This is a precondition on the edit, the same idea as the door's precondition on the file, but made at filing and checked at the place, and SAFE-12 does not describe it. A replacement is never taken while its quote still stands once, unless its new text contains the quote; the old block-wide test read `proof; this` as taken in place of `proof; this one` because it found the new words inside the quote.

## DOOR-6: the scan's stale view

SAFE-12's precondition is "the file's hash is what loom last read". Loom's plans are made from the scan, and the scan keeps neither the bytes nor their hash: `read_source` decodes (UTF-8, else Mac Roman) and turns CRLF and CR into LF, and every offset a plan holds (`Placed.at`) is in that reading. The prototype's `expect` therefore compares the file's bytes, decoded and read as the scan reads them, with the scan's text, and `writes.splice` maps scan offsets onto the file's own text (`raw_offsets`). That is exact, but it is a text comparison standing in for a hash; the real implementation should have the scan record each file's raw digest and decoding, so the precondition is a hash and the mapping is known to be valid.

The scan is also older than the lock. The first version decided which edits to write from the pending list made before the lock, and the door's own test found the result: an act killed before its write left a `begin`; the list, made before recovery, showed the edit "taken" (loom wrote it, said the journal); recovery then aborted the act; and Keep, trusting the list, recorded nothing and wrote nothing. Every decision (is it open, did loom write it, is it taken, where does it go) has to be made again after the lock is taken and recovery has run, and the list outside the lock is advisory. Likewise `written_edits`, which the list reads without the lock, has to judge an unsettled act by the file's bytes as recovery will, or a crash before the rename lists the edit taken (the crash table showed exactly that until it was changed).

## DOOR-7: act ids

SAFE-12 names acts by content (`restore:<doc>@<version>@<before-hash>`, `tick:<path>:<line>:<state>`) so that "an act whose `done` is in the journal returns its earlier answer and writes nothing". Content recurs: tick, untick, tick again gives the first and third the same id, as does saving a setting, saving it back and saving it again, or an agent making the same in-place edit twice and the person discarding it twice (the change id is a hash of path, words and context, so it recurs too). With content ids the third act would silently do nothing. In loom each act is either "set to state X" (restore, tick, settings, put-back), which is idempotent by nature, or "apply a change to an item with a status" (Keep, Discard), whose repeat the item's status refuses once re-read under the lock. So the prototype gives every act a unique id (`fresh_id`) except Keep, whose id is `keep:<edit>:<generation>`, the generation being the count of `reopened` events: an edit undone and kept again is a new act, and nothing else can make that pair recur. "Return the earlier answer" is then useful only for a client that resends a request whose answer it lost, which needs a request id the client sends, not one derived from content. An act that changes no file writes no journal line, or a Keep refused because the file moved would be "done" and could never be pressed again (the first version did exactly this).

## DOOR-8: records change shape

- The `kept` event held the key's hash after the write, computed from a rescan. For the journal to hold the act's records before the file is written, the hash must come from the plan: the prototype uses `hash_text(placed.taken)`, the block's own text with the edit in, which equals `key_hash` except when the edit opens a block of its own (a section), where the new block is cut out of its parent after the write. Nothing reads that hash today.
- A created edit on a key named by place gains `near` (DOOR-1, SAFE-4), and one at the head or foot of a body gains `edge` (DOOR-5); old edits without them keep the old behaviour.
- The `apply` ledger line stays for The Record only; the guard is the journal. The `undo` line's `from` and `to` are digests of bytes.
- Half of an act's records cannot be data written before the files: the rescan, the record of edits kept without writing, the annotation an edit answers, the look's absorb, the carry of annotations, and adopt's history step are all computed from the scan after the write. The prototype runs them as follow-ups inside the lock and before `done`; recovery replays only the journalled lines, so a crash among the follow-ups leaves the look and annotations unfinished, as today, though the file and the `kept` record agree. The real implementation must decide which of these are part of the act and make those computable from the plan.
- Recovery appends the journalled record lines when it finishes an act; if the crash came after they were appended and before `done`, they are appended twice. Harmless for `kept` (replay takes the last), but records must carry an id that makes their append idempotent before anything less forgiving is journalled.

## DOOR-9: lock scope and ordering

The lock is a file lock (`locks.locked`) on `<history>/writes.lock`, taken by the CLI, the server's threads and any other process alike. Its first scope (read, check, write) was too small: stamping the "Before keeping" landmark outside it raced the other Keep's stamp, and one thread of the two-thread test failed with the history's own "another loom process recorded step 0007 while this one was being prepared". With the stamp inside, the order is fixed: the server's `publication_lock` (a thread lock, outer), then `writes.lock`, then the history's step lock and the edit and annotation logs' locks (inner). Nothing takes the writes lock while holding an inner one, and no deadlock was seen in the threads, the real-process race or the harness. The cost is the hold: Keep holds the lock through the stamp, the write, two rescans and the carry (about 80 ms on synthetic, more on quant), and the server holds `publication_lock` while it waits, so a CLI Keep beside the viewer stalls the viewer for as long; `locks.WAIT` is 120 s. The real implementation should shorten the hold by moving the rescans out (make the follow-ups' inputs part of the plan) rather than widen it.

## DOOR-10: refuse or re-plan

With a bare precondition, two Keeps of different edits in one file at once turn into one success and one "changed since loom read it" (the second planned from a scan taken before the first wrote): nothing is lost, but the person's press fails. The prototype's API re-plans once from a fresh scan when the door refused "changed"; with it `r_race two` keeps both and the real-process race lost nothing in 15 trials. The CLI path has no re-plan. A save by the person's editor during Keep is either seen by the precondition (Keep refused, then re-planned with the save in) or lands after the rename, where it overwrites loom's write in the usual way of editors; the door cannot close that last instant, as SAFE-12 says.

## DOOR-11: cost

Measured with `$D/bench/door_cost.py` and `$D/bench/keep_cost.py` on this machine, other agents running:

| measure | before | after |
|---|---|---|
| one 10 KB write (`write_file` against an act through the door) | 0.52 ms | 3.06 ms (three fsyncs, two stores, two journal lines) |
| an act with 10,000 acts in the journal | — | 131 ms |
| an act with 50,000 acts in the journal | — | 741 ms |
| Keep of one edit through the write API, synthetic, median of 8 | 75 ms | 84 ms |

The journal is read whole several times per act (recovery, the done check, `written_edits`, and the list reads it too). A person keeping a few hundred edits a week reaches 10,000 acts in months. The real journal needs an index: settled acts rotated out to an archive, the hot file holding only unsettled acts and a per-edit map of what loom wrote.

## DOOR-12: bytes, line endings and encodings

The door keeps every byte outside an edit: Keep splices into the file's own text at offsets mapped from the scan's reading, and the inserted text takes the file's line ending (CRLF when most of its lines end so). For a file that is not UTF-8 the prototype refuses (`not-utf8`: "… is not UTF-8 text, so loom does not write into it; save it as UTF-8 first"), as `tasks.tick` already did, rather than splicing bytes. The reason: the scan decodes such a file as Mac Roman, which accepts every byte and is wrong for the Latin-1 files that occur, so loom has no reliable reading in which to place the edit or encode the agent's Unicode; splicing would put UTF-8 bytes into a Latin-1 file or guess an encoding, and refusing never damages. The cost is that a Latin-1 file takes no suggested edits at all; the list should say so before Keep (it does not yet). The door's store keeps non-UTF-8 bytes (`.bin`), so a restore or undo could give them back.

The door also exposed a fault in the text store under it: `snapshots.read_raw` read stored texts with universal newlines, so a look's or an undo's CRLF text came back LF, and SAFE-7's discard spliced offsets from one reading into the other. `read_raw` and `write_raw` now read and write bytes. Versions (`stamp_document`) still store the scan's normalised text; the prototype restores a version in the file's current line ending, which is a guess; the real implementation should make versions keep raw bytes.

## DOOR-13: where the journal lives

SAFE-12 puts the lock and journal at `.loom/writes.lock` and `.loom/writes/journal.jsonl`. Every `.loom` path must be either an agent's place or in loom's protected table (`agents.LOOM_DIRS`, checked by `test_paths`), and adding one changes the deny list loom writes into `.claude/settings.json` and the Codex rules, so every existing quilt would need `loom upgrade` and the demo fixtures would change (`test_doctor` failed on the demo's settings). The history directory is protected already and holds the text store the journal points into, so the prototype puts them at `<history>/writes.jsonl` and `<history>/writes.lock`, read from `[quilt] history`.

## DOOR-14: one-step undo, and records that follow the text

`change-undo {changes: [ids]}` undoes the Keep of each edit: when the file still holds exactly the act's after bytes and the act wrote no other edit there, the before bytes go back whole; otherwise each of that edit's splices whose new words stand exactly once is replaced by the words it replaced, so a later edit elsewhere in the file survives; otherwise it refuses ("changed where it was written since; restore a version from The Record instead"). The edit opens again (a `reopened` line in the same act) and the next Keep is a new act. A Keep that wrote nothing (the edit read as taken) is not undone: its text was in already, and opening the edit with the text in would only invite a second write. Keep all over three documents is undone by one request naming its edits.

The journal also lets records follow the file: after a restore or a put-back writes a file, a kept edit loom wrote there is opened again ("restored") when the words its Keep wrote stood in the file before the act, stand there no more, and fewer than half of them still stand in order. The first rule ("its text no longer reads as taken") was itself a text judgement and caused the very fault the door is meant to end: the harness found three sequences (3044, 3065, 3132) where the person had worked inside a kept edit, a restore or put-back reopened it because it no longer read as taken, and the next Keep would have written it a second time. Keyed on the journal's splice bytes, the rule errs the other way: an edit whose short text uses common words may stay recorded kept when a restore took it out, which is SAFE-9's old harmless state, not damage. The old put-back writes a whole file back, so undoing an older discard after a newer Keep takes the Keep out too (seed 3190); the real undo of a discard should splice as Keep's does.

A variant of the harness with `change-undo` among its acts (`$D/harness/safety_lib_door.py`, 100 sequences) found two more faults. The first version opened a Keep-that-wrote-nothing through an act that changed no file, and the door dropped such an act's record lines along with its journal lines, so `change-undo` said done and the edit stayed kept: an act with no file to write must still append its records. And a longer chain (seed 5072): a section placed after `\end{theorem}` is kept, undone, and put back by a restore of a version stamped between the two; while it stands there, open, an agent's deletion inside it is kept, so its words no longer match; Keep all then writes it a second time. Nothing recorded that the open edit's words were in the file, because a restore, not a Keep, put them there. The prototype now refuses to write, and lists as unplaced, an edit of eight or more words that loom wrote in an earlier generation and whose words mostly stand in the file again. The lesson for the real implementation: every act that moves an edit's words, in either direction, must update the edit's record through the journal; the prototype's word-share rules are stand-ins.

## DOOR-15: what the anchor precondition costs

Two edits suggested after the same quote, or at the foot of the same body: once the first is kept, the second's recorded neighbour is gone and it is listed unplaced; before, it was placed right after the quote, ahead of the first edit's text, so the two read in the reverse of their filing order. The person now has to ask again; arguably better than silent reordering, but it is a visible change, and it appeared at once in a benchmark that filed eight edits on two quotes. The neighbour record also stops the old phantom: a phrase suggested right beside an identical phrase that already stood there reads as not taken while the neighbour is unchanged (harness seed 3077, `\end{equation} by \eqref{eq:prose}.` suggested after a body that already ends so, read as taken until bodies recorded their edge). What remains is a replacement whose new text contains its quote (`$x$ is` replaced by `$x$ is $\{x, \sigma`, seed 3019), read as taken because the longer words already follow the quote; its context should be checked as an insertion's is.

## DOOR-16: smaller gaps

- Temp files are created beside the person's file (`.<name>.<random>.loom-tmp`), so a crash before the rename leaves one in the person's directory until the next act removes it. Temps in the history directory would keep the person's tree clean wherever it is on the same filesystem; a symlink's target elsewhere still needs a sibling temp.
- `os.fsync` on macOS does not force the drive's cache (`F_FULLFSYNC` does); the journal's "before any file" ordering is only as strong as that.
- Recovery runs at the start of every act, not at `loom serve` start; `loom changes` reads the journal but does not recover, and judges an unsettled act by bytes. `loom doctor` reports acts recovery left.
- `adopt.incorporate` keeps its own snapshot-and-rollback of the ledger, review origins and history around the door's act: when `finish()` fails, the act has no `done`, adopt writes the person's file back outside the lock, and the next act's recovery marks the act aborted. Two transaction mechanisms for one act; `sync.incorporate` has the same shape.

## DOOR-17: what the real implementation should do differently

- The scan records each file's raw digest and decoding, and plans carry them; the precondition is a hash comparison and the offset mapping is checked, not assumed.
- A journal with an index (settled acts archived, a per-edit map of what loom wrote) instead of a file read whole.
- Records with ids, appended idempotently; decide which follow-ups belong to the act and make them computable from the plan, so the lock is not held through rescans.
- Request ids from the viewer for the "earlier answer"; unique ids otherwise; Keep's `<edit>:<generation>`.
- Versions keep raw bytes; restore and every undo splice rather than rewrite whole files where they can; and every act that moves an edit's words, either way, updates the edit's record through the journal (a restore that takes them out reopens it, one that brings them back records it), instead of the prototype's word-share guesses.
- Temps in the history directory; `F_FULLFSYNC` on macOS; recovery at `serve` start.
- Adopt's and sync's rollback become the door's undo of the act, so one journal holds one transaction.
- The taken test, the anchor precondition and `near` are records-and-placement work, not the door: land them separately, with a body placement recording its neighbours.
- A test that refuses any `write_text`, `write_bytes`, `os.replace` or `unlink` on a person's path outside `writes.py`.

## DOOR-18: landing order, what waits, what to own

Each step leaves loom working and its tests green:

1. `writes.py` (store, journal with index, recovery, `write_bytes`) with `read_raw`/`write_raw` made exact; route `tasks.tick` and `config_edit` through it (smallest callers, closes SAFE-10 for Settings). Owns `writes.py`, `records/snapshots.py`, `tasks.py`, `config_edit.py`.
2. Route `pending.discard`, `history.acts.put_back` (contained) and `restore`; versions keep raw bytes. Closes SAFE-5, 7, 11's path half. Owns `history/acts.py`, `history/steps.py`, `pending.py` (`discard`).
3. Route Keep: decisions under the lock, byte splice, the journal as the guard, the `kept` record from the plan, one re-plan; delete `records.edits.apply`; refuse non-UTF-8 in the list as well as at Keep. Closes SAFE-1 (loom's shapes), 2, 3, 6 for Keep. Owns `pending.py`, `render/api.py` (`_change`, `_reopen`), `records/edits.py` (`keep`).
4. In parallel with 1 to 3, since it touches only placement: the taken test at the place, the anchor precondition with `edge` for body placements, `near` for keys named by place. Closes SAFE-1 shapes 1, 2, 5, SAFE-4, SAFE-8. Owns `records/edits.py` (`place`, `taken_how`), `records/store.py` (`written_on`), `cli/suggest.py`. Steps 3 and 4 both edit `records/edits.py` and `pending.suggested`: one after the other, or one owner.
5. `change-undo` and the viewer's undo of Keep; restore and put-back reopen what they take out and record what they bring back; the old reopen refused. Closes SAFE-9. Owns `pending.py` (`unkeep`), `render/api.py`, `arras/src/lib/review/history.svelte.ts`, the spec row.
6. The remaining writers (`adopt`, `sync`, `mv`, `atomize`, importer, canon import, `init --from`, agent layer, `pages.write`, new-file writers), then the grep test that nothing else writes; `doctor` and `serve` start recovery.

Must wait for it: the viewer's Review rebuild (its Keep, Discard and Undo need `change-undo` and the refusal codes `changed`, `not-utf8`, `changed-since`, so after step 5); one-step undo (review package B, which is step 5 and needs step 3's journal; its plan to "put its old words back where its new words still stand" is the door's splice undo); Overleaf pulls (`sync.incorporate` writes and deletes files under its own rollback and must become an act, step 6); Markdown suggestions (they go through Keep's splice and the taken test at the place, so after steps 3 and 4). Review package A ("Keep is safe to repeat") is steps 3 and 4 and should not be done separately with an `apply`-line guard, which this spike shows would not survive a crash before the line is written.

Files to own exclusively while it lands: `loom/src/loom/writes.py`, `pending.py`, `records/edits.py`, `records/store.py` (`written_on`), `records/snapshots.py`, `history/acts.py`, `history/steps.py` (versions' bytes), `tasks.py`, `config_edit.py`, `render/api.py` (`_change`, `_reopen`, `_history`, the endpoint list), `adopt.py` and `sync.py` (their incorporate), `cli/suggest.py`, and `tests/unit/test_write_safety.py`.

## DOOR-19: size

The prototype took about an hour and three quarters of one session (15:22 to 17:05), of which roughly half was waiting on before and after runs; four rounds of the harness each found something the unit tests had not (DOOR-5, DOOR-14). A careful version with tests (crash injection per writer, real-process races, a CRLF and a Latin-1 quilt in the suite, the journal index, versions' bytes, the remaining writers, the viewer's undo and the spec rows) is likely 6 to 7 sessions for a capable coding agent: one each for steps 1, 2, 4 and 5, one and a half for step 3, and one and a half for step 6 with the grep test and compaction.

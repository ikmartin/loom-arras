# Safety of writes to a person's files (v0.1 study, second wave)

Scope: every path by which loom writes, moves or deletes a file the person owns, tested by seeded sequences of acts against the write API in process and against real `loom serve` processes over HTTP, on copies of `demos/synthetic`, `demos/showcase` and the author's quant quilt, plus fault injection for crashes and races. Checkout: `v0.1-study` at 71621877. Nothing in the repository was changed except this file. Every harness, reproduction and result named below is in the scratch directory `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/safety` (called `$S` below); each reproduction takes the source quilt and a work directory as arguments and runs with the study's Python and `XDG_CONFIG_HOME=$S/xdg`.

Verdict: the release bar is not met. Eleven distinct faults. Six damage the person's text: four in an ordinary session (SAFE-1, 2, 4, 5: a sentence the agent proposes after `\end{lemma}`, an editor that saves while Keep runs, an answer filed on the third of three empty `\begin{proof}[Answer]` blocks, a restore after an `\input` was commented out) and two in files with Windows line endings or Latin-1 bytes (SAFE-6, 7). The guard against a second write is still a text test, so the class of last week's bugs is open, only narrower.

## Findings at a glance

| id | finding | weight | effort |
|---|---|---|---|
| SAFE-1 | Keep writes a suggested edit a second time whenever the edit is open while its text already stands where the taken-test does not look: text placed after the block's `\end{…}`, a short text written in and touched, a crash between write and record, two Keeps at once, a reopened Keep | blocks | hours (guard), days (SAFE-12) |
| SAFE-2 | Keep writes the file from a scan taken before it, under no lock shared between processes: a save made meanwhile is overwritten and kept nowhere, and a kept edit can be lost while recorded kept | blocks | hours |
| SAFE-3 | A crash between the write and the record leaves nothing loom can recognise: the `apply` line comes after the write, `<file>.loom-tmp` is left beside the person's file, and nothing (`doctor`, `lint`, `changes`) notices | hurts | with SAFE-12 |
| SAFE-4 | A suggested edit on a key named by place (`FILE#proof:3`) is written into another block once a block is put in before it and its own block cannot be told apart by its text | blocks | hours |
| SAFE-5 | Restoring a version writes every file the version holds but keeps first only the files the document reaches now: a file taken out of the document since is overwritten and the person's text in it is kept nowhere | blocks | hours |
| SAFE-6 | Keep and restore rewrite the whole file from the scan's normalised text: CRLF becomes LF throughout, a Latin-1 file is rewritten as UTF-8 of a Mac Roman reading (ö becomes ˆ), and versions cannot give the bytes back | hurts | hours |
| SAFE-7 | Discarding an agent's in-place edit in a CRLF file splices at offsets counted in another text: the agent's words stay, `\end{proof}` becomes `\end{proof the`, and every line ending changes | blocks (CRLF files) | hours |
| SAFE-8 | An insertion whose words already stand anywhere in its block reads as taken before anyone writes it: Keep records it kept, writes nothing, and the agent is told it was kept | hurts | hours |
| SAFE-9 | Keep has no one-step undo: the viewer offers none, The Record restores the whole document and leaves the edit recorded kept, Keep all needs one restore per document, and the API's reopen of a kept edit leaves its text in (feeding SAFE-1) | blocks (release bar) | a day |
| SAFE-10 | Writes that keep no version: Settings (`config.toml`, also left mode 0600), Keep into a file no document reads, every write into a document that reaches a conflicted key (one duplicated `\label` suffices), and the agent layer's `.claude/settings.json` | hurts | hours |
| SAFE-11 | The write API takes any local caller with the token as the person (an agent may read `.loom/serve.json`), and `history-restore` with a `path` writes outside the quilt | hurts | hours |
| SAFE-12 | Proposal: one door for every write to a person's file (lock, fresh read, byte-exact journal, atomic write, idempotent act id, recovery) | — | days |

The earlier audit's CORE-5 is confirmed and is worse than stated: its proposed fix (refuse an edit that has an `apply` line, take the edit log's lock) would not have caught SAFE-1 after a crash, because the `apply` line is written after the file (SAFE-3), nor SAFE-2, because the lock it names is not held while the text to write is read. TEST-1 is confirmed: the test in section 6 catches both of last week's bugs when run against the code before each fix, and nine strict-xfail cases in it reproduce the damage found here on today's code.

## 1. The map: every path that writes a person's file

Built from a read of all 62 files with write calls (a delegated sweep, then spot checks); rows marked R were reproduced in this study. "pub-lock" is `render/serve.py:365`, a `threading.Lock` held only around HTTP requests of one server process; nothing else is shared between processes. "Client deny" means only the agent's client settings (`.claude/settings.json`, Codex rules) stop an agent; loom has no check of its own there.

| # | path (write at) | surfaces | who | kept first | undo | what stops a second run | atomic / lock |
|---|---|---|---|---|---|---|---|
| 1 R | `pending.keep`, suggested edit (`pending.py:458`) | CLI `changes --keep/--keep-all`; HTTP `change-keep`; MCP `loom_changes` without the keep options (`ai/layout.py:61-63`) | person (`changes_cmd.py:79`, `api.py:415`) | `keep_versions(APPLY)` `pending.py:442`; nothing when no person document reaches the file or the document reaches a conflicted key (SAFE-10) | no viewer undo; The Record restore of the whole document (SAFE-9) | edit status `open` plus the text test `taken_how` (`records/edits.py:406-436`); `apply` line written after the file and never read | atomic, fixed temp name (`history/acts.py:118`); pub-lock over HTTP only |
| 2 R | `pending.discard`, in-place change (`pending.py:545`; **deletes** the file at `:542` when the old text is empty) | CLI `changes --discard`; HTTP `change-discard` | person | `keep_versions(UNDO)` `:530` and `write_raw` of the text now `:537` | `history-restore {path, text}` (`put_back`), one step | change id recomputed from look vs file | write atomic, unlink not; no lock |
| 3 | `pending.keep`, in-place change | as 1 | person | n/a: moves the look only, no file write | — | — | — |
| 4 R | `history.acts.restore` (`history/acts.py:155`) | HTTP `history-restore {document, version}` | person (`api.py:517`) | `keep_versions` of the files the document reaches **now** (SAFE-5); refuses when that is refused (`:149-150`) | restore the "Before restoring" version | writes only files whose text differs (`:151-153`) | atomic; pub-lock |
| 5 R | `history.acts.put_back` (`history/acts.py:197`) | HTTP `history-restore {path, text}` | person | `write_raw` of the text now (`:196`) | put back the returned digest | none | atomic; path not contained (SAFE-11) |
| 6 R | `tasks.tick` (`tasks.py:138`) | HTTP `file-tick` | person (`api.py:492`) | `write_raw` of the old text and a `tick` line | untick, one step, byte-exact (verified) | already in that state writes nothing; task id must match | atomic, byte-preserving (the one writer that is) |
| 7 R | `adopt.incorporate` (`adopt.py:871`) | CLI `adopt --incorporate`; HTTP `adopt-finish` | person | `stamp_document` and a byte snapshot rolled back on exception | restore "before adopt" landmark | preview token (verified: second use refused, no file changed) | `write_text`, not atomic; no lock |
| 8 | `sync.incorporate` (`sync.py:815`, also deletes) | CLI `sync incorporate`; HTTP `sync-incorporate` | person | `_stamp` per document and a byte snapshot with rollback; a file no document reaches gets no version | restore per document | `incoming == integrated` refuses | not atomic, byte-exact; no lock. Not exercised here (needs a git remote) |
| 9 | `mv` (`cli/history_cmds.py:654-658`) | CLI | client deny only | nothing; a `move` line | `loom mv NEW OLD` | existence checks, then `shutil.move` | no |
| 10 | `atomize --retire` (`cli/paper.py:621-624`) | CLI | client deny only | nothing; the identity test does not gate the move | by hand | existing retired path refused | no |
| 11 | `set_main_forced` → `config.toml` (`reshape/importer.py:163-181`) from mv, atomize, linearize, import, sync | CLI | — | nothing | Settings or by hand | idempotent | `config_edit._replace`: mode becomes 0600 |
| 12 R | `config_edit.save` (`config_edit.py:260`, `_replace` `:264-272`) | HTTP `settings-save` | person | **nothing** (SAFE-10) | save the old value again (verified byte-exact: comments survive) | `new != text` | atomic via `mkstemp`: mode 0600, a symlink replaced |
| 13 | `reshape/canon.apply_import` (`reshape/canon.py:58-68`) overwrites existing asset files; `init --from` overwrites `README.md`/`config.toml` (`cli/quilt.py:163-176`) | CLI `import`, `init` | client deny only | nothing | none | none | no |
| 14 | agent layer: `write_permissions`/`init_layer` write `.claude/settings.json` and Codex rules **whole** (`ai/layout.py:292-296, 377-395`); `ensure_root_line` edits `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`; `gitignore.ensure` appends | `ai init`, `upgrade`, HTTP `agents-update` | HTTP person; CLI client deny only | nothing | git | content compare | no |
| 15 | `pages.write` → `research-state.md` (`pages.py:106-110`) | CLI and MCP `loom_write state` | **agent too** | `write_raw` of the old text, `page-write` line | `put_back` with `from` | `--base` hash, checked outside any lock | atomic, fixed temp name |
| 16 | new-file writers: `new`, `id --to`, `deloom --to`, `linearize --to`, `history restore --to`, `fork`, `adopt --to`, `sync --to`, `pdf-save` | CLI, HTTP; `new` and `id` are MCP tools | `new`, `id`: agent too | n/a | delete | `destination()` refuses an existing file (check-then-write except `new`, `pdf-save`) | `new --to` and `id --to` may write outside the quilt (`cli/_common.py:205-207`) |

Corrections to the earlier audit's table: row 1 also keeps no version when no person document reaches the file or the document is conflicted; discard (row 2) also deletes a file; tick's guard is the task id, not a line hash; `atomize --retire` is not gated by its identity test; `import` overwrites assets and `init --from` overwrites `README.md`/`config.toml` (both missed); the agent layer overwrites `.claude/settings.json` whole; `put_back`'s path is not contained. Rows 8-11 and 13-16 were read, not run.

## 2. The harness and what it ran

`$S/harness/safety_lib.py` draws a sequence of symbolic acts from a seed and resolves each against the quilt as it stands: an agent files a suggested edit (replace a quote, insert before or after it, the body; 1-6 words, 22-60 words, a `\section*` with a proof, a phrase already in the block, a deletion; on a quote inside another edit's range; after `\maketitle`); the person types inside a kept text, inside a quoted text, elsewhere in the block, above it, at the end, empties the file, renames it, or types a suggestion in by hand; Keep one, Keep all, Discard, the API's reopen of a kept edit, the viewer's undo of a discard, undo of a Keep through The Record, the last request sent again, two Keeps at once (two threads in process; HTTP plus a CLI subprocess against a server), a save landing while Keep runs, restore of a version, tick and untick, Settings saved and saved back, an agent's in-place edit with tracking on and the person's keep, discard and undo of it. After every act loom performs it checks: only the named files changed; no `.loom-tmp` left; the same request again changes nothing; undo gives back the bytes; no paragraph of 20+ words appears more often than before; every word the person typed is in a file or a kept text; each suggested edit's unique word stands at most once, an open edit listed `ready` is not already in the file, one recorded kept is in it, one listed `taken` is; the bytes each write replaced are kept, byte-exact. `run_prop.py` runs seeds, `analyze.py` sums them, `show.py` prints one seed's trace.

All sequences are 35 acts; seeds are in each `results.jsonl` under `$S/runs/`.

| run | driver | quilt | sequences | acts | failing | damage to text | damage, not counting the injected save |
|---|---|---|---|---|---|---|---|
| A-synthetic | in process | synthetic, edits tracked | 200 | 7,000 | 188 | 103 | 18 |
| A-showcase | in process | showcase, edits tracked | 100 | 3,500 | 98 | 49 | 6 |
| A-quant | in process | quant | 60 | 2,100 | 56 | 23 | 9 |
| A-quant-track | in process | quant, edits tracked | 12 | 420 | 12 | 6 | 4 |
| A-synthetic-crlf | in process | synthetic, every `.tex` CRLF | 40 | 1,400 | 40 | 40 | 40 |
| H-synthetic | `loom serve` over HTTP | synthetic, edits tracked | 40 | 1,400 | 38 | 3 | 2 |
| H-showcase | `loom serve` over HTTP | showcase, edits tracked | 20 | 700 | 19 | 0 | 0 |
| H-quant | `loom serve` over HTTP | quant | 15 | 525 | 14 | 1 | 1 |
| total | | | 487 | 17,045 | 465 | 225 | 80 |

Besides these, 199 sequences ran on a first version of the harness whose repeat and undo checks gave false positives (kept under `$S/runs-old/`, not counted); 16 crash runs (section 3); 30 real-process race trials; and one sequence excluded above (A-showcase seed 3077, where the harness itself typed a suggestion in twice).

"Failing" overstates damage: nearly every sequence meets one of three frequent faults the generator provokes on purpose (it undoes Keeps through The Record, saves Settings, and proposes phrases already in the block). "Damage to text" counts sequences with a SAFE-1, 2, 5, 6 or 7 failure; the in-process runs inject the person's save into every Keep that draws that act, so the last column leaves it out. By fault, of the 465 failing sequences: SAFE-9 (recorded kept, text gone after an undo or restore) in 332 (71%), SAFE-8 (taken, never written) in 253 (54%), SAFE-10 (config mode 0600, 226; no version of `config.toml`, 36) in 49%, SAFE-2 (save lost, injected) in 183 (39%), SAFE-6 in all 40 CRLF sequences, SAFE-1 (an edit written twice) in 24 (5%), SAFE-2 (two Keeps at once losing a kept edit) in 22 (5%), SAFE-7 in 3, SAFE-5 in 2, and 17 quant sequences that restored a version of `hwk1.tex` which already held the pasted copies. Of the 24 SAFE-1 sequences, 14 were edits placed after `\end{…}` (one fault), 8 followed the API's reopen of a kept edit, and 2 a by-place key that had moved to another block (SAFE-4); so one underlying fault, the text test standing in for a record of the write, accounts for all of them. Shrinking by deleting acts worked poorly, since acts are resolved against the state the earlier acts made; each fault has instead a hand-written reproduction of a few lines, checked to fail on its own.

Things that held across every run: tick and untick are byte-exact; Settings saved back give back `config.toml` exactly; a restore sent twice changes nothing; a Discard of a suggested edit never touches a file; a Keep by id sent again is refused (`no-such-change`) and writes nothing; adopting an agent copy (`$S/repro/r_adopt.py`, showcase) keeps a version, changes only the named node file and refuses its token a second time; `loom accept` writes no person file.

## 3. Crash and interruption

`$S/crash/crash.py` runs `loom changes --keep ID` in a subprocess that `os._exit(9)`s at a chosen point (fault injection in the harness by monkeypatching, no repository edit), then reads the quilt as the next loom start finds it and presses Keep again. Four shapes of edit on `sy-000A` of the synthetic quilt:

| killed | state found | noticed by `changes`/`doctor`/`lint` | second Keep |
|---|---|---|---|
| after the version, before the write | file untouched, edit open and `ready`, an extra "Before keeping" version | no (nothing to notice) | writes once: correct |
| inside `write_file`, before `os.replace` | file untouched; `drafting/nodes/sy-000A.tex.loom-tmp` (the whole new text) left beside it in the person's directory | no; nothing ever removes it | writes once; the temp file stays |
| after the write, before the `apply` line and the record | text in the file, edit open, **no `apply` line** | listed `taken` for in-block edits, `ready` for one placed after `\end{remark}`; no warning anywhere | in-block: records it, writes nothing. After `\end`: **writes it again (2 copies)**. Short text touched by the person before the press: **writes it again** |
| after the record, before absorb/carry | edit kept, `apply` line present | — | nothing to do; the look and annotation carry are left unfinished, silently |

So a crash in the one window that matters leaves a state loom cannot tell from "the person typed this in", and the only line that would have said otherwise is written after the window closes. Nothing repairs or reports an interrupted write.

## 4. Findings

### SAFE-1: Keep writes a suggested edit a second time

Whether an edit is in already is decided by `taken_how` (`records/edits.py:406-436`), which looks for the new text only between `node.start` and `node.end` of its block (`:418`), and below twenty words only for the text exactly as suggested (`_written_since`, `:394-403`). Keep writes, then records (`pending.py:458` then `:472`). Any way an edit can be open while its text stands outside what `taken_how` sees makes the next Keep write it again:

1. An insertion placed after the block's `\end{…}` (quote ending on `\end{remark}`, `--after`) or before its `\begin{…}` lands outside `[node.start, node.end)`. `$S/repro/r_outside_block.py $S/src/synthetic W typed`: the sentence written in by hand, then Keep: 2 copies. `… reopen`: Keep, the API's reopen, Keep, reopen, Keep: 3 copies. In the harness this is 14 of the 24 sequences that wrote an edit twice.
2. A text under twenty words that was written in (by Keep before a crash, by the person, or by the agent in place) and then touched by the person: written again (`crash.py`, row "after the write", case `in-block-short-edited`; fast test `test_a_short_edit_written_in_and_touched_is_not_written_twice`).
3. Two Keeps of one edit in two processes (the CLI beside `loom serve`): the second scans after the first has written and before it has recorded, finds the edit `ready` whenever its text is of shape 1 or 2, and writes it again (`$S/repro/r_race.py $S/src/synthetic W same`, in process, the first Keep slowed after its write: 2 copies). With real processes and no slowing, 15 tries of an HTTP Keep beside a CLI Keep of one edit after `\end{remark}` never overlapped in that window (`r_http_cli_race.py`).
4. The write API's `change-discard {undo: true}` reopens a kept edit (`render/api.py:463-482`) and leaves its text in the file; the viewer sends it only for a discard, but nothing refuses it for a keep, and any later touch of the text or a renumbering of by-place keys (SAFE-4) makes it `ready` again (harness: 8 sequences, 2 of them through a real server).
5. A by-place key whose block moved (SAFE-4): the taken-test then reads the wrong block, finds nothing, and the edit is written again (quant, 2 sequences, one of them a 4-word suggestion the person had typed in by hand on `hull_ch1.tex#proof:40`).

Damage: a copy of the agent's text pasted into the person's file per press, as in quant. Weight: blocks. Fix: make a second write impossible by record, not by reading the text (SAFE-12: act id per edit, journal written before the file). Until then, three hours of guards: refuse to place an edit outside the block's body (quote must not reach `\begin`/`\end`; `place`, `records/edits.py:293-313`), drop the twenty-word floor for an edit whose `apply` line exists, write the `apply` line before the file, and refuse reopening a kept edit unless its text is gone.

### SAFE-2: a save made while Keep runs is lost; concurrent Keeps lose an edit

`pending.keep` takes the text to write from the scan the request started with (`pending.py:448`, scan at `render/api.py:426`), keeps a version of that same scan's text, and writes over whatever is on disk at `:458`. Between the two lie the pending list, the composition and the version stamp (tenths of a second on the synthetic quilt, more on a large one). No lock is shared between processes: `publication_lock` (`render/serve.py:365`) is a `threading.Lock` inside one server, and the CLI takes none.

- A save by the person's editor in that window is overwritten and kept nowhere: fast test `test_a_save_made_while_keep_runs_is_not_lost` (the save injected after the version stamp). In process the harness act `save_during_keep` lost the save every time it ran (94 of 200 synthetic sequences; in the 35 others that drew it no edit was ready and it did nothing, checked on 12 of them). Against a real server with the save timed at random 20-250 ms after the request, it landed in the window in 1 of the 48 HTTP sequences that drew the act (synthetic seed 2010).
- Two Keeps of different edits on one file in two processes: the second writes from a scan made before the first wrote, so the first edit's text disappears while it stays recorded kept. Real processes, no injection (`$S/repro/r_http_cli_race.py $S/src/synthetic W 48280 15`: an HTTP Keep and a `loom changes --keep` at once): **3 of 15 trials lost a kept edit**. In process: `r_race.py $S/src/synthetic W two`, deterministic; the harness's two-thread Keep lost a kept edit in 22 of 487 sequences.
- Two Keeps at once also often end with one of them failing "another loom process recorded step 0015 while this one was being prepared … run this again", which is the history's step lock doing what the write path does not.

Weight: blocks (the person's own typing is lost with no copy). Fix: under one cross-process lock, read the bytes, check them against the hash the plan was made from, and refuse ("the file changed; look again") when they differ (SAFE-12).

### SAFE-3: an interrupted write is invisible

See section 3. `write_file` (`history/acts.py:115-120`) uses a fixed sibling name `<name>.loom-tmp`, so a crash leaves it in the person's tree and two concurrent writers to one file share it; there is no `fsync`. The `apply` ledger line (`pending.py:460`) follows the write, and nothing reads it (`grep`: writers only, as CORE-5 says). Weight: hurts. Fix: SAFE-12's journal (intent before the write, unique `mkstemp` temp, recovery on start, `doctor` reporting an unfinished act).

### SAFE-4: a suggested edit is written into another block

`written_on` (`records/store.py:142-148`) follows an edit on a key named by place to the block whose hash is the edit's `against`, but when no block or several blocks have that hash it falls back to `node`, the block the key names *now*. A homework file before it is solved has several identical `\begin{proof}[Answer]\n\end{proof}`, so `against` never identifies one. `$S/repro/r_wrong_block.py $S/q0/quant W` (on a copy of quant's `hwk2.tex`): the agent files the answer to Problem 3 on `hwk2.tex#proof:3` and a new Problem 0 after `\maketitle`; Keep the problem, Keep the answer: **the answer to Problem 3 is written into Problem 2's proof**. The same fallback misplaces an edit whose own block was edited since it was filed, once anything is put in before it. The 2e106a45 message says such an edit "stays unplaced and says where it was filed"; the code places it on the block now at that place. Weight: blocks (silent misplacement in the author's own workflow). Fix: return None (unplaced) from `written_on` when the key is named by place and its block's hash does not match uniquely; at filing, refuse or anchor more strongly (preceding section title) when the block's hash is not unique in its file. Fast test: `test_an_edit_on_a_block_named_by_place_stays_on_that_block`.

### SAFE-5: restore overwrites a file it does not keep

`restore` (`history/acts.py:123-164`) writes every file in the version's `files` (`:139-155`) but keeps first only `keep_versions(result, [doc])`, the files the document reaches now. `$S/repro/r_restore_unreached.py $S/src/synthetic W`: comment out `\input{nodes/sy-0006}` in `results.tex`, add a paragraph to `sy-0006.tex`, restore `widgets-v1` of `main.tex`: the paragraph is gone from the file and from all of `.loom/history`. The harness met a restore that overwrote a file with no copy in three sequences of its own (synthetic seeds 1074, 2038 over HTTP, 3011); the one traced, 1074, is this shape after the person renamed the `\input` file `results.tex`. Weight: blocks (restore is an undo path, and it destroys the person's work). Fix: keep the raw bytes of every file restore (and `put_back`, and any writer) is about to replace, whatever the document reaches; SAFE-12 does this by construction.

### SAFE-6: Keep and restore rewrite bytes outside the edit

The scan decodes UTF-8, else Mac Roman, which accepts every byte (`scan/source.py:46-53`), and turns CRLF into LF (`:126`); Keep splices into that text and writes it whole (`pending.py:448, 458`); versions store the same normalised text, so a restore writes it too. `$S/repro/r_encoding.py $S/src/synthetic W crlf`: after one Keep the file has 0 of its 3 CRLF. `… latin1`: `Schröder, Gödel` in Latin-1 bytes comes back as `Schrˆder, Gˆdel` in UTF-8, with only a lint warning ever said. Damage: every line or every accented letter of the file changes; a diff in git or Overleaf shows the whole file. Weight: hurts (blocks for a co-author on Windows or with `\usepackage[latin1]{inputenc}`). Fix: splice in bytes at byte offsets, keep the file's newline convention, refuse a file that is not UTF-8 (as `tasks.tick` already does, `tasks.py:122-125`). Fast test: `test_keep_leaves_line_endings_alone`.

### SAFE-7: Discard in a CRLF file corrupts it

The change's place in the file is computed on the bytes decoded with CRLF kept (`looks.open_texts`, `looks.py:85-88`), the look's old text is read back through `read_text` with universal newlines (`records/snapshots.py:48-50`), and Discard re-reads the file with `read_text` too (`pending.py:536`) before splicing with the CRLF offsets. `$S/repro/r_crlf_discard.py $S/src/synthetic W`: an agent replaces "the" with `AGENT-WORDS` near the end of `appendix.tex` (CRLF); Discard leaves `AGENT-WORDS` in, turns `\end{proof}` into `\end{proof the`, and every CRLF into LF. A version was kept first, so it is recoverable by hand. Weight: blocks for any CRLF file. Fix: as SAFE-6, bytes in and bytes out; never `read_text` a person's file or a raw text. Fast test: `test_discarding_an_agents_edit_in_a_crlf_file_gives_back_its_bytes`.

### SAFE-8: an insertion that reads as taken is never written

An insertion is "taken as written" when its text stands anywhere in the block's whole text (`records/edits.py:425-426`). `$S/repro/r_phantom_taken.py $S/src/synthetic W`: the agent proposes `\cite[Theorem 2.1]{Kre99}` after "Gadgets exist:" in a remark that cites it further on; it is listed `taken`; Keep says "kept 1 change", records it kept, and the file is unchanged. Common phrases (`Hence`, `\qedhere`, a citation, `for all $n$`) recur in proofs. The harness drew a phrase from the same block in about one suggestion in eight, and such an edit read as taken in 253 of 487 sequences. Weight: hurts (a silent no-op the person and the agent both believe happened). Fix: an insertion is taken only when its text stands at its place (beside the quote), which `place` already computes.

### SAFE-9: no one-step undo of Keep; the records do not follow an undo

The viewer's history says of Keep "not undone here" (`arras/src/lib/review/history.svelte.ts:3`, `:180`). The person's way back is The Record: restore the "Before keeping a suggested edit" version, which puts the whole document back (any later edit too, though kept as a version first) and leaves the edit recorded kept with its text gone, so Review shows nothing to keep and `loom since` tells the agent it was kept. Keep all over three documents needs three restores. Harness: an edit recorded kept with its text absent after a restore or an undo in 332 of 487 sequences (by construction: the generator undoes Keeps). Undo of a Keep is refused outright when the document is conflicted (SAFE-10). Weight: blocks against the release bar's second half. Fix: an undo of Keep that writes back the bytes the Keep replaced, for that act only, and reopens the edit, in one step; refuse it when the file changed since, and offer the version instead (SAFE-12 gives both).

### SAFE-10: writes that keep no version

- Settings: `config_edit.save` keeps nothing (`config_edit.py:260`); the text before the write was in no store in all 9 quant HTTP sequences that saved Settings (in the tracked synthetic quilt the look happened to hold it). `_replace` writes through `mkstemp`, so `config.toml` ends mode 0600 after any save (all runs) and a symlinked `config.toml` becomes a file.
- Keep into a `.tex` no document reads (a scratch file of the person's): `documents_reaching` is empty, `keep_versions` keeps nothing, and the whole file before the write is in no store (`$S/repro/r_unreached_keep.py`).
- Every write into a document that reaches a conflicted key: `keep_versions` skips it and the act goes ahead (`history/acts.py:73-77`), so Keep, Discard and Keep all write with no version; restore then refuses (`cannot-keep`), so there is no undo either. A suggestion that repeats a `\label` line, or a person's paste of a lemma, is enough; among the synthetic sequences traced, seeds 3167 and 3197 reached it ("no version of main.tex was kept: drafting/main.tex reaches two definitions of sy-000D"), and in 3167 the undo of the next Keep was refused.
- `agents-update` and `loom upgrade` write `.claude/settings.json` whole (`ai/layout.py:377-395`); a person's own hooks or permissions there are replaced with no copy (read, not run).

Weight: hurts. Fix: when a document cannot be stamped, keep the raw bytes of each file (`write_raw`, as tick does); write `config.toml` keeping its mode; keep the replaced bytes of every file in any case (SAFE-12).

### SAFE-11: the write API and `put_back` trust too much

The write API's guards stop other web pages, not other local processes: a request with no `Origin` passes (`render/serve.py:69-81`), the token is in `.loom/serve.json`, which an agent's client is denied only for Edit (`agents.py:193-200`), and a request that names no `author` is taken as the reviewer (`render/api.py:415`). So an agent that may run `curl` or `python` can Keep, Discard, restore, tick and save Settings as the person. Separately, `history-restore {path, text}` writes to `root / path` with no containment when no file is there (`history/acts.py:192-197`): `$S/repro/r_put_back_path.py` writes `../outside-the-quilt.txt`. Weight: hurts. Fix: resolve and contain every path; deny Read of `.loom/serve.json` to agents; consider a per-tab token the viewer gets from the page, not from a file.

### SAFE-12: safe by construction

One module, `loom/src/loom/writes.py`, owns every write to a file outside `.loom/`, and nothing else may write one (a test greps for `write_text`/`write_bytes`/`os.replace` on person paths outside it).

    with writes.act(root, kind="keep", act_id=f"keep:{edit.id}", actor=who) as w:
        data = w.read(path)                      # bytes, under the lock
        w.expect(path, plan_hash)                # refuse if the file moved since the plan
        w.replace(path, new_bytes)               # staged, not yet written
        w.record(edits_event)                    # the act's own record, same commit
    # on exit: journal 'begin' (before/after hashes, bytes stored) -> atomic writes -> records -> journal 'done'

- Lock: `locks.locked(root/".loom/writes.lock")`, a file lock, taken by the CLI, the server's threads and the MCP server alike; `publication_lock` stays for publishing only.
- Fresh read and precondition: the act plans from bytes read under the lock, or states the hash its plan was made from; a mismatch refuses with "changed since you looked" (SAFE-2).
- Bytes: before and after bytes go into the content-addressed store exactly (`texts/<sha>.bin`), so every write has its version by construction (SAFE-5, SAFE-10), and splicing is on bytes with the file's own newline and encoding (SAFE-6, SAFE-7).
- Journal: `.loom/writes/journal.jsonl` gets `begin {act_id, kind, actor, files: {path: [before, after]}}` before any file is touched and `done {act_id}` after the act's records; files are written with a `mkstemp` temp in the same directory, `fsync`, `os.replace`, mode copied.
- Idempotence: `act_id` names the act (`keep:<edit>`, `restore:<doc>@<version>@<before-hash>`, `tick:<path>:<line>:<state>`); an act whose `done` is in the journal returns its earlier answer and writes nothing (SAFE-1 by record, not by text).
- Recovery: on any `act` entry and on `loom serve` start, each `begin` without `done` is finished when every file holds its `after` hash (append the records, then `done`), rolled back when every file holds `before`, and otherwise left as is and reported by `loom doctor` and Review with both texts at hand (SAFE-3).
- Undo: `writes.undo(act_id)` is a new act whose before and after are swapped, refused when the file no longer holds `after` (SAFE-9); the viewer's Undo for Keep, Discard, tick, restore and Settings calls it.

What it replaces: `history.acts.write_file`, `config_edit._replace`, the temp writes in `pages.py`, the snapshot-and-rollback in `adopt.py:725, 873-885` and `sync.py:797, 832-843`, the `apply` and `undo` ledger lines as the guard (they become journal entries), and `taken_how` as a write guard (it stays only to tell the person an edit is already in by their hand). Landmark versions (`keep_versions`) stay for The Record; safety no longer depends on them. Callers: Review's `change-keep`/`change-discard`/`history-restore`/`file-tick`/`settings-save`/`adopt-finish`/`sync-incorporate` through `render/api.py`; the CLI's `changes`, `adopt`, `sync`, `mv`, `write`; MCP's `loom_write` through the same CLI functions. An op registry (CORE-3) would hand the `act` to each op.

What this cannot make safe: an editor's unsaved buffer saved later over loom's write (loom sees it only at its next act, as a person's change); writers outside loom (an agent editing in place, iCloud or Dropbox sync, git checkout, Overleaf) that take no lock, which the precondition narrows to the instant between the check and the rename but cannot close on POSIX; network or cloud-synced filesystems whose rename and lock semantics differ; and which block an edit belongs to (SAFE-4), which is a question of block identity, not of writing.

## 5. Results summary

487 sequences (17,045 acts) on the second version of the harness (H-synthetic on a version one correction older; its two repeat flags are counted as benign), 412 in process and 75 against real servers; 465 met at least one fault, 80 damaged the person's text without help from an injected race. Eleven distinct faults; one root, the text test standing in for a record of the write (SAFE-1, with SAFE-3 and SAFE-12), lies under every sequence that wrote an edit twice.

| id | shortest reproduction (`$S/…`, args `SRC WORK`) | fault at |
|---|---|---|
| SAFE-1 | `repro/r_outside_block.py src/synthetic W typed` (suggest after `\end{remark}`, type it in, Keep: 2 copies); `crash/crash.py` row after-write | `records/edits.py:418`, `:394-403`; `pending.py:458-472`; `render/api.py:463-482` |
| SAFE-2 | `repro/r_http_cli_race.py src/synthetic W 48280 15` (3/15 lost); fast test `test_a_save_made_while_keep_runs_is_not_lost` | `pending.py:448`; `render/api.py:426`; `render/serve.py:365` |
| SAFE-3 | `crash/crash.py src/synthetic W` | `history/acts.py:115-120`; `pending.py:460` |
| SAFE-4 | `repro/r_wrong_block.py q0/quant W` (answer to Problem 3 lands in Problem 2) | `records/store.py:146-148` |
| SAFE-5 | `repro/r_restore_unreached.py src/synthetic W` | `history/acts.py:148-155` |
| SAFE-6 | `repro/r_encoding.py src/synthetic W crlf` and `… latin1` | `scan/source.py:46-53, 126`; `pending.py:448, 458` |
| SAFE-7 | `repro/r_crlf_discard.py src/synthetic W` | `pending.py:536`; `records/snapshots.py:48-50`; `looks.py:85-88` |
| SAFE-8 | `repro/r_phantom_taken.py src/synthetic W` | `records/edits.py:425-426` |
| SAFE-9 | Keep, then restore "Before keeping a suggested edit" in The Record: edit stays kept, text gone (harness act `undo_keep_record`) | `arras/src/lib/review/history.svelte.ts:3, 180`; `history/acts.py:123-164` |
| SAFE-10 | settings-save twice; `repro/r_unreached_keep.py src/synthetic W` | `config_edit.py:260, 264-272`; `history/acts.py:73-77` |
| SAFE-11 | `repro/r_put_back_path.py src/synthetic W` | `history/acts.py:192-197`; `agents.py:193-200`; `render/api.py:415` |

A note on the quant quilt itself: `course/solutions/hwk1.tex` has nine versions, all kept before a Keep; the largest number of times any paragraph of 20+ words stands in them runs 0, 1, 2, 2, 3, 4, 5, 6 (2026-11-12 17:56-17:57) and 1 (2026-11-13 00:40), and the file now holds such a paragraph twice. The version of 2026-11-13 00:40 is the newest with no paragraph repeated; restoring one of the 2026-11-12 versions from the third on brings two to six copies back, which the harness did in 17 sequences.

## 6. The test to keep

`$S/keep/test_write_safety.py` (about 400 lines, no dependency beyond loom and pytest). It copies `loom/tests/quilts/synthetic` (found from `loom.__file__`), sets `XDG_CONFIG_HOME` and the author `Pat` per test, strips agent markers, and drives `loom.render.api.handle` and `loom suggest` in process. Contents: four seeded sequences of 16 acts (suggest, a section after `\maketitle`, a long suggestion written in by hand and worked inside, the person's own words, Keep with a second press, Keep all, Discard, undo of a discard, tick and untick, Settings) checked after each act against the invariants of section 2; the two shapes of last week as fixed tests; and nine `xfail(strict=True, raises=AssertionError)` tests, one per damage shape found here (SAFE-1 twice, 2, 4, 5, 6, 7, 8, 10), each of which turns into a pass, and so fails the suite, once its finding is fixed.

Run: `cd $S/keep && /Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin/python -m pytest -q -p no:cacheprovider test_write_safety.py` takes 9-12 s: 6 passed, 9 xfailed on 71621877. Against the source before the fixes (extracted with `git archive`, run with `PYTHONPATH`): before 1ac44c5e, 4 fail (both fixed tests, seeds 1 and 3); before 2e106a45, 3 fail (the 2e106a45 test, seeds 1 and 3). So both of last week's bugs are caught by the fixed tests and, independently, by the seeded sequences.

To drop it into `loom/tests/unit/`: replace the `QUILTS` line with `from tests.unit._quilts import REPO` (`REPO / "tests" / "quilts"`), and the fixture's `monkeypatch.setenv("XDG_CONFIG_HOME", …)` and marker removal can go, since `tests/conftest.py`'s isolated environment does both. The full property harness (`$S/harness/`) is the long-running version: `run_prop.py SRC OUT SEED0 COUNT LENGTH inproc|http PORT [crlf] [on|off]`.

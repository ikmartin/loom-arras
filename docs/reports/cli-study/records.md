# CLI study, appendix: records, review, history and reshaping

The sweep of `accept`, `adopt`, `annotate`, `review`, `status`, `deps`, `downstream` (and `unravel`, `reach`, `pop`), `search`, `source`, `link`, `lint`, `history` (list, KEY, `show`, `restore`, `verify`), `stamp`, `fork`, `revert`, `live`, `mv`, `linearize`, `inline`, `atomize`, `id`, `new`, `import`, `init`, `deloom`, `draft` and `delete` (and `rm`, `remove`), made 2026-10-02 at commit `468c9af` for [the study](../cli-study.md). Every writing case ran in its own copy of the demo quilt or of the author's quilt (`relloc`), or in quilts made from a two-theorem paper; 302 transcripts. Grades: P pass, F fail, p partial, – not applicable.

## Grades

| command | purpose | T1 | T2 | T3 | T4 | T5 | T6 | worst problem |
|---|---|---|---|---|---|---|---|---|
| accept | record that a key's mathematics holds (per reviewer) | P | – | p | F | p | F | 54 s silent for one key in relloc |
| adopt | bring an agent copy's changes into the author's document | F | F | p | F | F | – | "No changes to incorporate" while a prose change waits |
| annotate | write, reply, resolve or edit an annotation | P | – | p | P | P | – | no MESSAGE files an empty annotation, exit 0 |
| review | rebuild viewer review data (= `loom build`) | p | – | F | F | P | F | 106–145 s silent; one line naming build/manifest.json |
| status | every key with its state | F | F | F | F | F | F | conflicted ids vanish into positional keys; 322-column rows |
| deps | what a key depends on | P | p | – | F | P | p | `--closure` differs from `source --closure` |
| downstream (+3 aliases) | what depends on a key | F | F | – | p | P | p | four names; a disclaimer in place of a verdict |
| search | find keys by id, title, number, citekey | p | F | F | F | F | p | a number not found, and no compile command named |
| source | print a key's or document's LaTeX | – | – | P | p | – | – | "% Bundle written by loom" when it writes nothing |
| link | print a viewer link | P | – | p | P | P | – | unknown key exits 1 (siblings exit 2) |
| lint | every diagnostic | F | F | F | p | F | F | 43 s silent, then 280 ungrouped lines up to 531 columns |
| history (list) | the steps of the quilt | – | p | – | F | p | p | "froze", auto names, unapplied reverts listed as history |
| history KEY | a key's versions | P | – | F | F | P | – | truncated hashes; "differs from every version" with no next step |
| history show | print a landmark | – | – | P | P | – | – | DOC@STEP takes the stem (main@4) |
| history restore | start a document from a landmark | P | – | p | F | P | – | the result conflicts with its live source and blocks revert |
| history verify | check history files | P | – | – | P | P | – | `--json` prints `[]` |
| stamp | record moved keys, or keep a landmark | P | – | F | F | p | p | prints "… adopts digests/storage/file/<hash>" |
| fork | give a document its own copy of a node | p | – | P | F | P | – | writes the node and history line before the patch is applied |
| revert | print a patch restoring KEY@N | F | – | p | F | P | – | records a revert every time it prints |
| live | make a superseded document live | P | – | F | P | P | – | silently creates conflicted ids |
| mv | rename a drafting document | P | – | P | p | P | – | "Recorded: move (ledger line 2)" |
| linearize | flatten in place of the spine | P | – | P | F | P | F | "kept … as an inclusion" when it inlined a fork |
| inline | flatten into a copy | P | – | F | p | P | F | does not supersede its source, so every id conflicts; exit 0 |
| atomize | split a document into node files | P | – | p | F | P | F | `--key` leaves the quilt conflicted until the patch is applied |
| id | label unlabelled environments | P | – | p | P | p | – | prints a patch with no word on applying it |
| new | allocate an id and write a skeleton | P | – | F | p | P | – | the node is reached by nothing; no `\input` hint |
| import | bring a paper into an existing quilt | F | – | F | F | F | p | counts and step number describe the wrong thing |
| init | create a quilt | F | – | p | F | p | p | 21 stderr lines, verdict on line 14, no next step after `--from` |
| deloom | the paper with loom removed | P | – | P | F | p | – | blocker line numbers count the flattened text; `--to` inside the quilt breaks lint |
| draft | make the agent's copy | P | – | F | F | P | – | a name collision is refused with no suggestion |
| delete/rm/remove | refuse | P | – | F | P | P | – | literal `<ID>`; the rm advice is wrong for results inside a document |

## Findings by command

**status.**
- **Verdict last (T1).** The verdict is the last line; on relloc it comes after 144 rows.
- **No grouping or order (T2).** All 144 rows say `draft`, and the 80 digest rows come before the author's 64. Rows are unsorted.
- **No next step (T3).** A stale row such as `dm-0001 … accepted, stale    own-text-changed (2026-10-02)` names no `loom accept`.
- **Raw and internal text (T4).**
  - Titles are raw truncated LaTeX (`{\cite[Definition 3.1, p.~1]{Calloway1`).
  - It shows implementation causes and derived flags (`own-text-changed`, `0 proved, 0 settled`).
  - Ids carry no theorem numbers, against 12.1.
- **Conflicts vanish.** After `live` made four ids conflicted, `status` listed `drafting/main.tex#remark:1 (Remark)`, never the word "conflicted", and ended on a clean summary.
- **Acceptance looks absent.** It counts per reviewer and says nothing about it (`records/store.py:108`). The demo shows "0 accepted" while `downstream dm-0002` lists `accepted by The loom demo`.
- **Width and miscounts (T5).**
  - Rows are padded to about 142 columns and reach 322.
  - `--stale` prints "1 stale of 1 accepted; 0 draft" when three keys are accepted and six are draft.
  - `--loose` counts "6 loose" under 8 rows.
- **Silent and slow (T6).** 14.5 to 37.4 s silent; `--explain` of one key took 19 to 37 s. 32 of 35 s go to `display_span` re-tokenizing a file per key (777 tokenize calls for 719 keys).
- **Help is wrong.** It says "Never exits nonzero", but `--explain dm-9999` exits 2.

**review.**
- **Output.** One line: `review updated: 0 stale keys; build/manifest.json published`. It names an internal path and never mentions `loom serve`.
- **Slow and silent.** 106 s, then 145 s on the rerun.
- **It is `loom build`.** The code is `build(open_quilt(...))` plus a count (`cli/review.py:37-45`).
- **No `--json`.**

**lint.**
- **Verdict last (T1).** "139 errors, 101 warnings, 39 infos" is line 280 of 280.
- **Ungrouped (T2).** 88 duplicate-id (all in digests), 43 missing-package, 27 unverified-locators and 25 dangling-link lines. Some name one location twice: `[digests/ranganathan_LogarithmicGromovWitten2022.tex:39, digests/ranganathan_LogarithmicGromovWitten2022.tex:39]`.
- **No next step (T3).** The default mode names no command; `--nodes` has good `fix:` lines.
- **Internal names (T4).** The codes `dangling-link`, `duplicate-id` and `unreachable` lack the `loom:` prefix, and `keys:` lists internal keys.
- **Width and speed (T5, T6).** 531 columns; 43 s silent.

**accept.**
- **Good verdict.** `accepted dm-0001 (Definition)  by ikmartin  2026-10-02`.
- **Internal wording (T4).** `snapshots: 1 written, 1 already present`, for one key.
- **Repeats silently.** Re-accepting a fresh key writes a new row and prints the same line.
- **Refusals.**
  - Good: `does not compile (! Undefined control sequence.); fix it or pass --force`, and `--stale needs confirmation; pass --yes`.
  - No remedy: `live incomplete keys prevent --all-live: dm-0005/proof, dm-0006/proof`.
- **Slow (T6).** 54.3 s for one key in relloc.
- **Agent guard.** An agent shell can accept with `--author ikmartin`, which is allowed by 11.8 but goes unmentioned.
- **Help gaps.** `--author` and `-y` have no help text.

**adopt.**
- **No summary first (T1).** The diff comes first, with no selection summary.
  - "Unselected proposals remain in the AI draft. Incorporation does not accept mathematics." is printed every time (`cli/adopt.py:69`).
  - The token is a 64-character hash.
- **False "no changes".** After the node changes were taken, it said "No changes to incorporate" while a prose change was still pending.
- **Stale preview.** The error says "refresh Incoming and preview again", which names a viewer screen. `Invalid preview token` gives no remedy.
- **Old token accepted.** An older token was accepted after a newer preview, and incorporated the older selection.
- **`--to`.** It writes the patch and also echoes it, with no "Wrote" line.
- **Patch format.** Patches use `a/`/`b/` prefixes (-p1); `revert`, `fork`, `id` and `atomize --key` use bare paths (-p0).
- **Help and width.**
  - The `--json` help is wrong.
  - The generated reference lists a hidden `--as` that only refuses.
  - `--json` reaches 1,618 columns.
- **Agent refusal.** Good.

**annotate.**
- **Empty annotation.** No MESSAGE files `"body": ""` with exit 0.
- **`--batch` is not atomic.** The first line is written, the second fails, and the error does not say the first was kept.
- **Silent repeat.** `--resolve` twice succeeds silently.
- **Good.** `a-2026-10-02-0001  dm-0002  note  (ikmartin)`; the `--severity`/`--kind` refusal; kind prefixes are accepted.
- **No next step.** `quote not found in dm-0002` does not name `loom source dm-0002`.
- **Agent filing.** In an agent shell, a note without `--as` is filed as "(agent)" with no warning.

**deps.**
- **Output.** `statement-edges:` / `proof-edges:` / `dm-0002 (Lemma)  via uses,ref`: jargon, and no counts.
- **Inconsistent closures.** `deps dm-0003 --closure` prints dm-0003 alone; `source dm-0003 --closure` prints four keys.
- **Slow.** 3.5–4.3 s silent on relloc.

**downstream (and unravel, reach, pop).**
- **First line is a disclaimer.** "dm-0002 (Lemma): nothing is changed by this report".
- **No counts or order (T2).** Sections have no counts; references are unsorted; one line is printed twice; there are five `(none)` sections.
- **Internal wording (T4).** `via transitive`, `ledger:`, raw ISO timestamps.
- **Four names.** All four print identical output and are listed as separate commands.

**search.**
- **Number search before a compile.** `search "Lemma 3.4"` says "nothing is numbered Lemma 3.4 in any drafting document; a document numbers only what its last compile saw", and names no compile command.
- **Number search after a compile.** It resolves: `rl-000G  Proposition 2.7  drafting/draft4.tex  (default document)`.
- **Too long.** `search kresch` gives 259 lines, up to 225 columns, with no count.
- **Raw and unsorted.** Titles are raw LaTeX; ids sort lexically (rem-2.10 before rem-2.4).
- **No matches.** "no matches" goes to stderr, exit 0, with no pointer to `refs find`.

**source.**
- **Writes nothing.** Its `--closure`-on-a-document error is exact.
- **Misleading header.** The `--closure` output is headed "% Bundle written by loom" and "\section*{Bundle for dm-0003}".
- **No `--json`.**

**link.**
- **Output.** One line, good: `[](quilt:dm-0002)`.
- **Exit code.** An unknown key exits 1; siblings exit 2.
- **No `--json`.**

**history.**
- **List.**
  - Rows look like `0002  stamp  …  stamp-nothing-changed  "nothing changed?"  froze 9`, with no header or count and unaligned columns up to 127 wide.
  - Unapplied reverts are listed.
- **history KEY.** `dm-0001@1  sha256:b910e473bf18  widgets-v1` and `head: differs from every version`, with no next command.
- **Words, not subcommands.**
  - A typo is "no such key".
  - `--plain` and `--to` are silently ignored outside their word.
  - Per-word help is impossible.
- **show.** `show drafting/main.tex@4` fails, because DOC@STEP takes the stem.
- **restore.**
  - `--to restored.tex` is refused ("goes directly under drafting/").
  - The restored document conflicts with its live source at once, and `revert` is then refused.
- **verify.** Good text; `--json` prints `[]`.

**stamp.**
- **Verdict.** "step 0003 froze 1 keys".
- **Housekeeping noise.** Document stamps print bibliography and storage lines; in relloc it printed "SiebertPuncturedLogarithB adopts digests/storage/file/0972338306d22915, which the bibliography no longer named".
- **Exit code.** "nothing to stamp" exits 1.
- **Duplicate names.** Refused well.

**revert.**
- **Records every run.** Every run appends a `revert` line to `.loom/history/ledger.jsonl`, including `--json` and no-op runs. Four runs left four "revert" rows and an unchanged file.
- **Contradictory no-op.** It printed "dm-0001 already has the text of @2", then "After applying, dm-0001 has the text of @2 … Recorded: revert (ledger line 5)".
- **Exit codes.** `revert KEY@9` and `revert dm-0007@1` exit 1.

**fork.**
- **Writes before the patch.** It writes `nodes/dm-0012.tex` and a history line, then prints the patch. Three runs left three unreachable orphans that `loom rm` refuses to remove.
- **`--json` is an unannounced dry run.** It shows an id it neither writes nor reserves.
- **Help mismatches.** The help says FILE, which is `--in`. `--as` means the new id here.
- **Good.** "…is yours to change: apply the patch above, or let your editor do it."

**live.**
- **Silent conflicts.** "drafting/main.tex is live", exit 0, while it creates four duplicate ids.
- **Missing file.** `live drafting/nope.tex` says "is not superseded".

**mv.**
- **Good.** It never overwrites, records renames made elsewhere, and keeps `[quilt] main` in step.
- **Wording.** "Recorded: move (ledger line 2)"; "main = drafting/paper.tex".

**linearize.**
- **Good refusal.** For shared nodes.
- **Contradictory output under `--fork`.** "dm-0001 -> dm-0012" and "kept nodes/dm-0001.tex as an inclusion (shared)", while the file has no `\input`.
- **Duplicate label.** The fork copied the user label `eq:fix`, and lint then reports it defined twice.
- **Slow.** 9.8 s silent.
- **`--json`.** Returns the raw history line.

**inline.**
- **Does not supersede.** "Wrote drafting/main-flat.tex", "Identity test: pass", exit 0, but the source is not superseded, so nine ids are conflicted.
- **Arguments.** `SRC DEST --to OTHER` ignores `--to`.
- **Outside the quilt.** It writes there.
- **Wrong help.** It calls itself "the reverse of atomize".

**atomize.**
- **"Moved" means copied.** "Moved 2 nodes" means copied; the source is unmodified, and `[quilt] main` moves silently.
- **Slow.** 9.7 s silent.
- **`--key`.** It writes the node and prints a patch, and the quilt stays conflicted until the patch is applied. A rerun exits 1.
- **Help gaps.** `--to`, `--proofs` and `--to-dir` have no help.

**id.**
- **Good.** `--next`, "nothing to label", and the anchoring refusal naming `--fix-anchoring`.
- **Patch.** It comes with no word on applying it.

**new.**
- **Good.** Fast, `--print`, and lists the taxa.
- **No placement.** It never says the node is reached by nothing, or where to `\input` it.
- **False error.** It claims "the default master declares: conjecture, … question", but main.tex declares neither.

**import.**
- **Everything on stderr.** Stdout is empty; the verdict is on line 10.
- **Wrong numbers.**
  - The plan says "kept as received in step 0001"; the import is step 0002.
  - "7 sections" counts the whole quilt.
- **No way forward.** "drafting/second.tex exists; import never overwrites" names no way to rename, and no next step follows.

**init.**
- **`--from` output.** 21 stderr lines, the verdict on line 14, five lines on `.gitignore`, and no `next:`.
- **Plain `init`.** Ends with a good `next:` line.
- **Already in a quilt.** "is already inside a quilt" does not suggest `loom import`.

**deloom.**
- **Good.** Blockers name their flags.
- **Line numbers count the flattened text.** "line(s) 76" for a 51-line `main.tex`.
- **Target inside the quilt.** `--to out/paper.tex` inside the quilt is accepted, and the output then fails lint.

**draft.**
- **Name collision.** `--ai main` is refused with no suggestion.
- **Wording.** "10 labels derived, 8 nodes based"; `--json` returns the raw history line.

**delete, rm, remove.**
- **One refusal for all.** "loom will not delete your notes; do this yourself with rm. Run loom unravel <ID> to see the consequences first."
  - The `<ID>` placeholder stays literal.
  - The rm advice is wrong for results inside a document.
- **Exit code.** 1.

## Workflows

1. **Start a quilt from a paper.**
   - Commands: `init DIR --from paper.tex --yes`, or `init` then `import FILE --yes`.
   - Guesses:
     - init or import;
     - that `--yes` is needed (learned after a compile);
     - the next step after `--from`;
     - that the import does not become the default document;
     - that a same-named paper cannot be imported.
2. **Write and label results.**
   - Commands: `new TAXON "Title"` plus a hand-written `\input`, or write, then `id FILE`; `id --next`; `lint`.
   - Guesses:
     - how to apply the patch (-p0 or -p1);
     - where to include a new node;
     - what "TAXON" means;
     - whether to atomize.
3. **Review and accept.**
   - Commands: `status [--stale | --explain KEY]`, `deps`, `downstream`, `source --closure`, `annotate`, `accept KEY [--proofs]` or `accept --stale --yes`, and `review` or `serve` for the viewer.
   - Guesses:
     - which of four "check" commands to run;
     - whose acceptances are counted;
     - what proved and settled mean;
     - how to clear a stale row;
     - that `review` is a two-minute build;
     - that conflicts make keys vanish.
4. **Keep history.**
   - Commands: `stamp -m` or `stamp DOC -m NAME`; `history`, `history KEY`, `history show NAME`; `revert KEY@N` and apply; `history restore NAME --to drafting/X.tex`.
   - Guesses:
     - stamp or accept;
     - which names are landmarks;
     - that DOC@STEP takes the stem;
     - that `revert` records whether or not the patch is applied;
     - that `restore` conflicts at once.
5. **Agent copy and adopt.**
   - Commands: the agent runs `draft DOC --ai NAME` and edits the copy. The author runs `adopt COPY`, then `--incorporate TOKEN`, then `--document-changes` for prose, then `status` and `accept`.
   - Guesses:
     - a free `--ai` name;
     - prose changes hidden behind "No changes";
     - a hash token;
     - "refresh Incoming";
     - that adopted mathematics still needs `accept`.

## Keep

- **Refusals that name the blocker and the flag.** `accept --force`, `linearize --fork`/`--keep-shared`, `deloom --keep-*`, `id --fix-anchoring`; `mv` and `atomize` never overwrite; `stamp`'s duplicate-name refusal; `draft` naming the existing copy.
- **`fix:` lines.** `lint --nodes`' `fix:` lines are the model for every diagnostic.
- **Errors that list the valid choices.** `history show`, `new`, `annotate --kind`.
- **Concise success lines.** `status --explain`, `mv`, `annotate`, `id --next`, `link`.
- **JSON hygiene.** Clean `--json` stdout, with prose on stderr.
- **Agent refusals that explain the role.**
- **Read-only `source`.** It writes nothing.
- **Number resolution.** `search` resolves printed numbers once compiled.
- **Speed.** Under 0.4 s on the demo.
- **Next steps.** Plain `init`'s `next:` line.

# CLI study, appendix: `refs` and `digest`

The sweep of the 27 `loom refs` subcommands and `loom digest extract` and `import`, made 2026-10-02 at commit `468c9af` for [the study](../cli-study.md), against copies of the author's quilt (76 bibliography entries, 52 digests, 3,140 mechanical results) and of the demo quilt. 229 transcripts. Network cases ran with the network blocked, but one `refs build` did reach it, in another sweep's scratch copy where fetching was on (the study's method notes say so). Grades: P pass, F fail, ~ partial, — not applicable, ? not observed.

## Grades

| command | what it does | T1 | T2 | T3 | T4 | T5 | T6 | worst problem |
|---|---|---|---|---|---|---|---|---|
| `refs add` | files a PDF or LaTeX source for CITEKEY in the store | P | — | ~ | F | P | — | no identity check: Brion's paper filed silently as Silverman's book |
| `refs build` | scan + resolve + fetch + extract + map, then a report | F | ~ | ~ | F | F | F | `--force` deletes the author's verified results; 228 s of total silence |
| `refs cite` | accepts or rejects an agent's citation suggestion; `--list` shows accepted ones | P | F | F | ~ | — | — | `--from` ignored; accepting twice duplicates; no list of pending ones |
| `refs coverage` | per-work table of source, PDF, pages, digest, waiting | F | F | F | F | F | — | truncated citekeys make rows indistinguishable; one sentence ×27; 298–400 columns |
| `refs discard` | discards a proposal with a reason | P | — | P | P | ~ | — | re-discarding succeeds and replaces the reason |
| `refs drop` | deletes records by work, session or state | F | F | P | P | P | — | an agent erased verified records |
| `refs fetch` | fetches source and PDF | ~ | F | P | ~ | P | ? | reports `source (candidate …)` for a work it did not fetch; disagrees with `build` |
| `refs find` | searches digested statements | F | ~ | ~ | F | F | ~ | `--work fragment` silently searches nothing |
| `refs forget` | tombstone for a citekey or hash | P | — | ~ | F | ~ | — | `--undo` refused without `--why`, against its help |
| `refs grep` | searches page text for a phrase | F | ~ | F | F | F | ~ | suggests `refs map` for works with no PDF; 627-column lines |
| `refs ingest` | matches a folder of PDFs to entries | F | F | F | F | P | — | three agreeing signals not filed, with no reason given |
| `refs link` | asserts a typed relation between results | P | — | P | P | ~ | — | accepts the author's own keys; `--session` free text |
| `refs links` | lists links, walking `--depth` | F | ~ | — | P | P | — | a citekey or unknown id: "nothing links X", exit 0 |
| `refs locate` | page rectangle of a quotation, plus a viewer link | P | — | ~ | F | P | — | raw coordinates; trusts the pid in `serve.json` |
| `refs map` | writes page text and the section map | F | F | — | P | F | ~ | on a work with no PDF: "0 mapped … 0 failed", exit 0 |
| `refs match` | works a person must look at | F | F | F | F | F | — | ignores `unreadable`; never lists unfiled PDFs |
| `refs overview` | prints a digest's Overview | F | — | P | F | F | ~ | a random pick on an ambiguous fragment, unlabelled |
| `refs page` | page text with its section | P | — | F | ~ | P | ~ | futile `refs map` advice; no fragment support |
| `refs path` | the work's store directory | P | — | ~ | — | F | F | 4 s to print a path |
| `refs propose` | records an agent's checked reading | ~ | — | P | F | F | — | `--json` failure prints the page to stdout; no `--as` |
| `refs recheck` | re-reads verified anchors | F | — | F | F | F | — | its advice does not clear the finding |
| `refs resolve` | looks identifiers up | F | F | F | ~ | F | ? | "add the field to your own entry" silently fails |
| `refs scan` | builds the bibliography, files `refs/` | ~ | P | — | F | F | — | appends a duplicate entry on every run; `--dry-run` unmarked |
| `refs unlink` | removes a link | P | — | — | P | ~ | — | unguarded, unattributed; an unknown id exits 1 |
| `refs unreadable` | declares that no document exists | P | — | P | P | ~ | — | `--undo` needs `--why`; `match` and `coverage` ignore it |
| `refs verify` | the author confirms a transcription | F | — | F | F | F | F | 21–71 s of silence; guard bypassed with `--author` |
| `refs why` | provenance of a result | P | — | ~ | F | P | — | "transcription verified" on mechanical results |
| `digest extract` | mechanical digest from stored LaTeX | ~ | P | ~ | F | F | ~ | its refusal names `refs add` with the arguments reversed |
| `digest import` | copies a digest from another quilt | P | P | F | ~ | P | — | `.tex` only, no artifact; exits 0 leaving three lint errors |

Every command but an argument error spends 1.3–5 s in `open_scan` before printing anything.

## Findings by command

**refs add.**
- **Output.** `Wrote digests/storage/work/81277838/paper.pdf`, with a version-control note on stderr.
- **No identity check.** A Brion PDF was filed as `silverman_AdvancedTopicsArithmetic1999`. The store already holds a wrong paper for `olsson_LogarithmicGeometryAlgebraic2003` (*Logarithmic Geometry and Moduli*, Abramovich et al.).
- **No next step for a PDF.** It never names `loom refs map` (a `.tex` file does get its next step).
- **Refusals.** Clean (`… exists; pass --force to replace it`, exit 2).

**refs build.**
- **Report.** The offline report is shown below; its verdict is the last two lines.

  ```
  resolved      77 entries: 15 state an arXiv id, 40 have a strong candidate, 22 have neither (lookup off)
  fetched       52 sources and 68 PDFs; 0 rejected on the title check (fetching off)
  extracted     52 digests
  mapped        68 works from PDF text, 4083 pages, sections found for 67
  …
  needs you       9  loom refs match lists them
  needs an agent 18  works with pages and no digest
  ```

- **Misleading counts (T5).**
  - "resolved 77" counts every entry.
  - "fetched 52" and "extracted 52" count what is on disk, with fetching off.
  - Hint lines reach 150 columns.
- **Missing or futile next steps (T3).**
  - "needs an agent 18" names no command.
  - "2 too thin to trust" names no action.
  - Offline, "source not fetched yet (3): loom refs build --fetch gets it from arXiv". With the network, the same three were "fetched and discarded: its title did not match", and the discard is not remembered.
  - "needs you" was 12 with the network and 9 without.
- **Raw text on stderr (T4).** The scan's `SiebertPuncturedLogarithB adopts digests/storage/file/0972338306d22915, which the bibliography no longer named`; raw titles with `\\` and newlines.
- **Silence (T6).**

  | run | wall | silent |
  |---|---|---|
  | networked | 19 s | 18.1 s |
  | `--force`, all works | 228.7 s | 227.9 s |
  | `--force`, one work | 4.5 s | 4.5 s |

- **Data loss.** After a verify into the Manolache digest, `build --force manolache_VirtualPullbacks2012` removed the node (count 1 → 0). The record still says `verified`, `recheck` says `0 moved`, and only the info lint `loom:retired-ledger-key` notices.
- **Refused builds still write.** A bad `--only` or an unknown citekey (exit 2) still appends a bibliography entry, and `--json` does so silently.
- **Thin `--json`.** It omits the blocked groups, both handoff lists, the thin list and `entered`.
- **Queues grow.** As duplicates accumulated, a run showed 83 entries, 21 under "no arXiv id" (from 15), and 24 under "needs an agent" (from 18).

**refs cite.**
- **Output.** `accepted ID: reason`, which does not say where the note went or what comes next.
- **`--from` is never used.** `--from nosuchsession` is accepted.
- **Duplicates.** Accepting three times gives three identical lines in `--list`.
- **No pending list.** `--list` shows only accepted suggestions; nothing lists pending ones.
- **No guard.** An agent can `--reject`.
- **Inconsistent shape.** The verbs are flags here, where `verify`/`discard` are subcommands.
- **Exit code.** A wrong annotation kind exits 1.

**refs coverage.**
- **Size.** 106 lines, widest 298 columns (400 for one work).
- **No verdict (T1).**
- **Repetition (T2).** One sentence is printed 27 times: "the digest was extracted from … its numbers and pages are unverified, so check one with loom refs page …".
- **Truncated citekeys.** Cut at 43 characters, so `abramovich-chen-gross-etal_PuncturedLogarit` appears three times.
- **Column collision.** `…   50     6preprint        -`.
- **Uncited rows.** 50 of 76 rows are `cited 0`.
- **No ids for waiting work.** "loom refs verify ID" is given with no ids.
- **Declarations ignored.** The row is unchanged after `unreadable`.
- **Thin JSON.** It lacks `waiting`.
- **Good.**
  - Fragment matching, with refusal by name.
  - The `cited by:` line.

**refs discard.**
- **Success.** Fine.
- **Re-discard replaces the reason.** Re-discarding a discarded result succeeds, and the next `propose` shows only the newest reason.
- **Suggests dropping the whole work.** On a verified result it suggests `refs drop --work X`.
- **Exit code.** An unknown id exits 1.
- **Agent refusal.** Clear.

**refs drop.**
- **No agent guard.** An agent removed two author-verified records with `drop --work atiyah… --yes`.
- **Refuses after the list in a pipe.** Without `--yes` it lists everything, then refuses.
- **Typos pass.** `--work nosuch` prints `nothing to drop`, exit 0.

**refs fetch.**
- **Refusal.** Exemplary.
- **Reports fetches that did not happen.** With consent and no network it printed `kresch_CycleGroupsArtin1999: source (candidate math/9810166)`, exit 0; nothing was fetched.
- **Disagrees with `build`.** It says "nothing to fetch" while `build` says "3 works could be fetched".
- **Odd flag name.** `refs fetch --fetch`.

**refs find.**
- **Truncated ids.** Cut at 58 characters.
- **Column collision.** `mechanicallevel 3`.
- **Too wide.** The per-work line is 284 columns.
- **Silent miss.** `--work manolache` gives `results: 0 in 0 works`.
- **No next step.** A hit names no next command.
- **JSON not grouped.**

**refs forget.**
- **`--undo` requires `--why`.**
- **Short hashes rejected.** A 5-digit prefix is "neither a citekey nor a hash".
- **Prints the full 64-character hash.**
- **The only remedy for the scan loop**, which nothing suggests.

**refs grep.**
- **Size.** 45 hits, up to 627 columns.
- **Garbage section labels.** `[6 Uy1]`, `[0 H*(F),]`.
- **Futile advice.** "9 of 76 works have no page text yet (loom refs map)": those works have no PDF.
- **Silent miss.** `--work manolache` gives 0 hits, exit 0.
- **Sibling entries double the hits.**
- **Good.**
  - The refusal of patterns.
  - The per-work cap.
  - The "read the page before quoting" note.

**refs ingest.**
- **Unexplained refusal.** `? Atiyah and Bott - 1984 - The moment map and eq  atiyah-bott_MomentMapEquivariant19  first-author,title-on-page,title-in-filename`: three signals agree and it is not filed, because it is ambiguous with the sibling `…1984A`, which is never said.
- **Truncated names.** Filenames and keys.
- **Unexplained legend.**
- **Generic next step.** `loom refs add CITEKEY FILE`.
- **Stale help.**
- **Does not map what it files.**

**refs link, links, unlink.**
- **`link` accepts the author's own key.** `rl-000Q`, which overlaps `\uses`.
- **`link` checks nothing early.**
  - `--session` is free text.
  - `--kind` is not a choice, so a bad kind is refused only after a 4.8 s scan.
- **`links` with a citekey.** It says "nothing links" though two links touch the work's results.
- **`links` with an unknown id.** Exits 0.
- **`unlink`.** An agent removed the author's link, and nothing recorded who.

**refs locate.**
- **Raw output.** `… p.19  text  211.4 609.3 361.6 620.2  (6 words, 1 line)`.
- **Link points at the wrong server.** In a copied quilt the `open:` link pointed at the author's real server, through the pid in `serve.json`.
- **Inconsistent page argument.** `--page` here; positional in `refs page`.

**refs map.**
- **Parts don't add up.** `2 mapped, 70 already current, 0 failed`: works with no PDF are not counted.
- **No-op passes.** On a work with no PDF: `0 mapped … 0 failed`, exit 0.
- **No progress count.** A forced run over 67 PDFs took 20 s, one line per work but no `n/67`.
- **"1 sections".**

**refs match.**
- **Repetition.** `no artifact and no identifier anyone will serve` appears nine times.
- **Raw LaTeX titles.**
- **One generic hint.** "add a PDF by hand".
- **Siblings as noise.** Six of the nine are `cited 0` sibling entries.
- **Ignores `unreadable`.**
- **Alignment breaks on long keys.**

**refs overview.**
- **Random pick on an ambiguous fragment.** `overview romagny` printed different papers on successive runs, unlabelled (`next(iter(set))`).
- **Overruns the overview.** It includes Notation and Acknowledgments paragraphs; lines reach 1,397 columns.

**refs page.**
- **Good.** Clean headers and range errors.
- **Futile advice.** `has no page text yet; run loom refs map stacks-project`.
- **No fragments.**
- **Wrong section.** Page 19 is labelled "Preliminaries".

**refs path.**
- **Slow.** About 4 s per call.
- **Conflicting flags.** `--pdf --src`: the last wins.
- **Futile advice.** `--src` names `refs fetch` with fetching off.

**refs propose.**
- **Good guards.**
  - The level-one gate.
  - The wrapper refusal.
  - The `--local` grammar.
  - The gloss detector naming `--supersedes`.
  - The discard reason returned on re-propose.
- **Breaks `--json` on failure.** A failed check prints 72 lines of page text to stdout.
- **No `--as`.** Required by `ai/rules.md`.
- **Unattributed proposals.** Without `--session`, an agent proposal is stored with an empty proposer.
- **Storage path in output.** "checked against digests/storage/doi/…/src/main.tex".
- **Wrong environment in the refusal.** The wrapper refusal always says `\begin{theorem}`.
- **Two matchers disagree.** `verify` said "quoted span not located" for a quotation `propose` had accepted.

**refs recheck.**
- **Counts mislead.** `2 verified anchor(s) re-read`, with 3,140 skipped and uncounted.
- **Its advice fails.** After tampering: "read the page again and loom refs verify what still holds". Re-verifying did not clear the finding.
- **Unknown key passes.** `0 re-read`, exit 0.

**refs resolve.**
- **Refusal.** Good.
- **Width.** Up to 301 columns.
- **Its advice fails.** "add the field to your own bibliography entry": a DOI added to `refs.bib` never reached `digests/bibliography.bib`.

**refs scan.**
- **Not idempotent.** Every run says `1 new` and `SiebertPuncturedLogarith{B,C,D,…} adopts …, which the bibliography no longer named`.
- **`--dry-run` is unmarked.** It also reports one entry more than the file holds.
- **Stale help.** It names the withdrawn `canonize`.

**refs unreadable.**
- **`--undo` requires `--why`.**
- **Ignored elsewhere.** `match` and `coverage` ignore it.
- **No warning for works with documents.** It accepts a work that has a PDF, a source and a digest without a word.
- **Agent refusal.** Good.

**refs verify.**
- **Order.** It prints 20–78 lines of context, then the verdict, then `snapshots: 1 written, 1 already present`.
- **Silence.** 21, 46 and 71 s after the output.
- **"n" is an abort, not a discard.** Answering "n" gives `Aborted!`, exit 1, with no pointer to `discard`.
- **Guard bypass.** An agent shell with `--author Isaac` verifies successfully.
- **Exit code.** An unknown id exits 1.

**refs why.**
- **Mechanical results claim verification.** `state transcription verified`, `anchor p.0 of sha256:917746fde16d (tex, level 3, mechanical)`.
- **Self-supersession.** A re-proposed id supersedes itself.
- **Lookup and exit codes.** A short id is not resolved; an unknown id exits 1.

**digest extract.**
- **Contradictory report.** `Extracted 0 results (); 0 sections`, then `recorded 1 result(s)`.
- **Width.** Lint lines reach 326 columns.
- **Broken advice.** The refusal names `loom refs add <FILE> CITEKEY`, with the arguments reversed.
- **Overlaps `build`.** It duplicates `build`'s extract step, with flags `build` lacks.

**digest import.**
- **Good.** It never overwrites and reports the rename count.
- **Imports text only.** `.tex` only, with no artifact or bibliography entry.
- **Exits 0 on a broken result.** The demo was left with three lint errors.

## Structural problems

- **C1. Sibling entries spread everywhere.** `A`/`B` entries and the scan loop pollute every command; nothing explains or merges them.
- **C2. `build --force` destroys verification.**
- **C3. `scan` re-adopts one document on every run.**
- **C4. Nothing lists what is pending.** No list of pending proposals, citation suggestions, or "needs an agent" works.
- **C5. Flags differ for one idea.**
  - `--reason`/`--why`.
  - `--author`/`--as`/none.
  - Session validated, free, or ignored.
  - Page positional or `--page`.
  - Work as fragment or exact.
  - `--force` with three meanings.
  - Consent flags named after their commands.
  - `--json` missing on 15 commands, and thinner than the text where present.
  - `--yes` with two meanings.
- **C6. Help and book contradict the code.**
  - `ingest`'s help.
  - `scan`'s help.
  - `unreadable`/`forget` `--undo`.
  - The group description covers 3 of 27 commands.
  - Book 8.9 and 8.9.1 put the store under `refs/`.
  - 8.6 names `refs/<citekey>.tex`.
  - 8.14 lists two author-only commands, against four.
  - 8.9 says a second run redoes only what changed.
  - `rules.md` asks for `--as` on `propose`.
- **C7. Five pieces of advice fail.** `map` with no PDF; `resolve`'s "edit your entry"; `recheck`'s "verify"; `extract`'s reversed `add`; `build --fetch` for a source already discarded.
- **C8. Overlapping commands.**
  - `build` vs its five steps.
  - Three intake commands.
  - Four "what's left" lists.
  - Three searches.
  - Six ways to say no.
  - `refs link` vs `loom link`; `cite` and `match` are misnomers.
- **C9. Mechanical results are stored as `verified`.**
- **C10. Two spellings of one work.**
- **C11. Every call costs a full scan.**
- **C12. Store integrity is invisible.** A wrong PDF on file, forgotten discards, garbage section labels.

## Workflow

1. **Cite.**
   - Commands: `\cite`; `refs scan` (inside `build`).
   - Guesses: that a later `.bib` edit does not propagate; the phantom entries.
2. **Get the papers.**
   - Commands: `refs build --resolve --fetch`, `refs match`, then `add` / `ingest` / a drop into `refs/`, `unreadable`, or `resolve` plus an edit; then `map` or `build`.
   - Guesses: which intake; that `add` and `ingest` need `map`; 9 or 12; that `match` ignores `unreadable`; which `.bib`; what `A` entries are.
3. **Digest them.**
   - Commands: `build`, or `digest extract`; for PDF-only works an agent runs `coverage` → `page`/`grep` → `propose --level 1`.
   - Guesses: which works need an agent; that `--force` wipes verified results; that "Extracted 0 results" is a failure.
4. **Review.**
   - Commands: `refs verify ID`, `refs discard ID --reason`, `refs why`, `refs cite`.
   - Guesses: where the ids come from; whether `verify` has hung; that "n" is not a discard.
5. **Use.**
   - Commands: postnotes and `\uses`; `refs find` / `loom search` / `refs grep`; `refs link`; `refs recheck`.
   - Guesses: which search; how a citekey becomes a result prefix; that `recheck`'s advice does nothing.

**What a person needs.**
- `build`.
- One "what's left" list with the pending ids.
- `add`, with an identity check and an automatic map.
- `unreadable`.
- `coverage` and `page`.
- `verify` and `discard`.
- One search.

**The rest.**
- **Steps of `build`:** `scan`, `resolve`, `fetch`, `map`, `digest extract`.
- **Agent tools:** `locate`, `propose`, `link`, `links`, `overview`, `find`, `grep`, `why`.
- **Upkeep:** `drop`, `forget`, `recheck`, `cite`, `ingest`.

## Keep

- **Consent refusals.** They name the config line and the one-run flag.
- **`build`'s `blocked` section.** Grouped, counted, one command per group, cut at twelve.
- **`propose`'s checks.** The quotation check that prints the page, the level-one gate, the wrapper and `--local` refusals, the gloss detector, the returned discard reason.
- **Author-only refusals that explain why.**
- **`grep`'s safeguards.** The refusal of regexes and the per-work caps.
- **`find` and `grep` always state coverage.**
- **Fragment resolution in `coverage`.** With refusal by name and `cited by:`: the rule for every command that takes a work.
- **Read commands validate `--session`.**
- **`page`'s range errors.** And its JSON carrying the hash.
- **`links --depth`.** And the "asserted, not checked" note.
- **`digest import` never overwrites.** And `extract` refuses sources outside the store.
- **`unreadable` and `forget` are reasoned and reversible.**
- **`drop`'s preview.** With `… and 85 more`.
- **`map`'s warnings** for scans and books.
- **`verify` shows both texts.** And keeps the proposer's wording when the author edits it.

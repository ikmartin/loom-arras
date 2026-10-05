# CLI re-grade, appendix: the library

The sweep of `loom library` (the bare report, `library WORK`, and the 15 subcommands `add`, `check`, `discard`, `drop`, `ignore`, `import`, `locate`, `propose`, `read`, `relate`, `review`, `search`, `update`, `verify`, `why`), made 2026-10-04 at commit `65ce069` to repeat the grading of [the study's `refs` appendix](../cli-study/refs.md) (commit `468c9af`, 27 `refs` and 2 `digest` commands) for plan 0.18's Delivery. Copies of the author's quilt only: one copy with its old `[refs]` table untouched, to see the refusal, and a base copy with `fetch = true` and `resolve = true` replaced by `[library]` and `online = false`, from which nine working copies were made, one per writing case that could disturb the next (reads; update and the long redo; the whole workflow; drop after verify; a tampered anchor; ignore and import; deleting a duplicate entry; ignore then delete, a DOI edit and a new citation; add). Also three copies of the demo quilt, one plain `loom init` quilt, and a quilt that was abandoned when its first gather found nothing. 261 transcripts: 259 from a harness recording the command, exit code, wall time, the silence before the first line and the longest gap, stdout and stderr apart, line count and widest line; and 2 from a pseudo-terminal, to answer `verify`'s question. `update --dry-run` was checked against a listing of every file's size and modification time and wrote nothing; the other dry runs were checked by reading the state after them. The study's library workflow ran end to end (cite → get the papers → digest → review → use) on these copies, as the umbrella's Verification asks. Outside the brief's method: the harness ran the venv's `loom` directly with `VIRTUAL_ENV` unset and `COLUMNS=100`. One case pointed a copy's `.loom/serve.json` at another live `loom serve` on this machine (the showcase demo, port 8795) to test `locate`'s link, and restored it at once. The reviewer name came from the global git config (`ikmartin`), which was read and never written. No run touched the network: `--online` ran only under `AI_AGENT=1`, where it is refused before any lookup. Other sweeps ran at the same time, so a reader that takes 1.3–1.7 s at light load took up to 4 s under load; ranges are given. The author's quilt still carries the duplicate entries and the wrong Olsson PDF that the old `refs scan` and `refs add` made, because loom never writes it, so several findings are about how today's commands handle that state. Grades: P pass, p partial, F fail, – not applicable; in T6, – means never more than about 2.5 s silent at light load, as the sibling appendices use it.

## Grades

| command | was | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | K | worst problem now |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `library` | `refs coverage`, `refs match`, `refs cite --list`, `refs build`'s report | P | P | p | p | p | – | p | p | p | the wrong Olsson PDF (*Logarithmic Geometry and Moduli*, Abramovich et al.) is listed as "need an agent: 62 pages olsson_LogarithmicGeometryAlgebraic2003" (K3: `--session` is refused only after the report prints) |
| `library WORK` | `refs coverage WORK` | P | P | P | p | p | – | p | P | p | "cited by 11 keys" in the verdict over a "cited by (15)" heading; `romagny` is refused as "4 works" though two are versions (K7) |
| `library update` | `refs build`, `scan`, `resolve`, `fetch`, `map`, `digest extract` | P | p | F | p | p | P | F | P | p | "next: loom library lists them" under "9 need you, 17 an agent", where `library` lists 3 and 5; "fetched 52 sources and 67 PDFs", "extracted 52 digests" on an offline run that did neither |
| `library add` | `refs add`, `refs ingest` | P | p | F | p | p | p | F | P | p | refuses the right Behrend–Fantechi PDF, "Behrend does not lead its byline", on a page whose byline reads "K. Behrend1 , B. Fantechi2"; its `next:` line loops for Olsson's own PDF |
| `library review` | new | P | P | P | P | P | – | P | P | p | an unknown `--session` is refused after the queue prints (K3) |
| `library verify` | `refs verify`, `refs cite --accept` | p | – | p | p | P | – | p | P | p | shows "quoted span not located; whole page" for a quotation `propose` accepted; "n" is still `Aborted!`, exit 1 |
| `library discard` | `refs discard`, `refs cite --reject` | P | – | p | P | p | – | P | P | p | discarding a discarded result again replaces the reason the next proposer is told, exit 0 |
| `library ignore` | `refs unreadable`, `refs forget` | P | – | p | P | P | – | F | P | P | "set aside" does not hold: after `ignore` and deleting the entry, the next `update` files the same document under a new key and digests it again |
| `library read` | `refs page`, `refs overview`, `refs path` | P | – | p | p | p | – | p | P | p | the Overview runs on into "Notation and conventions" (lines to 1,397 columns); `--where src` advises `update --online` for a work with no arXiv id |
| `library search` | `refs find`, `refs grep` | P | F | p | p | p | – | P | p | p | "(also in manolache_VirtualPullbacks2012A)" and "(extracted by loom)" on all 20 hits; `--pages` lists a work and its version as two hits |
| `library why` | `refs why`, `refs links` | P | P | p | p | P | – | p | P | p | provenance reads "anchor digests/manolache_VirtualPullbacks2012.tex (tex, level 3, mechanical)" and "extracted loom digest extract" |
| `library propose` | `refs propose` | P | – | P | p | p | – | P | P | F | no `--as`, so an agent's proposal is stored with no proposer ("proposed — 2026-10-05T00:31:39"); `--session nosuchsession` accepted (K2, K3) |
| `library locate` | `refs locate` | P | – | p | p | P | – | p | P | F | `--page 999` ends in a Python traceback (K3) |
| `library relate` | `refs link`, `refs unlink` | P | – | P | p | P | – | p | P | F | `--session nosuchsession` is accepted and stored as the relation's author, `"by": "nosuchsession"` (K3) |
| `library check` | `refs recheck` | P | p | F | p | P | F | p | P | p | 13.6–16.9 s of silence; its fix for a moved anchor ("loom library verify ID") does not clear it; it misses the wrong Olsson PDF |
| `library import` | `digest import` | P | P | p | P | P | – | P | P | F | `--name "bad name!"` writes `digests/bad name!.tex` with that citekey, exit 0 (K3) |
| `library drop` | `refs drop` | P | P | P | p | P | – | F | P | p | "verified nodes already in digests/ are not touched", yet it erases the record that protects them, and the next `update --redo` overwrites the author's verified text |

## Against the study

Rows for the steps of `refs build` take `library update`'s grades, since each step is now `update --only STEP` and prints `update`'s report.

| old command | old T1–T6 | now (its command) | now T1–T6 | the old worst problem: fixed / partly / not |
|---|---|---|---|---|
| `refs add` | P — ~ F P — | `library add` | P p F p p p | fixed: a PDF that does not show it is the work is refused (Brion's paper `--for` Silverman's book: "it does not show it is silverman_…", exit 2) |
| `refs build` | F ~ ~ F F F | `library update` | P p F p p P | fixed: `--redo` kept a verified result and said so ("verified results kept through the new extraction (1)"); the 202 s redo of every work printed progress at most 3 s apart |
| `refs cite` | P F F ~ — — | `library verify` / `discard` / `review` | p – p p P – | fixed: `--from` is gone, a second accept is refused ("resolved already"), `review` lists pending suggestions with ids |
| `refs coverage` | F F F F F — | `library`, `library WORK` | P P p p p – | fixed: citekeys whole, no sentence repeated, widest line 99 |
| `refs discard` | P — P P ~ — | `library discard` | P – p P p – | not: re-discarding succeeds and replaces the reason |
| `refs drop` | F F P P P — | `library drop` | P P P p P – | fixed: an agent is refused even with `--yes` (but see the drop-then-redo loss below) |
| `refs fetch` | ~ F P ~ P ? | `library update --only fetch` | P p F p p P | partly: no fetch of a candidate is reported, but offline `--only fetch` still reports "fetched 52 sources and 67 PDFs" |
| `refs find` | F ~ ~ F F ~ | `library search` | P F p p p – | fixed: `--work manolache` searches that work; `--work nosuch` is refused, exit 2 |
| `refs forget` | P — ~ F ~ — | `library ignore` | P – p P P – | fixed: `--why` is required with `--undo`, and the help now says so |
| `refs grep` | F ~ F F F ~ | `library search --pages` | P F p p p – | partly: lines fit 100 columns and no map advice is given, but "9 of 76 have none to search (loom library)" names a report that lists 3 |
| `refs ingest` | F F F F P — | `library add` (a folder) | P p F p p p | partly: every skipped file now has a reason, but on the author's `refs/` many reasons are false ("Brion does not lead its byline", "Atiyah does not lead its byline") |
| `refs link` | P — P P ~ — | `library relate` | P – P p P – | partly: the author's own keys are refused; `--session` is still free text, and is now recorded as who asserted the relation |
| `refs links` | F ~ — P P — | `library why` | P P p p P – | fixed: an unknown id is "no result …", exit 2; `why` lists relations |
| `refs locate` | P — ~ F P — | `library locate` | P – p p P – | not: raw coordinates; with `serve.json` naming another quilt's live server, `open:` links into that server |
| `refs map` | F F — P F ~ | `library update --only map` | P p F p p P | partly: a work with no PDF is "1 needs you" with a next step, not "0 failed"; the step line still says "mapped 0 works", exit 0 |
| `refs match` | F F F F F — | `library` | P P p p p – | partly: `ignore` is respected; a PDF in `refs/` that was never filed under its work (Olsson's own) is still listed nowhere |
| `refs overview` | F — P F F ~ | `library read WORK` | P – p p p – | fixed: `read romagny` is refused naming the matches, exit 2 |
| `refs page` | P — F ~ P ~ | `library read WORK PAGES` | P – p p p – | fixed: a work with no PDF names `library add FILE --for WORK`; fragments resolve |
| `refs path` | P — ~ — F F | `library read --where` | P – p p p – | fixed: 0.14 s for a citekey, 1.4–2.7 s for a fragment |
| `refs propose` | ~ — P F F — | `library propose` | P – P p p – | partly: a failed check under `--json` keeps stdout one JSON document; there is still no `--as` |
| `refs recheck` | F — F F F — | `library check` | P p F p P F | not: re-verifying after "p.1 no longer reads that way" leaves the finding in place |
| `refs resolve` | F F F ~ F ? | `library update --only resolve` | P p F p p P | not: a `doi` added to Silverman's entry in `refs.bib` never reached `digests/bibliography.bib`; the work still "no document and no identifier" |
| `refs scan` | ~ P — F F — | `library update --only gather` | P p F p p P | fixed: two runs leave 76 entries and change no file; the dry run says "dry run:" (but deleting a duplicate brings a new one, below) |
| `refs unlink` | P — — P ~ — | `library relate --undo` | P – P p P – | fixed: an agent cannot remove the author's relation, removal is recorded in `digests/links-removed.jsonl`, an unknown id exits 2 |
| `refs unreadable` | P — P P ~ — | `library ignore` | P – p P P – | fixed: `library` and `update` respect it ("declared unreadable, not retried") |
| `refs verify` | F — F F F F | `library verify` | p – p p P – | fixed: refused under `AI_AGENT=1` whatever `--as` says; 2–7 s in all, about 1.5 s after the answer |
| `refs why` | P — ~ F P — | `library why` | P P p p P – | fixed: a mechanical result reads "extracted by loom" |
| `digest extract` | ~ P ~ F F ~ | `library update --only extract` | P p F p p P | fixed: the refusal with reversed arguments is gone; a work with no source is "blocked: no arXiv id to fetch a source on" with `add … --for` |
| `digest import` | P P F ~ P — | `library import` | P P p P P – | not: it still copies the `.tex` only, and answers "Calloway14 is not in the bibliography" with "next: loom lint" |

Tally for this part. The study, 29 commands, T1–T6:

| | T1 | T2 | T3 | T4 | T5 | T6 |
|---|---|---|---|---|---|---|
| P | 12 | 3 | 7 | 7 | 9 | 0 |
| ~ | 4 | 4 | 8 | 5 | 5 | 6 |
| F | 13 | 8 | 10 | 16 | 14 | 3 |
| — or ? | 0 | 14 | 4 | 1 | 1 | 20 |

Now, 17 commands:

| | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | K |
|---|---|---|---|---|---|---|---|---|---|
| P | 16 | 6 | 5 | 4 | 9 | 1 | 5 | 15 | 1 |
| p | 1 | 3 | 9 | 13 | 8 | 1 | 8 | 2 | 12 |
| F | 0 | 1 | 3 | 0 | 0 | 1 | 4 | 0 | 4 |
| – | 0 | 7 | 0 | 0 | 0 | 14 | 0 | 0 | 0 |

## What is still wrong

### Defects that lose data or report a failure as success

- **`drop` then `update --redo` overwrites the author's verified rendering.** On a copy: `library verify manolacheVirtualPullbacks2012-thm-4.1 --yes --statement 'Edited by the author: …'`, then `library drop --work manolache_VirtualPullbacks2012 --yes` ("dropped 95 records; verified nodes already in digests/ are not touched"), then `library why manolacheVirtualPullbacks2012-thm-4.1` → "no result", exit 2. Then `library update --redo manolache_VirtualPullbacks2012` exits 0 and the node is back to the extracted text (`grep -c "Edited by the author"` → 0), with no "verified results kept" group and no warning. The drop's help says "Dropping costs re-reading, never correctness". Either drop keeps the records of verified results, or `--redo` keeps any node whose text differs from the previous extraction, or drop says that a later `--redo` will overwrite it.
- **The wrong Olsson PDF is still unreported, routed to an agent, and cannot be replaced.** `library read olsson_LogarithmicGeometryAlgebraic2003 1` prints "Logarithmic Geometry and Moduli / Dan Abramovich, Qile Chen, …", while the entry is Olsson's *Logarithmic Geometry and Algebraic Stacks*. `library check` names three "documents that may not be their work" and not this one. `library` lists it under "need an agent: pages and no digest" as "62 pages", so an agent in ingest mode would propose results from Abramovich et al.'s survey under Olsson's citekey, and `propose`'s quotation check would pass, because it checks against the wrong page text. The right PDF is in `refs/` and has an entry, `olsson_LogarithmicGeometryAlgebraic2003B` (`loom-source = {refs/Olsson - 2003 - …}`), which `library olsson_LogarithmicGeometryAlgebraic2003B` reports as "need you: no document and no identifier" with "fix: loom library add FILE --for olsson_LogarithmicGeometryAlgebraic2003B". Doing that (with or without `--force`, or from a copy outside the quilt) prints "1 document: 0 filed, 1 skipped … already in loom's store, filed from refs/Olsson - 2003 - …", exit 0, and `next: loom library add FILE --for WORK` again. The study named this PDF as defect 9; the identity check now guards new filings, but nothing checks or repairs the store, and the advice loops.
- **Removing a duplicate entry brings it back under a new key, with a second digest.** `library check` says "entries that name one document (16) … fix: keep one of them in your bibliography; loom never edits it"; `update` says "keep one and delete the others from digests/bibliography.bib". Deleting `manolache_VirtualPullbacks2012A` from `digests/bibliography.bib` and running `library update` gave "new entries (1): read from a document in loom's store itself Manolache2011Virtualpull" and "extracted (1): 96 results … Manolache2011Virtualpull", a new `digests/Manolache2011Virtualpull.tex`, and a new entry with no `loom-copy-of`, so it is no longer even a version of the work. Running `library ignore manolache_VirtualPullbacks2012A --why …` first ("set aside: …") and then deleting it gave the same new key and digest. Plan 0.18.5b's "a copy … is recorded and not filed, by `add` and by gathering" does not hold for a document already in `refs/`. There is no command that removes a duplicate.
- **`relate --session` with a typo records the typo as the relation's author.** `library relate … --kind same-notion --why x --session nosuchsession` exits 0; `digests/links.jsonl` holds `"by": "nosuchsession"`, and `relate --undo link-0003 --json` reports `"link": {"by": "nosuchsession", …}`. Run by the author, the relation is attributed to nobody who exists.
- **`--json` claims success over a refused call.** `library --json --session nosuchsession` prints the whole report with `"exit": 0`, then "Error: no session matches 'nosuchsession'" on stderr, and the process exits 2. The same order (report first, refusal after) holds for `library`, `review`, `search`, `read` and `check`.

### T1 · Lead with the verdict

- `library verify` on a terminal prints the quoted page (about 60 lines) and the rendering before the question; acceptable for a question, but "n" then ends `Aborted!`, exit 1, with no verdict of its own and no pointer to `discard`.
- `library WORK` for Manolache reads "digested from another version; done" while the next group says its numbers and pages are unverified.

### T2 · Group, count, then list

- `library search "virtual pullback"`: every one of the 20 hits ends "(extracted by loom)" and "(also in manolache_VirtualPullbacks2012A)", two to three lines each. With `--pages` a work and its version are two hits (`chang-kiem-li_TorusLocalizationWall2017` and `…2017A`, the same snippet; likewise five more pairs in the first 20), and "pages per work (45)" prints a `next: loom library search 'virtual pullback' --pages --work … --limit N` line under each of the 45 works.
- `library update --redo` (184 lines): each of the 33 "extracted" items repeats "numbering from the paper's .aux, except N unlabelled results counted by emulation; its lint: …"; "noted while extracting (35)" prints "environment X is not declared in this quilt; add \newtheorem{X}[theorem]{…}" 26 times, one per work and environment, instead of once per environment with its works.
- `library check`: "entries that name one document (16)" spends three to four lines on each, "X is a copy of Y's document: same title, authors and N pages  Y, X".
- `library add refs --dry-run`: 27 of 39 items read "…: already in loom's store, filed from refs/…", each repeating the filename, and do not say under which work it was filed.

### T3 · Every problem names its next command, and the command works

- `library update`'s last group, "9 works need you, 17 an agent / next: loom library lists them", while `library` lists 3 and 5 (it counts cited works; `update` counts every entry, versions included).
- `update`'s "blocked: no identifier and no document … fix: … or add a doi or eprint to the entry": adding `doi = {10.1007/978-1-4612-0851-8}` to Silverman's entry in `refs.bib` and running `update` changed nothing; the DOI never reached `digests/bibliography.bib` (a new entry with a DOI does get gathered).
- `update`'s and `check`'s advice on duplicate entries regenerates them (above).
- `update --redo`: "environment thm:1 is not declared in this quilt; add \newtheorem{thm:1}[theorem]{Theorem \ref{thm:1}}" for Molcho–Routis, a declaration that refers to a label in the cited paper.
- `library check` after a page's text changed: "fix: read the page again, then loom library verify ID for what still holds". `library verify atiyahbottMomentMapEquivariant1984-thm-3.8 --yes` succeeded and the next `check` reported the same finding, exit 1.
- `library check`'s "documents that are another work's … fix: loom library add FILE --for WORK, with the right document": `add` never replaces, and for Olsson it skips the right document as already stored (above).
- `library add`'s `next: loom library add FILE --for WORK files a document you know is that work` is printed for "it names arXiv:2504.01234v1, which no entry states", where the remedy is an entry in `refs.bib`, and for the Manolache preprint, where `--for manolache_VirtualPullbacks2012` is then refused as "it is manolache_VirtualPullbacks2012A's", a version of that same work.
- `library search pullback --work manolache --limit 3`: "… and 92 more; loom library search pullback --limit 95 shows every one" drops `--work`, so the suggested command shows 95 hits from every work. `--pages`: "9 of 76 have none to search (loom library)", where `library` lists 3.
- `library read atiyah-bott_MomentMapEquivariant1984 --where src`: "nothing there yet; loom library update atiyah-bott_MomentMapEquivariant1984 --online fetches it", for a work `update` lists under "blocked: no arXiv id to fetch a source on". Reading a preprint-digested work's overview prints "so check one with loom library read manolache_VirtualPullbacks2012 PAGES" from `library read` itself.
- `library discard` of a verified result: "edit or remove it there, or loom library drop --work manolache_VirtualPullbacks2012", which drops all 95 records of the work. Of an extracted result: "loom library update manolache_VirtualPullbacks2012 --redo extracts the digest again", which extracts the same result again.
- `library verify ID` without a terminal: "verifying needs you to have read both texts; pass --yes once you have", and neither text is shown (nor by `--dry-run`).
- `library import`: "Calloway14 is not in the bibliography … next: loom lint"; lint reports the same thing and fixes nothing.
- `library why manolache_VirtualPullbacks2012` (a citekey): "no result …; loom library search TEXT finds one by its words", where `loom library manolache_VirtualPullbacks2012` is the command for a work.
- `library ignore manolache_VirtualPullbacks2012 --dry-run`, a cited work with a source, a PDF and a digest: "would record: … set aside" with no word that it is cited eleven times.

### T4 · Use the reader's words

- `library`: "\textit{Stacks Project}"; `library WORK`: "[Thm.~4.3]".
- `library why`: "anchor digests/manolache_VirtualPullbacks2012.tex (tex, level 3, mechanical)", "extracted loom digest extract" (a withdrawn command), and for an extracted result the author's edit is headed "(- proposed, + verified)".
- `library locate`: "p.1  text  163.4 506.2 283.2 517.0  (4 words, 1 line)".
- `library verify`: "snapshots: 2 written, 0 already present". `propose`: "in digests/atiyah-bott_MomentMapEquivariant1984.proposed.tex". `relate --dry-run`: "would be written to digests/links.jsonl". `drop`: "verified nodes already in digests/".
- `library update`: ".aux", "counted by emulation". `library add`: "on first-author, title-on-page, title-in-filename".
- `library search --pages`: section labels such as "[1 If Y has irreducible components Y1 ,]" for Battistella et al.; `check` reports only one section map as a guess.
- `library read WORK` (overview) prints raw LaTeX, `\paragraph{Notation and conventions.}` and what follows.

### T5 · Numbers add up, and fit

- Two counts of works: `library` says "26 works cited, 19 digested" and "cited nowhere, so not followed: 25 entries" (51 works, versions folded); `update` and `search` say "52 of 76 works digested" (76 entries, versions counted). `update --redo`'s verdict says "this run extracted 33", its table "extracted 52 digests", its progress ran to "51/51".
- `library WORK`: "cited by 11 keys" in the verdict, "cited by (15)" as the heading (15 citations).
- After the author verified a proposal: `library atiyah-bott_MomentMapEquivariant1984` shows "verified 1" in its table and "a digest too thin to trust: 0 results over 28 pages" under it.
- "1 results, 29 pages" in `update`'s "too thin to trust".
- 62 of 259 harness runs printed a stderr line over 100 columns, nearly all single-sentence refusals and notes: `add --for` refusals 311–438, `propose --local` 278, `propose`'s gloss note 237, `read`'s version note 246–252, the old-config refusal 140. Stdout stayed within 100 columns everywhere except raw bodies (`read`, `locate`) and JSON.

### T6 · Show that it is alive

- `library check`: 13.6–16.9 s before its first line, whether for one work or all 76, with no progress.
- `library add refs --dry-run` (39 PDFs): 10.2 s silent.
- `library update`: progress every 2–3 s through extract and map (`extract 7/51 romagny_… 0:24`, `map 45/76 alper_… 3:09`), but 3–6 s silent before the first line while gathering.
- Every other command: 1.3–1.7 s at light load when it resolves a fragment or reads the library, 0.1–0.3 s for `read` with an exact citekey.

### T7 · Say only what happened

- `library update` offline: "fetched 52 sources and 67 PDFs; 0 rejected on the title check (offline)", "extracted 52 digests", "resolved 76 entries" on a run that fetched, extracted and resolved nothing; for one work, "fetched 1 source and 1 PDF". The counts are what is on disk.
- `library add` gives false reasons: the Behrend–Fantechi PDF's first page reads "The intrinsic normal cone / K. Behrend1 , B. Fantechi2", and `add … --for behrend-fantechi_IntrinsicNormalCone1997` refuses it, "Behrend does not lead its byline", exit 2. Without `--for`, 11 of the author's 39 PDFs are skipped with "X does not lead its byline" or "X is not in its byline", among them Atiyah–Bott, Brion and Romagny's own papers.
- `library ignore` says "set aside" and the document is offered again under a new key (above); `drop` says verified nodes are not touched, and they are lost on the next `--redo` (above).
- `library locate`, with `serve.json` naming another quilt's live server: `open: http://127.0.0.1:8795/library/atiyah-bott_…` into that server.
- `library read WORK --where src` for a work with no source prints a path that does not exist on stdout, exit 1.
- `library verify` shows "(quoted span not located; whole page)" for the quotation `propose` accepted on the same page ("This\nleads in particular …" across a line break): the two matchers still disagree.
- The session log records `library search pullback --limit 1` as "loom library search 1 pullback".

### T8 · Machine output carries what the text carries

- `--json` with an unknown `--session`: `"exit": 0` in the document, exit 2 from the process (above).
- `library search --json`: `"page": 0` for every extracted result, which has no page.

### K · The command line

- **K2.** `propose` has no `--as`, though `ai/rules.md` says "Name yourself with `--as` on everything you write", so an agent's proposal is stored with no proposer. `--session` means four things: log this call (`library`, `review`, `search`, `read`, `why`, `check`, `locate`), the asserter (`relate`, "it is recorded as who did"), the proposer (`propose`), and a filter (`drop`); `verify` and `discard` have none. A page is positional on `read` and `--page` on `locate` and `propose`. `ignore --undo` is a flag and `relate --undo LINK_ID` takes a value. `verify`'s agent refusal still says "whatever --author or --as says".
- **K3.** An unknown `--session` is accepted by `propose`, `relate` and `drop` (which then matches the proposal stored with the same typo), and refused by the readers only after they print. `locate … --page 999` ends in a traceback (`loom.refs.pages.MapRefused: pdftotext failed:`). `import --name "bad name!"` writes `digests/bad name!.tex`. `propose --local "Theorem 2"` and `read WORK 99` exit 1, while `read WORK abc` exits 2. Because `library` takes a WORK, a mistyped subcommand is a work: `library verfy` → "'verfy' names no work"; `library serch pullback` → "Got unexpected extra argument (pullback); see `loom library serch --help`".
- **K5.** Every author's act refused an agent the same way (`add`, `import`, `verify`, `discard`, `ignore`, `drop`, `relate --undo` of another's relation, `update --online`), also when `--as Isaac` was given. The guard also refuses an agent's `--dry-run` of `add` and `ignore`, which change nothing.
- **K6.** `loom library --help` lists the 15 subcommands alphabetically; `propose` and `locate` say "An agent's tool" in their sentence, but the person's commands do not come first and `check`, `import` and `drop` are not marked as upkeep.
- **K7.** Versions are folded into one work by `library`, `library WORK`, `search` (results) and fragment resolution, and listed as separate works by `update`, `check`, `search --pages`, the ambiguity refusal ("'romagny' names 4 works") and `add` ("it is manolache_VirtualPullbacks2012A's"). `loom search "virtual pullback"` answers with 6 digest headings and `library search` with 121 results, and neither points to the other.

## What got worse

- **New: removing a duplicate creates a new one** (above). The study's scan loop re-adopted one document; today a deleted entry comes back under a new key with a second digest, and `check` and `update` both advise the deletion.
- **New: `drop` then `--redo` loses verified text** (above). Before 0.18, `build --force` lost it directly; today `--redo` protects a verified result only while its record exists, and `drop` removes the record while saying the node is safe.
- **New: the identity check refuses right documents with false reasons.** `refs add` filed anything; `library add` refuses or skips correct PDFs whose byline the text layer spells with superscripts or spaced capitals, and says the author "does not lead its byline". Between that and "already in loom's store" for documents filed under the wrong entry, `add` filed none of the author's 39 PDFs.
- **New: readers validate `--session` after they answer**, so a refused call prints a full report, and `--json` carries `"exit": 0` over a process exit of 2. The study listed "Read commands validate `--session`" under Keep.
- **New: `relate --session` is recorded as the author.** The study's free-text session was only stored; today it replaces the asserter's name.
- **New: a mistyped subcommand reads as a work**, with a `see loom library serch --help` that names no command.
- **Grades lower on a row:** `refs add` T3 ~ → F, T6 — → p (the folder intake it absorbed); `refs discard` T3 P → p; `refs unreadable` T3 P → p; `refs ingest` T5 P → p; `refs page` T5 P → p (the version note on stderr, 246–252 columns); `refs scan` T2 P → p and `refs fetch` T3 P → F, because their rows now carry `update`'s report.
- **Not new, not found by the study:** `locate --page` past the last page crashes with a traceback.

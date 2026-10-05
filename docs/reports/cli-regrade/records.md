# CLI re-grade, appendix: records, review, history and reshaping

The sweep of `accept`, `adopt`, `annotate`, `status`, `deps`, `downstream`, `search`, `source`, `link`, `lint`, `history` (bare, KEY, `show`, `restore`, `verify`), `stamp`, `fork`, `revert`, `live`, `mv`, `linearize`, `atomize`, `id`, `new`, `import`, `init`, `deloom`, `draft` and the answers to `delete`, `rm` and `remove`, made 2026-10-04 at commit `65ce069` to repeat the grading of [the study's records appendix](../cli-study/records.md) (commit `468c9af`) for plan 0.18's Delivery. Every writing case ran in its own copy: nineteen copies of the demo quilt (`loom init --demo`), six copies of the author's quilt (`relloc`, its `[refs]` table replaced by `[library]` with `online = false`), a two-theorem paper for `import` and `init --from`, and fresh directories for `init`; 339 transcripts, each with the command, exit code, wall time, the silence before the first line, stdout and stderr apart, line count and widest line. Dry runs were checked byte-identical against a hash of every file outside `build/`. Outside the brief's method: the harness ran the venv's `loom` directly, and also unset `VIRTUAL_ENV`, `CODEX_SANDBOX` and `CURSOR_AGENT` and pointed `XDG_CACHE_HOME` into the scratch directory; the reviewer name came from the global git config, which was read and never written; two runs received a harness flag by mistake and were refused by loom with exit 2. Other sweeps ran at the same time, so relloc timings of one command varied by up to a factor of two between runs; ranges are given. `history show`, `restore` and `verify` were words of `history` and are subcommands now, invoked the same way, so their `was` is `=`. `build`, which replaces `review`'s publishing, belongs to the tooling sweep and is not graded here. Grades: P pass, p partial, F fail, – not applicable; in T6, – means never more than about 2.5 s silent on either quilt, as the study used it.

## Grades

| command | was | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | K | worst problem now |
|---|---|---|---|---|---|---|---|---|---|---|---|
| accept | = | P | P | p | P | P | p | p | P | p | `--all-live` and `--master` refusals name no way forward; re-accepting a fresh key writes a second row and prints the first-time line; 4.3–6.1 s silent on relloc (K2: a refusal still names `--author`) |
| adopt | = | p | p | F | F | p | F | p | P | p | on relloc every preview of a freshly drafted agent document exits 2 after 17.6 s of silence: `drafting/draft4.tex#remark:13 is missing: select its proposal or revise the document-level changes` |
| annotate | = | P | – | p | P | P | – | F | P | F | no MESSAGE files `"body": ""`, exit 0; `--batch` writes line 1, then refuses line 2 without saying line 1 was kept (K3) |
| status | = | P | p | p | p | P | p | F | P | p | `--explain` says "never accepted" of a key another reviewer accepted; 52 rows of "N not counted" for cited works |
| deps | = | P | P | – | p | P | p | F | P | p | `deps dm-0003 --closure` says "dm-0003 depends on nothing" after `deps dm-0003` listed two, while `source dm-0003 --closure` prints four keys (K7) |
| downstream | downstream, unravel, reach, pop | P | p | – | p | P | p | P | P | P | "via transitive"; two references on one line print as identical rows |
| search | = | P | p | p | F | P | p | P | P | P | digest titles printed as raw LaTeX (`"{\cite[Corollary 2.16, p.~6]{edidin-hassett-kresch-etal_BrauerGroupsQuotient2001}}"`), cited works and the author's results in one list |
| source | = | – | – | P | p | – | p | p | – | p | `--closure` still begins `% Bundle written by loom` and `\section*{Bundle for dm-0003}` (K7) |
| link | = | P | – | P | P | P | – | P | – | P | none of weight; no `--json` |
| lint | = | P | p | p | P | p | p | p | p | P | the cited-works group lists 7 codes covering all 180 of its diagnostics, then says `… and 173 more; loom lint --json` |
| history | = | P | P | – | p | P | p | P | P | p | a subcommand typo is "no such key: shwo", and `history shwo --help` documents a command `loom history shwo` |
| history KEY | = | P | – | F | P | P | p | P | P | P | "its text now differs from every version" names no next command |
| history show | = | – | – | P | P | – | p | P | P | p | DOC@STEP takes the stem only: `drafting/main.tex@1` refused, `main@1` accepted |
| history restore | = | P | P | P | P | P | – | P | P | p | the new document defines 7 ids twice at once (now announced, with fixes); the only writer with no `--dry-run` |
| history verify | = | P | – | – | P | P | p | P | P | P | 3.9 s silent on relloc to read the history |
| stamp | = | P | P | P | p | P | – | P | P | p | a document stamp still runs and prints the bibliography's housekeeping and a library finding (K4) |
| fork | = | P | P | P | P | P | – | P | p | p | every run writes the node file and a history line whether or not the patch is applied; two runs left orphans dm-0012 and dm-0013 |
| revert | = | p | – | P | P | P | – | P | P | P | the verdict comes after the patch, on stderr |
| live | = | P | P | P | P | P | – | P | P | P | none |
| mv | = | P | – | P | P | p | – | P | P | p | refusals up to 146 columns, unwrapped; under an agent marker it runs and the history names the author |
| linearize | linearize, inline | P | P | P | P | P | F | F | P | p | `--fork` lists the nodes it forked as "kept as inclusions" and copies `\label{eq:fix}`, so lint then has 2 errors, one in a document it never touched; 30.6 s silent on relloc |
| atomize | = | P | P | p | P | p | F | p | P | p | 41.8 s silent on relloc; after `--key`, status and lint advise `loom fork` instead of applying the printed patch |
| id | = | P | – | p | P | P | – | P | p | P | the patch comes with no word on applying it; `--json` is refused for a file |
| new | = | P | – | F | P | P | – | F | P | P | never says the node is reached by nothing or where to `\input` it; "the default master declares: conjecture, …, question", which main.tex does not |
| import | = | P | P | F | p | p | p | p | P | p | a same-named paper is refused with no way to rename it; no next step follows an import |
| init | = | P | p | p | p | p | p | P | P | P | "is already inside a quilt" still names no `loom import`; four lines on `.gitignore` every time |
| deloom | = | P | P | p | P | p | – | p | P | P | the blocker says "line(s) 76" for an `\incomplete` on line 45 of a 51-line main.tex |
| draft | = | P | – | p | p | P | – | p | P | P | `--ai main` is refused without a free name suggested; "10 labels derived, 8 results based" |
| delete, rm, remove (answers) | delete, rm, remove | P | – | F | P | p | – | – | – | P | "do it yourself with rm, after `loom downstream ID`": `ID` instead of the argument typed, and rm is wrong for a result inside a document |

## Against the study

| old command | old T1–T6 | now (its command) | now T1–T6 | the old worst problem: fixed / partly / not |
|---|---|---|---|---|
| accept | P – p F p F | accept | P P p P P p | partly: 54 s became 4.3–4.4 s silent, and 6.1 s before a compile line when the document must compile |
| adopt | F F p F F – | adopt | p p F F p F | fixed: a prose-only change now says `run loom adopt review.tex --document-changes`; the preview still omits a waiting prose change when a result changed too |
| annotate | P – p P P – | annotate | P – p P P – | not: no MESSAGE still files `"body": ""`, exit 0 |
| review | p – F F P F | gone; `build` publishes and `status --stale` lists (graded: status) | P p p p P p | fixed by removal; `loom review` now answers "Did you mean 'revert'?" |
| status | F F F F F F | status | P p p p P p | fixed: conflicted ids are a `conflicted` group with `fix:` lines; widest line 100 |
| deps | P p – F P p | deps | P P – p P p | not: `deps --closure` is the statement closure, `source --closure` adds proof dependencies (9 against 12 ids for rl-001G) |
| downstream (+3 aliases) | F F – p P p | downstream | P p – p P p | fixed: one name, and the verdict leads |
| search | p F F F F p | search | P p p F P p | partly: it now names `loom compile DOCUMENT`, a placeholder rather than the document |
| source | – – P p – – | source | – – P p – p | not: `% Bundle written by loom` |
| link | P – p P P – | link | P – P P P – | fixed: an unknown key exits 2 |
| lint | F F F p F F | lint | P p p P p p | fixed: verdict first, grouped, 100 columns, 1.9–3.7 s |
| history (list) | – p – F p p | history | P P – p P p | partly: `froze` and unapplied reverts are gone; auto names (`stamp-checkpoint "checkpoint"`) remain |
| history KEY | P – F F P – | history KEY | P – F P P p | partly: hashes are gone; "differs from every version" still names no next step |
| history show | – – P P – – | history show | – – P P – p | not: DOC@STEP still takes the stem |
| history restore | P – p F P – | history restore | P P P P P – | partly: the conflicts are announced with fixes, but the document still conflicts at once and `revert` is still refused after it |
| history verify | P – – P P – | history verify | P – – P P p | fixed: `--json` carries the verdict and diagnostics |
| stamp | P – F F p p | stamp | P P P p P – | partly: nothing is adopted and no hash printed, but the bibliography's housekeeping still runs and prints |
| fork | p – P F P – | fork | P P P P P – | not: the node and history line are written before the patch is applied, and `--json` now writes too |
| revert | F – p F P – | revert | p – P P P – | fixed: nothing is recorded; a no-op says "nothing to apply" |
| live | P – F P P – | live | P P P P P – | fixed: each id made conflicted is named with its `loom fork` fix |
| mv | P – P p P – | mv | P – P P p – | fixed: "moved … every record naming it follows" |
| linearize | P – P F P F | linearize | P P P P P F | not: under `--fork`, "kept as inclusions" for the nodes it forked and inlined |
| inline | P – F p P F | gone; `linearize` (supersedes its source) and `source DOC` | P P P P P F | fixed by removal; `loom inline` now answers "Did you mean one of: 'link', 'lint', 'live'?" |
| atomize | P – p F P F | atomize | P P p P p F | partly: `--key` now says the results are defined twice until the patch is applied, but the quilt is still conflicted and the advice is `loom fork` |
| id | P – p P p – | id | P – p P P – | not: no word on applying the patch |
| new | P – F p P – | new | P – F P P – | not: no placement hint |
| import | F – F F F p | import | P P F p p p | partly: the verdict names step 0002; the dry run and the confirmation refusal still say "kept as received in step 0001" |
| init | F – p F p p | init | P p p p p p | fixed: stdout, verdict first, `next: cd f2, then loom doctor; loom lint` |
| deloom | P – P F p – | deloom | P P p P p – | partly: `--to` inside the quilt is refused; the blocker's line numbers still count the flattened text |
| draft | P – F F P – | draft | P – p p P – | not: the collision now says why ("arras and the build tell documents apart by name") but suggests no name |
| delete/rm/remove | P – F P P – | answers of the main group | P – F P p – | partly: exit 2 and `loom downstream` named, but `ID` is a placeholder and the rm advice is unchanged |

The aliases `unravel`, `reach` and `pop` were graded with `downstream`; they are gone, and `loom unravel` and `loom pop` answer "No such command", `loom reach` "Did you mean 'search'?".

## What is still wrong

### Defects that lose data or report a failure as success

- **`linearize --fork` reports success over a quilt it left with two errors.** In a demo copy, `loom linearize drafting/main.tex --to drafting/flat.tex --fork` exits 0 with "it typesets to the same text as drafting/main.tex", lists `dm-0001 -> dm-0012` and `dm-0002 -> dm-0013` under "forked", and then lists `nodes/dm-0001.tex` and `nodes/dm-0002.tex` under "kept as inclusions, shared with another document (2)", though `flat.tex` has no `\input` and defines dm-0012 and dm-0013 inline. The fork keeps the user label `\label{eq:fix}`, so `loom lint` then exits 1 with `drafting/flat.tex:32, nodes/dm-0001.tex:7  label eq:fix is defined twice` and `nodes/dm-0002.tex:9  dm-0002/proof refers to dm-0012, which its master does not reach`: the `\eqref{eq:fix}` in the node `drafting/outline.tex` still includes now resolves into the new flat document, so a document the command never touched has a wrong dependency. A forked copy must drop or rename user labels as `fork` itself does (its copy of dm-0002 carries only `\label{dm-0012}`), and the "kept" group must list only what is kept.

### A command that cannot do its work on the author's quilt

- **`adopt` refuses every agent document drafted from a document with an unlabelled node.** On relloc, `loom draft drafting/draft4.tex --ai review3` succeeds, and `loom adopt drafting-ai/review3.tex` (no edits made, with `--document-changes`, or with a key) exits 2 after 17.6–19.3 s of silence: `drafting/draft4.tex#remark:13 is missing: select its proposal or revise the document-level changes`. Reproduced on the demo by adding one unlabelled `remark` to `main.tex`: `drafting/main.tex#remark:2 is missing`. Neither `draft` nor `adopt` names the fix (`loom id drafting/draft4.tex`), and "select its proposal" names no command.

### T1 · Lead with the verdict

- **`adopt` omits a waiting prose change.** With a result change and a prose change both in `drafting-ai/review.tex`, `loom adopt drafting-ai/review.tex` says "preview of 1 result from review.tex into drafting/main.tex; nothing incorporated yet", and `--incorporate TOKEN` says "Changes incorporated; main as it was is landmark main-before-adopt-review; mathematics remains to be reviewed"; only the next `adopt` says the prose waits behind `--document-changes`.
- **`revert` prints the patch, then its verdict last on stderr**: "Apply the patch to nodes/dm-0001.tex and dm-0001 has the text of @1 (widgets-v1) again."

### T2 · Group, count, then list

- **`status`** on relloc ends with "in cited works (52)" and 52 rows, most of them `N not counted  CITEKEY` (`76 not counted  Abramovichetal2014Compar`), the same sentence 52 times; `--include-digests` is named once at the end.
- **`lint`** prints one diagnostic twice (`drafting/draft4.tex:386  \cite[Def. 2.3]{romagny_GroupActionsStacks2005} names no result …  rl-000H/proof`, twice), and every line repeats its key after a message that already names it (`2 annotation(s) on rl-0002 no longer match its text  rl-0002`).
- **`downstream rl-000G`** prints `drafting/draft4.tex:479   in  rl-000N` twice, two references on one line with no column to tell them apart.
- **`search kresch`** gives "259 matches" as one list sorted by taxon, all from digests, with a JSON group whose heading is `""`; the author's results and the cited works are not separated.
- **`adopt`** prints "Unselected proposals remain in the agent document. Incorporation does not accept mathematics." on every preview.
- **`init`** spends four lines on `.gitignore` globs every time, and `init --from --dry-run` prints two groups both headed "would write".

### T3 · Every problem names its next command

- **`adopt`**: a stale token says "Source, proposal or reviewer changed; refresh Incoming and preview again" (a viewer screen); `--incorporate deadbeef` says "Invalid preview token" and nothing more; `--to build/review.patch` names no `--incorporate TOKEN`, though the help says `--to` "names the `--incorporate TOKEN` that applies exactly it".
- **`atomize --key dm-0004`** prints a patch and leaves dm-0004 conflicted until it is applied; `status` then advises `fix: loom fork dm-0004 --in drafting/main.tex` and `fix: loom fork dm-0004 --in nodes/dm-0004.tex`, and `lint` adds `fix: loom id --next`. None applies the patch. A rerun says "drafting/main.tex: nothing to move for dm-0004", exit 1, and does not reprint it.
- **After `history restore`**, `status` advises `fix: loom fork dm-0001 --in nodes/dm-0001.tex` for an id defined by the restored document and its node file. Its dry run patches the live node file, giving the original definition the id dm-0012 and removing `\label{def:widget}`; applied, the acceptances and annotations of dm-0001 would follow the restored landmark copy. Only the fix that forks inside the restored document is safe.
- **`history dm-0001`**: "dm-0001 has 1 recorded version; its text now differs from every version", with neither `loom stamp -m …` nor `loom revert dm-0001@1` named.
- **`new lemma "…"`**: "dm-0012  wrote nodes/dm-0012.tex, a new lemma", with no word that nothing reaches it and no `\input{nodes/dm-0012}` line to add.
- **`import`**: `import …/main.tex --yes` into the demo says "drafting/main.tex exists; import never overwrites a document" with no way to import under another name; a successful import ends without a next step.
- **`init`** inside a quilt: "… is already inside a quilt", with no `loom import`.
- **`delete dm-0004`** (and `rm`, `remove`): "do it yourself with rm, after `loom downstream ID` shows what depends on it". `ID` is not the `dm-0004` typed, and dm-0004 is a remark inside `drafting/main.tex`, which rm would delete whole.
- **`annotate dm-0002 "x" --quote "not in text"`**: "quote not found in dm-0002", exit 1, with no `loom source dm-0002`.
- **`accept --all-live`** and **`accept --master drafting/outline.tex`**: "live incomplete keys prevent --all-live: dm-0005/proof, dm-0006/proof", with no way to accept the rest.
- **`deloom`** of a superseded document says "drafting/draft4.tex is not a document of this quilt; `loom status` lists them": it is a document, and `status` lists keys, not documents.
- **`lint`**: most groups name no command (`loom:uses-missing`, `loom:detached-annotation`, `loom:unmatched-postnote`, `loom:undigested-citekey`, and `unreachable` for the orphans `fork` leaves).
- **`search`**: "nothing matches 'zzzzqq'" names no `loom library search`; the number hint names `loom compile DOCUMENT` rather than the default document.
- **`id drafting/extra.tex --fix-anchoring`** prints the patch and nothing else.
- **`draft … --ai main`**: "drafting/main.tex is already named main; arras and the build tell documents apart by name", with no free name such as `--ai main-review`.
- **Removed commands** are answered by click's guesses: `loom review` "Did you mean 'revert'?", `loom inline` "Did you mean one of: 'link', 'lint', 'live'?", `loom reach` "Did you mean 'search'?"; `unravel` and `pop` name nothing. Only `delete`, `rm` and `remove` get a written answer.

### T4 · Use the reader's words

- **`search`** prints digest titles as raw LaTeX: `"{\cite[Corollary 2.16, p.~6]{edidin-hassett-kresch-etal_BrauerGroupsQuotient2001}}"`, `"{\cite[Definition 3.1, p.~1]{Calloway14}}"`.
- **`status`** prints raw, cut LaTeX titles (`\cite{edidin-graham_Localizatio…`, `Proof of Lemma~\ref{lem:indepen…`), the cause `own-text-changed (2026-10-05)`, and no theorem numbers.
- **`deps`** says `via uses,ref` and `via postnote`; **`downstream`** says `via transitive`.
- **`adopt`** names its preview by a 64-character token (`--incorporate 83beaa21…c213`).
- **`import`** prints `from .loom/history/0002-second/second.tex via second.bib  knuth` and "proofs: 2, 2 beside their statement, 0 by reference, 0 by enclosure, 0 unattached".
- **`draft`**: "10 labels derived, 8 results based on drafting/main.tex".
- **`stamp DOC`** prints `refs/: 39 documents in loom's store, none new`; a quilt stamp's landmark is named `stamp-checkpoint` for `-m checkpoint`.

### T5 · Numbers add up, and fit

- **`lint`** on relloc: "in cited works (180)" lists 7 codes whose counts sum to 180, then "… and 173 more; loom lint --json"; nothing more exists. The last line, "40 in works nothing cites; loom library check lists them", does not say 40 of what.
- **`atomize`** on relloc: "45 files in nodes/", then "written (2)" listing the spine and `config.toml` only.
- **`import --dry-run`** and the confirmation refusal list "kept as received in step 0001" while the verdict says "the landmark of step 0002".
- **`deloom`**: "1 \incomplete{…}, line(s) 76" for the mark on line 45 of `drafting/main.tex` (51 lines); the kept list then says "line 65", a line of the output file, without saying which file.
- **Unwrapped refusals** over 100 columns: `mv` 146, `accept` under an agent 166, `init` 156 (a path), `delete` 116, `adopt --to` into the sources 132.

### T6 · Show that it is alive

On relloc, silence before the first line (no command here prints progress except `accept`, while it compiles): `atomize` 41.8 s (demo 7.1 s), `linearize` 30.6 s (demo 8.0 s), `adopt` 17.6–19.3 s, `accept` 4.3–4.4 s (6.1 s before `compiling 1/1 drafting/draft4.tex`), `status` 2.0–4.3 s, `history` and `history KEY`, `show`, `verify` 1.3–4.0 s, `lint` 1.9–3.7 s, `source` 2.8–3.2 s, `deps` 2.7–3.1 s, `downstream` 2.9 s, `search` 2.6–2.9 s; and `import` 4.5 s and `init --from` 3.8 s on a two-theorem paper (the identity test's compile). Listing the history, or verifying it, should not need a scan.

### T7 · Say only what happened

- **`status --explain dm-0002`** on the demo says "never accepted", while `.loom/state.toml` holds an acceptance by "The loom demo" and `downstream dm-0002` lists it.
- **`deps dm-0003 --closure`** says "dm-0003 depends on nothing" directly after `deps dm-0003` says "depends directly on 2 results".
- **`annotate`**: a second `--resolve` of the same annotation, and a second `--discard`, each append an event and print "resolved …" and "withdrew …" as if new; with no MESSAGE an annotation is filed with an empty body.
- **`accept dm-0001`** twice writes two rows and prints "accepted dm-0001 as ikmartin" both times; `accept dm-0002 --force` over a failing compile says only "accepted dm-0002 as ikmartin".
- **`new lemmma x`**: "the default master declares: conjecture, definition, lemma, proposition, question, remark, theorem"; `main.tex` declares neither conjecture nor question.
- **`source KEY --closure`** writes nothing and says "% Bundle written by loom".
- **Records credit the author with an agent's acts**: with `AI_AGENT=1`, `stamp`, `fork`, `mv`, `import`, `linearize` and `draft` record `"actor": "ikmartin"` in the history, and `loom new` writes `% !LOOM author: ikmartin` into the node (see K5).

### T8 · Machine output carries what the text carries

- **`fork --json`** of a completed fork says `"ok": false` with exit 0 (`ok=dry_run`); its dry run says `"ok": true`.
- **`lint --json`** on relloc has `"notes": []`; the text's "40 in works nothing cites; loom library check lists them" is not in it.
- **`id FILE --json`** is refused ("--json applies to --next").
- **`status --json`**'s `summary` has no count of the 13 "sections with findings" its verdict names.

### K · The command line

- **K1.** The removed names are answered by fuzzy guesses (T3 above) rather than by their replacements.
- **K2.** The agent refusal of `accept` says "whatever --author or --as says", and `accept` has no `--author`. `history restore` is the one writer without `--dry-run`. `adopt` writes `--- a/drafting/main.tex` patches (-p1) while `revert`, `fork`, `id` and `atomize --key` write `--- nodes/dm-0001.tex` (-p0).
- **K3.** `annotate` accepts an empty message; `annotate --batch` writes each line before checking the next (line 1 kept, line 2 "no such key: dm-9999", exit 2); "quote not found" exits 1.
- **K4.** `fork` and `atomize --key` write before the patch they print is applied; `stamp DOC` runs the bibliography scan and reports its findings.
- **K5.** With `AI_AGENT=1`, `stamp`, `fork`, `mv`, `import`, `linearize`, `atomize`, `deloom`, `revert` and `init` all run; none is in `AGENT_COMMANDS` and the help marks none with `*`. `history restore` refuses, because it writes a drafting document, yet `mv`, `import`, `linearize` and `atomize` write or move drafting documents and do not. The history then credits the author. `annotate` from an unnamed agent is filed as "(agent)" rather than refused (plan 0.18.4's `_common.writer` is not used by `annotate`; `ai/rules.md` documents the fallback), and `annotate … --as ikmartin` from an agent shell files a note in the author's name.
- **K6.** `status --help` says "Never exits nonzero"; `status --explain dm-9999` exits 2. `atomize`'s first line says "Move each node of SRC", its second "SRC is not modified". `accept`'s says "Record acceptance rows and snapshots for KEYS; the only writer of the ledger", and `deps`'s "direct statement-edges and proof-edges". `fork`'s first line names FILE, which is `--in`.
- **K7.** "Closure" is two things (`deps --closure` the statement closure, `source --closure` with proof dependencies too); "Bundle" survives in `source`; `annotate --discard` prints "withdrew"; `history shwo --help` prints the KEY help under "Usage: loom history shwo".

## What got worse

- **Removed commands misdirect.** `loom review` suggests `revert`, `loom inline` suggests `link`, `lint` or `live`, and `loom reach` suggests `search`; before plan 0.18 each ran (badly). Only `delete`, `rm` and `remove` were given an answer.
- **`lint`'s count is new and false.** "… and 173 more" after a group that has shown everything comes from the output layer's cut, which counts the 180 diagnostics against 7 rows.
- **`history shwo --help`** documents a command that does not exist, which the group reshape introduced.
- **`accept`'s agent refusal names `--author`**, a flag the 0.18.4 rename removed.
- **`fork --json` now writes.** Plan 0.18.4 meant it (K4: `--json` is no longer a dry run), but a reader who used it to inspect a fork now leaves an orphan node per run; `--dry-run --json` is the inspection.
- **Grades lower than the study's**: `deloom` T3 (P to p: the new "`loom status` lists them" advice); `atomize` T5 (P to p: "written (2)" omits the node files); `delete` T5 (P to p: the answer is 116 columns); `source`, `history show` T6 (– to p) and `adopt` T6 (– to F), because this sweep timed them on relloc and the study recorded no relloc time for them. `adopt`'s refusal on relloc was not tried by the study, so whether it is new is not known.

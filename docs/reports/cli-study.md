# The loom command line: a study against the terminal principles

A study of every loom command as it stood at commit `468c9af` (2026-10-02), measured against the terminal principles T1–T6 (book 1.10), with the principles themselves tested against what the command line gets wrong. It was asked for on 2026-10-02, after `loom refs build`'s report on a real quilt proved unreadable and a long run looked hung. No code was changed.

The deliverables are part three (revisions to the principles), part four (every deficiency found) and part five (the redesign, with part six the redesign of `refs`). The per-command gradings are in the appendices under [`cli-study/`](cli-study/).

## Part one: the verdict

The command line does a great deal correctly underneath and says it badly. Its refusals are its best part: they name what blocks and the flag that clears it, and that habit should spread to everything. Its reports are its worst: on a real quilt nearly every report puts the verdict last, prints one sentence dozens of times, runs past 200 columns, names loom's storage paths and hashes, and is silent for up to sixteen minutes. Six principles describe most of that, and fixing the output layer once, for every command, would fix most of it.

The study also found what the principles do not describe, and some of it matters more than any layout:

- **Twelve defects lose or corrupt the author's data, or report success over a failure** (part two). Four can lose work outright: `sync init`'s defaults publish over the quilt's own branch, `sync incorporated --yes` lets the next push revert a coauthor, `refs build --force` deletes results the author verified, and `refs scan` appends a duplicate bibliography entry on every run. That last one is in the author's quilt now.
- **One function makes almost every slow command slow.** `records/dependencies.py`'s `display_span` re-tokenises a whole file once per key: on the author's quilt, 772 tokenisations and 47.5 s of one profiled 51.6 s run, and 32 of 35 s of `status`. Caching it per file removes most of the T6 failures before any progress line is written.
- **The command surface has grown by accretion**: 96 names for 91 commands, four names for one report, three commands that only refuse, two commands per session action, five flatteners, three searches, three intake commands, and `refs` with 27 subcommands where a person needs about ten. Flags mean different things on different commands (`--as` is a person on six commands and a new name on three). None of T1–T6 catches any of this, which is why part three proposes a second set.

## How the study was made

Three sweeps ran in parallel, one per part of the command tree: `refs` and `digest` (29 commands), records, review, history and reshaping (31), and the tooling, sessions, AI layer and sync (41, counting the root). Every command ran in realistic cases — the normal case, wrong and missing arguments, a refusal, `--json`, an empty case, and a long run — in scratch copies of the author's quilt (`relloc`, 76 bibliography entries, 52 digests, 64 results of the author's own and 4,089 nodes counting digests) and of the demo quilt, never in the originals. Each run's transcript records the command, exit code, wall time, the longest silence, stdout and stderr separately, line count and widest line: 788 transcripts in all. Every command's output was graded against T1–T6, its behaviour checked against chapters 8, 11, 12 and 17, and the most serious findings were checked again by hand.

Two things went outside the plan. One `refs build` ran with network access, in another sweep's scratch copy where fetching had been switched on: it made identifier lookups and fetched two arXiv listings, and wrote only inside the scratch area. And one `loom inline` wrote a file to `/tmp` to test whether it would, which it did; the file was removed at once.

## Part two: defects that lose data or report a failure as success

These come first because a reader of the principles would not find them. Each was reproduced, and the first five were re-checked against the code.

| # | defect | evidence |
|---|---|---|
| 1 | `loom sync init` defaults to `--remote origin --branch main`, which is normally the quilt's own repository; with no flags, `sync publish --push` replaced that branch's tree with the source-only projection, removing `config.toml`, `ai/` and `.loom/` from what a coauthor pulls. Book 4.6 names `overleaf` and `master`. | `cli/sync.py:47-48`; tooling transcripts `sync-init-defaults-origin`, `sync-publish-push-origin` |
| 2 | `loom sync incorporated --yes` records a pull as incorporated without checking it was applied; the next `sync publish --push` silently reverted the coauthor's edit. `sync finish` is the checked path for the same step. | tooling `sync-b-*` |
| 3 | `loom refs build --force CITEKEY` rewrites `digests/CITEKEY.tex` from the source, deleting every result the author verified into it, while `results.json` still says `verified`; `refs recheck` reports `0 moved`. | `refs/build.py:395-420`; refs `build-force-after-verify` |
| 4 | `loom refs scan` re-adopts the same stored document on every run (`SiebertPuncturedLogarith`, then `A`, `B`, `C` …), saying the bibliography "no longer named" it, which is false. Every `refs build` and every document stamp runs it, refused and `--json` builds included. Three runs on a copy of the author's quilt took its bibliography from 76 entries to 79; the author's own quilt already carries two of these. | re-run by hand; refs `scan-*` |
| 5 | `loom revert` appends a revert to the history every time it prints a patch, applied or not, including `--json` and runs with nothing to change. Book 17.11 makes applying it the author's act. | `cli/history_cmds.py:309`; records `revert-*` |
| 6 | `loom inline` writes a flat copy without superseding its source, so every id is then defined twice, and it reports "Identity test: pass", exit 0. | records `inline-*`, `lint-after-inline` |
| 7 | `loom ai discard --before yesterday` does not validate the date and discards every session, exit 0. | tooling `ai-discard-before-garbage` |
| 8 | Author-only acts are open to agents: `session delete --purge --yes` erased three annotations, `refs drop --work X --yes` erased verified records, `refs unlink` removed the author's link with no record of who, and `refs verify ID --author Isaac` from an agent shell verified a proposal in the author's name. `ai/rules.md` tells agents these refuse them. | tooling `session-delete-agent`; refs `drop-agent`, `verify-agent-as-person` |
| 9 | `loom refs add` files any PDF under any citekey with no identity check; the author's store already holds the wrong paper for `olsson_LogarithmicGeometryAlgebraic2003` (it is *Logarithmic Geometry and Moduli*, by Abramovich et al.), and nothing reports it. | refs `add-wrong-pdf` |
| 10 | `loom ai refresh` prints "AI draft is already up to date" when the refresh hit a conflict (its `--json` says `conflicts: [dm-0002]`), exit 0, so an agent loops; `loom adopt` says "No changes to incorporate" while a prose change waits behind `--document-changes`. | tooling `ai-refresh-conflict`; records `adopt-after` |
| 11 | `loom status` shows conflicted ids as positional keys (`drafting/main.tex#remark:1`), never the word "conflicted", and ends on a clean summary; `loom live`, which created the conflict, says nothing. | records `status-after-live` |
| 12 | `loom refs overview FRAGMENT` picks one of the matching works at random (`next(iter(set))`) and does not say which; successive runs printed different papers. | refs `overview-fragment-*` |

## Part three: revisions to the terminal principles

### What the study says about T1–T6

The six principles held up: every failure they name was found many times over, and no failure of output shape was found that they miss. The study suggests sharpening four of them, adding two about output, and a separate set for the shape of the command line, which T1–T6 were never meant to cover and which carries most of what is structurally wrong.

Measured against them (the per-command grades are in the appendices):

- **T1** fails on about a third of the commands that report. `status`, `lint`, `check`, `doctor`, `build`, `refs build`, `refs coverage`, `upgrade` and `sync publish` all print the verdict last; `check` on the author's quilt prints `ok drafting/draft4.tex` and then `check: FAILED`, the reason being 279 lines of stderr.
- **T2** fails wherever there is a list: `lint` prints 280 ungrouped lines with one error 88 times, `refs coverage` one sentence 27 times, `doctor` the same fix line under nine tools, and `refs build` the "second document" line once per document (the report that began this study). The exception is `refs build`'s own `blocked` section, which groups, counts and names one command per group, and is the model.
- **T3** is the principle loom follows best and fails in the most dangerous way: five pieces of advice name a command that does nothing in that state (part four, section D).
- **T4** fails nearly everywhere: storage paths, 12- to 64-character hashes, truncated citekeys, and implementation words (`froze`, `adopts`, `offered`, `mechanical`, `fragment`, `own-text-changed`, `Identity test`, `Recorded: … (ledger line N)`).
- **T5** fails on width more than on arithmetic: lines reach 322 (`status`), 531 (`lint`), 627 (`refs grep`) and 1,397 (`refs overview`) columns. Where it fails on arithmetic it misleads: `status --stale` says "1 stale of 1 accepted" when three are accepted, `refs build` counts every entry as "resolved", and `refs map`'s parts do not add up to the works.
- **T6** fails without exception: no command reports progress, and nothing in `src/loom` could. On the author's quilt the silences were `build --force` 955 s, `refs build --force` 228 s, `review` 106 to 145 s, `serve` start 63 s, `check` 65 s, `accept` (one key) 54 s, `ai orient` 51 s, `lint` 43 s and `status` 14 to 37 s.

### Proposed revisions to T1–T6

- **T1, add:** a success that leaves work undone says so. "No changes to incorporate" while a change waits, and "already up to date" over a conflict, are verdicts that are false.
- **T2, add:** sort by what matters to the reader, the author's own results before the cited works', and say what was left out (`… and 85 more`). In `status`, `lint` and `search`, the digests of other people's papers drown the author's 64 results.
- **T3, revise:** every problem names a next command *that works in that state*. Five commands advise one that silently does nothing (`refs map` for a work with no PDF, `refs add` with its arguments reversed, editing a `.bib` that loom never re-reads, `refs verify` to clear a finding it does not clear, `loom session watch` to get an answer). A suggested command is tested, in the state that prompts it.
- **T5, add:** an identifier is never truncated. `refs coverage` cut citekeys at 43 characters and three rows became indistinguishable; a long name goes last on its line, or the line wraps.
- **T6, revise:** first make it fast; then make what is still slow show that it is alive. A command a person runs many times a day (`status`, `lint`, `accept`, `ai orient`) should not need a progress line.

### Two new output principles

- **T7. Say only what happened.** Output describes what the command did and nothing it did not: no "source (candidate …)" for a fetch that did not happen, no "Identity test: pass" over a quilt left broken, no "wrote" for a skipped file, and a dry run marked as one on every line. This is V3, *claim only what is known*, for the terminal.
- **T8. Machine output carries what the text carries.** Every command that reports offers `--json`; its JSON holds everything the text says (not a thinner subset); and stdout stays pure on failure as on success. Today 56 of 91 commands have no `--json`, `refs build --json` drops the blocked groups and both handoff lists, and `refs propose --json` prints 72 lines of page text to stdout when its check fails.

### A new set: the command line itself

These are about the command line's shape rather than what one command prints, so they would form their own set in Chapter 1, appended after C as 1.2 provides (the letter K, for commands, is unused).

- **K1. One action, one command, one name.** No aliases and no two commands for one act; a step of a pipeline is a flag of the pipeline, not a command of its own; a refusal is a help line, not a command. (`downstream`/`unravel`/`reach`/`pop`; `delete`/`rm`/`remove`; `ai start`/`session new`; `review`/`build`; `refs build`'s five steps as five commands.)
- **K2. One idea, one flag, one meaning.** A flag means the same thing on every command, and an idea has one flag. (`--as` is a person on six commands and a new name on three; `--why` and `--reason`; `--author` and `--as` for identity; `--to` a file on nine commands and a link's target on one; `--resolve` consent on two commands and "mark resolved" on a third; `--force` with five meanings.)
- **K3. Refuse what is not understood.** Every argument is validated before anything runs, and an unknown key, work, engine, date or value exits 2 by name, as 12.1 says. (`--engine troff`, `--before yesterday`, `--keys nope-9999`, `--severity huge`, `--work typo` are all accepted, several with exit 0 and a wrong result.)
- **K4. A command does what its name says and nothing more.** A command that reads never writes, a command that prints a patch never records one, a refusal leaves no trace, and a dry run touches nothing. (`revert` records; `fork` and `atomize --key` write before the patch is applied; refused `refs build`s append to the bibliography; `stamp` does bibliography housekeeping.)
- **K5. Guard by consequence, uniformly.** Every act that is the author's, or that destroys, refuses an agent identity the same way and asks before destroying; the guard is on the act, not on the command that happens to perform it. (Part two, defect 8.)
- **K6. The help is a map of the work.** `loom --help` groups commands by the task they serve, puts the person's commands first, marks the agent's and the maintenance commands as such, and never lists an alias. (Today: 43 entries, 7 aliases and 3 refusals among them, alphabetical, descriptions cut mid-sentence.)
- **K7. One thing, one name, everywhere.** The command line, the viewer and the book call a thing the same: the viewer's Library is the CLI's `refs`, the book's reference layer and the store's `digests/`; an agent's copy is also an "AI draft", `drafting-ai/` and `draft --ai`; a withdrawn annotation is "discard", "withdrawn" and "discarded" in three places.

## Part four: the deficiencies

Every deficiency found, grouped by kind. The principle each breaks is named; "—" marks one that no principle, old or proposed, covers, and "K" or "T7–T8" one that only a proposed principle does. Evidence is in the appendices under the command named.

### A. Correctness and data loss

The twelve defects of part two, and:

| # | deficiency | principle |
|---|---|---|
| A13 | `fork` and `atomize --key` write node files and a history line before the author applies the printed patch; repeated `fork` runs leave orphan nodes that `loom rm` then refuses to remove. | K4 |
| A14 | `fork --json` is an unannounced dry run showing an id it neither writes nor reserves. | K4, T7 |
| A15 | `adopt` accepted an older preview token after a newer preview and incorporated the older selection. | — |
| A16 | `annotate KEY` with no message files an empty annotation, exit 0; `annotate --batch` is not atomic, and its error does not say the first lines were kept. | K3, T7 |
| A17 | Two `--closure`s disagree: `deps --closure` is the statement-only closure (one key for `dm-0003`), `source --closure` adds proof dependencies (four), and the help of `source` says "exactly the statements". | K2 |
| A18 | Acceptance is per reviewer and nothing says so: `status` shows "0 accepted" while `downstream` lists acceptances by another reviewer. | T7 |
| A19 | Mechanical extraction results are stored as `verified`, and `refs why` says "transcription verified" for 3,140 results no person read. | T7, K7 |
| A20 | `refs discard` on a discarded result succeeds again and replaces the reason `propose` returns; on a verified result it suggests `refs drop --work`, which drops the whole work. | K4, T3 |
| A21 | `refs fetch` remembers no title-check discard, so `refs build` offers the same three discarded sources on every run. | — |
| A22 | `ai check` attributes writes by modification time, so a fresh copy of a quilt gave 57 "agent wrote outside run" errors; a clone, a checkout, `upgrade` or the author's own edits trip it the same way. | — |
| A23 | `upgrade` overwrites an edited `loom.sty` without a word, ignores an edited `CLAUDE.md` without reporting it, and offers no dry run. | K4, T7 |
| A24 | Two serves on one quilt are allowed and retrigger each other's rebuilds; a running `serve` rebuilds on every file `refs build` writes, competing with it. | — |
| A25 | `refs locate`'s viewer link trusts the process id in `serve.json` and pointed a copied quilt at the author's real server. | — |
| A26 | `check --bundles all` fails on the shipped demo: bundles use the default document's preamble, so a result in `outline.tex` (`dm-0006`, a conjecture) cannot compile. | — |
| A27 | `refs page` labels page 19 of Manolache "Preliminaries" though it holds Construction 3.6; `refs grep`'s section labels include `[6 Uy1]` and `[0 H*(F),]`. | — |
| A28 | Two spellings of one work (citekey `manolache_VirtualPullbacks2012`, result prefix `manolacheVirtualPullbacks2012`) and no command maps one to the other. | K7 |

### B. Silence and speed

| # | deficiency | principle |
|---|---|---|
| B1 | `display_span` re-tokenises a file per key; on the author's quilt it is 32 of 35 s of `status` and 47.5 s of one profiled 51.6 s run, and the root of most silences below. | T6 |
| B2 | No command reports progress; there is no progress code in `src/loom`. | T6 |
| B3 | Silences on the author's quilt: `build --force` 955 s, `refs build --force` 228 s, `review` 106–145 s, `serve` start 63 s, `check` 65 s, `accept` 54 s for one key, `ai orient` 51 s on every call, `compile` 54 s, `lint` 43 s, `status` 14–37 s, `refs verify` 21–71 s after its output. | T6 |
| B4 | Every command scans the whole quilt before printing, 1.3–5 s even for `refs path`; `refs verify` scans twice. | T6 |
| B5 | The build cache key includes loom's own code in a checkout, so any loom change re-renders all 4,143 fragments. | — |
| B6 | Reshaping commands (`atomize`, `inline`, `linearize`) are 10 s silent even on the demo. | T6 |

### C. Output shape

| # | deficiency | principle |
|---|---|---|
| C1 | Verdict last: `status`, `lint`, `check`, `doctor`, `build`, `refs build`, `refs coverage`, `refs match`, `refs verify`, `adopt`, `import`, `init --from` (verdict on line 14 of 21), `upgrade`, `agent check`, `ai annotations`, `ai check`, `sync publish`, `sync status`. | T1 |
| C2 | Ungrouped repetition: `lint` (280 lines; one error 88 times; some locations printed twice), `build` and `check` (139 errors, some printed four times), `refs coverage` (one sentence 27 times), `refs match` (one reason 9 times), `doctor` (one fix line 9 times), `refs build` (one line per sibling document), `ai check` (57 identical errors), `ai init` (17–19 `wrote` lines). | T2 |
| C3 | Digests drown the author's results: in `status` 80 digest rows come before the author's 64, all 144 saying `draft`; `lint`'s 88 duplicate-id errors are all in other people's digests and never say so. | T2 |
| C4 | Unsorted lists: `status` rows, `downstream` references, `search` (`rem-2.10` before `rem-2.4`). | T2 |
| C5 | Lines too wide: `status` 322, `lint` 531, `check` 339, `refs grep` 627, `refs coverage` 298–400, `refs overview` 1,397, `agent check` 513, `sync prepare` 305, `doctor` 143 (a path column), `adopt --json` 1,618. | T5 |
| C6 | Identifiers truncated: citekeys at 43 characters in `refs coverage`, result ids at 58 in `refs find`, filenames in `refs ingest`, the work key `SiebertPuncturedLogarith`, titles as raw LaTeX cut mid-command in `status` and `search` (`{\cite[Definition 3.1, p.~1]{Calloway1`). | T4, T5 |
| C7 | Counts that do not add up or say what they count: `status --stale` "1 stale of 1 accepted" (three accepted), `status --loose` "6 loose" under 8 rows, `refs build` "resolved 77 entries" (every entry), "fetched 52" and "extracted 52" with fetching off, `refs map` parts short of the total, `refs recheck` "2 re-read" with 3,140 skipped uncounted, `refs find` "53 of 76 digested", `import` counting the whole quilt as the paper's, `build` "4089 nodes" with `nodes/` empty. | T5 |
| C8 | Columns collide: `refs coverage` `6preprint`, `refs find` `mechanicallevel 3`, `refs match` on a 45-character key. | T5 |
| C9 | Implementation words: `froze`, `adopts`, `offered`, `mechanical`, `level`, `fragment(s)`, `keys`, `nodes`, `own-text-changed`, `via transitive`, `ledger:`, `Identity test: pass (pdftotext identical)`, `Recorded: … (ledger line N)`, `snapshots: 1 written, 1 already present`, `Resolving closure`, "bundle" (a withdrawn noun) in `source` and `compile`, `refs/loom/publication`, 12- to 64-character hashes in `adopt`, `history`, `sync`, `refs forget`. | T4 |
| C10 | Storage paths in output: `refs add`, `refs path`, `refs propose` ("checked against digests/storage/doi/…/src/main.tex" when the user typed `main.tex`), `review` ("build/manifest.json published"), `ai check`, `stamp`. | T4 |
| C11 | `ERROR:` and `Error:` both in use; diagnostic codes with and without the `loom:` prefix (`dangling-link`, `duplicate-id`, `unreachable`). | K7 |
| C12 | Compile failures name no location: `FAILED drafting/main.tex: ! Undefined control sequence.` names no macro, file, line or log. | T3, T4 |
| C13 | `init` and `import` write their summary to stderr and leave stdout empty, against 12.1. | T8 |
| C14 | Dates and times without context: `session next` shows `HH:MM` across days; `downstream` shows raw ISO timestamps. | T4 |

### D. Advice that fails

| # | deficiency | principle |
|---|---|---|
| D1 | "run `loom refs map X`" (from `page`, `locate`, `grep` and lint) for a work with no PDF; `map` then prints "0 mapped … 0 failed", exit 0. | T3 |
| D2 | `refs resolve`'s "add the field to your own bibliography entry": `digests/bibliography.bib` is append-only and never re-reads the author's `.bib`, so the edit never arrives and the lint stays. | T3 |
| D3 | `refs recheck`'s "loom refs verify what still holds": re-verifying does not clear the finding. | T3 |
| D4 | `digest extract`'s refusal names `loom refs add <FILE> CITEKEY`, arguments reversed; the command fails. | T3 |
| D5 | `refs build`'s "build --fetch gets it from arXiv" for sources the title check discards on every fetch (A21). | T3 |
| D6 | `session send`'s "Start one with: loom session watch"; watching answers nothing. | T3 |
| D7 | A rejected `sync publish --push` repeats git's "use git pull" (the command is `loom sync fetch`), then prints "Done.". | T3 |
| D8 | `agent check`'s "fill in ai/ai-config.toml": no command creates that file, and `ai init` does not. | T3 |
| D9 | `adopt`'s "refresh Incoming" names a viewer screen, not a command. | T3, T4 |
| D10 | Next steps missing where they are needed: `status` (a stale row names no `loom accept`), `ai drafts` (no `loom ai refresh`), `refs add` of a PDF (no `map`), `refs build`'s "needs an agent 18" (no command lists them), `refs coverage`'s "loom refs verify ID" (no ids), `new` (no `\input` hint), `search` for a number before a compile (no compile command), `sync fetch`/`prepare`/`publish` (none names the next), `upgrade`'s `.new` files, the outside-a-quilt error (no `loom init`), a busy port in `serve` (no `--port`). | T3 |

### E. The command surface

| # | deficiency | principle |
|---|---|---|
| E1 | Four names for one report: `downstream`, `unravel`, `reach`, `pop`, listed as four commands; the book makes `unravel` canonical, the listing leads with `downstream`. | K1 |
| E2 | Three commands that only refuse: `delete`, `rm`, `remove`, with a literal `<ID>` placeholder and advice ("do it yourself with rm") that is wrong for a result inside a document. | K1, T3 |
| E3 | `review` is `loom build` with another summary line; `check --no-compile` is `lint` on stderr without locations. | K1 |
| E4 | Five flatteners: `source DOC` (prints), `linearize` (writes, supersedes), `inline` (writes, does not supersede: A6), `deloom` (strips loom), `history show --plain`. | K1 |
| E5 | `ai start` and `ai name` duplicate `session new` and `session rename`, with different output and argument shapes. | K1 |
| E6 | `session say` and `session send` write to one inbox, split by speaker; a person is refused `say` while an agent may `send`. | K1 |
| E7 | Two incorporation paths in `sync`: `patch` → apply → commit → `incorporated` (unchecked; A2) and `prepare` → `git apply` → `finish` (checked). | K1, K5 |
| E8 | Three AI setups, none complete: `init --ai` only at creation, `ai init` writes no launcher config and refuses once `ai/` exists, `upgrade` adds nothing. | K1 |
| E9 | "check" means three things: `loom check` (CI), `ai check` (an mtime audit), `agent check` (the launcher), and `doctor` and `agent check` disagree about one state. | K1, K7 |
| E10 | `history` takes words, not subcommands: `show`, `restore`, `verify` and a key share one argument, so a typo becomes "no such key", flags are ignored outside their word, and per-word help is impossible. | K6 |
| E11 | `status`, `review`, `lint`, `check`, `doctor` overlap without a stated division; `build` is not needed by a person who runs `serve`, and the help never says so. | K1, K6 |
| E12 | `stamp` and `accept` both "record this text now"; the names do not separate a history stamp from a mathematical acceptance. | K7 |
| E13 | `link` (a viewer link) and `refs link` (a relation between results) are one word for two acts. | K7 |
| E14 | `search`, `refs find` and `refs grep` search three disjoint scopes and do not point to each other. | K1 |
| E15 | `refs build` duplicates `refs scan`, `refs resolve`, `refs fetch`, `refs map` and `digest extract`, and the parts select differently (`fetch` "nothing to fetch", `build` "3 works could be fetched"). | K1 |
| E16 | Three intake commands with three matching policies: `refs add` (none), `refs ingest` (two signals), `refs scan` (a document's own identifier); none maps what it files. | K1 |
| E17 | Four overlapping "what is left" lists: `refs build`, `refs match`, `refs coverage`, lint. | K1 |
| E18 | Six ways to say no in `refs`: `discard`, `drop`, `unlink`, `forget`, `unreadable`, `cite --reject`. | K1 |
| E19 | No command lists pending proposals, pending citation suggestions or the works that "need an agent"; the author cannot get a proposal's id from the command line. | — |
| E20 | Misnamed commands: `refs cite` does not cite, `refs match` does not match, `refs drop`'s help says "the store is safe to delete" of a command that deletes records. | K7 |
| E21 | `refs` and `digest` split one workflow between two groups; `digest extract` has flags `refs build` lacks (`--engine`, `--no-compile`). | K1 |
| E22 | Book chapter 12's description of `refs` ("Fetched works: where their artifacts are, how to add one by hand…") covers 3 of its 27 commands. | K6 |
| E23 | The sibling `…A`/`…B` entries of 8.16 are right in principle and unexplained in practice: they double `grep` hits, make `ingest` ambiguous, inflate `match` and `build`'s queues, and make a fragment name two works. | K7 |

### F. Flags and naming

| # | deficiency | principle |
|---|---|---|
| F1 | `--as` is an identity on `annotate`, `refs link` and four `session` verbs, a new id on `fork`, a citekey on `digest import`, and a hidden refusal on `adopt` (still in the generated book reference). | K2 |
| F2 | Identity is `--author` on 15 commands and `--as` on 6; `annotate` takes both; on `ai discard`, `--author` is a filter, not an identity. | K2 |
| F3 | A reason is `--why` on four commands and `--reason` on two. | K2 |
| F4 | `--to` is a required option, a positional-or-option (where `inline` silently prefers the positional), a "copy instead of diff" (`id`), a "write and echo" (`adopt`), and a link's target (`refs link`); its path rules differ (`restore` wants `drafting/X`, `deloom` says outside drafting but means outside the quilt). | K2 |
| F5 | `--resolve` gives network consent on `refs build` and `refs resolve` and marks an annotation resolved on `annotate`; the consent flags repeat their command's name (`refs fetch --fetch`). | K2 |
| F6 | `--force` has five meanings; `--all` four; `--yes` two. | K2 |
| F7 | `--session` has five meanings across 28 commands (log this call, write into, attach to, park on, rename), is validated on some and free text on others (`refs propose`, `refs link`, `refs drop`), and is ignored on `refs cite --from`. | K2 |
| F8 | A session is named five ways: `WHICH`, `SESSION`, `[RUN]`, `--session`, or the active one by default; two resolvers disagree, one reporting an ambiguous name as "no session matches", against 12.1 and DR-199. | K2 |
| F9 | A page is positional in `refs page` and `--page` in `refs locate`; a work is a fragment in `coverage` and an exact citekey elsewhere, where `--work typo` silently matches nothing. | K2, K3 |
| F10 | `refs propose` has no `--as`, though `ai/rules.md` requires it on every write; an agent proposal without `--session` is stored with an empty proposer. | K2 |
| F11 | Patches use `a/`/`b/` prefixes in `adopt` and bare paths in `revert`, `fork`, `id` and `atomize --key`. | K2 |
| F12 | About 25 options have no help text (most `status` filters, `accept --author`, `annotate --reply` and `--resolve`, `atomize --to`, `search --kind`, `id --prefix`, `ai drafts --json`). | K6 |

### G. Exit codes and validation

| # | deficiency | principle |
|---|---|---|
| G1 | Exit 1 where 12.1 says 2 (an argument naming nothing, or an environment problem): `link` with an unknown key, `revert KEY@9`, `refs why`/`verify`/`discard` with an unknown id, `refs unlink`, a bad `--local`, `refs cite` with a wrong kind, `atomize --key` repeated, `annotate --batch` with an unknown key, every `sync` environment error, `sync patch --to` an existing file, `sync documents add` a missing document, `sync incorporated` without a terminal, `agent check` in the normal unconfigured state. | K3 |
| G2 | Exit 1 where nothing is wrong: `stamp` with nothing to stamp, `delete`. | K3 |
| G3 | Exit 0 over a wrong or empty result: `build --keys nope-9999`, `compile --engine troff`, `ai discard --before yesterday`, `ai annotations --severity huge`, `refs find`/`grep --work typo`, `refs links CITEKEY`, `refs drop --work typo`, `refs recheck typo`, `digest import` leaving three lint errors, `inline` leaving conflicts. | K3, T7 |
| G4 | `status`'s help says "Never exits nonzero"; `status --explain UNKNOWN` exits 2. | T7 |
| G5 | `refs unreadable --undo` and `refs forget --undo` require `--why`, against their help; `refs forget` rejects a 5-digit hash as "neither a citekey nor a hash". | K3 |
| G6 | Conflicting flags accepted silently: `refs path --pdf --src` (last wins), `compile KEY --draft FILE` (the key is ignored), `inline SRC DEST --to OTHER` (`--to` ignored). | K3 |

### H. Machine output

| # | deficiency | principle |
|---|---|---|
| H1 | 56 of 91 commands have no `--json`, among them `accept`, `annotate`, `build`, `check`, `compile`, `import`, `init`, `review`, `source`, `link`, `upgrade`, every `sync` command and most `refs` writers. | T8 |
| H2 | Where present, `--json` means a result, an unannounced dry run (`fork`), an announced one (`atomize --key`), the raw history line (`mv`, `draft`, `linearize`), a preview (`adopt`), or a write that still records (`revert`). | T8, K2 |
| H3 | JSON thinner than the text: `refs build` (no blocked groups, no handoff lists), `refs coverage` (no `waiting`), `refs grep` (no totals), `refs find` (not grouped), `history verify` (`[]`). | T8 |
| H4 | `refs propose --json` prints 72 lines of page text to stdout when its check fails. | T8 |

### I. Help, book and code disagree

| # | deficiency | principle |
|---|---|---|
| I1 | `loom --help`: 43 entries, 7 of them aliases repeating their target's text and 3 refusals, alphabetical, no task groups, no agent marking, descriptions cut mid-sentence; bare `loom` prints it to stderr and exits 2. | K6 |
| I2 | Help that is wrong: `fork`'s FILE (it is `--in`), `adopt --json`, `inline`'s "reverse of atomize", `check`'s "milestone M3" and "bundles", `refs scan` naming the withdrawn `canonize`, `refs ingest`'s claims about `match` and two signals, `session new`'s "named after today" (it is `untitled`), `ai annotations` promising status (it shows severity), `upgrade` claiming vendor files are refreshed. | T7 |
| I3 | Book 12.1 promises ids shown with their number (`rl-0004 (Lemma 3.4)`); `status`, `deps`, `downstream` and `accept` never show one, though `search` resolves numbers after a compile. | — |
| I4 | Book 12.11 says `init --ai` is `ai init`; it is not. Book 4.8 and 9 still name `promote`. Book 8.9 and 8.9.1 put the store under `refs/`, which 8.16 says loom never writes; 8.6 names `refs/<citekey>.tex`. Book 8.14 lists two author-only `refs` commands; the code and `ai/rules.md` have four. Book 11 promises `ai refresh` an "explicit report". The generated 12.2 lists the hidden `adopt --as`. | — |

## Part five: recommendations

### 1. In this order

1. **The defects of part two**, each with a test that would have caught it. Defect 4 also needs a one-off repair: the author's quilt carries duplicate `SiebertPuncturedLogarith` entries that `loom refs forget` would stop, and the append-only bibliography needs them removed by hand once.
2. **The scan's hot spot**: cache `env_tree` per file text in `records/dependencies.py`. One change, measured before and after on the author's quilt; it should take most of the 14–145 s silences under a few seconds and leave T6 to the genuinely slow (`build`, `compile`, `refs build`).
3. **One output layer for every command**, before any command is restyled, so that T1–T8 are properties of the layer rather than of 91 call sites. A module (`loom/cli/report.py`) with: a verdict line printed first; groups with a heading, a count and sorted items, cut at a limit with `… and N more`; a next command attached to each group; widths held under 100 columns with identifiers never truncated; a progress reporter on stderr (stage, item, `n/total`, elapsed, a "still working" line after 15 s, one plain line per item when stderr is not a terminal); and `--json` produced from the same object, so the two cannot drift. Every command then builds a report and returns it.
4. **A check, like `scripts/checks/principles.py`, that runs every command** against the demo quilt in its normal and refusal cases and asserts what can be asserted: verdict on the first line, no line over 100 columns, no storage path or hash in output, exit codes from 12.1's rule, `--json` valid and pure. T6 is checked by timing the slow commands with a fake slow step.
5. **The surface (K1)**, by the map below.
6. **The flags (K2)**, by the table below.
7. **The help (K6)**, grouped by task.

### 2. The surface

| today | proposed | why |
|---|---|---|
| `downstream`, `unravel`, `reach`, `pop` | `downstream` | K1; the direction is the name `deps` already pairs with |
| `delete`, `rm`, `remove` | none; the unknown-command message for these three says why loom does not delete and names `loom downstream` | K1, E2 |
| `review` | removed: `build` does it | E3 |
| `check --no-compile` | removed: `lint` does it | E3 |
| `inline` | removed: `linearize` writes, `source DOC` prints | E4, A6 |
| `history WORDS` | `history` (list), `history KEY`, and subcommands `history show`, `history restore`, `history verify` | E10 |
| `ai start`, `ai name` | removed: `session new`, `session rename` | E5 |
| `session say`, `session send` | `session say`, for both; the author's marks attach to what a person says | E6 |
| `agent check` | `doctor --agents` (which exists) | E9 |
| `ai init` | `ai init`, which also writes `ai/ai-config.toml` and works in an existing quilt; `init --ai` calls it | E8 |
| `ai check` | removed until it can attribute a write to an agent by something other than a modification time | A22 |
| `sync incorporated`, `sync patch` | removed: `sync prepare` and `sync finish` are the checked path; `sync status --patch` prints the incoming diff | E7, A2 |
| `sync init` defaults | `--remote` and `--branch` required, and refused when the remote is the quilt's own upstream | A1 |
| `refs …` (27), `digest extract`, `digest import` | `library …` (12): part six | E15–E23 |

### 3. The flags

| idea | one flag | replaces |
|---|---|---|
| who is acting | `--as NAME` | `--author` (15 commands) and `--as` |
| a new name or id | `--name` | `--as` on `fork` and `digest import` |
| the file to write | `--to FILE`, always an option, one path rule: anywhere but the quilt's sources and its drafting directories, unless the command writes a drafting document | positional DEST, `--to` on `refs link` |
| a reason | `--why` | `--reason` |
| network consent for this run | `--online` | `--fetch`, `--resolve` as consent |
| a session | `--session`, one resolver, which names the matches when ambiguous | `WHICH`, `SESSION`, `RUN` |
| no confirmation | `--yes` | `--yes` (two meanings) |
| show without writing | `--dry-run`, on every command that writes | `--json` used as a dry run |
| machine output | `--json`, on every command that reports | — |

### 4. The help

`loom --help` in groups, each a line of what it is for, the person's commands first:

```
Start      init, import, doctor
Write      new, id, lint, status, source, search
Review     annotate, accept, deps, downstream
History    stamp, history, revert, mv, fork, linearize, deloom
Library    library (the papers you cite: part six)
Agents     draft, adopt, session, ai          (ai: commands an agent runs)
Publish    build, serve, compile, check, sync
Upkeep     upgrade, live
```

## Part six: the library, a redesign of `refs`

### What a person does

The sweep mapped the work a person does with the papers they cite onto today's commands, and the shape is five steps: **cite** (a `\cite` in a draft), **get the papers** (resolve identifiers, fetch, or file a PDF by hand), **digest them** (extraction, or an agent proposing results from the pages), **review** (verify or discard each proposal), and **use** (cite a result, search, link). A person needs about six commands for that and an agent about four more; today there are 29, and the one a person needs most, a list of what waits for them with ids, does not exist.

### The name

**`loom library`**, the viewer's word for the same thing (its Library view and route), so the command line, the viewer and the book use one name (K7). `refs` names the author's seed folder, `refs/`, which is a different thing; the book's "reference layer" and the store's `digests/` keep their meaning as the book's and the store's words.

### The commands

Twelve, in three groups: what a person runs, what an agent runs, and upkeep.

| command | does | replaces |
|---|---|---|
| `library` | The library's state, verdict first: what waits for you, grouped by the action that clears it, each with its command; what waits for an agent; proposals waiting for your review, with their ids; then one count of what is done. Takes a work name or fragment. | `refs coverage`, `refs match`, `refs build`'s report, `refs cite --list`, the waiting counts |
| `library update [WORK…]` | Gather the bibliography, look up identifiers, fetch, extract and map, with progress (stage, work, `n/total`, elapsed), then the same report as `library`. `--online` allows the network for the run; `--only STEP` runs one step; `--redo` extracts again **and keeps every verified result**. | `refs build`, `refs scan`, `refs resolve`, `refs fetch`, `refs map`, `digest extract` |
| `library add FILE… [--for WORK]` | File PDFs or LaTeX sources, or a folder of them: matched to a work by what they say (identifier, title, byline), refused with the reason when the match is weak or the PDF names another work, mapped at once. A second document for a work is filed beside it as a version of the same work. | `refs add`, `refs ingest` |
| `library review` | The queue: every proposal and citation suggestion waiting for the author, with id, work, result and page, one line each. | (nothing today) |
| `library verify ID…` | The author confirms a transcription, or accepts a citation suggestion. Author-only. | `refs verify`, `refs cite --accept` |
| `library discard ID… --why` | The author refuses one, with the reason the next proposer is told. Author-only. | `refs discard`, `refs cite --reject` |
| `library ignore WORK --why [--undo]` | Stop asking about a work: one with no document anyone can hold (today's `unreadable`), or a stored document the author deleted on purpose (today's `forget`); the target says which. Author-only. | `refs unreadable`, `refs forget` |
| `library read WORK [PAGES]` | A work's pages, its overview, or with `--where` its store directory; takes a fragment, and refuses an ambiguous one by listing the matches. | `refs page`, `refs overview`, `refs path` |
| `library search TEXT [--pages] [--work WORK]` | The digested statements; with `--pages`, the page text. `loom search` searches the author's own results and says how many more the library holds. | `refs find`, `refs grep` |
| `library why ID` | Where a result came from, its state, and who changed it. | `refs why` |
| `library propose …`, `library locate …` | The agent's tools, marked as such in the help. | `refs propose`, `refs locate` |
| `library relate FROM TO --kind --why`, `library relate --list [ID]`, `library relate --remove ID` | Typed relations between results; named so that `loom link` (a viewer link) and this no longer collide. Removal is attributed. | `refs link`, `refs links`, `refs unlink` |
| `library check` | The store's integrity: anchors re-read, a filed PDF whose first page names another work, an empty digest, a section map with garbage labels, duplicate versions. | `refs recheck`, plus checks nothing does today (A9, A27) |
| `library import PATH`, `library drop …` | Upkeep: a digest from another quilt; removing recorded results, author-only. | `digest import`, `refs drop` |

### What changes underneath

- **Extraction never deletes a verified result** (defect 3): `--redo` writes the extracted nodes and keeps every node the author verified, reporting any that the new extraction contradicts.
- **The bibliography gathering is idempotent** (defect 4): a document already offered an entry is not offered another, and the existing duplicates are reported once with the command that removes them.
- **Mechanical results are `extracted`, not `verified`** (A19), so `library why` and the viewer stop claiming a person read them.
- **Versions of one work are one work** (E23): the 8.16 decision stands — a second document is filed beside the first and never over it — but the command line and the viewer show "2 versions" of one work, a fragment names the work, and searches report a hit once with its versions.
- **A work has one name**, its citekey, everywhere a person types or reads one (A28); result ids keep their prefix, and every command takes the citekey or a fragment of it.
- **Advice is tested** (D1–D5): a work with no PDF is never told to map, and a source the title check discarded is remembered and not offered again.

### What it reads like

`library` on the author's quilt, in the shape proposed (illustrative; the counts are today's):

```
Library: 76 works cited, 52 digested. 12 need you, 18 need an agent, 2 proposals wait for review.

Need you (12)
  no document and no identifier (6)           library add FILE --for WORK, or library ignore WORK --why "…"
    Kato1989Logarithmicstruc        Logarithmic structures of Fontaine–Illusie
    stacks-project                  The Stacks Project
    …
  title did not match on fetch (3)            library add FILE --for WORK
    GrossandSiebert2022Theca        …
  wrong document on file (1)                  library add FILE --for WORK
    olsson_LogarithmicGeometryAlgebraic2003   the PDF on file is "Logarithmic Geometry and Moduli"

Proposals waiting for review (2)              library review
Need an agent (18)                            works with pages and no digest: an agent runs ingest mode
```

And `library update`, while it runs (stderr in a terminal, one line rewriting itself):

```
update  extract  7/18  ranganathan_InvitationEnumerativeGeometry   compiling   0:42
```

### What it costs

Every `refs` and `digest` reference changes: book chapter 8, 11.8, 12, the mode templates and `ai/rules.md` with their demo copies, arras's write-API names where they say `refs`, and the tests. No compatibility layer, by the standing rule that no quilt outside the fixtures depends on the old names. A plan for it would build the output layer of part five first, since `library`'s report is the first consumer of it, then the commands, then the book.

## What works and must be kept

- **Refusals that name the blocker and the flag that clears it**: `accept --force`, `linearize --fork`/`--keep-shared`, `deloom --keep-*`, `id --fix-anchoring`, `mv` never overwriting, `stamp`'s duplicate-name refusal, `refs fetch`'s consent refusal naming both the config line and the one-run flag. Part three's T3 is these, generalised.
- **`refs build`'s `blocked` section**: grouped by cause, counted, one command per group, cut at twelve with a pointer. The model for every list.
- **`lint --nodes`' `fix:` lines** and **`doctor`'s ok/warn/fail model** with a fix line and an exact JSON shape: the model for every diagnostic, once the verdict moves to the top.
- **The agent identity refusal**, which names the marker, the flag and an example; **`session say`'s link checking**; **empty states that name a command** (`session list`, `ai drafts`).
- **`refs propose`'s guards**: the quotation check that prints the page, the level-one gate, the `--local` grammar, the gloss detector, the discard reason returned to the next proposer.
- **Clean `--json` stdout** wherever it exists and succeeds; **errors that list the valid choices** (`history show`'s landmarks, `new`'s taxa); **"Did you mean …?"** for a typo; **plain `init`'s `next:` line**, which every writer should copy; **`serve`'s one line per change**; **sub-second answers on the demo**, which part five's hot-spot fix should bring to real quilts.

## Appendices

- [`cli-study/records.md`](cli-study/records.md) — records, review, history and reshaping: the per-command grades and findings.
- [`cli-study/tooling.md`](cli-study/tooling.md) — doctor, build, check, compile, serve, upgrade, agent, ai, session, sync and the root.
- [`cli-study/refs.md`](cli-study/refs.md) — `refs` and `digest`.

The 788 transcripts were made in a scratch directory of the session that ran the study and are not kept in the repository; every finding above names the command and case, so each can be reproduced on a copy of the quilt.

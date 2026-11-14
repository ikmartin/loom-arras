# v0.1 study: Review and Problems

The author's complaint: Review is opaque, clunky, buggy and in the way; he expects it to show mathematics that changed and edits AI proposed, it does both poorly and shows much else; Problems is mostly loom's misbehaviour, not issues in the quilt. This report measures that on real quilts, plays both sides of every write through the real server, and proposes Review as two lists.

## Method

Copies of `~/quilts/quant`, `~/quilts/relloc` and `demos/showcase` were served by this checkout's loom (71621877) on ports 48001-48003, with `XDG_CONFIG_HOME` in scratch holding the author's reviewer name, and their agent configuration neutralised (`.mcp.json`, `.cursor/mcp.json`, `.codex/config.toml`, `.gemini/settings.json` renamed in the quant copy). The relloc census from the served copy (`--no-compile`) is identical, row for row, to the manifest the author's own server published today at 14:01, which was copied with the quilt. Agent acts used the CLI with `--as "Trial Agent"`; person acts used the HTTP write API with the token and headers the viewer sends (`scripts/api.py`). Screenshots are 1440 px wide, full page, under `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/review/shots/` (named below by file name only, all in that directory). All three servers were stopped; `lsof -i tcp:48000-48049` is empty.

## Findings

| id | finding | weight | rec |
|---|---|---|---|
| REV-1 | What Review counts is 33% (quant) and 72% (relloc) mathematics-changed or AI-proposed; of the rows it draws, 17% and 13%. Quant's "proposed edits" are an agent's grading comments; relloc's "changed mathematics" is one adoption from nine days ago, with no change shown | blocks | fix: two lists (section 5) |
| REV-2 | Keep is not undoable in one step anywhere, and neither is Discard of an in-place edit | blocks | fix |
| REV-3 | Keep can write a suggested edit twice (reproduced), and a write recorded only as `apply` leaves a pending row for text already in the file (quant, live) | blocks | fix (CORE-5) |
| REV-4 | An unplaced suggested edit cannot be discarded in the viewer; a waiting edit is stranded for good when the one it waits on is kept | blocks | fix |
| REV-5 | In-place edits carry no author; with the default settings an agent's in-place change to mathematics is invisible | blocks | fix (defaults, attribution) |
| REV-6 | Problems shows no problem of the person's own LaTeX on any of the three quilts; the one such problem that matters, a failed compile, is not on it at all | blocks | fix |
| REV-7 | One change is listed twice with two different acts; keeping an edit on an accepted block makes it a second item to accept | hurts | fix |
| REV-8 | "Waiting to be accepted" is loom's bookkeeping: 100 stale taken-in rows, 64 never-accepted, a false "Nothing is being worked on", and a demo whose acceptances nobody else sees | hurts | remove, redefine |
| REV-9 | Rows speak loom: edit ids, `#proof:8` keys, commands, raw `{\color{red}` | hurts | fix |
| REV-10 | A kept edit lost to an editor's stale save is silent | hurts | fix |
| REV-11 | Agent copies duplicate the proposed-edit channel and appear in two sections at once | hurts | hide (CORE-9) |
| REV-12 | Keep takes 1.6-4.8 s on showcase, 2.2 s on quant and 14-18 s on relloc; Review shows a file edit 10-15 s after it | hurts | fix (CORE-18) |
| REV-13 | Accept needs a compile and a reviewer name, and refuses incomplete blocks it lists | hurts | fix |
| REV-14 | Markdown has no proposed-edit route; a new empty file is listed as an empty change; Keep into a file no document reaches keeps no version | hurts | fix |
| REV-15 | A long replacement is drawn as the whole old text struck and the whole new text underlined, not by words | hurts | fix |
| REV-16 | A save while Keep runs: not reproduced in 8 tries, but the window exists in the code | cosmetic | fix (cheap) |
| REV-17 | An agent's untyped annotation, such as a question, is in no Review list | cosmetic | keep (it belongs in the document) |

## 1. Census of Review

Sections today (`arras/src/lib/review/sections.ts:33-37`): Your Changes (waiting to be accepted, then changes to keep, plus a To do toggle), Proposed Changes, Problems, Library, The Record (Versions, Sessions, Everything recorded).

### quant (a learner's quilt: lessons in Markdown, homework solutions in LaTeX)

Column counts: Your Changes 30, Problems 57, Proposed none, Library none. Shots: `quant-review.png`, `quant-review-top.png`, `quant-review_proposed.png`, `quant-review_problems.png`, `quant-review_library.png`, `quant-review_record.png`, `quant-review_record_sessions.png`, `quant-review_record_acts.png`.

| section | rows | kind | class |
|---|---|---|---|
| Your Changes › Waiting to be accepted | 0, and the box "Nothing is being worked on. No document is being worked on, so there are no blocks to review" | NoDrafts (`routes/review/+page.svelte:232`); quant's proofs are unattached, so it has no blocks | O, and false |
| Your Changes › Changes to keep | 29 ready suggested edits on `hwk1.tex`, all by one agent | each inserts a `{\color{red}…}` comment into the learner's answer: feedback sent as an edit | E (in kind) |
| | 1 `taken` suggested edit on `hwk2.tex`, "keeping it records it kept" | loom wrote it on 11-12 18:16 (an `apply` line in the ledger) and never recorded it kept | O (a loom bug, REV-3) |
| Your Changes › To do (toggle) | 24 open annotations from the agent | hints on the solutions | O |
| Proposed | 0 | | |
| Problems | 57 errors, all `loom:unattached-proof`; 2 remarks | valid LaTeX (a proof after `\item`) | O |
| Library | 18 works | | O |
| The Record | 9 versions of hwk1 (nine "Before applying a suggested edit", the take-twice incident), 3 sessions, 54 acts | | O |

### relloc (the author's paper)

Column counts: Your Changes 100, Proposed 4, Problems 33, Library 4. Shots: `relloc-review.png`, `relloc-review-top.png`, `relloc-review_proposed.png`, `relloc-review_problems.png`, `relloc-review_library.png`, `relloc-review_record*.png`.

| section | rows | kind | class |
|---|---|---|---|
| Your Changes › Waiting to be accepted | 100 "Taken in from the copy examples-shared" in `examples.tex` | blocks adopted on 11-04 (ledger step 4) and never accepted; 31 refused "Can't be accepted yet: it is marked incomplete"; a row shows a title and a Read link, never the change | M, stale |
| | 64 "Never accepted" in `draft5.tex`, folded | the author has never accepted anything: 0 of 2,011 keys have a row | O |
| Your Changes › Changes to keep | 0 | `track_edits` off, no suggested edits | |
| Proposed | 2 agent copies: examples-shared (219 to take or leave) and toric-application (28) | | E |
| | 2 works with proposed results (42 and 30) | library verification | O |
| Problems | 33 counted warnings (28 `unmatched-postnote`, and one each of `agent-permissions-stale`, `dependency-cycle`, `macro-shadowed`, `missing-proof`, `needs-classification`); 521 folded (copy 364, works 59, remarks 98) | section 2 | O |
| Library | 37 works, 4 "need you" | | O |
| The Record | 6 steps, 2 sessions, 33 acts | | O |

### showcase (the demo testers open), before the trials

Your Changes 2 (E: two Referee Agent suggestions), Problems 3 (O), Proposed 1 (O: a work's proposed result). "Waiting to be accepted" lists all 25 blocks as never accepted, because the committed `state.toml` holds 14 acceptances by "The loom showcase" and acceptance is per reviewer: no tester will ever see the demo's accepted states.

### The fraction

By what the column counts: quant 29 of 87 (33%) are M or E, and all 29 are comments delivered through the edit channel, because annotations on quant's unattached proofs detach when text above moves (quant findings 29, 32); relloc 102 of 141 (72%), of which the 100 M rows are one nine-day-old adoption that shows no change and a third of which cannot be accepted. By rows drawn across Review: quant 29 of 173 (17%), relloc 102 of 800 (13%) (To do, behind its toggle, left out). On no quilt does Review show a single statement whose text an agent changed with the change drawn.

The O kinds, whether the person can act, whether they would miss them:

| O kind | act possible | missed? | goes to |
|---|---|---|---|
| Never accepted (folded backlog) | Accept each | no | away |
| Taken in from a copy or pull | Accept | only if shown with the change | list 1, as changes |
| `taken` suggestion loom already wrote | Keep records it | no (bug) | away once REV-3 is fixed |
| To do (open annotations from others) | open each | no; the document's Comments list has them | the document |
| Works' proposed results | Check them | yes, in the Library | Library |
| Problems (loom's model and loom's own) | mostly a command to copy | no | section 2 |
| Library rows | many | yes, but not in Review | Library |
| Versions, sessions, everything recorded | restore, open | versions yes (they are the undo) | the document's history ▾; the rest away |

## 2. Census of Problems

Every code present on the three quilts, with counts (person / agent copy / cited works), and its class: (a) a problem in the person's own LaTeX they would recognise and can fix; (b) meaningful only in loom's model; (c) loom's own difficulty.

| code | severity | quant | relloc | showcase | class | note |
|---|---|---|---|---|---|---|
| `loom:unattached-proof` | error | 57/0/0 | | | b | a proof after `\item`; compiles |
| `loom:unmatched-postnote` | warning | | 28/36/0 | 1/1/0 | c | the digest lacks a result the citation names: loom's reading of someone else's paper |
| `loom:uses-missing` | info | | 34/230/0 | | b | |
| `loom:uses-unused` | info | | 52/44/0 | | b | |
| `loom:cites-proposed-node` | warning | | 0/19/0 | | b | |
| `loom:missing-proof` | warning | | 1/13/0 | 1 | b | a theorem whose proof comes later, or never, is a person's choice |
| `loom:dependency-cycle` | warning | | 1/7/6 | | b | possibly a real circularity; say it on the block |
| `loom:macro-shadowed` | warning | | 1/2/0 | | b | the person's `\incomplete` against loom's |
| `loom:needs-classification` | warning | | 1/0/0 | | b | |
| `loom:agent-permissions-stale` | warning | | 1 | | c | loom's own generated file lags loom |
| `loom:detached-annotation` | info | 2 | 5/8/0 | 2 | b | |
| `loom:undigested-citekey` | info | | 3/1/0 | | c | |
| `loom:unresolved-work` | info | | 3 | 1 | c | |
| `loom:annotation-types` | info | | 1 | | c | |
| `loom:unverified-locators` | warning | | 0/0/23 | | c | |
| `loom:missing-package` | warning | | 0/0/20 | | c | in a digest |
| `dangling-link` | error | | 0/4/6 | | c here | in a copy and in digests; (a) only in the person's own file |
| `duplicate-id` | error | | 0/0/4 | 1 | b here | showcase: `sh-0020` in two separate documents, which LaTeX accepts; fixes offered are `loom fork …` commands to copy |
| `loom:postnote-from-another-version` | info | | | 1/1 | c | |
| `loom:superseded-file`, `unreachable` | info | | | 1, 1 | b | |

On these three quilts the person is shown no class (a) problem. The class (a) problem a person actually has, a document that does not compile or compiles with errors, never reaches Problems: compile results travel by the stream and appear only as "did not compile" in the file tree (`arras/src/lib/manifest/compiles.svelte.ts:40`, `loom/src/loom/render/compiles.py:49`). Problems separates by owner (person, copy, work: `arras/src/lib/diagnostics.ts:125`, `loom/src/loom/scan/owners.py:142`), not by class, so loom-model codes in the person's files count as "yours" (quant's 57, relloc's 28). This confirms CORE-15 with real counts.

**Rule for what a person is shown.** Problems lists only class (a), shown on the document it concerns (a dot on the document in the tree and its toolbar) and gathered on one page reached from there, not as a Review section. Class (a) is: the document does not compile, or compiles with errors (first TeX error, file:line, from the log); undefined references and citations from the log; `missing-include`; `inclusion-cycle`; a label defined twice within one document (`duplicate-id` and `loom:duplicate-label` restricted to one document); `loom:unknown-environment`; `loom:non-utf8-source`; `dangling-link` in the person's own file. Class (b) is never a problem: where it limits a feature, the feature says so where it is (a block that cannot be accepted says why in its popup; an annotation that lost its place says so in the Comments list). Class (c) goes to a log an agent or a developer reads (`loom lint --all`, `loom doctor`, `.loom/build/diagnostics.json`); a digest's problems go to the work's page in the Library with "Digest it again". No fix is ever a command to copy.

**Graded `error` while the document compiles** (`loom/src/loom/scan/diagnostics.py:18-90`), to regrade or reclass: `loom:environment-spans-files`, `loom:line-anchoring`, `loom:unattached-proof`, `loom:reference-to-loose`, `loom:macros-unloaded`, `loom:macros-missing`, `loom:closure-failed`, `loom:citekey-slug-collision`, `loom:atomize-target-exists`, `loom:interface-version`, `loom:history-missing`, `loom:history-edited`, `loom:history-corrupt`, `loom:id-reused`, `loom:derived-id-in-person-document`, `loom:agent-document-unrecorded`, `loom:plain-id-in-agent-document`, and `duplicate-id` / `loom:duplicate-label` / `dangling-link` when the two definitions or the link are not in one document's compile. None of these stops TeX.

## 3. Trust trials

Showcase copy unless noted; "Review" means the manifest the viewer draws, read after each act, and the page where noted.

| # | act | Review afterwards | on disk | verdict |
|---|---|---|---|---|
| 1 | agent annotates sh-0002 with a question (untyped) | in no Review list; To do counts only types that stay open (`arras/src/lib/review/annotating.svelte.ts:263`) | log line | REV-17 |
| 2 | agent suggests a short, a long, and two non-overlapping edits on one paragraph | each a card, ready | none | right; the long one is drawn as all old struck then all new, though most words stand in both (`showcase-tracked-review-mid.png`) (REV-15) |
| 3 | agent suggests an edit overlapping one already waiting | "unplaced: e-2026-11-13-f2m12r, suggested before it, is on the same words; keep or discard that first" | | REV-9 |
| 4 | person edits the words a suggestion quotes | after about 10 s: "the text e-2026-11-13-6bb9n4 quotes no longer stands in sh-0002"; Keep and Discard both disabled (`arras/src/lib/review/ChangeCard.svelte:86-87`), while the API discards it fine | | REV-4, REV-9 |
| 5 | person keeps an edit, then keeps it again | the second answers 404 "no change … waits on you; `loom changes` lists them" | once | right; the wording is a command |
| 6 | HTTP Keep raced against the person's own `loom changes --keep` | one wins, the other "no change waits" | once | right in three tries |
| 7 | the API's undo of a Keep (`change-discard` with `undo`, `loom/src/loom/render/api.py:438, 463`), then a two-word edit inside the kept sentence, then Keep | row reads ready again; Keep answers "kept 1 change" | **the sentence twice** in sh-0003: "…is connected. It maps onto the sum-zero vectors when the quiver is connected." | REV-3 |
| 8 | Keep all with 6 ready and 2 waiting | kept 6; the edit that waited on a kept one is now "quotes no longer stands", with no act | right | REV-4 |
| 9 | person discards an agent's in-place edit (tracking on), then asks to undo it | undo: 404 "an in-place change discarded comes back from History"; no section is called History; The Record restores a whole version | old words back | REV-2 |
| 10 | agent edits sh-0003 in place, tracking off, block never accepted | nothing anywhere | changed | REV-5 |
| 11 | same, block accepted | "Divergence · changed since you accepted · See change", no author; the panel shows the accepted text with the moved words lit, not a difference on the text (`showcase-see-change.png`) | | partly right |
| 12 | tracking turned on in Settings (`settings-save`), then the agent drops a lemma's hypothesis ($w \geq 0$), writes a survey note, appends to README, and the person fixes a typo | four identical "Edit in the file · since your look" cards; the lemma, never accepted, is not in "Waiting to be accepted" | | REV-5 |
| 13 | agent edits an accepted block in place, tracking on | listed twice: a "changed since you accepted" row with Accept, and an "Edit in the file" card with Keep and Discard | | REV-7 |
| 14 | person keeps suggestions on an accepted block | the block becomes "changed since you accepted": a second decision about the same edit | | REV-7 |
| 15 | person accepts sh-0003, sh-0002, sh-0001 | accepted 3 of 3; needs the document compiled (`loom/src/loom/cli/review.py:47-59`) | | REV-13 |
| 16 | a kept edit undone by an editor saving its stale buffer | nothing; the record says kept | edit gone | REV-10 |
| 17 | the person saves the file 0.12-4 s into a Keep (showcase, quant, relloc; 8 tries) | | the person's line survived every time | REV-16 |
| 18 | agent makes a copy (`loom draft --ai trial --as "Trial Agent"`) and edits it | Proposed: "trial · 1 to take or leave"; the copy's diagnostics duplicate the person's | | REV-11 |
| 19 | agent suggests on an empty `.tex`; on a Markdown note | `.tex`: kept fine (quant finding 40 is fixed); the new empty file is listed as a change `'' → ''`; Markdown: "no such key: notes/plain.md" | blank.tex: no version kept, only an `apply` line | REV-14 |
| 20 | relloc: Keep of a two-word suggestion | answered after 14.1 s, 17-18 s on later tries | right | REV-12 |

Minimal reproductions:

- REV-3, double write: `loom suggest K --quote Q --after --with S --as "X Agent"`; POST `change-keep {"changes":[E]}`; POST `change-discard {"changes":[E],"undo":true}`; edit one word inside S in the file; POST `change-keep {"changes":[E]}`. S is now in the file twice. Cause: whether an edit is in already is judged from text alone (`taken_how`, `loom/src/loom/records/edits.py:406`; a text under 20 words must stand exactly, `:391`), and the `apply` line that says it was written is never read. Live instance: quant's `e-2026-11-12-e07zzr` has an `apply` line at 2026-11-12T18:16:05Z and no `kept` event, so Review offers it today as an agent's suggestion "its block reads as it taken already".
- REV-4, stranded: two suggestions where B is "after" words A replaces; Keep A; B is unplaced for good, and the viewer offers neither act on it (`ChangeCard.svelte:86-87`, `ready()` in `arras/src/lib/review/changes.ts:30`).
- REV-10: Keep E; overwrite the file with its text from before the Keep; Review is silent.
- REV-16: the code reads the file through `open_scan` (`loom/src/loom/render/api.py:426`), keeps a version (`loom/src/loom/pending.py:442`), then writes the text computed from the scan (`pending.py:448, 458`) with no check that the file is unchanged.

## 4. "Mathematics that changed"

Candidates against the three users:

| candidate | reader with no draft | explorer | proofreader | verdict |
|---|---|---|---|---|
| differs from what the person last accepted | empty: nothing is accepted | empty: relloc has 0 acceptances in a month | right, but includes their own edits | too narrow |
| differs from what the person last looked at (the look) | right for agent-written notes | right | floods with the person's own edits; needs `track_edits` | right base, wrong filter |
| changed by an agent | right | right | misses a coauthor's pull | right filter, needs attribution |
| arrived in an Overleaf pull | n/a | n/a | one source among several | a cause, not a definition |

**Recommendation.** A statement or proof, and in a Markdown file a section, whose text now differs from the text the person last saw, excluding changes the person made themselves. Computed from the look loom already keeps (`loom/src/loom/looks.py`, `.loom/looked/`), always on, cut by words (`pending.cut`) and grouped by block (`pending._blocks`). The look advances when the person marks a row Seen, keeps or discards a proposed edit, accepts a block in the viewer, and when loom itself writes; a change to a file agents may not write (`[agents] deny`) is taken to be the person's own and advances it silently; a pull or an adoption, which loom performs, does not, and is named as the cause. Attribution beyond that comes from the agent app where it can say: Claude Code can run a PostToolUse hook on Edit and Write that tells loom which file an agent wrote, which turns "not you" into "Claude Code Agent". The residual risk, an agent writing a denied file through the shell, is caught by acceptance staleness for accepted blocks and by the versions; say so in the orientation.

**A row** shows the block in place, rendered by TeX, with removed words struck and new words underlined (the Markup the document already draws, `loom/src/loom/render/pending.py`), its name and number ("Lemma 2.5 (Support)", never `#proof:8`), its document, who or what changed it when loom knows (an agent's name, "from Overleaf", "taken in from …"), when, and, for a block the person had accepted, "you had accepted it; N results rest on it". Acts: **Seen** (into the look), **Undo** (old words back, a version kept first, undoable itself). Clicking opens the document at the block in Markup, the viewer's rule that a change is read where it lives.

**Accept** means "I vouch for this block as it reads now". It costs one click in the block's popup or on a Changed row, marks the block seen as well, needs no compile and no separate reviewer name (default to the author name loom has; VIEW-14). Acceptance shows as a badge on the block in the document (accepted, or changed since accepted with its causes), not as a Review list; "never accepted" is not a state anyone is shown. For someone who never accepts: no badges, no backlog, no staleness anywhere, and the Changed list still works because it rests on the look, not on acceptance.

## 5. Review as two lists

**Changed** (section 4) and **Proposed** (below), nothing else. Each counts what waits, and opens on whichever has rows.

**Proposed: which routes survive v0.1.**

- Suggested edits: keep, as the only route. Extend them to any text file the viewer shows (a Markdown section by quote, quant finding 12), and to whole files proposed in protected folders (finding 40's workaround). This is the one channel the person can read in place, keep, discard and, after REV-2, undo.
- Agent copies: hide (CORE-9 agrees). An agent proposes a rewrite as suggested edits on the person's document, a section at a time. Agent documents of its own stay ordinary files, and their changes are Changed rows.
- In-place edits to the person's files: prevented by default, not reviewed as proposals. Where a person allows them, they are applied changes and appear in Changed with Undo, not in Proposed.

One card per suggested edit, grouped by document in document order: the block rendered in place with the edit's words struck and underlined by words (REV-15), the agent's comment, the annotation it answers, Keep and Discard, and a one-click Undo after either. An edit whose words were edited since is shown with what it was written on and keeps **Discard** ("Your text changed under it; the agent can propose it again"); a waiting edit says "after the edit above" in words, never an id. Keep all and Discard all per document stay.

**Defaults for a new quilt.** `[agents] deny` = the directories of the person's documents: `loom init --from` and `loom import` know the paper's directory, and the orientation stops listing the author's documents as editable (`loom/src/loom/assets/ai/orientation.md:30`). `[review] track_edits` disappears: the look is always kept, because Changed rests on it, and with the deny above the person's own edits do not appear. Today's template has `deny = []` and `track_edits = false` (`loom/src/loom/cli/quilt.py:39, 42`; INV-6 verified).

**Where everything else goes.**

| shown in Review today | goes to |
|---|---|
| Waiting to be accepted: changed since accepted | Changed rows, with "you had accepted it"; the badge in the document |
| Waiting to be accepted: taken in from a copy or a pull | Changed rows, caused "from Overleaf" or "taken in"; `review_origins` goes |
| Never accepted, Accepted groups | away |
| To do (annotations from others) | the document's Comments list, which has them already |
| Agent copies (Proposed) | hidden with the copy commands |
| Works' proposed results (Proposed) | the Library, under its "proposed" filter, which exists |
| Overleaf pulls | hidden unless `[sync]` is set; once taken in, Changed rows |
| Problems | the document's status and a page reached from it (section 2) |
| Library | its own place in the column, out of Review |
| The Record › Versions | the document's history ▾, which already pages and restores |
| The Record › Sessions | session items in Docs (VIEW-5) |
| The Record › Everything recorded | away from the viewer; `loom history` for a developer |

## 6. Implementation

Work packages, each owning its files; A, C, F and H can start at once and run in parallel; B follows A; D and E can run in parallel after a one-hour agreement on the card component; G comes last.

**A. Keep is safe to repeat** (Python, independent). Before writing, refuse an edit that already has an `apply` line, and judge "taken" by record first and text second; take the edit log's lock (`loom/src/loom/locks.py`) across write and record, so the CLI and the server serialise; check the file's hash at write time against the scan, and refuse in words if it moved (REV-16); make `_reopen` refuse a kept edit (B gives the real undo); when a kept edit's words are gone from its file, list it as "a kept edit is no longer in the file" (REV-10). Owns `loom/src/loom/pending.py` (`keep`), `loom/src/loom/records/edits.py` (`keep`, `taken_how`, delete the dead `apply`), `loom/src/loom/render/api.py` (`_change`, `_reopen`), `loom/src/loom/history/acts.py` (`keep_versions` keeps the raw file when no document reaches it, CORE-6). Tests: keep twice sequentially and concurrently (CLI against HTTP); reopen, edit inside, keep; crash between write and record (raise after `write_file`); file changed between scan and write; quant's `e07zzr` recorded as kept, not offered.

**B. One-step undo of Keep and Discard** (after A). A `change-undo` write: for a kept suggested edit, put its old words back where its new words still stand, else refuse in words; for a discarded in-place change, put the words back from its `undo` ledger entry (`history.acts.put_back` exists). The viewer pushes both onto its undo stack (`arras/src/lib/review/history.svelte.ts:3, 180`). Owns `loom/src/loom/pending.py` (new `unkeep`), `loom/src/loom/render/api.py`, `arras/src/lib/review/history.svelte.ts`. Tests: keep then undo restores the exact bytes; undo refused after the person edited inside; discard then undo.

**C. Problems by class** (independent). A class per code in `loom/src/loom/scan/diagnostics.py`, the regrades in section 2, a compile failure or error turned into a class (a) diagnostic from the log (`loom/src/loom/render/compiles.py`, `loom/src/loom/render/build.py:564, 612`), the class published in the manifest; the viewer filters by class (`arras/src/lib/diagnostics.ts:125`), and `arras/src/routes/review/problems/+page.svelte` shows class (a) only, with no command fixes (`arras/src/lib/components/Diagnostics.svelte`). Tests: the registry test requires a class for every code; quant, relloc and showcase show 0; a broken `\end` shows 1 with its line.

**D. The Proposed list** (viewer, light Python). Suggested edits only; Discard enabled on unplaced edits (`arras/src/lib/review/ChangeCard.svelte:86-87`); word-level marks for suggested edits (apply `pending.cut` to old and new in `loom/src/loom/render/pending.py`); messages without ids or commands (`pending.py:281-294`, the `Unplaced` strings in `records/edits.py`); names, not keys, on cards. Owns `arras/src/lib/review/ChangeCard.svelte`, `changes.ts`, `proposed.ts` (reduced to suggested edits), `arras/src/routes/review/proposed/+page.svelte` (becomes the list). Tests: the four trial cases above; keep all with one waiting.

**E. The Changed list** (Python and viewer; largest). The look always on: drop `track_edits` (`loom/src/loom/scan/quilt.py:66, 108`, `loom/src/loom/config_edit.py:37, 348`, the toggle in `arras/src/lib/shell/settings/Agents.svelte:67`), take the first look at `init`; absorb changes in denied paths (`loom/src/loom/looks.py`, `pending.in_place`); group by block and keep only statements, proofs, Markdown sections and new or removed files; Seen and Undo; accept without compile (`loom/src/loom/review_queue.py:177`, `cli/review.py:47`) and keep its in-place keep (`render/api.py:967`); drop "taken in" and "never accepted" (`review_queue.rows_for`, `loom/src/loom/review_origins.py`). Viewer: `arras/src/routes/review/+page.svelte`, `arras/src/lib/review/yourChanges.ts`, `queue.ts`, `ReviewPanel.svelte`. Tests: an agent's edit in an allowed file is listed; the person's in a denied file is not; a change to an accepted block appears once; Seen clears it; Undo restores and is undone.

**F. Defaults and routes** (independent, hours). `deny` set at `init --from` and `import` (`loom/src/loom/cli/quilt.py`, `loom/src/loom/cli/paper.py`); hide `draft --ai`, `adopt`, `ai drafts|refresh|close|reopen` and the `adopt-*` endpoints (`loom/src/loom/ai/layout.py` `AGENT_COMMANDS`, `loom/src/loom/cli/__init__.py`, `render/api.py` `CAPABILITIES`); hide sync unless `[sync]` is set; fix the orientation line. Tests: a new quilt from a paper denies its directory, and the permission files say so.

**H. Suggested edits on any shown text file** (independent). `loom suggest PATH --quote OLD --with NEW` for Markdown and other text, and a whole-file proposal for a new file; placement by quote in the file (`records/edits.py` `home`, `place`); drawn in the Markdown item (`loom/src/loom/files.py` bodies). Owns `loom/src/loom/cli/suggest.py`, the target resolution in `records/edits.py` (coordinate with A on that file: A owns `keep` and `taken_how`, H owns `home` and `place`). Tests: keep and undo on a Markdown section; a proposed new file in a denied folder.

**I. Attribution from the agent app** (optional for v0.1, after E). A Claude Code PostToolUse hook written by `loom/src/loom/ai/layout.py` that records the agent's writes, read by `pending.in_place` to name the author. Owns `ai/layout.py`, a new `loom/src/loom/records/writes.py`.

**G. Navigation** (last). Two sections in `arras/src/lib/review/sections.ts`; `arras/src/lib/shell/Column.svelte` gives the Library its own place; The Record leaves Review (`arras/src/routes/review/record/**`), Versions stays in history ▾.

**Deletable once hidden** (with CORE-9): `loom/src/loom/adopt.py`, `section_drafts.py`, `draft_lifecycle.py`, `drafts.py`, `review_origins.py`, `render/incoming.py` `attach_adoptions`, `incorporation_review.py` if sync goes too; `arras/src/lib/review/ContributionReview.svelte`, `IncomingPull.svelte`, `contribution.ts`, the copy and pull parts of `proposed.ts`, `arras/src/routes/review/record/sessions/+page.svelte`, `acts/+page.svelte`. No backwards compatibility is owed: relloc's 100 taken-in rows and its open copies simply go.

## What the 2026-11-03 panel study got right and was never built

- CH4, who made a change: in-place edits still read "Edits in the file" (`arras/src/lib/review/changes.ts:37`), with no author.
- PR1 and its pattern "show the person only what is theirs": built as a split by owner, not by class, so loom's model still counts as the person's (quant 57, relloc 28).
- PR2, fixes as terminal commands: still "COPY loom fork …" and "COPY loom library …" (showcase and relloc Problems).
- FR1, counts that mean "this waits for you": Your Changes counts 100 stale adoptions; Problems counts loom's own codes.
- CH5 and HI3, a way back from an act: versions and a restore now exist, but no act is undone in one step (REV-2).
- IN7 and IN9, refusals caused by what is not the person's: the copy channel it found unusable is still the route behind relloc's 219 waiting changes.

What it got right and was built: Accept in the viewer, Keep and Discard on suggestions, per-change cutting by words, Markup and Final in the document, versions at each act with restore, Problems titled in words.

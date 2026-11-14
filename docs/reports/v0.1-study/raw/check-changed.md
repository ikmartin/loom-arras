# v0.1 study: checking "Changed"

The claim under test (`review.md` section 4 and package E; `cuts.md` CUT-7): a list of the statements, proofs and Markdown sections whose text differs from what the person last saw, not counting the person's own edits, can be computed from loom's existing look, always on, with changes in agent-denied files taken as the person's and agent-owned places left out, without flooding the person and at a bearable cost on a large quilt. This check replays a month of the author's two real quilts and simulates the list at every moment he plausibly looked.

## Method

Copies of `~/quilts/relloc` (998 MB) and `~/quilts/quant` (211 MB) in `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/check-changed/`, `.loom/serve.json` deleted first; loom from this checkout (71621877) with `XDG_CONFIG_HOME` in scratch; ports 48501-48503, all stopped. Scripts are in that directory's `scripts/`, outputs in `data/`.

- **States.** For every file the look covers (and, as a variant, the agent copies), the sequence of its texts from 10-12 to 11-13 was rebuilt from: loom's history texts (versions, `loom write` before/after, looks, tick `from` texts), the agent app's own transcripts (Claude Code; every Edit, MultiEdit and Write replayed on the text, every shell command kept), 24 hand-made snapshots of the copy in relloc's session and build directories, and the files as they are now (`scripts/replay.py`). What the replayed agent edits did not explain between two known texts is a residual; each residual was classified by the loom acts and agent shell commands in its interval, and then checked by hand.
- **Units.** A LaTeX statement (any `\newtheorem` environment of the quilt) or proof, keyed by label; LaTeX prose between blocks, by the section above it; a Markdown section from a heading to the next heading; any other file whole; a new or removed file (`scripts/units.py`). Changes are cut by lines, not words: a block spans lines, so the units touched agree with `pending.cut`, and the copy's diff takes seconds instead of a quarter of a minute (CHG-2).
- **Looks.** Strict: the person's own acts in loom's records (ledger acts under either of his two names, his annotations, notes, keeps, looks taken), clustered into sittings 30 minutes apart, plus one final look on 11-13 at 21:30Z: 8 looks in relloc, 11 in quant, the first of each being the baseline for "since seen". Loose: the same plus his prompts to agents in the agent app: 27 and 21 looks.
- **Variants.** Deny rule: a change in a denied file is the person's and hidden ("person"), or shown ("shown"). Copies: `.loom/copies/` out or in. Unit: U1 statements and proofs only; U2 the design (U1, Markdown sections, new and removed files); U3 all prose (U2, LaTeX prose, other text files). Baseline: M1 since last seen, the person marking everything seen at each look; M2 never cleared since the first look loom actually took (relloc 11-03, quant 11-07); since last accepted (below). Rows that loom wrote on the person's word (a kept suggested edit, a tick, Settings) move the look and are never rows; an adoption is a row, as the design says.

## Findings

| id | finding | weight |
|---|---|---|
| CHG-1 | The look is cheap where it looks: 13 files and 440 KB in relloc, 32 files and 435 KB in quant. In-process on relloc, `in_place` takes 22 ms and tracking adds 0.2-0.26 s to a build of 10-16 s, once the reviewer name is not looked up by subprocess (CHG-13). The quilt's 1 GB is under `.loom/`, which the look never walks | holds |
| CHG-2 | A look that covered the agent copy would cost 12-21 s of word diff (26-50 s of `in_place` under load) on every rebuild while the copy differs from it (612 KB, 248 states in a month). Agent-owned places must stay out, as they are today by construction, and no file should be diffed whole by words | condition |
| CHG-3 | Over the month the person's own edits fell only in denied files (relloc `draft5.tex` 10-12..14; quant's three solutions), and no agent wrote a denied file (none of the 1,438 Edit and Write calls in either quilt, failed ones included, targeted a denied path; the denied files' texts show no change but the person's and loom's). The deny rule hid 100% of the person's own edits and 0 of the agents' | holds here |
| CHG-4 | Without the copy, relloc's Changed is empty at 5 of 7 looks; its one long list (102 rows) is 100 blocks the person himself adopted plus 2 agent files. The mathematics agents rewrote (231 blocks of the copy between 11-04 and 11-13) appears only if copies are in, and then as one list of 333 rows | the claim's purpose is not met for relloc |
| CHG-5 | Quant's Changed holds only agent-written Markdown: median 1 row per look, worst 231 rows at one look, of which 140 are sections of one course outline, 58 lesson sections, 15 syllabus sections and 13 new files, all from one revision the learner asked for. With statements and proofs only, quant's list is empty at every look | floods |
| CHG-6 | Never cleared, the list stands at 233 (quant) and 102 (relloc) rows from the day of the big change on; relloc saw no person act in loom for 9 days (11-04..11-13) while agents rewrote the copy | condition |
| CHG-7 | Grouping removes the flood: one row per file for Markdown and other files, and one row for a file where more than 20 blocks moved at once, gives a worst list of 3 rows (relloc), 12 (relloc with copies), 23 (quant; 11 without the 12 new figures) | fix |
| CHG-8 | "Since last accepted" shows nothing on either quilt (0 acceptances); as a baseline it would count the person's own edits, since acceptance has no author: quant 40-85 rows, mostly his own proofs | do not use |
| CHG-9 | From loom's records alone, 95% of change events in relloc's open files and 24% in quant's carry their author (a loom act, or a denied path); the rest, and all 1,413 in the copy, are agents' shell scripts and file writes loom never sees | limits |
| CHG-10 | Attribution by coincidence with agent activity does not work: within 10 minutes of the person's own exactly-timed acts an agent was active 71% of the time in quant and 39% in relloc (79% and 78% within 30 minutes) | do not use |
| CHG-11 | The agent app's file-tool writes (what a PostToolUse hook on Edit and Write sees) are 42% of quant's agent change events and 15% of relloc's copy; the rest are shell scripts (`python3 - <<EOF ... open(p,'w')`), and relloc's 10-12 and 10-27/28 changes came from agents whose transcripts are not on this machine | limits |
| CHG-12 | Markdown sections are an unstable unit: section sizes run from 312 B to 22.8 KB (median 487 B); research-state is one section, the outline 156. In 102 Markdown changes, 16 rewrote headings: 128 renamed, 146 added, 79 removed. Loom's heading ids are slugs of the words, so every rename is a new section | fix the unit |
| CHG-13 | Both quilts hold two looks under two names of the same person (one from `git config`, one from loom's config), so which look a list reads depends on how the process resolved the name. Without a loom author name the name is resolved by a `git config` subprocess on every call: 609 calls per relloc build untracked, 1,215 tracked; the 606 extra calls cost 10-16 s per rebuild as measured here, about 2 s at an assumed 3 ms a call | fix first |
| CHG-14 | An adoption shows as 100 rows, one per block the person himself chose to take in (11-04 19:01Z), each a whole new block with nothing in it marked as changed | fix (one row) |

## 1. The look today

From the code (`loom/src/loom/looks.py`, `pending.py`, `render/pending.py`, `render/serve.py`, `render/api.py`, `tasks.py`):

- **What it stores.** `.loom/looked/<slug(reviewer)>.json` = `{who, when, files: {path: sha256}}`, each text stored once in `.loom/history/texts/` (`looks.take`, `looks.py:94`). It covers every shown text file: UTF-8, at most 1 MB (`files.TEXT_LIMIT`), LaTeX's auxiliary files left out (`looks.open_texts`, `looks.py:73`). Any path with a component starting with `.` is not shown (`files.Shown._hidden_name`, `files.py:171`), so `.loom/copies/`, `.loom/sessions/` and `.loom/build/` are never in it.
- **When it moves.** Taken whole: when `loom serve` starts and the reviewer has none (`serve.py:898-905`); when tracking is turned on in Settings (`api.py:632-636`); on "keep all" with no look yet (`api.py:430`, `cli/changes_cmd.py:82`). Moved in part: keeping an in-place change (`pending._into_look`, `pending.py:433`); after loom writes a kept suggested edit (`pending.absorb`, `:480`); on the viewer's Accept, for changes inside the accepted blocks only (`pending.keep_accepted`, `:650`, from `api.py:970`); on a tick (`looks.take_line`, `tasks.py:140`). Discarding an in-place change writes the look's words back into the file. Nothing moves it on a save.
- **What a build pays.** `pending.in_place` (`pending.py:190`): read the look, read every shown text file, hash it, read the look's text of each changed file, `pending.cut` each by words (difflib over words, `autojunk=False`), and find the statement or proof holding each change (`_blocks`, environments and proofs only, so a Markdown change has no block). `render/pending.attach_pending` then writes a patch and a row per change into the manifest, and `kept_own` runs for each node (606 calls on relloc).
- **What `[review] track_edits` switches on.** `pending.look_texts` returns nothing when it is off (`pending.py:151`), so no in-place change is listed, `changes_since` is not published (`render/pending.py:499`), `serve` takes no first look, and Settings takes one when it is turned on. Off, an existing look is ignored but kept. Both quilts have it off today and hold looks from when it was on.

**Cost on relloc** (13 open files, 440 KB; the look of 11-03 under the git name, 11 in-place changes in 4 files, one of them the 212 KB adoption):

| measure | tracking off | tracking on |
|---|---|---|
| `open_texts` / `look_texts` / `in_place` / patches, in-process | | 1.6 / 2.3 / 21.7 / 8.6 ms |
| look functions inside one `loom build --no-compile` (timers around `in_place`, `kept_own`, `attach_pending`) | 66-75 ms (`in_place` called 607 times, returns at once) | 270-330 ms |
| wall clock, `loom build --no-compile`, 4 alternating pairs | 15.1, 12.0, 13.0, 16.5 s | 14.2, 11.9, 19.9, 15.5 s |
| `loom serve --no-compile`, one-word edit in `drafting/examples.tex` to a new manifest, 2 servers x 4 edits each | 9.5, 9.6, 27.8, 25.4; 24.8, 13.7, 12.4, 12.8 s (median 13.3) | 16.6, 17.0, 16.0, 20.8; 11.9, 9.5, 8.3, 10.7 s (median 14.0) |
| the same build with no loom author name configured (the git fallback): `git config user.name` subprocesses | 609 calls, 17.8 s of a 46 s build | 1,215 calls, 34.5 s of a 60 s build |

The machine's load average was 6-38 throughout (other sessions), which swamps the wall-clock rows: they bound the build, they do not resolve the look. The in-process rows do: tracking adds 0.2-0.26 s to a build of 10-16 s when loom has an author name. Without one, the reviewer name is resolved by spawning `git config user.name` once per call (`scan/quilt.py:214`, uncached), and `pending.in_place` resolves it once per node through `kept_own`: tracking doubles the calls from 609 to 1,215 per relloc build. Each call took 16-27 ms at the load of these runs, so the git calls alone were 18 s and 35 s; the 606 calls tracking adds cost 10-16 s at that rate, and still about 2 s at an assumed 3 ms a call on a quiet machine. The author's newest look in quant (11-12) is named by the git fallback, so this is his setup (CHG-13).

**CHG-2: the copy.** `pending.cut` on the copy, between hand-made snapshots: snapshot 2 to 3 (337 KB to 614 KB, 512 changes) 21.0 s; 8 to 9 (733 KB to 611 KB, 78 changes) 17.8 s; 0 to 10 (263 KB to 612 KB, 715 changes) 12.0 s. `pending.in_place` with the copy added to a look (`scripts/copy_look_cost.py`, tracking on): with the look's copy text at snapshot 9 (11-10), 36.4 s, 19 changes, 3 blocks; at snapshot 2 (11-09), 25.8 s, 69 changes, 202 blocks; at snapshot 0 (11-09), 49.7 s, 715 changes, 209 blocks (load average 20-38 during these runs). Every rebuild pays it again until the person marks the copy seen, and each agent save to the copy triggers a rebuild.

## 2. Replay: what the records allow

| | relloc | quant |
|---|---|---|
| ledger entries (loom's acts) | 32: 22 `loom write` (20 of the research state, 2 digest overviews), 2 copies, 2 stamps, 1 each of import, adopt, keep, close, reopen, move | 55: 20 `loom write`, 13 stamps, 12 applies of suggested edits, 6 ticks, 4 keeps |
| texts of earlier versions | at those acts only (237 texts) | at those acts only (114 texts) |
| agent app transcripts used | 118 files, 415 MB; 10,704 tool calls, 110 prompts by the author | 7 files, 48 MB; 1,066 tool calls, 68 prompts |
| other evidence | 24 snapshots of the copy made by agents by hand; file times | file times |
| states rebuilt | 285 across 15 files: 248 of the copy, 20 of the research state, 1-2 of each other file | 165 across 32 files |
| agent edits that did not place on the replayed text | 30 of 249 (a shell script had changed the text in between) | 1 of 91 |

Who made each change, counted as change events (a unit touched by one transition):

| | events | person, own editor | loom on the person's word | loom itself | agent through loom | agent file tool | agent shell script | agent, seen only by coincidence |
|---|---|---|---|---|---|---|---|---|
| relloc open files | 225 | 6 (`draft5.tex`, 10-12..14) | 118 (the adoption) | 66 (ids written by `import`) | 23 (`loom write`) | 12 | 0 | 0 |
| quant open files | 925 | 89 (82 in the three solutions, 5 ticks, 2 Settings) | 115 (kept suggested edits) | 0 | 21 | 303 | 348 | 49 |
| relloc copy | 1,413 | 0 | 0 | 0 | 0 | 211 | 911 | 291 |

Every residual was resolved by inspection: quant's link rewrite in five lessons on 11-05 (`quilt:refs/…pdf` to `cited:work:…`) is an agent's Python loop over `course/lessons/*.md` that never names a file; relloc's copy changes on 10-12 (17:20-22:51Z) and 10-27/28 coincide with "Referee Agent", "Simplify Agent" and "Audit Agent" messages in loom's own session inbox, from an agent app whose transcript is not on this machine; the 10-12..14 changes in `draft5.tex` are the person's (18 word-level differences from the paper as received besides loom's ids, 4 of them in preamble comments, one a notation an agent had searched for at 17:19 on 10-12; saved on 10-14, when no agent ran). Nine agent shell commands open a quant solution and seventy name `drafting/`; each writes a test copy elsewhere, none the denied file.

## 3. What Changed would have shown

Rows per look, design deny rule (denied changes are the person's), strict looks. Typical is the median; "zero" counts looks with an empty list.

| quilt | copies | unit | baseline | looks | median | p90 | worst | empty | worst made of |
|---|---|---|---|---|---|---|---|---|---|
| relloc | out | U1 statements and proofs | since seen | 7 | 0 | 0 | 100 | 6 | the adoption |
| relloc | out | U2 design | since seen | 7 | 0 | 1 | 102 | 5 | adoption 100, research state 1, new note 1 |
| relloc | out | U3 all prose | since seen | 7 | 0 | 1 | 116 | 5 | adoption 114 (100 blocks, 14 prose), 2 agent |
| relloc | out | U2 | never cleared | 2 | 51 | | 102 | 1 | as above, from 11-04 on |
| relloc | in | U1 | since seen | 7 | 12 | 88 | 331 | 1 | copy 231 blocks by agents, adoption 100 |
| relloc | in | U2 | since seen | 7 | 7 | 25 | 333 | 1 | copy 231 (21 removed), adoption 100, 2 agent |
| relloc | in | U3 | since seen | 7 | 11 | 31 | 373 | 0 | copy 259, adoption 114 |
| relloc | in | U2 | never cleared | 2 | 167 | | 333 | 1 | as above |
| quant | none | U1 | since seen | 10 | 0 | 0 | 0 | 10 | nothing: agents never touch the learner's LaTeX |
| quant | none | U2 | since seen | 10 | 1 | 2 | 231 | 3 | outline 140, lessons 58, syllabus 15, orientation 4, research state 1, 13 new files |
| quant | none | U3 | since seen | 10 | 1 | 2 | 231 | 3 | same |
| quant | none | U2 | never cleared | 11 | 232 | 233 | 233 | 1 | same, from 11-12 on |

With the loose looks (his prompts to agents too), since seen, U2: relloc 26 looks, median 0, worst 101; with copies median 1, p90 50, worst 383 (11-11 05:57Z, all copy blocks after one night of fixer agents); quant 20 looks, median 0.5, p90 44, worst 188.

**The person's own edits in the list**, by deny rule (strict, since seen):

| quilt | unit | deny = the person's (design) | deny = shown |
|---|---|---|---|
| relloc | U1/U2 | 0 rows at every look | 1 row (10-15) |
| quant | U1 | 0 | 26 (11-09), 3 (11-11), 35 (11-13: 7 proofs he wrote, 28 duplicates of the Keep-twice bug he deleted) |
| quant | U2 | 0 | 66 rows over 10 looks; worst look is still the agents' 231 |

So the flood the review feared from the person's own edits does not occur here, because the deny list covered every file he edits; the flood that does occur is agents' bulk work cut fine (CHG-5, CHG-7) and the adoption (CHG-14).

**Since last accepted.** Neither quilt has an acceptance, so the list is empty. Taken as "since the first look, whoever changed it" (acceptance staleness has no author), it is quant U1 40-85 rows (26 of the person's own proofs, 45 kept by the person, 14 whose key my replay lost), relloc U1 100.

**Grouped** (one row per Markdown or other file; one row per file where more than 20 blocks changed between looks, else one per block): relloc worst 3 rows (12 with copies), quant worst 23 (11 if new figure SVGs are not rows), never cleared 3 and 24.

## 4. Whose edit was it

| source | what it can know | relloc open files | quant open files | relloc copy |
|---|---|---|---|---|
| S1 loom's own write records (adopt, keep, tick, `loom write`, import) | exact, with the actor's name | 207 of 225 (92%) | 143 of 925 (15%) | 0 |
| S2 path denied to agents | file-level; right only while the agent app enforces deny and no agent writes there by shell | 6 (3%), all right | 82 (9%), all right | 0 |
| S3 coincidence with loom-side agent records (session messages, annotations, edits, ledger) within 10 min | a guess | 12 (5%) | 696 (75%) | 1,376 (97%) |
| S4 the agent app's file-tool report (PostToolUse on Edit/Write/MultiEdit) | exact for those tools; blind to shell writes | 12 (5%) | 303 (33%) | 211 (15%) |
| nothing | | 0 | 0-4 | 37 (3%) |

S3 was right on every change it claimed here only because the person never edited an undenied file; measured directly, an agent was active within 10 minutes of 24 of the person's 34 timed acts in quant and 7 of 18 in relloc (within 30 minutes: 27 and 14), so in a quilt where he edits an allowed file, S3 names an agent for most of his own edits (CHG-10). S1 plus S2, what loom can stand behind, cover 95% of relloc's open files, 24% of quant's, and none of the copy (CHG-9). If everything unattributed is shown as "changed outside loom", the list is exactly the design rows above: on these quilts every such row was an agent's, so nothing of the person's leaks in, but no row says which agent.

What the agent app could add: Claude Code's transcript names every Edit and Write and every shell command, but a shell command does not say which files it wrote, and shell scripts made 64% of the agents' change events in the copy and 55% in quant's open files (48% named the file, 7% looped over a glob). A PostToolUse hook on Bash would have to diff the tree before and after each command to attribute those. The agents of 10-12 and 10-27/28 in relloc left no transcript here at all. Codex left none on this machine (no `~/.codex/sessions`), so CUT-7's first condition (an app that ignores deny) was not exercised by this history; nothing in it shows deny was ever crossed.

## 5. The learner's case

What Changed shows in quant: the agent's lessons, outline, syllabus, orientation, findings and research state, as Markdown sections, and the figures it generates as new files. The learner's own work (three LaTeX solution sets in `course/solutions/`, denied) never appears, and neither does the agent's grading: the 29 open suggested edits on `hwk1.tex` belong to Proposed, and the 11 kept ones moved the look when loom wrote them. Ticks move the look too. Statements and proofs alone would show the learner nothing, ever: his LaTeX has 57 proofs and no theorem environment, and agents never write it.

Sections as a unit (`scripts/md_sections.py`, final texts and every Markdown transition):

- **Identification.** Loom has no Markdown section today: in-place changes in Markdown have no block (`pending._blocks` takes environments and proofs), and headings get ids only when drawn, as a slug of their words with a counter for repeats (`files._rewriter`, `files.py:293`). A section is therefore "from a heading to the next", keyed by that slug.
- **Sizes.** 273 sections in 16 files: median 487 bytes, 90th percentile 2.9 KB, largest 22.8 KB. The research state is one section (9.7 KB in quant, 14.3 KB in relloc); `findings.md` is one 22.8 KB section of numbered items; the course outline is 156 sections. The same act, an agent revising a file, is 1 row in one file and 140 in another.
- **Renames.** Of 102 Markdown transitions, 16 changed headings: 128 renamed, 146 added, 79 removed. Most renames strip numbering (`E.01 Pandas fluency` to `Pandas fluency`, `D.01 Derivatives markets; …` to `Derivatives markets; …`); two swap places (`S.19` and `S.21`). Keyed by slug, each rename reads as one section removed and another added, so a numbering pass over the outline would list every section twice.
- **Workable unit.** A Markdown file as the row, with its changed sections listed inside it and the change drawn in place, keyed by position and text rather than by heading words; a section is a place inside the row, not a row.

## 6. Verdict

**Holds, with changes to the definition.** The look is the right base and costs about a quarter of a second a build on the person's files; the deny rule did exactly what it should on these quilts (every one of the person's edits hidden, no agent edit hidden). As specified, the list floods for reasons the claim did not anticipate: an agent's bulk rewrite of Markdown cut into heading sections (231 rows at one look in quant), an adoption cut into its blocks (100 rows in relloc), and a person who does not clear it (233 and 102 rows standing). On relloc the mathematics agents actually changed lives in the copy, which the look excludes, so Changed shows almost nothing of it.

**The definition to build.**

- A row is a **file** whose text differs from the person's look, excluding files whose every change is absorbed (below). Inside a LaTeX file the row lists the statements and proofs changed (by name and number), drawn in place in Markup; inside a Markdown or other text file, the changed passages. A file where more than 20 blocks or a whole new file arrived is one row that says so ("taken in 100 results from the copy", "new file, 9 sections").
- Computed from the look as it is (`looks.py`, `pending.in_place`), always on, first look at `init`, over shown files only, so `.loom/` (copies, sessions, build) stays out; cut by lines first and by words only inside a changed block, so no file costs a 600 KB word diff.
- Absorbed silently: changes in `[agents] deny` paths; loom's writes on the person's word (Keep, discard, tick, Settings, Accept), as today. Not absorbed: adoptions and pulls, with their cause; `loom write` by an agent, with the agent's name from the ledger.
- Authorship shown only from S1 (loom's records) and S2 (deny); every other row says "changed outside loom" with no name, unless an agent-app hook (S4) names it. Never S3.
- Seen per row and "Seen all", and an agent's AI document (the copy) listed as a document in the tree with its own change count, not as rows.

**Measured cost:** 22 ms for `in_place`, 0.2-0.26 s added to each build on relloc's open files with an author name configured (without one, 606 extra `git config` subprocesses per build, CHG-13); a 600 KB agent file inside the look would cost 12-21 s per rebuild by words.

**Worst list it would have produced on these quilts** (grouped as above, since seen, strict looks): relloc 3 rows (the adoption as one, the research state, a new note); quant 23 rows on 11-12 (11 Markdown files of one revision, 12 new figures; 11 if figures are not rows). Ungrouped, the same looks are 102 and 231 rows.

**What must be true first.**

1. One look per person: resolve the reviewer name once per process and never fall back silently to `git config` (CHG-13), and merge the two looks each quilt has.
2. `[agents] deny` covers every directory the person edits, at `init` and `import` (both quilts already do), and the orientation says that a change there is taken as the person's.
3. Agent-owned places stay in dot directories or are listed for exclusion (CUT-7 condition 2 holds by construction today; Lean's `lean/` would not).
4. "Seen all" exists, or the list is useless after the first busy day (CHG-6).

**Unknowable without the agent app's cooperation.** Who changed an allowed file when the person and an agent both work (an agent was active within 30 minutes of 78-79% of his acts); which agent; whether an agent wrote a denied file through the shell, which no app's deny list stops (Claude Code's covers its Edit and Write tools only); everything an app without hooks or transcripts does (relloc's 10-12 and 10-27/28 agents). Loom sees saves; only the app knows who saved.

## Files

Scripts and data under `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/check-changed/`: `scripts/extract_agent.py` (transcripts to tool calls), `replay.py`, `units.py`, `simulate.py`, `attribution.py`, `coincide.py`, `mech.py`, `md_sections.py`, `profile_look.py`, `time_build.py`, `edit_loop.py`, `copy_look_cost.py`, `reviewer_cost.py`; `data/sim-relloc.json` and `data/sim-quant.json` hold every series. The quilt copies there are scratch; nothing under `~/quilts` or `~/notes` was written.

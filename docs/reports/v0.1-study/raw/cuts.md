# v0.1 study, third wave: the cuts under attack

Adversarial review of the hiding and removal proposed by the first two waves. Checkout `v0.1-study` at 71621877. Real use was counted read-only from `~/quilts/relloc/.loom` and `~/quilts/quant/.loom` (ledger, annotation and edit logs, session inboxes and `run.log`s, copies, configs); nothing there was written. Trials ran on hand-made copies under `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/cuts/` (`showcase/`, and `lin/`, a linear quilt made from `demos/showcase/drafting/main.tex` with a three-line `config.toml`, since `loom init` refuses an agent's shell), with `XDG_CONFIG_HOME` in scratch. No server was started. Person-only acts (Keep, adopt) were not performed; filing, placement, patches and lint were enough to settle each question.

Caveat on counts: `run.log` records only calls made with `--session` or over MCP (`loom/src/loom/cli/build_cmds.py:39-53`, `loom/src/loom/mcp/server.py:332-346`), so a command missing from it may still have been used. Records under the actor "The synthetic quilt" are the author's (quant findings item 25) and are counted as his.

## Verdicts at a glance

| # | cut | verdict | the reason in one line |
|---|---|---|---|
| CUT-1 | agent copies hidden, suggested edits the only route | **do not cut**; take adoption out of Review instead | it is the author's main channel for AI-written mathematics (relloc: a 3,122-line AI document, 361 of 404 annotations, 97 named agents in four days), and suggested edits as built cannot carry (ii), (iii) or (iv) |
| CUT-2 | node surgery hidden | **cut, but narrower and with two fixes first** | `reshape/` is shared by import, compile, manifest and adopt; only atomize/fork/linearize/live/deloom/revert/restore-to go; keep `id --next`, `new --print`, `import`, `mv` |
| CUT-3 | sessions hidden, one per connection | **hide the footer and picker only**; keep transcripts readable and sessions agent-named | every report goes to `session say`; 144 transcript messages since 11-06; per-connection binding would split relloc's four-day session and does not exist on the shell route |
| CUT-4 | graph view hidden | **cut as proposed**, keep the context lists | no agent text, plan or journey needs the drawing; ContextItem's rest-on / used-by lists do |
| CUT-5 | Overleaf publish hidden, read-only mirror | **cut as proposed** | no use in either quilt; the mirror reuses fetch/incorporate |
| CUT-6 | shell variant hidden, MCP only | **hide the choice, keep the variant** | relloc runs on the shell variant alone; MCP signs one name per server, so 97 subagents could not be told apart |
| CUT-7 | Review as Changed + Proposed; acceptance a badge; Record/Sessions/Library/Problems out; track_edits always; deny the person's directories | **cut, with four conditions** | both real quilts already deny their document directories and have zero acceptances; but Codex ignores deny, always-on tracking would flood with agent files, Lean needs a card in Proposed, and Everything recorded is the only undo of a discard today |
| CUT-8 | Problems shows LaTeX problems only | **cut for the person, keep every code for agents** | audit's uses-ledger and Lean's closure rest on model codes; fork fixes must be reworded |
| CUT-9 | static, host-neutral viewer machinery; fixture x3 | **cut after the dev proxy exists**; keep one fixture | `npm run dev` runs on the static fixture today |
| CUT-10 | tests trimmed | **cut as proposed, after the sequence safety test** | keep the `unchanged` assertion per case and the generator check at merge |
| CUT-11 | history documents moved out of the search path | **cut as proposed**; leave the live plan in place | four pointer lines and 235 citations to update |
| CUT-12 | other proposed cuts | mostly as proposed; do not merge modes, do not remove transcripts | table below |
| CUT-13 | unproposed candidates | cut desktop-chat/LM Studio/Zed/JetBrains entries, relations, unused agent tools; keep research state and types | table below |
| CUT-14 | defects found while testing | section-body suggestion deletes the heading; agent files count as the person's | below |

## Real use in the author's two quilts

| record | relloc (paper; shell variant; `deny = ["drafting/"]`) | quant (learning; MCP; `deny = ["course/solutions/"]`) |
|---|---|---|
| agent copies | 2 open: `examples-shared.tex` 3,122 lines, 483 environments, 171 `-ai` ids, last written 11-10; `toric-application.tex` (section copy of draft5's "Punctured Stable Maps"), 524 lines. One adoption of 100 keys with prose and order (11-04); 219 + 28 changes waiting | none |
| annotations | 404 created; **361 on copies**; 270 created and 206 resolved on 11-09..11; ~30 author names, all agents but 5 by the author; 312 resolved by agents on copies | 31 created 11-09..12 (28 by the agent, 3 by the author), plus 125 before the 0.30 migration |
| suggested edits | none | 35 created (29 on 11-13), 4 kept, 1 withdrawn |
| sessions and transcripts | 2 sessions; 60 + 121 messages; the second (11-09..13) from 97 distinct agent names; 11 messages by the author in October; that session's directory holds ~400 files: scripts, briefs, fix logs and 10 hand-made snapshots of the copy | 3 sessions, 41 messages, 34 of them 11-04..13 |
| research state and overviews (`loom write`) | 19 state writes 11-03..11, 2 overviews | 20 state writes |
| acceptance | 0 (no `state.toml`) | 0 |
| versions | 2 automatic (before adopt, after keep) | 13 automatic before Keep; 1 named ("stamp1") |
| node surgery | `import` once (10-12), `mv` once (11-03, the copy into `.loom/copies/`), `loom id` 4 times on the copy; no atomize, fork, linearize, live, deloom | none |
| Overleaf sync | none | none |
| library | 27 digests, 72 proposals on 2 works, 0 relations | 0 digests, 0 relations |
| ticks | — | 6 |

The research state in relloc says, in its first paragraph, that new mathematics "is worked out in `drafting/examples.tex`, whose working copy is the agent document `.loom/copies/examples-shared.tex`", and on 2026-11-13 the author asked an agent for "a reading guide to the long document", meaning the copy.

## CUT-1: agent copies

Proposed: hide `loom draft --ai`, adopt, refresh, `.loom/copies/`; suggested edits become the only route (CORE-9, `review.md` section 5 and F).

**a. Code.** Copies run through about 30 Python files (`adopt.py`, `drafts.py`, `section_drafts.py`, `draft_lifecycle.py`, `reshape/copy.py`, `render/incoming.py`, `render/api.py`, `render/compare.py`, `render/watch.py`, `scan/owners.py`, `scan/source.py`, `scan/lint.py`, `history/ledger.py`, `review_queue.py`, `agents.py`, `tex/runner.py` among them) and some 38 arras files mention copies or adoption. `loom draft` is in `cli/history_cmds.py` and uses `reshape/copy.plan_copy` (`cli/history_cmds.py:138`); `adopt` uses `reshape/linearize.flatten`, `reshape/copy.derived_key` and `reshape/fork.plan_fork` (`adopt.py:20, 493-494`), so CUT-2 and CUT-1 are entangled. Ownership is what keeps AI text apart from the person's: a copy's keys are owned `copy` (`scan/owners.py`), carry `-ai` ids, and are protected only by being in `.loom/copies/`, which every agent may write (`agents.py:41`; `.claude/settings.json` allows `Edit(.loom/copies/**)`).

**b. What agents are told.** The routing to copies is normative, not incidental: rules.md's table sends "changes that only work together" to an agent document (`assets/ai/rules.md:42`), and the test is spelled out: "A change that only makes sense with others, or that moves, merges, splits or reorders results, is an agent document" (`rules.md:52`). Full privilege on copies, including closing others' findings, is `orientation.md:29` and `rules.md:73`. Draft mode writes into an agent document by default (`modes/draft.md:17-18`); flow sends structural changes there (`modes/flow.md:33`); simplify sends merge-or-delete there (`modes/simplify.md:22`); review files findings on copies too (`modes/review.md:27`); `ai drafts` is in "Where to look" (`orientation.md:53`). Hiding the commands without rewriting these sends every agent into a refused command, after which, in a quilt that denies the person's directories, its only outlet is an ordinary file.

**c. Real use.** The heaviest of any feature measured (table above). Relloc's revision of 11-09..13 is a pipeline the copy makes possible: referees (R1-R8, B1-B6) annotate the copy, fixer agents (X1-X6, S06-S14, Final Fix) change it and resolve the findings, drift referees and last checks re-read it, with ten snapshots taken by hand between passes.

**d. Journeys and works-well.** inventory marks copies E and P; quant uses none. The orientation call that works well (`quant-findings.md` section 2) prints the copy rules.

**e. Planned work.** attach.md C4 lists "agent document" as a row kind of the activity page; Lean (`lean.md` R3-R8) does not touch copies; review.md's replacement assumes agent documents "stay ordinary files, and their changes are Changed rows".

**What replaces a copy, tested on `lin/`.** A suggested edit lives in one key's own text: the quote must be found in `Records.own_pieces` of that key (`cli/suggest.py:95-99`), and a section key's own text is only its heading.

| case | with suggested edits as built | carries it? |
|---|---|---|
| (i) long rewrite of a section | One edit per block: a quote spanning the theorem, its proof and the corollary on the section key is "quote not found"; the section's "body" is its heading, and replacing it **deletes `\section{…}\label{sh-0300}`** (CUT-14). The person reads N unrelated cards; `compile --with` previews one edit for one key. | partly: block by block, no unit, no preview |
| (ii) changes that only make sense together | A remark proposed by edit A and an edit D citing it (`\ref{sh-0402}`) are filed independently; keeping D alone leaves a dangling reference. An edit on text that A proposes is refused ("no such key: sh-0402"), and `loom annotate` on an edit id is "no such key", so no agent can referee or fix a proposal before the person sees it. | no |
| (iii) moving or reordering results | Three edits: delete the lemma, delete its proof, insert both after another proof. `--after` with no quote lands inside the proof environment; the insertion works only by quoting `\end{proof}`, which `rules.md:61` tells agents not to do. Keeping the insertion without the deletions duplicates `\label{sh-0006}`; keeping only the deletions loses the lemma. | no |
| (iv) an AI drafting a whole document | An ordinary file needs nothing from loom when it stands alone (quant's lessons). If it builds on the paper, loom's graph resolves `\ref{sh-0009}` across documents but lint raises `loom:reference-to-loose` at **error** severity twice, TeX prints `??`, and the file's keys are listed as the person's ("keys of yours", owner `person`) with `person` diagnostics. Under always-on tracking every block it writes is a Changed row. A whole-file proposal into a denied folder is not built (review.md H). | partly; and the AI/person boundary disappears |

**Verdict: do not cut.** The copy is what keeps AI-written mathematics in the paper's context (its preamble, its ids, its graph) while marking it as the AI's; removing it removes the only way to do (ii)-(iv) and to run any multi-pass AI review before the person decides. What review.md rightly objects to is the person-side backlog, not the workspace. Instead:

- Keep `draft --ai` (with `--section`), `ai drafts`, `ai refresh`, `-ai` ids and copy ownership for agents.
- Take copies out of Review's Proposed list; show each as an "AI document" in the tree with its state, readable and annotatable like any document; put "Take into my document…" (today's adoption, unchanged underneath) on that document only. Hide `ai close/reopen` from people.
- Keep the rules' test (`rules.md:52`) as the line between the two routes; it is the clean boundary the author asked for.
- Cost of this: hours in the viewer (`arras/src/routes/review/proposed/+page.svelte`, `proposed.ts`, `DraftActions.svelte`). Cost of the proposed hide: hours plus a rewrite of `rules.md:42, 52, 73`, `orientation.md:29, 53`, four modes and the permission files, and relloc's open document is stranded. Cost to bring back after removal (2,900 lines, 45 files, their tests): days, and agents retaught.

## CUT-2: node surgery

Proposed: hide atomize, fork, linearize, nest, deloom, new, id, live, mv, revert, history restore, import "and their kin" (CORE-10, inventory section 3, about 3,000 lines).

**a. Code.** `reshape/` is not surgery alone. `linearize.flatten` is used by compile (`tex/assemble.py:34`, `tex/bundle.py:42`), the manifest (`render/manifest.py:334`), versions (`history/steps.py:232`), copies (`drafts.py:13`, `section_drafts.py:114`, `adopt.py:20`); `importer.closure_of` by the digest extractor (`digest/extract.py:17`), `refs/sourcemap.py:50` and `sync.py:22`; `canon.plan_draft`/`apply_import` is `import` and `init --from` (`cli/paper.py:27, 256`); `ids.unified_diff` by `pending.py:670`, `records/edits.py:375`, `since.py:350`, `doctor.py:591`; `fork.conflict_fixes` by lint and review (`cli/lint_cmd.py:19`, `cli/review.py:1394`), whose fix text is a `loom fork …` command; `fork.plan_fork` by adopt (`adopt.py:494`). Removable without touching anything kept: `atomize.py` (383), `deloom.py` (174), the CLI bodies of atomize, fork, linearize (`_linearize`, 168), live, revert, `history restore --to`, quilt-wide stamp; roughly 1,200-1,500 lines, not 3,000.

**b. Agents.** `id` and `new` are agent commands (`ai/layout.py:23-24`); draft mode prescribes `loom id --next` and `loom new --print` (`modes/draft.md:17, 20`); the orientation says `loom id` tags an untagged environment (`orientation.md:16`).

**c. Real use.** No atomize, fork, linearize, live or deloom in either ledger. `import` once (relloc's start), `mv` once (the author moving the copy), `loom id` four times on the copy.

**d. Journeys.** `import`/`init --from` is how a proofreader's paper gets in (inventory 2a asks for an agent tool or a viewer action for it). The showcase that testers open is atomized and shows `duplicate-id` on `sh-0020` with `loom fork` fixes to copy (review.md section 2).

**e. Planned work.** Lean pins formal stamps to a key (`lean.md` section 3, R3); a lemma with the author's own `\label{thm:x}` has only a positional key (`install.md` INST-11), so stable keys need `id` (through a suggested edit) or INST-11's fix. The Overleaf mirror does not import.

**Verdict: cut, narrower, after two fixes.** Hide from people and agents: atomize, fork, linearize, live, deloom, revert, `history restore --to`, quilt-wide stamp. Keep: `import` and `init --from` (make them reachable without a terminal), `mv` hidden from help but present (records follow a rename; otherwise every annotation on the file detaches, INST-11), `id --next` and `new --print` for agents, `id FILE` hidden from people. First: reword `conflict_fixes` so lint stops offering `loom fork` (or the hidden command is printed as a fix), and remove the forked `sh-0020` from the showcase or make the showcase linear. Hide: hours. Remove: a day once the fixes are in; bring back from git in hours.

## CUT-3: sessions and transcripts

Proposed: hide in the viewer, one session per agent connection (CORE-12 "remove", VIEW-4, ATT-8, inventory section 3).

**a. Code.** Transcripts are served from the inbox (`render/serve.py:421-430`); the build also writes static pages "so a viewer with no publisher running still reads the chat" (`render/build.py:344-363`), which can go. `since` reports transcript messages; `ai orient --session` prints the session's log and chat; MCP calls log to the active session (`mcp/server.py:305-312`); the session directory is an agent's permanent place (`agents.py:41`). `session-use` and `session-purpose` have no caller (INV-12).

**b. Agents.** "Your report is a `loom session say` message" (`orientation.md:7`), §5 (`:58-64`), rules' table and "A report is one transcript message" (`rules.md:41, 48`), scripts saved in the session directory (`rules.md:18`, standing rule 7). Modes chain through the transcript: referee reads an earlier audit or referee report there (`modes/referee.md:9`), simplify starts from an audit's patch list there (`modes/simplify.md:14`). Hiding transcripts in the viewer while these stand makes every report invisible, against the rules' own premise "what it does not show is never seen" (`rules.md:37`).

**c. Real use.** 144 messages since 11-06 across both quilts; relloc's 11-09 session spans four days and 97 agent names, and its directory is the pipeline's workspace. Relloc has no MCP at all, so "per connection" has nothing to bind to there.

**d. Journeys.** inventory marks `session say` L E P ("every report").

**e. Planned work.** attach.md C4 groups the activity page by session and opens each group to its report; C2 binds a session per process. Lean sends status reports to the transcript and audit reports to the session directory (`lean.md` LEAN-11, step 13).

**Verdict: hide the footer and picker only.** Hide the amber footer, the picker and The Record › Sessions; show transcripts as "agent reports" inside the activity page (C4). Bind a session lazily per MCP process only when none is named, and keep `session new` and `--session` for agents so one piece of work can span conversations and subagents. Remove `session-use`, `session-purpose` and the static transcript pages (about 40 lines). Do not remove `mailbox.py` or `session say` (CORE-12) unless the rules and four modes are rewritten to report in the app's chat, which subagents' reports never reach. Bring-back cost if removed: a day plus the rules.

## CUT-4: the graph view

Proposed: hide `/graph` and the local graph (VIEW-15, VIEW-17).

**a. Code.** `routes/graph/+page.svelte` and `lib/graph/` are imported by `DocumentItem.svelte:15` and `ContextItem.svelte:10, 193`; ContextItem draws its graph "last and small" after the rest-on and used-by lists. The Python graph (`cli/graph.py`, `deps`, `downstream`) is separate.

**b. Agents.** No agent text mentions the drawing; agents use `deps` (7 logged calls) and `downstream` (4), and modes use `downstream`.

**c. Real use.** Not measurable: the open state is browser-local (`DocumentItem.svelte:47-59`).

**d, e.** No works-well entry depends on it. Lean's R11 hand-off uses `cli/graph.py:146, 308`, not the viewer.

**Verdict: cut as proposed (hide).** Keep ContextItem's lists and drop only its embedded graph section. Hide: hours. Remove (2,460 lines, ELK chunk, 13 e2e tests) after the pilot if nobody asks; bring back from git.

## CUT-5: publishing to Overleaf

Proposed: hide `sync publish`, `--push`, `sync documents`; read-only mirror (INST-9 to INST-11).

**a. Code.** The mirror reuses `sync.fetch`, `incorporate`, `configure` (`install.md:110-111`); `adopt.py` imports only `SyncError` from `loom.sync`. **b.** The orientation lists `sync incorporate` and `sync publish --push` as author-only (`orientation.md:42`); nothing sends agents to sync. **c.** No sync record in either quilt. **d.** Serves only the Overleaf pilot. **e.** The mirror needs Keep on mirrored documents to stop writing the file (`install.md:115`), which touches the Proposed list (CUT-7).

**Verdict: cut as proposed** (hide; keep the code, since the mirror is built on it). Coordinate with CUT-7: on a mirrored document, Keep becomes "Copy new text / Done in Overleaf".

## CUT-6: the shell variant

Proposed: hide, MCP only (attach.md C6, ATT-18).

**a. Code.** The variant is `--mcp/--shell` (`cli/ai.py:222-249`), two root lines (`ai/layout.py:69-70`) and two permission files (`ai/layout.py:170-190`). Over MCP the server supplies `--as` (`mcp/tools.py:19`), so every call of one connection, subagents included, carries one name (LEAN-9).

**b. Agents.** The orientation teaches both, and `--batch` and stdin exist only in a shell (`rules.md:60`).

**c. Real use.** **Relloc is on the shell variant**: its `CLAUDE.md` holds the shell line, it has no `.mcp.json`, and its permission file allows no `mcp__loom__*`. All of relloc's agent names (97 in one session) were signed with `--as` in a shell. Quant uses MCP with one name.

**d.** Works-well relies on MCP for quant. **e.** Lean's independent auditor needs a distinct signer (LEAN-9); Codex's sandbox argues for MCP as the default (ATT-13).

**Verdict: hide the choice, keep the variant.** Default new quilts to MCP and hide `--shell` from the person (ATT-18), but keep the shell variant and the shell route. Going MCP-only first needs a per-call agent name on MCP tools (a subagent's name under the server's), tried on a relloc-like pipeline. Hide: hours. Removing it would break the author's paper quilt.

## CUT-7: Review, acceptance, track_edits, deny

**a. Code.** Acceptance staleness is `records/store.py:286-418`, which Lean's R6 reuses. Always-on tracking means the look (`looks.py:3`: every open text file up to 1 MB) and `pending.in_place` on every build, gated today by `scan/quilt.py:66, 108-111` and `pending.py:151`. "Everything recorded" is the only viewer route for `history-restore {path, text}`, which puts back text an undo set aside (inventory row 58).

**b. Agents.** The orientation describes acceptance states (`orientation.md:16`) and that edits in place are unseen unless tracked (`:30`); `since` reports acceptances and staleness (`:60`). Deny is enforced for the agent's own edits only by Claude Code; "Codex, Gemini CLI and Cursor do not" (`orientation.md:36`, ATT-11).

**c. Real use.** Zero acceptances in both quilts. Both quilts already deny their document directories. Looks exist in both but are split by the misattributed author name (`looked/ikmartin.json` and `looked/the-synthetic-quilt.json`).

**d.** quant items 12 and 36 ask for exactly the always-on look; Changed serves the learner.

**e.** Lean puts the attest card in Proposed and stale formal stamps in Your Changes (`lean.md` R8 and section 7A's last paragraph). Lean writes `lean/` files and `.lake` (LEAN-4) where the look would walk them. The library's proposals move to the Library (library.md).

**Verdict: cut, with four conditions.**

1. **Codex and deny.** review.md takes a change in a denied path as the person's and advances the look silently (`review.md:164`). With Codex, whose own edits ignore deny, that hides an agent's edit to the person's paper. Show such changes as Changed rows (cause unknown) unless the client enforces deny, or attribute through the app (review.md I).
2. **What the look covers.** Exclude agent-owned places from Changed: `.loom/copies/` (already a dot directory), `lean/` and `.lake/`, and any directory the agent layer marks as the agent's; otherwise a relloc-sized AI document or a Lean project floods Changed. Measure the look's cost on relloc first (CORE-18).
3. **Proposed admits more than suggested edits**: Lean's attest card, and on a mirrored document the "Done in Overleaf" variant.
4. **Undo before The Record goes.** Remove Everything recorded only after review.md's B (one-step undo of Keep and Discard) lands, and fix the split-name look (quant item 25) before Changed rests on looks.

Acceptance as an optional badge with no backlog: cut as proposed; keep the ledger and its staleness computation. Deny by default: cut as proposed, given condition 1, and only together with CUT-1's verdict: in relloc, deny plus no copies leaves agents nowhere to write the paper's mathematics.

## CUT-8: Problems shows LaTeX problems only

**a. Code.** 74 registered codes (`scan/diagnostics.py`); lint and review print `loom fork` fixes through `conflict_fixes`. **b. Agents.** Agents run `loom lint` (12 logged calls) and compile; audit's [uses-ledger] is the work of `uses-missing` and `uses-unused` (`rules.md:118`); the copy codes (`derived-id-in-person-document`, `plain-id-in-agent-document`, `agent-document-unrecorded`) police the `-ai` boundary. `ai orient`'s Live state and the serve start line print error counts ("57 errors in your documents", quant findings section 3). **c.** Quant 57 `unattached-proof`, relloc 33 counted warnings, none of class (a) (review.md section 2). **d.** None. **e.** Lean needs `\uses` to be right, since a definition the statement uses but does not cite escapes the formal closure (`lean.md` section 7E).

**Verdict: cut for the person, keep for agents.** Filter by class in the viewer (review.md C); keep every code in `loom lint` and its JSON; regrade the `error`s that never stop TeX, which also fixes orient's Live state and the start line; reword fork fixes (CUT-2). Do not delete codes.

## CUT-9: static and host-neutral machinery, fixture in three copies

**a. Code.** About 500 lines in `arras/src` (viewer.md section 4); `npm run dev` serves the static fixture with no write API and `serve-static.mjs` answers `/_api` with 404; three fixture copies kept equal by `scripts/checks/fixtures.py`. **b-e.** Nothing for agents, users, Lean, library or attach.

**Verdict: cut after the Vite proxy to a running `loom serve` exists** (VIEW-13), since today's only hot-reload loop is the static fixture. Keep one fixture, `docs/specs/fixture`, as the manifest contract. Remove: a day or two; bring back: not wanted.

## CUT-10: tests

**Verdict: cut as proposed, in this order.** First add the seeded sequence safety test (TEST-1), since the suites being trimmed are what currently stands between a refactor and a person's file. Keep the `unchanged` assertion per output case (refusals and dry runs write nothing: the AI boundary in executable form). Drop the static suite's write mocks and its tests of hidden features, keeping read-only rendering not covered by the reading suite. A merge gate for regeneration is fine if `test_quilts_match_generator.py` runs there, since it is the only alarm for a change in what loom writes to records.

## CUT-11: plans, reports, frozen records out of the search path

**a.** `AGENTS.md:9, 22`, `CLAUDE.md:83` and `docs/contributing.md:68` point at the paths; 235 files cite plans; no script reads them. **b-e.** Nothing shipped depends on them; the author works from one master plan file in plan mode (his memory notes).

**Verdict: cut as proposed** (move to `docs/archive/`, one sed), keeping the plan file currently in use and this study's reports where they are until the plan is built.

## CUT-12: other cuts proposed in the reports

| proposal (source) | dependency found | verdict |
|---|---|---|
| Remove transcripts, ~650 lines (CORE-12) | rules and four modes route reports there; C4 builds on them | do not (CUT-3) |
| Merge nine modes into five (INV-23) | relloc's session files show audit, referee, simplify, flow ("clarity"), draft and question each used separately and chained through the transcript | do not merge files; the viewer may offer five |
| Hide `mv` (inventory) | used once by the author; keeps records on a rename | hide from help, keep |
| Hide quilt-wide stamp, `history verify`, `restore --to`, `revert` | one named stamp ever ("stamp1"); automatic versions are what is used | as proposed |
| Hide The Record › Everything recorded | only viewer route to `history-restore {path, text}` | after review.md B |
| Hide library bookkeeping (`drop`, `import`, `ignore`, `check`), Settings › Problems | `library check` is an agent command | as proposed for people |
| Remove indexes (threads, tags, taxa, loose) (VIEW-16) | `/threads` duplicates sessions; `% !LOOM tags` stays parsed | as proposed |
| Hide PDF page editor (`pdf-save`) | none found | as proposed |
| Hide `ai delete`, `annotate --batch` from people | `--batch` is how shell agents file many findings (`rules.md:60`) | as proposed; keep for agents |
| Remove `session-use`, `session-purpose` (INV-12) | no caller | as proposed |
| Gemini CLI and Cursor files by default, GEMINI.md, the Gemini test (ATT-16, CORE-13, TEST-18) | both quilts carry the files, no use | as proposed |
| Second and later entry points (VIEW-5) | sessions picker (CUT-3); Keep in five places | as proposed |
| Remove `review_origins.py`, "taken in" rows (review.md) | records adoption and pull origins; Changed wants "from Overleaf" as a cause | cut once the cause comes from the ledger |
| Hide `status` from a learner (quant item 4) | the orientation's first instruction is `loom status` | reword the orientation; keep `status` for agents |
| CLI reference and its test, figure script (TEST-13, TEST-14) | none | as proposed |
| AddWork form and dialog states (LIB-10, LIB-12) | replaced by the library intake | as proposed |
| Ten review passes, `~/notes` rule out of public docs (PROC-45, PROC-46) | the author's own rules | the author's call |

## CUT-13: things nobody proposed cutting

| candidate | journeys | dependency check | verdict |
|---|---|---|---|
| `ai init --client` entries for Claude Desktop chat, LM Studio, Zed, JetBrains (`ai/clients.py:57-66`) | none for Claude Code or Codex pilots | attach.md leaves desktop chat out of v0.1; no tests a pilot needs | **cut** (hide) |
| Relations between results (`library relate`, `scan/relations.py`, the relation half of `library why`) | L, in theory | 0 relations in either quilt; `rules.md:56` tells agents to use it; ~250 lines | **cut the rule line and the agent tool**; keep the code |
| Unused agent tools: `check`, `build`, `history verify`, `library locate`, `library check`, `library why` | none | none appears in either quilt's logs (incomplete, see caveat); 42 tools cost ~12k tokens at arrival (ATT-15) | **cut from `AGENT_COMMANDS`** after a check of the shell history |
| Research state and overviews (`loom write`) | L E | 39 state writes and 2 overviews; quant's learner profile lives there | **keep** |
| Annotation types and looks | L E P | relloc used five kinds, quant four; Settings › Annotations edits them | **keep** types; per-annotation styling could hide |
| Named versions ("record this version", `stamp -m`) | P | one named stamp ever; automatic versions are the undo | hide naming; keep versions |
| Compare (`compare`, CompareLayer, compare cache) | P | use not measurable; overlaps the Changed list once built | keep until Changed ships, then decide |
| HTML pages agents write (frame server, `files.json`) | L | works-well entry | **keep** |
| Digests and library proposals | L | 27 digests, 72 proposals in relloc | **keep** |

## CUT-14: defects found in the trials

- **A suggestion on a section key's body deletes the section heading.** `body_span` treats text that is no environment as all body (`records/edits.py:231-234`), and a section's own text is its heading, so `loom suggest sh-0300 --with TEXT` produces a patch that removes `\section{The rank of the cycle lattice}\label{sh-0300}` and glues TEXT to the next `\begin{theorem}`. The rules invite exactly this call ("With no `--quote`, it is about the key's body", `rules.md:65`). Blocks: Keep would destroy a heading and a label.
- **An insertion between results needs a quote the rules forbid.** `--after` with no quote puts text inside the environment; placing a block after a proof works only by quoting `\end{proof}`, against `rules.md:61`.
- **An agent's ordinary file is the person's.** Keys in an agent-written `ai/survey.tex` are listed among "keys of yours", and its diagnostics are owner `person`, two of them `error`. If copies go, this is where AI text ends up.
- **Copies have no versions.** Relloc's agents kept ten 600 KB snapshots of the copy by hand in the session directory; loom keeps versions only of the person's documents.

# Review panel: a study

Made on 2026-11-03, after the author reported that Incoming "seems broken in parts": "Use all proposed edits" and "Use proposed version" appear to do nothing, the second sits beneath the change and moves, a document's history cannot be paged through or gone back to, and Problems is full of errors the author cannot fix. The question is every way Review fails the person using it, sorted so that the fixes can be planned.

## Method

Two scratch copies were served by `loom serve` from this checkout (`6f9c1cbc` plus the counter's removal) and driven in the browser at 1440×900; neither original was touched.

- **relloc**, a copy of the author's quilt: two documents, a session, 36 works, and the agent copy `examples-shared.tex` of `drafting/examples.tex` with 102 unapplied changes. Three edits were made in it to give Changes something to show.
- **synthetic**, a copy of `loom/tests/quilts/synthetic`, the quilt the write tests use: an agent copy `aidoc.tex` with 7 changes, one of them a conflict, and the fixture's planted errors.

Every section was opened, every control pressed, the network calls read, and the code behind each failure read where the cause was not plain. Positions are measured in page pixels.

## Verdict

Review reads well and acts badly. Five causes account for most of what follows.

1. **A choice is not an act, and the page does not say so.** Incoming's "Use all proposed edits" and "Use proposed version" only record a selection; the act is "Preview selected changes", seven screens further down on relloc, and then "Incorporate". Pressing them looks like nothing happening, because nothing does.
2. **The answer lands far from the question.** Every refusal is drawn at the top of a long page while the button that caused it is at the bottom, and controls move as messages appear. A press that fails looks exactly like a press that did nothing.
3. **The person is shown what only loom or the agent can fix.** None of relloc's 174 errors is in the author's files: 104 are in digests loom generated, 70 in the agent's copy. Incoming refuses to take back a copy over a duplicate id elsewhere in the document, or over the copy's references to the other document, which it makes on purpose. The fixes offered are terminal commands.
4. **History is a ledger of explicit stamps, not a document's past.** A month of work on relloc is two rows. There is no way to record a version from the viewer, to see a document change over time, or to go back to an old version; an undo made in Changes is said to be "kept in the history" and is not listed there.
5. **The viewer mostly cannot act.** Needs review cannot accept, Suggestions cannot apply or dismiss, History cannot restore, Problems cannot fix. The one place mathematics is accepted is inside Incoming's preview.

## Categories

Each finding carries one category, the one its fix answers to, and a severity.

| Category | Means |
| --- | --- |
| Doesn't do what it says | a control's label promises what does not happen |
| Fails silently | something happened or failed and the page does not say |
| Unstable or hidden | a control moves, is covered, or is out of reach |
| Missing capability | the page implies a task it cannot do |
| Not actionable | it shows what the person cannot act on from there |
| Non-obvious behavior | it works, but nothing on screen predicts what it will do |
| Needlessly complicated | more steps, modes or states than the task needs |
| Obtuse design | built around loom's concepts and words, not the person's task |
| Redundant | the same thing twice, or two controls for one act |
| Useless | shown, but nothing anyone acts on |
| Inconsistent | the same kind of thing done differently in different places |
| Wrong or stale | a count, state or label that is untrue |

Severity: **blocks** (a task cannot be done), **misleads** (the person will believe something false or act wrongly), **friction** (it can be done, at a cost), **cosmetic**.

## Findings

### Across Review

- **FR1 · Wrong or stale · misleads.** The numbers beside the sections count different things, and most are not work waiting. Changes counts files changed and Incoming contributions waiting, which are; but Suggestions counts every open suggestion, including ones that cannot be applied (SU3); Library counts works with no copy (10) while its own page says 3 need the person (LI1); Sessions counts open sessions (1); Problems counts errors and warnings (229), none of them the author's (PR1).
- **FR2 · Non-obvious behavior · friction.** "Review" opens on Needs review, which is empty on both quilts (NR1), rather than on what waits; Changes, listed first, is not where it lands.
- **FR3 · Non-obvious behavior · friction.** Opening anything listed in Review leaves Review. A block (Needs review), a suggestion, a problem's location and a session each open a tab in Docs, a result shown alone rather than in its document, and the way back is the browser's or a link inside that tab ("See this block in Review").
- **FR4 · Inconsistent · friction.** Each section is built on its own pattern: Needs review a framed card with tabs, Changes plain text with grey buttons, Incoming browser-default buttons, Library a styled table with row menus, Sessions and History bare tables, Problems a folding list whose filters move into the left column (PR5).
- **FR5 · Wrong or stale · cosmetic.** The page header carries the default document's title ("Localization of relative virtual classes (PRELIMINARY DRAFT)") on quilt-wide pages: Needs review, Incoming, Sessions, History; it stays when Needs review is switched to `examples.tex`.

### Needs review

- **NR1 · Wrong or stale · misleads.** The queue says "Nothing needs review" and "NEEDS REVIEW (0)" while the Documents tab lists about 70 blocks of `draft5.tex`, every one `draft`, never reviewed. The queue holds only decisions left from incorporating a pull or a copy (`m.unresolved` with status `needs-review`); the section's name and its empty state hide that.
- **NR2 · Missing capability · blocks.** Nothing in Needs review acts: no accept, no request for review, no way to open a block's objection. Its help dot says acceptance "is recorded from the command line; this page only reads it back".
- **NR3 · Obtuse design · friction.** The Documents table gives every row a "Details" fold while its Reason column is empty on all but two rows; a fold reads "drafting/draft5.tex · local-proof", "1 open objection · 1 detached", "Reached by: drafting/draft5.tex". The objection is not a link.
- **NR4 · Useless · cosmetic.** An empty queue still draws the whole framed two-column workspace, its left list empty.
- **NR5 · Useless · cosmetic.** The document picker offers `examples.tex`, which answers "No blocks in this document".

### Changes

- **CH1 · Fails silently · misleads.** Keep answered at once ("kept README.md") but the row stayed on screen, unchanged and with no pending state, for about five seconds; the button looked dead. Undo, by contrast, greys its buttons while it runs.
- **CH2 · Wrong or stale · misleads.** Keeping one file moves the header's "since your look, 2026-11-03 16:56" to the moment of the keep (17:56), while the changes still listed predate it. Cause: `looks.keep` sets `look.when = stamp()` whichever path is kept.
- **CH3 · Missing capability · blocks.** Keep and Undo work on a whole file. A file holding an agent's edit and the person's own is all or nothing, and Undo throws away the person's edits in it with the agent's.
- **CH4 · Missing capability · misleads.** Nothing says who made a change. An agent's edit and the person's own edit in their editor look alike, so the person must Keep their own work, and cannot tell which changes are an agent's.
- **CH5 · Fails silently · misleads.** Undo asks nothing first and says nothing after. The header promises the text is "now kept in the history", but History does not list it (HI2), so it cannot be found or brought back from the viewer.
- **CH6 · Inconsistent · friction.** A changed file has Keep and Undo; a new file has Keep only, with "keep it, or delete it yourself".
- **CH7 · Obtuse design · friction.** Each change is a raw source diff in two monospace columns; the file name is not a link, and there is no way to see the change in the rendered document or go to it.

### Incoming

- **IN1 · Doesn't do what it says · blocks.** "Use all proposed edits" only selects (`adopt-decision`); nothing is applied. On relloc every change was already selected from an earlier visit, so pressing it changed nothing on screen. What applies is "Preview selected changes", then "Incorporate selected changes".
- **IN2 · Doesn't do what it says · misleads.** "Use proposed version" also only selects; pressed again, it does nothing. Its feedback is a 2px outline on itself and the small word under the change's row in the list.
- **IN3 · Unstable or hidden · blocks.** "Use proposed version" and "Leave out for now" sit beneath the full proposed text. Over eight consecutive changes on relloc they stood at 1286, 771, 518, 493, 749, 562, 584 and 516px in a 900px window, below the fold on the first, jumping at every "Next change" while Next and Previous stay at the top.
- **IN4 · Unstable or hidden · blocks.** "Preview selected changes" stands at 6317px of a 6380px page on relloc, after the 102-row list: seven screens below the controls that make the choices it previews.
- **IN5 · Fails silently · blocks.** A refusal is drawn at the top of the section (213px) while the button pressed is at 6317px. Pressed, nothing visible happens.
- **IN6 · Doesn't do what it says · blocks.** "Use all proposed edits" leaves the preamble out, and Preview then refuses: "Selected edits need proposed preamble definitions: \incomplete. Include Preamble changes or revise the edits." The fix is a checkbox inside "Preamble changes", the last row of the list.
- **IN7 · Not actionable · blocks.** With the preamble included, Preview refuses relloc's copy in about sixty sentences run together in one paragraph: "rl-001R refers to rl-001L, which its master does not reach rl-001R refers to rl-001F, …". `examples.tex` cites `draft5.tex`'s results on purpose, through `xr-hyper`; nothing in the viewer can change that, so this copy can never be taken back from the viewer.
- **IN8 · Not actionable · blocks.** A conflict says "Both versions changed. Reconcile the text in your editor, then refresh Incoming." yet offers "Use proposed version", which records the choice; Preview then refuses with "sy-0001: both versions changed; reconcile the two copies in your editor, run loom ai refresh, and refresh Incoming". The page lets the person choose what it will refuse, the advice is a terminal command, and there is no "refresh Incoming".
- **IN9 · Not actionable · blocks.** On synthetic, Incorporate refused: "drafting/main.tex reaches sy-999B, defined by two files each; a landmark needs one text per key. loom lint --nodes shows them." A duplicate id anywhere the document reaches, unrelated to the changes chosen, blocks every incorporation, and the viewer cannot fix it.
- **IN10 · Unstable or hidden · friction.** Each choice adds or moves a line above the controls, so "Preview selected changes" stood at 397, then 416, then 436px over three presses; a click aimed where it had been sent nothing.
- **IN11 · Doesn't do what it says · misleads.** After a choice, the proposed side read "Rendering comparison…" and never recovered; after the refused Incorporate, both sides of the preview did the same.
- **IN12 · Wrong or stale · misleads.** Preview says "2 mathematical blocks selected" (Orbits and Gadget), lists four under "Mathematics affected" (Orbits and three proofs) without Gadget, and ends "4 mathematical blocks remain pending".
- **IN13 · Non-obvious behavior · misleads.** Orbits' "Proposed version" was blank; Gadget's reads the same as its current version, with no note saying what differs.
- **IN14 · Needlessly complicated · friction.** One contribution is reviewed in two nested workspaces, each with its own list and pager and its own words: Use proposed and Leave out for now, then Accept and Keep for review; "Change selected source" is the way back.
- **IN15 · Needlessly complicated · friction.** A change's state is one of three ("Use proposed", "Not selected", "Left out for now"), printed under its row like a button label; the last two differ only in loom's bookkeeping.
- **IN16 · Obtuse design · friction.** The list names changes by key ("rl-001T", "rl-001V/proof"), proofs as rows of their own, 102 of them on relloc with no grouping, search or filter; the heading reads "rl-001T New result rl-001T".
- **IN17 · Obtuse design · friction.** The page explains itself in loom's terms: "Changes will go into drafting/examples.tex and the node files it uses. You can explicitly accept inspected mathematics when incorporating."; "Some choices changed because their source changed. Review those changes again." (which?); "Outstanding changes in this draft, including earlier edits."
- **IN18 · Inconsistent · friction.** Results are chosen with buttons; prose and ordering, and the preamble, with checkboxes inside their own rows.
- **IN19 · Inconsistent · friction.** Mathematics can be accepted here, while incorporating, and nowhere else in the viewer (NR2).
- **IN20 · Inconsistent · cosmetic.** The selection step's buttons are the browser's defaults; the preview's are styled.
- **IN21 · Useless · cosmetic.** A new result's "Current working version" is a grey monospace box reading "No current definition" beside the rendered proposal.

### Suggestions

- **SU1 · Missing capability · blocks.** Nothing on the page acts: no apply, no resolve, no dismiss. Applying is done by hand in an editor.
- **SU2 · Doesn't do what it says · misleads.** The lead promises "Each opens in place, with the change shown, and the patch that takes it is here." None of the five suggestions on the two quilts shows a patch: all are prose, with no proposed text.
- **SU3 · Wrong or stale · misleads.** A prose suggestion ("Worth recording if you want local targets…", "For the slide, the fixed-point clause can go") cannot be applied, yet is listed as "waiting to be applied" and counted (FR1).
- **SU4 · Missing capability · misleads.** A suggestion does not say which document it is on. relloc's three are on the agent's copy (`rl-001T-ai`, Convention 6.1 of `examples-shared.tex`) and read as if on the author's paper.
- **SU5 · Wrong or stale · cosmetic.** References come out doubled: "Corollary Corollary 7.8", "Theorems Theorem 4.8 and Theorem 6.43", "Examples Example 8.3 and Example 8.5".
- **SU6 · Obtuse design · cosmetic.** The quoted words show their LaTeX: "Let \(X\) be a complete toric variety…".
- **SU7 · Inconsistent · cosmetic.** Authors read "Claude Agent", "Referee Agent", "agent", and "The synthetic quilt", a quilt's name standing as a person.

### Library

Rebuilt in 0.24.4 and mostly sound.

- **LI1 · Inconsistent · misleads.** The section's count (10, works with no copy) disagrees with the page's own "needs you 3".
- **LI2 · Non-obvious behavior · friction.** A work with a DOI and no paper (Atiyah–Bott 1984, Brion 1997) shows "—" and no reason or fix in its row; a row names a missing copy only when loom raised `no-readable-copy`.
- **LI3 · Wrong or stale · cosmetic.** "Stacks Project · Authors": the literal word as its author list.

### Sessions

- **SE1 · Non-obvious behavior · misleads.** Opening a session to look at it also selects it as the place the person's writes go: the footer changes to it. The code does so on purpose, so the footer and the transcript never name two sessions; nothing on screen says that looking changed it.
- **SE2 · Useless · friction.** "What it did" is the raw command log: `loom compile drafting-ai/examples-shared.tex` fifteen times running, `loom annotate rl-0020-ai --quote --kind objection`, paths as they were then. Nothing is grouped, filtered, or linked to what it changed.
- **SE3 · Fails silently · cosmetic.** A session with no transcript shows a blank Transcript tab, with no line saying nothing was said.
- **SE4 · Obtuse design · friction.** The table's "OPEN 16" is unexplained (open annotations); "LAST OPENED 2026-10-12" although the session wrote on 2026-11-03; there is no new session and no "write here" in it, since both live in the footer's picker.

### History

- **HI1 · Missing capability · blocks.** History holds a step only when someone stamps, from the command line, and never on save; the viewer cannot record a version. relloc, worked on for a month, has two rows: the import and the copy. There is nothing to page through.
- **HI2 · Missing capability · blocks.** Only steps are listed. The undo made in Changes, the copy's move, its close and reopen, page writes and keeps are all in the ledger and none is shown, so the text an undo set aside cannot be found (CH5). Cause: the page draws `m.history.steps` alone.
- **HI3 · Missing capability · blocks.** Nothing goes back. Neither the table, a landmark, `history ▾` nor compare offers "restore this version" or "start a document from it", and no result has a version list to revert to; those are `loom history restore` and `loom revert` at the command line.
- **HI4 · Wrong or stale · misleads.** A landmark renders a raw `\subsection*History and contributions` heading and raw citation keys ("[atiyah-bott_MomentMapEquivariant1984]") where the live text has numbered sections and [AB84].
- **HI5 · Wrong or stale · misleads.** Compare counts "64 differences" between the import and the live text, most of them rendering (numbering, citation labels, equation numbers) rather than words.
- **HI6 · Doesn't do what it says · blocks.** Stepping to a difference scrolls only the live side (to Theorem A, marked new); the landmark side stays at the top, so the before is never beside the after.
- **HI7 · Obtuse design · friction.** The table is a ledger (STEP, WHAT "imported" or "agent document", LANDMARK, WHO), not a document's story: no filter by document, no "what changed in this step".

### Problems

On relloc: 174 errors, 55 warnings, 103 infos. By the file each names: of the errors, `duplicate-id` (88), `loom:duplicate-label` (15) and `dangling-link` (1) are all in `.loom/digests/`, which loom generates from cited works, and `loom:reference-to-loose` (70) is all in the agent's copy. Of the warnings, 31 are in digests, 11 in the copy, 6 are dependency cycles, and 7 are in the author's files.

- **PR1 · Not actionable · misleads.** Every error shown is loom's own output or the agent's copy; the author's files have none. The red count and "174 errors" say the paper is broken.
- **PR2 · Not actionable · blocks.** 269 of 332 carry no fix, and the 63 that do offer a terminal command to copy ("loom id --next", "loom library update", "loom annotate --resolve …"). The duplicate-id fix tells the author to "give one copy a fresh id by hand", in a file loom generated.
- **PR3 · Useless · friction.** A location opens a tab holding only a pink box: "Defined in two files: .loom/digests/… It has no text until one definition moves or is forked — see problems.", which links back to Problems.
- **PR4 · Obtuse design · friction.** Problems are grouped by code ("duplicate-id", "loom:reference-to-loose", "loom:uses-unused"), not by what is wrong in words; two of the groups are near-duplicates (`duplicate-id`, `loom:duplicate-label`).
- **PR5 · Inconsistent · friction.** The filters (severity, subject, code) take over the left column on this page alone; everywhere else it is the navigation.
- **PR6 · Useless · friction.** 103 infos stand beside the errors, most of them bookkeeping (`loom:uses-unused`, 52).
- **PR7 · Obtuse design · cosmetic.** The help dot ends "Recorded and reported by the command line: lint. Run it with --help for what it takes."

## Patterns

Read across sections, the findings share fixes.

- **One act per control, said where it is pressed.** Choosing and doing are split in Incoming (IN1, IN2, IN6), and answers are drawn away from the press everywhere (IN5, CH1, CH5). A control that records a choice should say so in its label, the act should be one button that stays in reach, and every outcome, refusal included, should appear beside the control or in one fixed place.
- **Controls in fixed places.** Act buttons beneath variable content (IN3, IN4, IN10) should move to a bar that does not scroll with the change.
- **Show the person only what is theirs.** Diagnostics on loom's own digests and on an agent's copy (PR1, PR2), and refusals caused by them (IN7, IN9), belong to loom or the agent; Problems should separate them, and Incoming should not stop on them.
- **Act in the viewer.** Accept (NR2), apply and dismiss (SU1), record a version and restore one (HI1, HI3), and per-change keep (CH3) are the acts a person reaches Review for; each is the command line's today.
- **A document's past.** Versions recorded as work happens, every undo and incorporation listed, a per-document timeline that can be paged and compared both sides in step, and a way back (HI1–HI6, CH5).
- **The person's words.** Names instead of keys (IN16), plain explanations instead of loom's terms (IN17, NR3, PR4, HI7), and counts that mean "this waits for you" (FR1).
- **One look.** The sections should share one set of controls, table and empty state (FR4, IN20, PR5).

## Counts

| Category | Findings |
| --- | --- |
| Wrong or stale | 10 |
| Obtuse design | 9 |
| Inconsistent | 8 |
| Missing capability | 8 |
| Doesn't do what it says | 6 |
| Useless | 6 |
| Non-obvious behavior | 5 |
| Not actionable | 5 |
| Fails silently | 4 |
| Unstable or hidden | 3 |
| Needlessly complicated | 2 |
| Redundant | 0 |

| Severity | Findings |
| --- | --- |
| blocks | 16 |
| misleads | 18 |
| friction | 21 |
| cosmetic | 11 |

Sixty-six findings. Redundant has none on its own; the near-duplicate problem codes (PR4) are its one instance, filed under Obtuse design.

# Red team: coverage of the people the plan serves

A hostile review of `docs/plans/0.32-v0.1.md`, read with `state.md`, `codebase.md`, `register.md`, `register-notes.md` and the reports under `raw/` (chiefly `walk.md`, `walk-small.md`, `explore.md`, `quant-findings.md`, `review.md`, `library.md`, `install.md`, `tinytex.md`, `check-changed.md`, `security.md` and the safety harness). The question throughout is whether the plan delivers what the author asked for to the two to four pilots it is for. Nothing was run; every claim about loom is cited from the study, and every claim about the plan quotes it.

Severity: **stuck** (a pilot cannot go on without the author or a terminal), **slowed** (a pilot gets through, with a chore, a wrong turn or a doubt), **wording** (the plan misleads a builder or the author, and the fix is in the text).

## Summary

| id | objection | severity |
|---|---|---|
| RTC-1 | No sizes or critical path, so the author cannot weigh cuts against "soon" | wording |
| RTC-2 | Foundations' registry gates every endpoint workstream and is unsized | slowed |
| RTC-3 | The rubric is pass/fail gates with no measure of whether pilots were served | wording |
| RTC-4 | Tiers contradict the author's own ranking and omit things he asked about | wording |
| RTC-5 | The codebase evaluation does not name the tests and practices to drop, nor answer "extendable by other people" | wording |
| RTC-6 | `state.md` overstates Complete and names a different "five" from the notes | wording |
| RTC-7 | (A) Review's done-when measures row categories, not whether a change can be read | slowed |
| RTC-8 | (A) An Overleaf pilot's own edits arrive by pull and fill Changed | slowed |
| RTC-9 | (D) The notes page is a phrase in a traps cell with no design and no gate | slowed |
| RTC-10 | (E, F) Tab drag and the toolbar are in passing; the small toolbar is missing though 760 px is required | slowed |
| RTC-11 | (G, H) The activity page has no owner while the plan removes every other home of transcripts | stuck |
| RTC-12 | (H) Quote, versions, compare, split view, the margin legend and the marking gestures have no answer | slowed |
| RTC-13 | (H) The introduction has no owner, no content and no test | slowed |
| RTC-14 | Linux is not mentioned | slowed |
| RTC-15 | "A robust linking system" has no workstream; hiding the graph can take its visible half with it | slowed |
| RTC-16 | Modes are not reachable by the person | slowed |
| RTC-17 | Dragging in a paper draft has no owner and no done-when | stuck |
| RTC-18 | "No human types a loom command" is broken three ways the plan does not address | slowed |
| RTC-19 | A Codex pilot has no fallback, and Codex is checked after the design that depends on it | stuck |
| RTC-20 | Without Homebrew there is no page text, so the library's AI search fails on a clean Mac | stuck |
| RTC-21 | A scanned textbook is closed to the agent though Claude Code can read PDF pages | slowed |
| RTC-22 | The three zones are undefined for a quilt with no paper, and agents' places keep no versions | slowed |
| RTC-23 | Feedback filed as suggested edits counts as "proposed edits" in Quiet | slowed |
| RTC-24 | The Overleaf pilot gets a copy chore per edit, ships last, may ship "a step behind", and their plan is unconfirmed | stuck |
| RTC-25 | "Add all" leaves every paywalled PDF to be fetched by hand | slowed |
| RTC-26 | The library's core promise, an AI finding the important results across many papers, is neither evaluated nor planned | slowed |
| RTC-27 | `explore.md` is not in the register, so its findings are invisible to a builder following the plan | slowed |
| RTC-28 | Orphaned findings, two of them weighted "blocks" | stuck |
| RTC-29 | Decision 1's defaults, the boundary itself, have no owner | stuck |
| RTC-30 | Safe's check does not exercise the writes v0.1 adds, and its anchoring bar allows mass detachment | stuck |
| RTC-31 | Installable can pass on the showcase while a pilot's paper fails | stuck |
| RTC-32 | Attachable can pass while every loom call asks the person's approval | slowed |
| RTC-33 | Legible is graded by language models on the showcase, with the tasks unnamed | slowed |
| RTC-34 | Fast's typeset threshold is already met today; its write threshold does not stop lost keys | slowed |
| RTC-35 | Quiet counts categories on two quilts by one person | slowed |
| RTC-36 | Complete has no real model, and lets the Overleaf pilot's whole use ship late | stuck |
| RTC-37 | Essential things outside all seven gates | slowed |
| RTC-38 | What to cut | — |

## 1. The four deliverables

| deliverable | delivered by | verdict |
|---|---|---|
| 1. Shape, five tiers, criterion and rubric | plan, "The bar" and "What goes in" | partly: tiers exist but misplace and omit (RTC-4); gates exist but several lack teeth (RTC-30 to RTC-37) and none measures the pilots' outcome (RTC-3) |
| 2. Where loom is today | `state.md` | yes, and the strongest of the three; Complete is overstated and the "five" disagrees with the notes (RTC-6) |
| 3. A master plan for agents | plan, "Workstreams" | partly: specific per workstream, but unsized, with no critical path (RTC-1) and a heavy precondition (RTC-2); author's complaints D, E, F sit in a traps cell (RTC-9, RTC-10) |
| 4. Codebase evaluation, six questions | `codebase.md` | partly: inefficiency, modification and speed of development answered well; "extendable by other people" thin; "tests and practices to drop" answered for one file (RTC-5) |

### RTC-1. No sizes, no total, no critical path

- **Asked:** "edited for efficiency, since the goal is to get this into people's hands".
- **The plan says:** "Sizes are the study's estimates in coding-agent sessions and have run high in the author's experience." It then gives a size only for Safe ("About six or seven sessions for the door, four or five for anchoring") and the Lean trial's agent time per lemma.
- **Gap:** The register has an effort for nearly every package (I1 a day, I2 two to three days plus a day, I3 three to four days, A1 a day, A4 two to three, A5 one to two, A6 two to three, L-G two to three, O1 four to six, F1 to F14 nine to eleven, V5 hours to four days), and `register-notes.md` f says "Only LEAN-§7D estimates a whole; no report sizes the rest or fits it into two weeks." The plan does not fix this. The author cannot see that formalization alone is about half of a two-week push (LEAN-§7D), or that the Overleaf pilot's mirror sits at the end of the longest chain (Safe door, then anchoring, then O1).
- **How bad:** wording; it decides what ships late.
- **Change:** Add a "size" column to every workstream table, from the register's effort cells, and one paragraph naming the critical path: Security → Safe door → anchoring → Overleaf; Install and Attach in parallel; Review after the door. State the total and which gates sit on the critical path.

### RTC-2. Foundations gates every endpoint workstream and is unsized

- **Found:** `register-notes.md` b.20 leaves the registry's timing open: "start it for the viewer's writes now … or after". X2 is "days".
- **The plan says:** "`render/api.py` belongs to Foundations until the operations registry exists, after which a workstream adds an operation, not an endpoint." Foundations' done-when holds eight items: a live viewer in `loom serve`, `scripts/regen`, a three-minute lane, merge on green with macOS and pinned TeX, the safety test, errors and identity out of `cli/`, the registry, and history archived.
- **Gap:** Attach (A1's setup endpoint), Library (L-D, L-G), Install (I4), Overleaf (O1) and Formalization (F5) all add writes; the "Alongside Safe" lanes therefore wait on the registry, which is listed under "First". No pilot ever sees the registry.
- **How bad:** slowed (the release).
- **Change:** Either size X2 and put it on the critical path in RTC-1's paragraph, or defer it to after v0.1 and have Foundations merge endpoint additions to `render/api.py` in sequence (one owner, a queue), so the lanes start at once. Split Foundations' done-when into "needed before parallel work" (live viewer, regen, lane, safety test) and "later".

### RTC-3. A rubric with no measure of the target

- **Asked:** "a criterion and a rubric for grading whether loom has hit the target", the target being that colleagues "pick up loom and immediately use it".
- **The plan says:** "It ships when it meets the bar", seven pass/fail gates. "For the pilots" lists what to watch "to decide what waits".
- **Gap:** Nothing grades whether v0.1 served the pilots once in their hands. The gates are also binary; `state.md` already grades not met / partly / met, but the plan does not adopt levels.
- **How bad:** wording.
- **Change:** Add after the gates: "v0.1 has hit its target when, two weeks after release, each pilot has run their own journey (learning, exploring or proofreading) in at least three sittings without the author's help, has lost no text, and has asked the author fewer than five 'how do I' questions; each question is logged and becomes a Legibility task." Grade each gate not met / partly / met as `state.md` does.

### RTC-4. Tiers against the author's own ranking

- **Asked:** "Zotero is a nice-to-have; everything else here is a must." "Formalization … should be supported in v0.1." Complaint H asks about Quote, versions, compare, split view and transcripts. The philosophy names modes.
- **The plan says:** Highly desirable holds "Zotero through a Better BibTeX export", "Formalization, in its smallest truthful form" and "An agent activity page"; Complete lets formalization "ship a step behind".
- **Gap:** Zotero is promoted above the author's ranking; formalization is demoted below it without his say; the activity page is tiered but owned by no workstream (RTC-11); modes, versions and compare, Quote, and the research-state page (which `explore.md` and `state.md` both say must be kept) appear in no tier.
- **How bad:** wording.
- **Change:** Move Zotero to Nice to have, noting that dragging from Zotero comes free with the window drop once tried by hand (LIB-23 way 2). Write formalization's tier as "the author's call: built for v0.1; whether release waits for it is his". Add to Critical: "the person can start a mode from a selection" (RTC-16), "versions in one place, with compare" (RTC-12), "the research-state page kept". Add Quote to Highly desirable with RTC-12's fix.

### RTC-5. Tests and practices to drop, and extension by others

- **Asked:** "whether there are unnecessary tests and inefficient practices to drop" and "what makes it more extendable by other people".
- **`codebase.md` says:** its ranked table drops one thing, `test_output.py` to one run per case (#7). "What makes it hard to extend" is one paragraph; recipes are deferred "After v0.1".
- **Gap:** The register already holds the list: about 220 static e2e tests of features v0.1 hides (TEST-9), 66 hand-written write mocks (TEST-10), the CLI reference and its test (TEST-13), the figure script in every full run, 45 to 68 s (TEST-14), three Pythons per push (TEST-17), width and theme parametrisations (TEST-16), tracked `.pyc` and `build/` (TEST-19); and practices: plan-per-phase (PROC-37), work-queue rows at 10 to 20 minutes each (PROC-30), the ten review passes read by every agent every session, about 700 words (PROC-45), principle citations in new comments (PROC-33). None is in `codebase.md` as a recommendation. The Lean collaborator is a v0.1 contributor, and nothing tells them how to add a mode or a skill.
- **How bad:** wording.
- **Change:** Add a "Drop" table to `codebase.md` with those items, the time each costs and the condition each waits on (CUT-10: after the safety test). Move two recipes before v0.1: "add a mode" and "add a vendored skill set", a paragraph each.

### RTC-6. `state.md` overstates Complete and names a different five

- **Found:** `state.md`: "Complete … partly … Each can be done today by someone who knows loom and has a terminal." Also "Both failed or struggled on the same five: whether an AI can see my comment; whether one is connected; undoing a Keep; commenting on a sentence …; and leaving a note attached to nothing." `register-notes.md` g: "Both failed or only partly managed (the firmest evidence): 3, 4, 7, 12, 14, 15."
- **Gap:** Overleaf proofreading cannot be done today with or without a terminal: sync publishes rather than mirrors and "has never been run against Overleaf itself" (INST-9); formalization: "Nothing exists in loom". The two "fives" differ: `state.md` includes task 2 and half of 14, and leaves out 12 (adding a paper), the other half of 14 (all notes in one place) and 15 (problems fixable in the app). The plan's Legible gate says "the five tasks both failed" without naming them.
- **How bad:** wording; a builder who takes `state.md`'s five never tests complaints C, D and the errors page.
- **Change:** `state.md` Complete row: "proofreading and learning partly; Overleaf and formalization not at all". Name the tasks in the gate (RTC-33).

## 2. The complaints

| complaint | workstream and done-when that answer it | how firmly |
|---|---|---|
| (A) Review opaque, clunky, buggy, in the way | Review: "Its check above [Quiet]; accept an AI's change and undo it in two actions"; Decision 2; Problems by class in Review's traps | firm on shape and undo; thin on whether a row shows the change (RTC-7); wrong for the Overleaf pilot (RTC-8) |
| (A) "The errors page is almost entirely symptomatic of loom" | Review traps: "Problems: a class for each code; the person sees problems in their own text, including a failed compile, on the document"; Quiet: "Problems lists only problems in the person's own text" | firm |
| (B) Slow, relloc especially | Speed: the Fast gate | named; thresholds weak (RTC-34); agent-call latency absent |
| (C) Library: keys, import, wrong match, agent suggestions, a library page | Library: done-when "Dropping a PDF anywhere leads to one row in one of four states …; the wrong match no longer reproduces; an agent's suggestions arrive as a list with 'Add all'; the page sorts, filters and searches inside papers"; Decision 9 | firm; multi-file drop and paywalled PDFs missing (RTC-25); page text needs poppler (RTC-20) |
| (C) "how many different possible UIs are there upon dropping a pdf? Should be ONE" | Library done-when, four states | firm |
| (C) Zotero | Highly desirable, no owner named | in passing |
| (D) A notes page, sortable, with links to context | Legibility traps: "Also here: the notes page" | in passing; no design, no gate (RTC-9) |
| (E) Drag a tab to the other side | Legibility traps: "Also here: … tab drag" | in passing; not tested by the walks (RTC-10) |
| (E) "The state of loom is generally more ambiguous" | Legible gate | indirect |
| (F) Toolbar large; large, medium and small views | Highly desirable: "A toolbar that folds at medium width"; Legibility traps: "the toolbar's medium size" | in passing; the small view is absent (RTC-10) |
| (G) What an agent sees; can it see my page; is one attached | Attach: Attachable gate (presence chip, "sees what it may read and change", notice) | firm on presence; "what it sees" not in the check (RTC-32) |
| (H) What does highlighting do, can an agent see it | Legibility traps: "A selection offers Comment, and the comment lands on the selection"; Attach's statement panel | partly: how many marking gestures remain is not decided (RTC-12) |
| (H) What does Quote do | nothing | absent (RTC-12) |
| (H) What does annotate do | Legibility traps (annotate on selection) | partly |
| (H) Are my annotations visible to agents | Attach: "a statement of what it sees" | partly: a general panel, nothing on the annotation |
| (H) Where did the agent's work end up; which document | Attach: "a notice when it writes"; activity page in Highly desirable, unowned | partly; the page has no owner (RTC-11) |
| (H) How do I accept a suggested change | Review: Proposed list | firm, but the done-when calls Keep "accept" (RTC-7) |
| (H) Why several ways to see the compiled PDF | Detracting: "three ways to open a PDF" | firm |
| (H) When is a version created; navigate older versions; compare side by side | nothing | absent (RTC-12) |
| (H) How do I open a split view | Legibility traps: "Links open in the same pane unless the person asks for beside" | partly: no control named (RTC-12) |
| (H) How do I see transcripts; what is a transcript | Decision 4 ("the agent's report") | the name yes, the place no (RTC-11) |
| (H) A 1-2 minute video, tour or short readme | Legible: "A two-minute introduction exists"; author's queue 8 | existence only (RTC-13) |
| (H) "features should be intuitive, explain themselves …" | Legible gate | indirect; VIEW-10's "How loom works" panel and legend absent (RTC-12) |

### RTC-7. Review's done-when measures categories, not whether a change can be read

- **Asked:** (A) "I don't know what I'm looking at and I don't trust it. I expect it to show me math that has changed and proposed edits from AI agents, it does those two things poorly."
- **Found:** "No row in either quilt shows a statement an agent changed with the change drawn" (`state.md`, from REV-1); "relloc's 'changed mathematics' is one adoption from nine days ago with no change shown" (REV-1); rows "speak loom: edit ids, `#proof:8` keys, commands and raw `{\color{red}`" (REV-9); a long replacement drawn as all old struck and all new underlined (REV-15); "An unplaced suggested edit cannot be discarded in the viewer" (REV-4, **blocks**); "One change is listed twice with two different acts" (REV-7).
- **The plan says:** Review done-when: "Its check above; accept an AI's change and undo it in two actions". The traps cover the look, authorship, units, Problems and AI documents. None of REV-4, REV-7, REV-9, REV-15 is named.
- **Gap:** Review can meet Quiet (nine rows in ten are the right category) with rows that still show no change, speak in ids, or cannot be discarded. "Accept an AI's change" also uses the word Decision 13 reserves for the badge; the act meant is Keep.
- **How bad:** slowed; the complaint survives the workstream.
- **Change:** Review done-when: "every Changed and Proposed row draws its change in words, in place, rendered, naming the result ('Lemma 2.5'), never an id or a command; an unplaced edit can be discarded; one change is listed once; keep an AI's suggested edit and undo it in two actions." Add walk tasks 7 and 8 to Review's own check.

### RTC-8. An Overleaf pilot's own edits fill Changed

- **Asked:** (A) Review should show "math that has changed" and "not plague the user with irrelevant information".
- **The plan says:** Decision 2: "*Changed*: what changed in the person's documents since they last looked, other than by their own hand: a pull from Overleaf, a document taken in, an edit by an agent where one is allowed."
- **Found:** `check-changed.md`: "Absorbed silently: changes in `[agents] deny` paths …. Not absorbed: adoptions and pulls, with their cause." A pilot who "writes only on Overleaf" makes every one of their own edits on Overleaf, and every one arrives in loom by pull. The replay that set Quiet's threshold covers two quilts with no mirror.
- **Gap:** For the Overleaf pilot, Changed is a list of their own writing plus their co-author's, which is exactly the noise complaint A names. Neither the study nor the plan checked whether Overleaf's git history says who made each change.
- **How bad:** slowed for that pilot, every day.
- **Change:** In Overleaf's traps: "Find whether Overleaf's git commits name their author. If they do, a pull's Changed row shows only changes by others, with 'and N of yours' folded. If they do not, a pull is one row per file, 'N changes from Overleaf', opened in Markup." Add a mirrored quilt with a simulated co-author to Quiet's check.

### RTC-9. The notes page has no design and no gate

- **Asked:** (D) "a notes page … where all the notes across the quilt are exposed and can be sorted/viewed in different ways with links to their context."
- **The plan says:** Highly desirable: "A page of all notes." Legibility traps: "Also here: the notes page".
- **Found:** `register-notes.md` f: "A page of all notes (an author's wish) has a finding (INV-16, WALK-25) and no design." "Notes" today is one annotation type, per document; a person's Plain comments are not in it (WALK-25); a highlight counts as both a comment and a note (SWALK-18); there is no "new note" (SWALK-16); EXP-9 wants "only mine".
- **Gap:** A builder does not know what "a note" is (the Note type, every annotation, the research state, Markdown note files), how it sorts, or when it is done. The Legible gate's "five" (as `state.md` names them) includes a note attached to nothing but not all notes in one place.
- **How bad:** slowed; the author's own complaint can be "done" by a list of Note-type annotations.
- **Change:** Give the notes page its own row in Legibility with this done-when: "one page lists every annotation the person or an agent made, of every type, on every document, Markdown file and work page; filters by type, author (with 'only mine'), document and open or settled; sorts by date and by place; each row opens at its context beside; a 'New note' needs no type change and can attach to nothing." About a day (INV-16).

### RTC-10. Tab drag and toolbar sizes are in passing; the small view is missing

- **Asked:** (E) "I can't drag a tab to the other side"; (F) "a large view …, a medium view which is more collapsed, and a small view which is quite collapsed where tools are grouped under their own drop down icons."
- **The plan says:** Highly desirable: "Tabs that drag between panes and survive a reload. A toolbar that folds at medium width." Legibility traps: "Usable at 760 pixels beside an agent app" and "Also here: … tab drag, the toolbar's medium size".
- **Found:** At 760 px in a split "the Comments button is gone" (WALK-20); VIEW-8: "medium now, narrow with the panes work" (medium hours, narrow two to four days).
- **Gap:** "Usable at 760 pixels" needs the small toolbar the tiers do not ask for; two panes at 760 px are about 380 px each. The walks in Legibility's done-when test neither drag nor toolbar sizes, so both can be skipped while the gate passes.
- **How bad:** slowed.
- **Change:** Tier: "A toolbar in three sizes, the smallest grouping tools under menus." Legibility done-when adds: "a tab drags to the other pane and to a place among its tabs; at 1,440, 1,100 and 760 px, in one pane and in two, every toolbar control is reachable."

### RTC-11. The activity page has no owner, and transcripts lose every other home

- **Asked:** (H) "Where did the agent's work end up? Did they annotate a document, if so which one? … How do I see agent transcripts and what is the agent transcript?" (G) "Is an agent currently 'attached'?"
- **The plan says:** Decision 4: "Sessions stay as the agent's report. The footer and picker go." Detracting: "The session footer and picker." Decision 2 makes Review two lists, which removes The Record. Highly desirable: "An agent activity page." No workstream lists the activity page in its goal, done-when or traps.
- **Found:** CUT-3's verdict pairs hiding "the footer, picker and The Record › Sessions" with "show transcripts as agent reports in the activity page". ATT-7: "No view answers 'what did the agent do today, and where'". `explore.md` step 9: the week was "reconstructable from the research state and the transcript".
- **Gap:** If Legibility hides the footer and picker and Review drops The Record, and nobody builds the page, transcripts are unreachable for the person and "where did the agent's work end up" has no answer but a transient notice.
- **How bad:** stuck (a week-old agent conversation cannot be found without a terminal).
- **Change:** Assign A6 to Attach, two to three days, with done-when: "after one agent conversation, the person finds on one page, newest first, every annotation, suggested edit, AI document and report it made, each opening at its place; the transcript is shown there as 'the agent's report'." Add to Legibility's traps: "hide the footer, picker and The Record › Sessions only in the change that ships the activity page."

### RTC-12. Six of complaint H's questions have no answer

- **Asked:** (H) "what does 'quote' do? … When is a version of my document created, how do I easily navigate between older versions, how do I compare documents side by side? How do I open a split view?" and "state should be obvious and predictable".
- **Found:** Quote copies LaTeX with `\ref{sh-000C}` (WALK-29), mid-word (SWALK-2), and is the only hand-off to the agent. Versions: "When is a version created? only after the fact" (walk C); "the user got the version not intended" (WALK-18); "versions in four places" (VIEW-5). CUT-13: "hide the naming of versions but keep versions; keep compare until Changed ships." The margin's markers and colours need "a legend" (walk.md's list, item 9). "Four overlapping ways to mark text" (walk-small).
- **The plan says:** Nothing on Quote, versions, compare or the legend. Detracting removes "Second and third ways to do one thing", which a builder may apply to versions and compare.
- **Gap:** The questions the author wrote down as a first-time user stay unanswered, and the compare view that `state.md` lists under "must not be broken" is unprotected.
- **How bad:** slowed.
- **Change:** Legibility done-when, as walker tasks with these answers: versions live in the document's history menu, each automatic version names what made it ("before keeping Claude's edit to Lemma 2.5"); compare stays; one control splits the pane; Quote copies the rendered words with "Theorem 3.4" and the document, whole words only; a legend for the margin markers opens from the toolbar; a selection offers two acts, Comment and Quote, and a bare highlight is not a note.

### RTC-13. The introduction has no owner, no content and no test

- **Asked:** (H) "as easy as possible for a new user to pick up loom and immediately use it, perhaps after seeing a 1-2 minute tutorial video or running through a quick interactive tour or reading a short readme."
- **The plan says:** Legible: "A two-minute introduction exists." "Last: the gates": "Then the release, the two-minute introduction, and the pilots." Author's queue 8: "the introduction".
- **Found:** `walk.md` lists what an introduction must say; half of it ("connects through a one-time `loom ai init` in a terminal", "undo a Keep from The Record › Versions › Restore", "Sessions are your AI conversations") stops being true under the plan.
- **Gap:** The gate passes on anything that exists. No one writes the script, no one tests whether a newcomer who has seen it does better, and its format (video, tour, page) is not chosen.
- **How bad:** slowed; the author's stated onboarding path is the least specified thing in the plan.
- **Change:** Legibility owns "the introduction's script and a one-page 'How loom works' reached from the home page and the toolbar's ?" (VIEW-10). The author records the video from the script. The Legible check runs one fresh walker who reads or watches the introduction first; it passes when that walker does the named tasks (RTC-33) and the introduction runs under two minutes.

## 3. The requirements

| requirement | verdict | where |
|---|---|---|
| Deep understanding of why a result is true | partly | the plan's first paragraph; no workstream puts it in the agent's orientation (PROC-16, D11 unowned; RTC-28) |
| AI-generated mathematics and documents welcome | delivered | Decision 3 |
| A clear boundary around what an AI may edit | partly | Decision 1; owner missing (RTC-29); undefined without a paper (RTC-22); Codex (RTC-19) |
| A robust linking system | partly | anchoring in Safe, stable work ids in Library traps; nothing else (RTC-15) |
| Annotations for back-and-forth without rewriting | delivered, with RTC-23 | Critical tier; Markdown annotations |
| Modes make AI mathematics accurate and understandable | partly | Attach traps only (RTC-16) |
| An AI searching many papers for the important results | partly | Library is intake and organisation only (RTC-20, RTC-26) |
| Review exposes load-bearing changes | partly | Changed has no notion of "load-bearing" (RTC-15) |
| Proposed changes easy to accept or decline | delivered locally; not on Overleaf (RTC-24) | Decision 2 |
| No irrelevant information or meaningless chores | partly | Quiet; chores in RTC-24, RTC-25 |
| An application launched and pointed at a quilt or a new one | delivered | Decision 6; Install and launch |
| Drag resources in: paper drafts | absent (RTC-17) | — |
| Drag resources in: library resources | delivered | Library done-when |
| For managing and reading, not an editor | delivered | "Not an editor" |
| CLI mainly for agents | delivered | Decision 5 |
| No human touches the command line | partly (RTC-18) | "After installing, no human types a loom command" |
| Browser tab acceptable, standalone better | delivered | Nice to have |
| Mac required | delivered | Installable |
| Linux hoped for | absent (RTC-14) | — |
| Windows hoped for | deferred by name | Not needed yet |
| Easy to install from GitHub | delivered | Decision 7, Install |
| No integration between quilts | delivered | "One quilt at a time" |
| Not an agent harness | delivered | "Loom calls no model" |
| Formalization supported | partly | Highly desirable, may trail (RTC-4) |
| Overleaf over git, no zip | delivered as a decision; at risk in practice (RTC-24) | Decision 10 |
| Claude Code first, Codex and Gemini checked | delivered as stated; no fallback (RTC-19) | Decisions |
| Breaking changes allowed | delivered | format number |
| An introduction for new users | partly (RTC-13) | Legible |

### RTC-14. Linux is not mentioned

- **Asked:** "Mac required, Linux and Windows hoped for"; pilots "mostly on Macs".
- **Found:** INST-19 rank 5: "Linux in hours, Windows a week+". `tinytex.md`: loom's own TeX "works the same on Linux"; CI already runs on Linux (INST-15). pypdfium2, if chosen for RTC-20, has Linux wheels.
- **The plan says:** Windows in "Not needed yet" and "What waits"; Linux nowhere.
- **Gap:** "Mostly" leaves room for a Linux pilot, who would have no install script.
- **How bad:** slowed for any Linux pilot; nothing for the rest.
- **Change:** Add to Nice to have: "Linux: the install script detects it and uses TinyTeX's Linux build; tried once in a container." Promote it if the pilot survey (RTC-19) finds a Linux user.

### RTC-15. "A robust linking system" has no workstream

- **Asked:** "A robust linking system exposes connections between sources." "Review should expose when load-bearing mathematics has changed."
- **Found:** CUT-4 lets the graph go only if "ContextItem's rest-on and used-by lists must stay". WALK-24: the cited-paper view ("used here", "used by") is "strong". LTRIAL-3: "the closure omits definitions reached through macros …, and `loom downstream sh-0003` omits it", so a definition's change does not reach the results that use it. `review.md` §4: a Changed row should say "you had accepted it; N results rest on it".
- **The plan says:** Detracting: "The graph view." Nothing protects the lists. LTRIAL-3 appears only in Formalization's traps ("the record carries its own map"). Decision 2 does not mention what rests on a change.
- **Gap:** The philosophy's linking system has no named v0.1 face, the part of it a pilot sees is unprotected by the cut that hides the graph, and "load-bearing" is not computed or shown.
- **How bad:** slowed.
- **Change:** Critical tier: "The links a person sees: a citation opens the cited result beside, hover previews, 'rests on' and 'used by' on every result, `cited:` links that survive a work's correction." Detracting: "The graph view (keep ContextItem's rests-on and used-by lists)." Decision 2: "a Changed row on a statement says how many results rest on it." What waits: "dependencies reached through macros (LTRIAL-3) for everything other than formal records."

### RTC-16. Modes are not reachable by the person

- **Asked:** "Modes help make AI-generated mathematics accurate and human-understandable."
- **Found:** INV-22: "A person cannot start a mode from the viewer." ATT-9: "Ask an agent" exists only for a work's overview. LIVE-14: the command line lists modes as `/mcp__loom__<mode>`; the Code tab is untested. b.15 (nine files or five) is open; CUT-12 measured relloc using six separately.
- **The plan says:** Attach traps: "Modes appear as commands in the command line; whether the Code tab lists them is unknown, so also write each mode as a project skill."
- **Gap:** A pilot who never types `/` never meets a mode, and nothing tells them they exist.
- **How bad:** slowed; one of the philosophy's four mechanisms is invisible.
- **Change:** Critical: "From a selection or a result the person can ask for a mode (ask, check, referee, simplify, formalize), which copies the request to paste into the agent app." Decide b.15 in Decisions: keep the nine files, offer five in the viewer (CUT-12). The introduction names them.

### RTC-17. Dragging in a paper draft has no owner

- **Asked:** "you drag resources in (paper drafts, library resources)".
- **The plan says:** Critical: "a window that takes a dropped paper". Library's done-when: "Dropping a PDF anywhere leads to one row". Install's done-when is the clean-Mac run.
- **Found:** INST-16: "a paper's `.tex`, a source archive or a folder can come in only through `loom import` on the CLI"; WALK-28: "dropping a `.tex` on the file tree did nothing". I4 (window drop and an import endpoint) is "2-3 days" and owned by no workstream in the plan.
- **Gap:** A learner's or explorer's own draft, as a folder or `.zip`, has no path in. Every dropped PDF goes to the library, including the PDF of the person's own draft.
- **How bad:** stuck for any pilot whose paper is not on Overleaf.
- **Change:** Install and launch owns I4. Done-when: "dropping a paper's folder, `.zip`, `.tar.gz` or `.tex` on the home page makes a quilt with it typeset; dropping one on an open quilt adds it as a document of the person's, as a row in the same tray as the library's."

### RTC-18. Three ways the plan still sends a person to a command line

- **Asked:** "no human should ever have to touch the command line for loom to be useful".
- **The plan says:** "After installing, no human types a loom command." And, for the pilots: "how to report a problem (an issue with what `loom doctor` prints)".
- **Found:** The pilot page itself requires a command. Texts the agent relays still say "run it in a terminal of your own", `loom serve starts the viewer`, and "next: cd mypaper, then loom doctor; loom lint" (LIVE-18, ATT-12). A new quilt's front door is a README "teaching `loom new`, `loom library add`, `loom ai init` and `loom upgrade`" (LIVE-3). The Legible gate checks screens, not what an agent relays, and walks only the showcase.
- **How bad:** slowed.
- **Change:** Settings shows doctor's report with "Copy report" (INV-24); the issue template asks for it. Attach's done-when adds "no string an agent is given tells the person to type a command" (A8). Install's done-when adds "a new quilt opens on its document, never on a README of commands".

### RTC-19. A Codex pilot has no fallback

- **Asked:** pilots use "Claude Code in the Claude desktop app or Codex"; "Build for Claude Code; a manual Codex and Gemini check before shipping."
- **Found:** Codex's own edits ignore deny (ATT-11); CUT-7 condition 1 rests on it; `check-changed.md`: "Codex left none on this machine …, so CUT-7's first condition … was not exercised". Whether Codex loads the project's MCP server at all is unknown (ATT-4).
- **The plan says:** "Codex and Gemini get a manual check before shipping"; the check is in "Last: the gates".
- **Gap:** Decision 1 and Changed are designed and built before anyone knows whether they hold for a pilot who uses Codex. If the check fails at the end, the plan does not say what ships to that pilot.
- **How bad:** stuck for a Codex-only pilot if ATT-4 fails.
- **Change:** Author's queue, first item: ask the pilots which agent app, which TeX, whether Homebrew, Zotero, Overleaf (and whose plan), screen size, and operating system. If any uses Codex, run ATT-4 and ATT-11 before Review builds Changed. State the fallback: the shell route, the panel saying deny is not enforced in Codex, and Changed showing changes in denied paths as "changed outside loom" (CUT-7).

## 4. The three journeys, walked under the plan

Each step assumes every workstream has met its done-when. "Stop" marks a place the plan as written leaves the pilot stuck, confused or doing a chore.

### A graduate student learning from a textbook and two papers

| step | what happens under the plan | stop |
|---|---|---|
| 1. Pastes the install line | script installs uv, loom, loom's TeX and Loom.app (Decision 7) | — |
| 2. Opens Loom.app, New quilt | home page; asked their name once | which folders are "theirs" in a quilt with no paper? Decision 1 assumes a paper's directory (RTC-22) |
| 3. "Use with Claude" | files written; card says to trust the folder in the Code tab | if the Code tab does not trust on folder pick, every loom call prompts (author's queue 1; RTC-32) |
| 4. Drops the textbook (a 600-page scan, no DOI) | tray: Added "Statistical Inference — Casella, Berger", "Ready, scanned" | the agent cannot read it through loom (QF-6); nothing tells it to open the PDF pages itself (RTC-21) |
| 5. Drops the two papers | network asked once; keys like `perelmanRicciFlowSurgery2003` | on a Mac without Homebrew, no page text: `library read` and `--pages` search fail (INST-8; RTC-20) |
| 6. "Write me a lesson on chapter 3" | agent writes Markdown in its own place; notice appears | — |
| 7. Selects a sentence in the lesson, comments | Markdown annotations (Critical, after Safe) | does the agent see it? a general panel says agents read annotations; the student must still go to the agent app and ask (no "Ask" on a selection, RTC-16) |
| 8. Agent rewrites the lesson outline | agent's place; left out of Changed | the old outline is gone: agents' places keep no versions (CUT-14d, QF-36; RTC-22) |
| 9. Writes homework in LaTeX, asks for grading | agent files feedback | if it files feedback as edits, as quant's agent did with 29 `{\color{red}…}` edits, Proposed fills with noise that Quiet counts as proposed edits (RTC-23) |
| 10. "Where are all my notes?" | a notes page (Highly desirable) | unspecified; may list only Note-type annotations (RTC-9) |
| 11. Updates loom with the same line | home server restarts the viewer | the agent app's running `loom mcp` mixes versions silently (LIVE-16); A13 is not in the plan |

### A postdoc exploring a question

| step | what happens under the plan | stop |
|---|---|---|
| 1-3. Install, new quilt, attach | as above | as above |
| 4. Drags in their draft's folder | no owner, no done-when (RTC-17) | **stuck** without a terminal |
| 5. Cold open | default document within 90 s (Fast) | — |
| 6. Marks the open lemma with a Question | works today (`explore.md` step 1) | — |
| 7. Agent attempts in an AI document | read beside the paper; `\incomplete` drawn (Learner done-when) | references outside the copied section print "??" (EXP-8, unregistered; RTC-27) |
| 8. Agent records a dead end | "Dead end" type (Learner done-when) | the agent is not told to read what was tried first, so it re-derives a recorded dead end (EXP-2, unregistered) |
| 9. Agent tests a claim with a script | script in the session folder | the evidence cannot be opened from the viewer (EXP-5, unregistered) |
| 10. "Is this known?" | agent searches the library | with few works digested and no page text without poppler, the answer is thin (RTC-20, RTC-26) |
| 11. Proof works; takes it into the paper | "Take into my document" without a terminal (Review traps) | — |
| 12. A week later, "what happened?" | research state; transcript | the transcript's home is the unowned activity page (RTC-11) |

### A researcher proofreading a draft on Overleaf with a co-author

| step | what happens under the plan | stop |
|---|---|---|
| 1. Install | as above | on a fresh Mac, git is the Command Line Tools shim; the mirror runs on git (INST-7; not in the plan) |
| 2. New quilt from an Overleaf link | the home page's New calls O1's endpoints (I3) | the pilot's project must be on a premium plan (INST-9); no one has asked (RTC-24) |
| 3. "Proofread section 3" | annotations and suggested edits on the mirrored document | — |
| 4. Keeps twenty suggested edits | "Copy new text / Done in Overleaf" (CUT-5) | twenty trips to find the place in Overleaf and paste: the chore the author's philosophy rules out (RTC-24) |
| 5. Agent proposes a rewrite as an AI document | "Take into my document" | cannot write a mirror; the plan does not say what happens (RTC-24) |
| 6. Co-author edits on Overleaf; "Update" | pull; annotations follow (anchoring) | the pilot's own Overleaf edits arrive in the same pull and fill Changed (RTC-8) |
| 7. Formalizes a lemma | 10.7 GB, prompts per command family, attest card in Proposed | may not exist in v0.1 ("a step behind") |
| 8. The release date | Overleaf "may ship a step behind if the author says so" | this pilot's whole use is the mirror (RTC-36) |

### RTC-20. Without Homebrew there is no page text

- **Asked:** "The library should let an AI search many papers to find precisely the important results."
- **Found:** `install.md`: without poppler "there is no page text (`MapRefused`, `src/refs/pages.py:118-125`), so agents cannot read or search it through loom and marks have no words"; "The only remedy loom gives is `brew install poppler` …, and a fresh Mac has no Homebrew." INST-8 offers pypdfium2, two to four days.
- **The plan says:** Decision 7: "How diagrams and PDF figures render without Homebrew is **open**: settle it first with a short trial (ship Ghostscript, or convert figures another way)." Installable checks "a typeset paper, diagrams and figures included".
- **Gap:** The open question is framed as pictures only. A clean Mac passes Installable and leaves every library PDF unreadable to the agent, along with marks' words and the import identity test.
- **How bad:** stuck: the learner's books and the explorer's search do not work.
- **Change:** Decision 7: "How pictures render and how PDF page text is read without Homebrew is open; settle both in the trial (pypdfium2 for text and pictures, INST-8, or ship poppler)." Installable's check adds: "a dropped born-digital PDF's pages are readable and searchable by the agent".

### RTC-21. A scanned textbook is closed to the agent

- **Found:** QF-6: "`loom library read Cas 80` prints the header line and no text"; "an agent can't help with that book". LIB-15: OCR deferred, "say it plainly". QF-8: the rules say "Inputs come from loom commands, never from reading directories". Claude Code's own Read tool reads PDF pages as images.
- **The plan says:** Library traps: "A textbook has no DOI and may be a scan."
- **Gap:** For the learning journey the main book is often a scan, and the plan closes it to the agent when the agent app could read it.
- **How bad:** slowed.
- **Change:** Learner workstream: "`library read` on a page with no text says so and gives the PDF's path and page; the orientation tells the agent to read such pages from the file." Hours.

### RTC-22. Zones for quilts without a paper, and no versions in agents' places

- **Found:** `check-changed.md` condition 2: "`[agents] deny` covers every directory the person edits, at `init` and `import`." QF-36: "A large edit to a Markdown file has no undo" (hurts, "the damage bar"). CUT-14d: "Agent copies have no versions"; relloc's agents kept "ten 600 KB snapshots of the copy by hand".
- **The plan says:** Decision 1: "New quilts deny agents the person's document folders. One panel in the viewer states this." Review traps: "Places agents own are left out of the look."
- **Gap:** A learner's or explorer's quilt has no paper to name its folders, a folder made later has no zone, and the settings that assign zones are "written for programmers" (WALK-10). An agent's rewrite of a lesson, an outline or an AI document is unrecoverable.
- **How bad:** slowed; for a learner whose lessons are the agent's, data loss.
- **Change:** Decision 1 adds: "A quilt without a paper asks once which folders hold the person's own writing; a folder in the tree can be marked 'mine' or 'the agents'' in one click." Safe adds S3's versions of agents' places (hours).

### RTC-23. Feedback filed as edits counts as "proposed edits"

- **Found:** REV-1: "quant's 'proposed edits' are an agent's grading comments"; `review.md`: "29 ready suggested edits …, each inserts a `{\color{red}…}` comment into the learner's answer: feedback sent as an edit".
- **The plan says:** Quiet: "nine rows in ten … are changed mathematics or a proposed edit".
- **Gap:** The gate counts the noise as signal; the agent's rules do not separate feedback from edits.
- **How bad:** slowed.
- **Change:** Attach (agent texts): "a finding or a comment is an annotation; a suggested edit is text the person would keep as written." Quiet's check classifies an edit that inserts a remark as noise.

### RTC-24. The Overleaf pilot: chores, sequencing and an unconfirmed plan

- **Asked:** Overleaf "over git"; review "in an easy accept-or-decline way" without "meaningless chores".
- **Found:** INST-9: "Overleaf's git is a premium feature"; `register-notes.md` e: "confirm the Overleaf pilot's owner has premium git". INST-10: Keep on a mirror becomes "Copy new text / Done in Overleaf".
- **The plan says:** Author's queue 6: "An Overleaf project with git access for the mirror" (the author's own). Overleaf "Depends on Safe's anchoring", placed "After Safe". Complete: "exploring, Overleaf and formalization may ship a step behind if the author says so." Review traps: "Take into my document" must work "on a paper split into files"; nothing for a mirror.
- **Gap:** If the pilot's project owner is not on a paid plan, four to six days of O1 serve no one. Every kept edit is a manual round trip. An AI document cannot be taken into a mirror. The pilot's only use arrives last on the longest chain and may be cut from the release.
- **How bad:** stuck.
- **Change:** Author's queue, before O1 starts: confirm the pilot's plan. Complete: "Overleaf must pass if the Overleaf pilot is in the first group." Overleaf done-when adds: "kept edits on a mirror gather in one list, each with its location and new text, copied in one act; an AI document on a mirror offers the same list." Sequence a read-and-annotate mirror (fetch, render, annotate) before anchoring lands, and let anchoring improve it.

### RTC-25. "Add all" leaves paywalled PDFs to the person

- **Asked:** (C) "agents often suggest a dozen references which I must manually import myself"; "I use Zotero to download, click 'Show in finder', drag the pdf".
- **The plan says:** Library done-when: "an agent's suggestions arrive as a list with 'Add all'".
- **Gap:** "Add all" adds entries and fetches what arXiv and open sources give; journal papers still need a download, a Finder trip and a drop each. Dropping twelve PDFs at once is not in the done-when (LIB-11: "dropping twelve PDFs adds one, silently").
- **How bad:** slowed: the chore shrinks but stays.
- **Change:** Library done-when: "'Add all' fetches every open-access PDF and source; the rest wait under 'Needs a PDF' with a link to each publisher page; a drop of many PDFs pairs each with its waiting entry through the one question."

### RTC-26. The library's search for results is neither evaluated nor planned

- **Asked:** "The library should let an AI search many papers to find precisely the important results."
- **Found:** `codebase.md` "Not examined: … the library's digest building and search beyond intake". `explore.md` step 5 ran on five works, two digested. P5 moves digests to "on demand".
- **The plan says:** Library: "One predictable way in, and a library that holds up when large." All its done-when items are intake, keys, suggestions and the page.
- **Gap:** Nothing checks that an agent can find "precisely the important results" across a real-sized library, or says when digests are made once they are on demand.
- **How bad:** slowed; the promise may fail silently.
- **Change:** Complete adds: "in a quilt of thirty or more works, the agent answers 'is this lemma known?' with page-level citations." Speed's traps say when a digest is made under P5 (on first open, or by a mode).

### RTC-27. `explore.md` is not in the register

- **Found:** `register.md` registers fifteen reports and a log; `explore.md` is not one, and no EXP id appears in `register.md` or `register-notes.md`. `register-notes.md` f still says "the EXPLORE journey (no report tries it)".
- **The plan says:** "read this file, then your workstream's heading in `register.md`". The Learner row cites `raw/explore.md`; the done-when covers EXP-1 (unproved steps) and EXP-6 (types); Review's traps cover EXP-4.
- **Gap:** EXP-2 (a recorded dead end not found and re-derived), EXP-5 (evidence hidden; "What it did" empty for shell agents), EXP-7 (no single place says what is open) and EXP-8 ("??" in section copies) reach no builder.
- **How bad:** slowed for every explorer.
- **Change:** Register EXP-1 to EXP-10 under heading 8; correct notes f. Learner done-when adds: "before an attempt the agent reads the question's annotations and research-state entry (rules and the question mode); a session's files open read-only from its report; a section copy's outside references resolve."

## 5. Findings left behind

The plan's mechanism is a pointer from each workstream to a register heading. Safe's row has no such pointer (every workstream but Security, which points at `raw/security.md`, says "Register N"), so heading 1's rows that are not SAFE faults are owned by no one. The table below lists every "blocks" finding, and every "hurts" a pilot meets in the first week, that no workstream names in its goal, done-when or traps and that the plan does not defer by name. "Pointer only" means the row sits under a workstream's heading but nothing in the plan would make a builder do it.

### RTC-28. Orphaned findings

| id | weight | what a pilot meets | status |
|---|---|---|---|
| CUT-14a | **blocks** | "a suggested edit with no quote on a section key deletes the section's heading and label"; the rules invite the call | orphan: heading 1, no pointer from Safe, not among the harness's nine expected failures |
| REV-4 | **blocks** | an unplaced suggested edit cannot be discarded; a waiting edit is "stranded for good" | pointer only (Review) |
| SAFE-11 (path) | hurts | `history-restore` with a `path` "writes outside the quilt" | orphan: not among the five security fixes; not in Safe's traps |
| REV-10 | hurts | an editor saving a stale buffer undoes a kept edit "and nothing says so" | orphan: the door "cannot make safe" it; reporting it is nobody's |
| QF-36, CUT-14d | hurts; not graded | an agent's rewrite of a lesson or AI document cannot be undone | orphan (RTC-22) |
| PERF-copy | not graded; met by anyone who copies a quilt | a copied quilt carries the original's `serve.json`, so `loom serve` on the copy refuses | orphan |
| ATT-7, LIVE-11 | hurts | no answer to "what did the agent do, and where" | tiered, unowned (RTC-11) |
| ATT-9, INV-22, WALK-29, SWALK-2 | hurts | no "ask about this"; Quote hands over LaTeX and internal labels, mid-word | orphan (RTC-12, RTC-16) |
| ATT-12, LIVE-18 | hurts | the agent relays "run it in a terminal of your own" | pointer only (RTC-18) |
| LIVE-3 | cosmetic by its report; a command screen by the plan's rule | a new quilt opens on a README of commands | pointer only (RTC-18) |
| LIVE-16, QF-41 (the `code_stamp` half) | hurts | after an update the agent's server mixes versions silently | pointer only; Decision 13 freezes names, not versions |
| LIVE-7 | hurts | a page whose server stopped "carries on with no banner" | pointer only |
| INST-7 | hurts | the Command Line Tools dialog on a fresh Mac when loom or the mirror runs git | pointer only; not in the Installable check |
| VIEW-10 | hurts | no help, no legend, no visible search | pointer only (RTC-12, RTC-13) |
| WALK-6 | slows them | the page jumps 110-240 px on every comment | pointer only |
| WALK-14, REV-9 | slows them | raw LaTeX and ids in tooltips, cards and Problems | pointer only (RTC-7) |
| QF-24, QF-33 | hurts (misleads agents) | wrong section labels on book pages | pointer only |
| PROC-16, D11 | not graded | the agent is never told the person is trying to understand | orphan between Foundations (docs) and Attach (`assets/ai/`) |
| EXP-2, EXP-5, EXP-8 | hurts | see RTC-27 | unregistered |
| ATT-3, INV-6, LIVE-12, REV-5 | **blocks** | the defaults that make Decision 1 real | no owner (RTC-29) |

- **How bad:** stuck for CUT-14a (Keep destroys a heading and label) and Decision 1's defaults; slowed for the rest.
- **Change:** Add "Register 1" to Safe's row and name CUT-14a, SAFE-11's path containment and REV-10's report ("a kept edit is no longer in the file") in its traps. Give each other row above an owner in that workstream's traps, or a line in "What waits".

### RTC-29. Decision 1's defaults have no owner

- **Found:** S6 owns `scan/quilt.py:66`, `cli/quilt.py:39-42`, `cli/paper.py`, `ai/layout.py` and `assets/ai/orientation.md:30`; `register-notes.md` a.1: "A change of default must change both". Three live confirmations that today an agent's edit "shows nowhere" (LIVE-12, SMALL-4, ATT-3).
- **The plan says:** Decision 1; Critical: "A new quilt in which agents propose changes to the person's documents and cannot write them"; Safe's check: "An agent's edit to a person's document is either refused or shown."
- **Gap:** Safe owns neither file; Install owns new-quilt creation but not its defaults; Attach owns `assets/ai/` but not `cli/quilt.py`. The gate checks a change no workstream is told to make.
- **How bad:** stuck: the boundary, the plan's central promise, can be left at `deny = []`.
- **Change:** Install and launch owns S6 (it owns new-quilt creation), with Attach changing `orientation.md:30` in the same change. Install's done-when adds: "a new quilt made from a paper denies agents its folders, and the panel says so."

## 6. The rubric's teeth

### RTC-30. Safe

- **The check:** "The write-safety test passes with no expected failures left, and a few hundred random sequences on three quilts do no damage …. The anchoring harness puts no record on the wrong block across its seven papers."
- **Passes and still fails the person:** The harness drives five writes: `change-keep`, `change-discard`, `history-restore`, `file-tick`, `settings-save` (counted in `safety-harness/harness/`). v0.1 keeps or adds other writes to a person's file or records: "Take into my document" (adoption), Overleaf pulls, library filing and unfiling (LIB-1 to LIB-5: "the one place in the library where loom can damage the person's records"), suggested edits and annotations on Markdown. None is exercised. The nine expected failures do not include one-step undo (SAFE-9) or CUT-14a. The anchoring bar counts wrong placements only; today's code "detached 615 and lost 960" of 4,693, and a design that detaches everything would pass.
- **Fails for a reason that does not matter:** the spike's five remaining damaged sequences were "all refused second Keeps"; whether a refusal counts as damage is not said.
- **Change:** The check adds: "the random sequences include adoption, a sync pull, library file and unfile, and Markdown suggested edits; one-step undo of every write restores the exact bytes; the anchoring harness puts no record on the wrong block and detaches or loses no more than N% (set from `check-labels.md`'s safe design); a refused act is not damage."

### RTC-31. Installable

- **The check:** "The author runs it on a clean Mac or a virtual machine and counts: one line, no loom command afterwards."
- **Passes and still fails the person:** The paper is unnamed, so the showcase passes; "real papers needed four, eight and twenty rounds of fetching missing packages" (`state.md`). "No TeX and no Homebrew" leaves the Command Line Tools unstated (INST-7). Page text is not checked (RTC-20). Whether the locally written Loom.app opens without a Gatekeeper prompt is unverified (`register-notes.md` d #11).
- **Thresholds:** "one line" is defensible from `live.md`'s count of four commands today.
- **Change:** "On a clean Mac without TeX, Homebrew or the Command Line Tools: one pasted line; Loom.app opens with no Gatekeeper prompt; three real papers (the ones that needed four, eight and twenty rounds) typeset with their figures; a dropped born-digital PDF is searchable by the agent; no loom command afterwards."

### RTC-32. Attachable

- **The check:** "A fresh quilt, 'Use with Claude', one plain request: the agent's comment appears with a notice, with no typed command. The chip says 'connected' only while a server process is alive."
- **Passes and still fails the person:** Where it runs is unstated; the command line here was never signed in, and the Code tab, where pilots work, is untested (`state.md`). If picking a folder is not trust, "every loom call prompts" (`register-notes.md` d #3), and the check still passes. "Sees what it may read and change" is in the gate's description, not its check.
- **Change:** "In the Code tab of the Claude desktop app with a real model: at most two approval prompts from setup to the agent's first comment; the panel answers 'can it see my page?' and 'can it change my paper?' in words a walker repeats correctly."

### RTC-33. Legible

- **The check:** "The two first-time-user walks are run again by fresh agents …: the five tasks both failed now succeed for both, the stronger walker achieves seventeen of eighteen, and no screen shows a terminal command. A two-minute introduction exists."
- **Passes and still fails the person:** The walkers are language models driving synthetic DOM events; `walk.md` warns that "about a third of what I learned came from tooltips" it hovered on purpose. The five are unnamed and disagree between documents (RTC-6). The walks run on the showcase only, so the pilot's own new quilt (LIVE-3), Markdown, the library page, Overleaf and the notes page go unwalked. 760 px is required by Legibility's traps but not re-walked. Which one task of eighteen may fail is unstated. The introduction need only exist.
- **Change:** Name the tasks: 2, 3, 4, 7, 12, 14 (both halves), 15, plus RTC-12's six questions and RTC-10's drag and toolbar. Run them at 1,440 and 760 px, on the showcase and on a new quilt made from a pilot-like paper, after the introduction (RTC-13). Add one human: a colleague who has never seen loom does tasks 2, 3, 4 and 7 while the author watches and does not help.

### RTC-34. Fast

- **The check:** "On the showcase: under 1 s. On a quilt of relloc's size: first sight within 5 s and typeset within 20 s; a write from the viewer answers within 1 s; a first open shows the default document within 90 s".
- **Passes without improvement:** "Under a second on the showcase" is today's figure (`state.md`). Save to seen on relloc is "9-15 s" today including the snippet's TeX run (PERF-2), so "typeset within 20 s" is already met. Complaint B ("loom is slow, particularly the relloc quilt") is answered by thresholds it already meets, except first sight and first open.
- **"Nothing typed is lost" is not checked:** EXP-3 lost keys at write latencies of 1.29-1.52 s and found the cause is that keys are captured only after the write returns; at 1 s, typing at 110 ms a key still loses about nine characters.
- **Outside the gate:** agent calls, "1.5-1.7 s" for search and source and "5.8-7.1 s" for status without an author name, so "an agent making 40 calls waits 1-4 minutes on loom" (PERF-10). The cheap half of P6 (keep one scan in the MCP server, "a day") is deferred together with in-process tools.
- **Change:** "relloc: typeset within 8 s of a save (speed.md's target with changes 1, 2 and 4 is a first publication in 3-4 s, the block's typesetting 2-3 s later); keys typed straight after marking all reach the comment (a test that types at 20 ms a key); a typical agent call under 1 s." Move P6's first half to Highly desirable.

### RTC-35. Quiet

- **The check:** "nine rows in ten on copies of the author's quilts are changed mathematics or a proposed edit … Replaying a month of history gives no list over twenty-five rows".
- **Passes and still fails the person:** It counts categories, so comments filed as edits (RTC-23) and rows with no change drawn (RTC-7) pass. Two quilts by one person, both of which already deny the person's folders, with no mirror (RTC-8) and no Codex (RTC-19). The twenty-five-row ceiling sits just above the design's simulated worst of 23 (`check-changed.md`), so it checks the build against its design, not against a pilot.
- **Change:** "On the author's quilts, a mirrored quilt with a simulated co-author, and a new quilt after a week of an agent's work: nine rows in ten are a change the person would act on, each drawing the change; the person's own edits appear in no row."

### RTC-36. Complete

- **The check:** "Three scripted journeys played by an agent pair, as in `raw/explore.md`; the library's one-flow test; the Overleaf mirror on a real project; one lemma formalized …" and "exploring, Overleaf and formalization may ship a step behind if the author says so."
- **Passes and still fails the person:** "An agent pair" with no real model in the Code tab (`state.md`: "No trial used a real model inside Claude Code's own connection"). Overleaf "a step behind" means the Overleaf pilot, one of two to four, gets a v0.1 they cannot use.
- **Change:** "Each journey in the Code tab with a real model, the person's side played by the author; Overleaf passes if the Overleaf pilot is in the first group; each journey starts from the install line, not from a prepared quilt."

### RTC-37. Essential and outside every gate

- **The typeset paper looks right.** WALK-35: "a mathematician judges the tool by how the paper looks"; `codebase.md` did not examine the TeX-reading core. Add to Complete: "each pilot's own paper reads correctly in the viewer: numbering, references, figures and equations match the PDF."
- **An update leaves the quilt and the agent working.** The format number is planned; the agent's stale server (LIVE-16) and the "loom is not running" banner (LIVE-7) are not. Add to Installable: "running the line again updates loom, restarts the viewer, and the open agent conversation is told to restart its server."
- **A pilot can report a problem without a terminal** (RTC-18).
- **The library finds results** (RTC-26).

## 7. What to cut

### RTC-38. What a pilot would not miss in the first month

| cut | evidence | saves |
|---|---|---|
| Hide Accept (the badge and its act) for v0.1; keep the ledger | The author has accepted nothing: "0 of 2,011 keys have a row" (`review.md` §1), "0 acceptances" in both quilts (CHG-8). Hiding it removes the Accept/Keep confusion (SWALK-8; walk.md item 7), the reviewer-name refusal (VIEW-14) and the compile Accept needs (REV-13). Formal staleness no longer rests on acceptance (LTRIAL-4, R6). | part of R-E and R-V; one concept less in the introduction |
| "These two names are one person" | It repairs the author's quant records (QF-25); a pilot is asked their name once by the new-quilt flow. Repair quant by hand. | a records feature in Safe's traps |
| The operations registry before v0.1 | No pilot sees it; it gates every endpoint lane (RTC-2) | days, and a precondition |
| Zotero through the Better BibTeX export (way 1) | The author ranked Zotero nice-to-have; dragging from Zotero comes free with the window drop if it works in a browser (LIB-23 way 2; to be tried by hand, unverified #17) | a day |
| The library page's extra sorts, "last opened", grouping and bulk acts | A pilot's month-one library is small; "nothing breaks at 200 or 1,000 in speed" (LIB-18). Keep search (including inside papers), date-added order and the Suggested and Needs-a-PDF filters. The author's own large library is the case for the rest, after release. | part of L-F; "last opened" needs a new per-person record |
| Release waiting for formalization | Already allowed by Complete; make it the default rather than the exception. It is nine to eleven days and "would displace roughly half of a two-week schedule" (LEAN-§7D). The proofreading pilot can try it in a later update. | the release date |
| A window of loom's own | Already Nice to have; confirm it is out | 1-2 days |

Not to cut, though it looks cuttable: anchoring (the Overleaf pilot and anyone editing beside annotations need it), the exploring conventions (hours), the notes page and tab drag (the author's own complaints), and the five security fixes (each small; SEC-1 turns a prompt injection into code execution).

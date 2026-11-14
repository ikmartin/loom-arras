# v0.1 study, walk2: first-time user walk through the showcase quilt

Tester: a first-time user (mathematics graduate student), reporting only from what the running application and the project folder showed. I did not read loom source, docs, tests or other testers' reports. The only loom command run was `loom serve --port 48160` in a copy of demos/showcase, with XDG_CONFIG_HOME set to a folder inside my test folder. Browser at 1440 px wide. Screenshots are in /private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/walk2/shots/ and my running log is /private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/walk2/log.md.

Action counts are approximate (clicks, drags, typing, and reads of the screen counted together).

## Part A: first sight, before any click

My guesses were: a project tree on the left titled "The loom showcase" with Docs and Review tabs; a main pane showing README.md as prose; red "AI" badges on files (an AI wrote or can see them, I guessed); a grey "view" dropdown; a bottom-left bar "not writing in a session" (an AI session status, I guessed); a collapsed "Library 5" (references, I guessed); and Review as where an agent's findings or suggestions wait.

Wrong guesses: I did not expect Review to be split into Your Changes, Proposed Changes, Problems, Library and The Record. I did not know what the "AI" badges meant and still do not. The guess that Library holds references was right.

## Part B: tasks

### Task 1, read a theorem and its proof: DONE, about 4 actions

Outline entry "3.1 Bounded balanced weightings" scrolled the paper to Theorem 3.4 (Counting) and its proof. The proof is in the typeset page, labelled "Proof." and ending with a small square. Screenshot B1-02-section3.

### Task 2, select a sentence in the proof and leave a comment: DONE with difficulty, about 11 actions, anchor is wrong

The first drag selected a phrase in Definition 3.3, and a "Quote" pill appeared (see C2). Second, I selected a proof sentence and pressed the speech-bubble icon in the top-left toolbar. It switched on a mode whose banner said "Comment is on. Click where the comment should go. Esc stops." Clicking in the paper opened a comment box whose dashed outline covered the whole proof paragraph, not the sentence I had selected. Screenshot B2-04-comment-placed.

My first attempt was lost: a batch click landed on the status banner text, the draft disappeared with no message, and the Comments count stayed at 14. Screenshot B2-05-check. The second attempt saved: author "ikmartin", date Nov 13, a yellow mark on the word "Proof", Comments 15. Screenshot B2-07-attempt2-submitted.

### Task 3, can an AI assistant see the comment: NOT DONE (unclear), about 6 actions

I looked for a sign of an assistant attached to the project and found none that says whether it can read my comment. The Review page and the Sessions table (see task 4) are the only places that mention sessions, and neither says what a session can see. I stopped here rather than guess.

### Task 4, is an AI assistant connected right now: PARTLY, about 4 actions, answer is contradictory

The bottom bar says "not writing in a session". Its popup lists "WRITING INTO" with two sessions (referee-sh-0009, Sep 16; survey-bellamy, Sep 15), each with a blue dot, plus "CLOSED (2)" (reading Bellamy 19, quick-pass). The Record's Sessions tab says "Not writing in a session" at the top and lists the two sessions as "open" with "Write here". I could not tell whether an open session is connected, and the two messages look contradictory. I did not click "Write here", since that would change state. Screenshots B3-02-session-bar, B4-02-sessions.

### Task 5, find something an AI wrote or proposed, and how I know: DONE, about 4 actions

Your Changes lists two suggestions from "Referee (Agent)", dated Sep 16, with Keep and Discard buttons, and the sidebar item Proposed Changes says "from agents and collaborators" with one result from the Bellamy paper and a "Check them" button. I knew the work was an AI's from the "(Agent)" name on the card. Screenshots B3-01-review-tab, B5-01-proposed.

### Task 6, read an AI change, accept it, then undo it: DONE with great difficulty, about 18 actions

Reading the change: the Changes dropdown in the document toolbar offers a Markup view (removed words struck through, new words underlined) and a Final view. Markup showed the change clearly. Screenshot B6-03-changes-menu. Clicking the teal text itself opened nothing.

Accepting: I used Keep on the Theorem 3.1 suggestion in Your Changes, which wrote the sentence into the file with no confirmation. Screenshot B6-05-after-keep. Your Changes then had "1 change waiting".

Undo: the paper's undo arrows were greyed out, and Cmd+Z in the text did nothing visible. The history dropdown has no undo, only "record this version", "live text", and version rows with "compare". I compared flows-v2 with the live text, which showed two green-marked differences. Then in The Record, Versions, flows-v2, "Restore this version" asked "Put main-atomic.tex back as it was on Sep 17? Its text now is kept as a version." After Restore the Record listed three versions, including "Before restoring flows-v2" holding the text as it was before undo. So the undo was reversible, but it restores the whole file, not just the change. Screenshots B6-07-after-undo, B6-09-compare, B6-12-after-restore, B6-13-restored.

### Task 7, find what changed since last checked and mark one result checked: DONE, about 3 actions

Your Changes, main-atomic.tex: "Never accepted 21" is a checkbox group listing each changed block (Convention 1.1, Quiver, Divergence, Balanced weighting, and so on) with Read and Accept buttons. I pressed Accept on Saturation (Proposition 2.6). The banner read "Accepted Saturation.", the count went to 20, and an "Accepted 1" group appeared. Screenshot B7-02-after-accept. The task said "checked"; the product says "accepted".

### Task 8, open the compiled PDF: DONE, about 2 actions

The PDF entry under main-atomic.tex in the file tree opened the compiled paper at 93 percent, page 1 of 3, in a tab beside the HTML text. Screenshot B8-01-pdf. The right-hand pane still showed my earlier compare of flows-v2 (see SWALK-11).

### Task 9, paper and a reference side by side: DONE, about 2 actions

Clicking the citation "[2, Theorem 3.2]" in the paper opened Bellamy19 at page 2 beside the paper, with Theorem 3.2 highlighted. Screenshot B9-01-citation-click.

### Task 10, add a paper by dragging in a PDF: PARTLY, about 9 actions

First I dragged notes/handout.pdf from my copy of the showcase onto the Library list in the sidebar. The page reported the drop, but nothing was added: Library stayed at 5 and "handout" appeared nowhere on the page. Screenshots B10-02-drag-hover, B10-03-after-drop.

Then the "+" beside the Library count opened "Add a work to the library", with a text box (DOI, arXiv id or link, zbMATH number, or BibTeX) and a drop zone "Drop a PDF here, or choose one". Dropping the PDF there worked: "handout.pdf, or drop another.", a pre-filled Title "Balanced quivers: a reading handout", blank Author and Year, and an unexplained checkbox "Fetch and digest it now". After Add, Library went to 6 and the info panel said "added by hand, not cited yet" and offered "Cite it as \cite{Bal}". Screenshots B10-05-zone-drop, B10-06-added.

### Task 11, leave a note not attached to a sentence, and find all notes: PARTLY, about 8 actions

The Notes count in the document toolbar and the Notes panel are where notes live. There is no "add note" button. The comment icon's dropdown has a TYPE list (Plain, Revision, Suggestion, Question, Note, "+ Add new...") and a LOOK group. I chose Note and clicked what I thought was empty margin; it attached to the proof of Corollary 3.2 as a paragraph-sized box. So I could not make a note that is attached to nothing. I typed "Check later whether the forest case needs its own argument." and saved it. The Notes panel then listed three notes for this paper, including mine ("ikmartin, Note, Nov 13", "proof of Corollary 3.2", "Go to it"). The panel covers this document only; I did not find an all-documents list. Screenshots B11-02-comment-menu, B11-04-note-saved, B11-05-notes-all.

### Task 12, find what the application says is wrong and whether I could fix it: PARTLY, about 6 actions

Review, Problems: "1 error", "2 warnings", "6 remarks", and "In your files 3": a duplicate id (sh-0020 defined in two files), a citation naming a result its digest lacks (\cite[Lemma 5.9]{Arden24}), and a lemma with no proof (sh-0402). Remarks (6) is folded. Each item has Open links to the line, and the fixes are COPY buttons holding terminal commands ("loom fork ...", "loom id --next", "loom library Arden24"). COPY changed to "COPIED" and put the command on the clipboard, and I did not run it, as I am not allowed to. Open on sh-0402 showed raw LaTeX with a lemma and no proof; I could not fix it in the app. So I could find and open each problem, but I could not fix any of them inside the application. Screenshots B12-01-problems, B12-02-copy, B12-03-open-missing-proof.

## Part C: answers from the screen alone

C1. What does highlighting text do? YES, with a surprise. The Ab tool in the annotation toolbar marks the text, reports "Marked. Start typing to add a comment, or select more text.", and offers "Add comment". The mark also counted: Comments went from 16 to 17 and Notes from 3 to 4. Screenshot B-C-03-highlight.

C2. What does "Quote" do? YES. It copies the selected text with its file and section, and the card says "Copied with where it came from. Paste it to your agent." The copied text began mid-word ("er of balanced weightings ..."), which looked like a bug. Screenshot B2-02-after-quote.

C3. Who sees an annotation? UNCLEAR. Annotations show the author name (ikmartin), and nothing on screen says who else can see them.

C4. Where does an AI's work end up? YES, but in three places: suggestions in Review's Your Changes (labelled "Referee (Agent)"), agent results in Proposed Changes, and agent notes in the Notes panel (for example "Referee (Agent), Note"). I did not find one place that gathers it all.

C5. What is a "session"? UNCLEAR. It appears as a named item under "WRITING INTO", "open" or "closed", with "Write here", rename, close and delete. I took it to be a named AI working thread. It was not defined on screen.

C6. What do the coloured marks in the margin mean? UNCLEAR. There are small yellow, orange, red and blue squares on the right margin. The colours seem to match the annotation types (yellow Plain, orange Suggestion, red Revision, blue Question), but nothing on screen says so, so this is my inference only.

## Part D: words and labels I did not understand at first sight

Annotate: I guessed it turns on marking; it does, and it opens a set of tools. Changes (with a count): I guessed AI changes; it is the suggested edits in the file, with Markup and Final views. Comments and Notes (counts): I thought both were the same; they count different annotation types, and a highlight counts in both. Outline: the section list; I understood it at once. history: versions of the file plus "live text" (the current text). record this version: take a snapshot; not tried. compare: shows differences between a version and the live text. Restore: puts the file back to a version and keeps the current text as a version. Review: a second tab with change and problem lists. Docs: the file tree. Your Changes: suggestions waiting for Keep or Discard, and blocks waiting to be accepted. Accept: vouches that you read a block; it is not the same as Keep. Keep: writes a suggestion into the file. Discard: drops it. Read: a link on each block in the accept list; not tried. Proposed Changes: agent or collaborator results. Problems: what is wrong in the files; with "error", "warnings" and "remarks". Library: papers you read and cite. The Record: versions, sessions and everything done. Referee (Agent): the name of an AI author. Session and WRITING INTO: see C5. Write here: not tried, so unknown. Digest and Fetch and digest it now: I took digest to be a processed copy of a paper for citation checks; the Problems text ("what its digest holds") supports that guess. Overview and Source and Digest (library status): unclear. unreadable: a library group of works the application could not read; I did not open one. need you (on Manage the library, "3 need you"): unclear. Research state: a file in the tree with a crossed-out icon, unexplained. Remarks: folded problems. duplicate-id, fork, loom id --next, loom library, unmatched-postnote: terms and commands in Problems, unexplained. canon and flows-v2 (in the Restore prompt and the URL): unexplained. Plain, Revision, Suggestion, Question, Note (comment types): labels only. Look, Thickness, Opacity, Save as new type, Customize: unexplained, not tried. AI badges on files: unexplained.

## Findings

SWALK-1. Opening the app gave no orientation: the purpose of the panes, the red AI badges and the bottom session bar were all unexplained. Slowed me; minor on its own.

SWALK-2. Quote copies a snippet for pasting into an agent. It sits beside the selection with no hint of that. The quote began mid-word. Slowed me at first; the card explained it once read.

SWALK-3. Comments need a mode. The speech-bubble icon switches on "Comment is on. Click where the comment should go." It is easy to miss, and clicking on text after a selection does not use the selection. Slowed me.

SWALK-4. The comment box anchored to the whole proof paragraph, not the sentence I selected. The mark is misleading about what the comment is about. Slowed me and may mislead a reader.

SWALK-5. A stray click on the status banner "Not saved yet: write the comment" silently discarded my draft. The banner looks like text, and nothing warned me. Stopped my first attempt at task 2.

SWALK-6. Whether an assistant can see my comment: no answer on screen. Stopped task 3.

SWALK-7. The bottom bar says "not writing in a session" while the popup lists two sessions under "WRITING INTO", and the Sessions table says both are open. I could not tell whether an assistant is connected. Stopped task 4.

SWALK-8. Keep writes the suggestion into the file at once, with no confirmation and no undo next to it. Accept and Keep are two verbs for nearby actions. Slowed me.

SWALK-9. There is no undo for a Keep. Cmd+Z did nothing visible, and the paper's undo arrows were greyed out. The only route was Restore on an old version of the whole file, which keeps the current text as a version. The restore is safe, but it is a big hammer. Stopped me for several minutes; task 6 took about 18 actions.

SWALK-10. Clicking the teal text of a pending suggestion does nothing. I expected a detail view. Minor.

SWALK-11. After a compare, a second pane (flows-v2 compare) stayed open and showed up again on the PDF and citation pages, with no visible way I could see to close it except its own tab. Slowed me; I did not understand why it persisted.

SWALK-12. The Changes dropdown offers only "Keep all 2" and "Discard all 2", so a single change must be kept from Your Changes. The dropdown does not say so. Slowed me.

SWALK-13. Accept (task 7) uses "Accepted" and "Never accepted", not "checked". I understood it, but the word differs from the task's wording. Minor.

SWALK-14. Dropping a PDF onto the Library list silently did nothing. Only the "+" dialog accepted the file. The list gives no hint that it is not a drop target. Slowed me a lot (task 10).

SWALK-15. The "+" has no tooltip or label; I found the add dialog by trying it. The "Fetch and digest it now" checkbox and the word "digest" are unexplained. Minor.

SWALK-16. There is no "add note" control. A Note is a comment type; clicking empty margin attached it to a paragraph. I could not make a note that is attached to nothing. Stopped the literal task 11.

SWALK-17. The Notes panel lists notes for this document only. I did not find one list of all notes across documents. Slowed me; I did not confirm whether The Record covers it.

SWALK-18. A plain highlight is counted as an annotation and as a note, so Comments and Notes both change. Surprising; minor.

SWALK-19. Problems: I could find and open each problem, but none could be fixed inside the app. The fixes are terminal commands, and "loom fork", "loom id --next" and "loom library" mean nothing to a first-time user. Stopped task 12's fixing part.

SWALK-20. Good: the PDF opened next to the HTML text (task 8), and a citation link opened the reference beside the paper with the cited theorem highlighted (task 9). Both were quick and clear.

SWALK-21. Good: the Your Changes and Proposed Changes lists show each suggestion's author with an "(Agent)" label, which answered "how do I know it's an AI" at once. Positive.

SWALK-22. Minor: the sidebar tree lists many node files (sh-0001 and similar) under a "nodes" folder, with no clue which one is the paper. Minor.

## The five things that confused me most

1. Whether an assistant is connected and can see my comment. The bottom bar, the WRITING INTO list and the Sessions table seem to disagree, and nothing says what a session can see (SWALK-6, SWALK-7, C5).
2. Undo for Keep. There is no simple undo; the only route is restoring a whole old version of the file (SWALK-8, SWALK-9).
3. Adding a PDF to the Library. The drop on the list does nothing, and the working route is a "+" with no label (SWALK-14, SWALK-15).
4. Marking text. Quote, comment, highlight and note all mark text, and each does something different: Quote copies, a comment anchors to the whole paragraph, a highlight counts as a note, and a note cannot be free-standing (SWALK-2, SWALK-4, SWALK-16, SWALK-18).
5. Problems that can only be fixed in a terminal. The application names the problem and offers copy-paste commands I could not interpret (SWALK-19).

# The annotation system: what exists, and the principles it will be revised against

Study for the annotation revision, part one (prompt #1 of `docs/long-prompts/annotation-study.md`), settled with the author on 2026-09-24 and 2026-09-25. It records what loom and arras do today, the definition the revision uses, and the principles and decisions it will be measured against. The critique and the fix list are part two.

## 1. What an annotation is

**An annotation is a record of four parts; how it looks and how it is used are derived from the record, never chosen separately.**

| part | question | values today |
|---|---|---|
| kind | what does it say? | objection, suggestion, question, confirmation, citation, note |
| target | what is it about? | a node (statement, proof, section, digest result), a display region (`sy-0003#eq:fix`), a document (master or file), or a page of a cited work; a node target may name the document it is read in (§4, decision 9) |
| anchor | where within the target? | none (the whole target), a text quote, a PDF text span, a PDF box |
| state | where does it stand? | status (open, resolved, discarded), anchor health (anchored, detached, written against text that has since changed), and position (top-level or reply) |

Two attributes ride along without defining the record: severity (major, moderate, minor; objection and suggestion only) and the author (a person or an agent).

**Styling is `style(kind, state, anchor, surface)`, and interaction a small set of verbs, each a function of the anchor and the surface.** Treating styling as a free dimension is what produced the variety below; as a function, every inconsistency is a bug in one place.

## 2. What exists today

### 2.1 Distinct annotations

Eight pairings of target and anchor occur:

| target | anchors it takes |
|---|---|
| node | none, text quote |
| display region | none (a box round the display), text quote |
| document | none, text quote |
| page of a cited work | PDF text span, PDF box |

With six kinds, that is 48 kinds of record, each in one of three statuses, one of three anchor healths, and top-level or reply. Canon documents and sessions cannot be targeted. The data model is `loom/src/loom/records/annotations.py`, `records/log.py` (five events: created, replied, edited, resolved, discarded) and `records/store.py` (the manifest's `annotations` map).

### 2.2 Visual styles: 24

| where | renderings |
|---|---|
| on the page (9) | text mark (wash and inset underline); block mark; display mark (a rule under the equation); superscript count when several annotations share a phrase; "N comments" chip for unanchored annotations; PDF mark (tint only, no underline); PDF corner count (orange); active outline; expanded outline |
| boxes (3) | inline card with a kind-coloured stripe; floating card with the stripe removed; the comparison-mode card, always open |
| lists (5) | "What it did" row; packet tray row; Context's detached rows; Context's discarded rows; suggested citations |
| authoring and transient (7) | selection highlight; dashed box on text; solid box on a PDF; the annotate chip on text; the annotate chip on a PDF; the travel flash; the "nothing to travel to" notice |

The same annotation can appear at once as a mark, an open box, a "What it did" row, a tray row, a count in the Library, and a mark in a hover card; in comparison mode it is doubled, an always-open card plus a second box when its mark is clicked.

### 2.3 Interactions: 24 gestures for about seven verbs

| verb | gestures |
|---|---|
| open | click a mark; Enter on a mark; click a count chip; click a PDF mark; follow a `quilt:` link |
| close | ×; Escape (which also closes an open verb panel); click away |
| travel | double-click a mark; double-click a PDF mark; double-click a box |
| act | reply; edit; resolve and undo; discard with a reason and undo; toggle a suggestion's payload between verbatim and rendered |
| create | select text then the annotate chip; the box tool or Alt-drag; the composer; "note on the whole …" when a quote is not found |
| bulk | show or hide all (`e`/`h`, or the rail) |
| configure | box placement (floating or inline); the session filter |

Hover differs by surface: a native tooltip ("kind: author") on text, a stronger tint on a PDF, and on a link a preview of the target rather than the annotation. A box cannot be travelled to: travel from a mark lands on its "What it did" row.

### 2.4 Overlap between kinds, and the nouns

- **note and confirmation** overlap: both ask nothing and take no severity, and a confirmation with no text is a tick. The book says resolving writes a confirmation; the code does not.
- **citation and suggestion** overlap in that both propose something; a citation's payload is a work, and `loom refs note` accepts or rejects it.
- **objection and question** both ask, but ask different things of the author.
- **Five nouns name one record:** annotation, comment (`loom comment`), finding (`loom ai findings`), note (a page note; also one of the kinds) and review record (a session's annotations replayed). `loom refs note` and `reference_notes` are a different store. "placement" names two unrelated things: where a suggestion's text goes, and where the viewer puts boxes.

### 2.5 Colours: 22 values or tokens

| encodes | tokens |
|---|---|
| kind (8) | four stroke-and-wash pairs, for objection (red), suggestion (amber), question (blue), and `ok` (green) — a kind name no annotation has, so a confirmation is drawn neutral on text and orange on a PDF |
| severity (3) | major and moderate as state colours, minor as an undefined token; the rule never matches the markup (`.severity` against `.sev`) |
| undefined (3) | `--annotation`, `--annotation-tint`, `--annotation-tint-strong`, always their hard-coded orange fallbacks |
| the rest (8) | accent and its wash, the selection highlight, the PDF lead dot, the quote rule, and outlines borrowed from link and state colours |

Colour encodes kind on text, kind or nothing on a PDF, and nothing in lists. State is almost never drawn: a resolved annotation looks exactly like an open one, and "detached" is a word with no style.

### 2.6 Faults found along the way

These are recorded here for the fix list, not fixed:

- `refs-note` over the write API skips the citation check and uses the body as the work, against DR-170 (`loom/src/loom/render/api.py`).
- A reply to an annotation on a page copies only the text triple, so it probably publishes detached.
- Replies take `--kind` without validation.
- The book's schema in 7.2 is the old per-file format, and 7.2 says resolving rewrites a field in place.
- The book (15.2) describes a margin placement, retired in code, whose stacking code still runs (`arras/src/lib/fragments/mount.ts`).
- The session filter hides counts but not marks on text, and hides marks on a PDF.
- The withdrawn-reply branch in the box is unreachable.
- `Reading.svelte` imports `AnnotationBox` and never uses it.

## 3. Principles

The six visual principles of plan 0.14, restated for `style()` and `interact()`.

**A1 · The text comes first.** At rest the page shows marks and nothing else: no open boxes, and at most one count per node. An annotation marks its place and waits to be opened.

**A2 · One annotation, one mark.** On the page an annotation appears once: as a mark, or, with no anchor, as the single count on its node. The lists that show it (What it did, the tray, Context) link to it rather than restate it.

**A3 · Draw only what loom knows.** A resolved annotation looks resolved. A detached one is never drawn at a guessed place; it is listed as detached. One written against text that has changed is not marked in the new text. No state is shown only as a word.

**A4 · One channel, one question.** Each visual channel answers exactly one question, and no two channels answer the same one:

| channel | answers |
|---|---|
| hue | what kind of thing is said |
| weight | how severe (objection and suggestion; the other kinds take the middle step) |
| wash | which annotation's box is open, whatever its kind and severity, at one strength; at 3%, that it is settled |
| shape | what it is attached to: an underline for a phrase, a rule for a display, a tint for a PDF span, an outline for a box |

**A5 · Opening an annotation never costs the text.** A box never covers the words it is about. Travel between a mark and its record is one gesture each way and leaves both on screen.

**A6 · Quiet by default.** This is the principle against visual noise.
- At rest only open, top-level annotations are drawn.
- Settled annotations (resolved or discarded, marked by hand) are not drawn until the reader turns them on, and then at 3% wash with the underline at half weight and 50% opacity, the words untouched.
- The system uses four hues, one neutral and three weights, and nothing else.
- An annotation looks the same on every surface: text, PDF and hover card.

## 4. Decisions

Settled with the author:

1. **The definition** is (kind, target, anchor, state), with styling and interaction derived.
2. **Confirmation merges into note.** "This is right" does not earn its own colour. The kinds become objection, suggestion, question, citation and note.
3. **Settled means resolved, marked by hand, for every kind, notes included.** Nothing settles by being read, so there is no read state.
4. **Settled annotations are hidden at rest.** When the reader turns them on, the annotation fades and the words do not: its wash drops to 3% and its underline to half the weight it had at 50% opacity, so a settled major objection is a half-strength red at 1.5px. The kind's hue survives.
5. **Hues:** objection red, suggestion yellow, question blue, citation violet. Violet rather than green, because green already means an accepted key on the node badges, and red against green is the pair a colour-blind reader loses.
6. **An open note** is drawn at rest in the neutral colour at the middle weight; a settled note is the same at 3% wash and a half-weight, half-opacity underline.
7. **Severity** is three steps of the underline's weight within a hue, and nothing else: the wash is one strength whatever the severity. Only objection and suggestion carry it.
8. **"annotation" is the one noun,** in commands, the viewer and the documents. `loom comment` becomes `loom annotate`, and `loom ai findings` becomes `loom ai annotations`. "N comments" and "notes on a page" become annotations, so "note" names only the kind.

9. **A node annotation may belong to a document.** Some claims about a node hold only in one document: that `ex-0002` is redundant in `draft1.tex`, where `ex-0001` already covers it, says nothing about `draft2.tex`, which uses `ex-0002` alone. Such an annotation targets the node and names the document it is read in; one that names no document is about the node wherever it appears, which stays the default. It is drawn as a mark in the document it names; on the node's own page it is listed, with the document named, and not marked on the text; in any other document it is absent. The manifest's `reached_by` already says which documents hold a node, so a named document that no longer reaches the node is a detached annotation like any other.

Open for part two:
- Whether `loom refs note`, which accepts or rejects a citation suggestion into a different store, keeps its name.

---

# Part two: the critique, and the fix list

Prompt #2 of the study, 2026-09-25. The critique measures what exists (§2) against the principles (§3) and the decisions (§4), then against questions of its own. The fix list follows from it. The demo that shows each fix before and after is at https://claude.ai/artifact/GL1qguYs69VoB1iRBxH8Ke, and its rows are the images under `images/0.15-PRE-annotation-study/`: one `<row>-before.png` and `<row>-after.png` for each of objection, suggestion, question, citation, note, confirmation (whose after is note's), settled, and the composer.

## 5. Critique against the principles

**A1, the text comes first.** Mostly met at rest: nothing opens until clicked. Broken in comparison mode, where every annotation's card is permanently open under its node, and by the count chip, which sits inside the node's label line at 9px and reads as part of the heading.

**A2, one annotation, one mark.** Broken three ways. A node with an unanchored annotation shows a chip; a phrase with two annotations shows a mark and a superscript; in comparison mode an annotation shows as a card and, once clicked, as a second box on top of it. And the box repeats its own mark: the quote is printed inside the box, italic with a rule, directly beneath the words it quotes.

**A3, draw only what loom knows.** The weakest area. A resolved annotation is drawn exactly like an open one, and only the word "resolved" in 76%-size faint type says otherwise. "detached" is a word with no style behind it. A confirmation is drawn neutral on text and orange on a PDF because the CSS looks for a kind named `ok`. Severity is words only: the chip rule targets `.severity` and the markup says `.sev`, so it never matched. Three colour tokens are undefined and always fall back to a hard-coded orange.

**A4, one channel, one question.** Hue carries kind on text, kind-or-orange on a PDF, and nothing in lists. Weight carries nothing. The active outline borrows the stale-state colour and the expanded outline the link colour, so two outlines answer "which one is selected" in two colours borrowed from unrelated questions.

**A5, opening never costs the text.** The floating box is placed below its mark with a 4px inset and flips above when there is no room, which is right; but at 420px wide and up to 60vh tall it covers the paragraph after the one it is about, and the verb panel for reply or edit opens as a second popup above the box. Travel is one-directional: a box has no id, so double-clicking a mark lands on a "What it did" row rather than the box.

**A6, quiet by default.** Not met. Every open annotation of every kind is drawn in colour at rest, resolved ones included, so a reviewed node looks as busy after review as before. Twenty-two colour values do the work of five. Each surface draws its own mark: wash-and-underline on text, tint-only on a PDF, an orange chip on a PDF corner.

## 6. Critique as design

Questions the principles do not ask, and the answers.

**Does every kind need its own visual style?** No. Hue must say what kind of thing is said, because a reader triaging a page needs to tell an objection from a question before opening either. Beyond hue, nothing about a kind should differ: the mark's shape is the anchor's, the box's layout is the same for every kind, and the four hues plus neutral are the whole vocabulary. Today an objection's box also gets a red wash the others lack, and a suggestion's payload is set in red regardless of the suggestion's own hue.

**What mark best says "this is annotated" while leaving the text readable?** Of the two devices in use, the wash (a background tint behind the words) and the underline, the wash costs more: it lowers the contrast of every character it covers, competes with the selection highlight and the search highlight, and on a PDF is the only device, where it fights the page's own tint. The underline costs nothing in legibility, sits below the glyphs where descenders already go, and carries weight and hue without touching the letterforms. The mark should be an underline alone, with the wash reserved for the one annotation that is open, so that "which of these is the box about" is answered by the wash and "what is annotated" by the underline.

**Is the box the right size for its job?** No. It is the reader's answer to "what does this say", and that is a body of one to three sentences. Today it carries a header of six items (kind, severity, date, status, author, detached), a quote of the words it is already attached to, the body, a payload block with its own uppercase header and a mode toggle, a reply thread, and a verb row of four verbs that folds behind `⋯` when narrow. The kind is already said by the hue; the quote by the mark; the status by A6 (an open box is open); the date and author matter once and can share a line.

**Is the composer the right shape?** Nearly. It asks for three things: what to say, what kind of thing it is, and how severe. Today the kind is a `<select>` with six entries the reader cannot see at once, severity is a second select that appears and disappears as the kind changes (the form jumps), the submit is labelled "note it" whatever the kind, and the header shows the target key (`sy-0003`) rather than the words being annotated.

**Are the verbs the right verbs?** Four verbs, two of them undoable, plus withdraw on a reply. Reply and edit each open a second popup with its own textarea. Resolve is one click with no confirmation, and undo is a fifth verb in link blue that appears in the resolved state. Discard asks for a reason in a popup. That is three popups from inside one box.

**Where does the same fact live twice?** The kind: in the hue, the stripe, the header word, the chip colour and the did-row word. The quote: in the mark and the box. The status: in the header word and, once A6 holds, in whether the annotation is drawn at all. The author: in the header and the native `title` tooltip on the mark.

**What is retired but still drawn?** The margin placement's stacking code, the withdrawn-reply branch, an unused import of the box in the PDF reader, and the `k-ok` kind.

## 7. Fix list

Each fix names the error and how the fix resolves it.

### 7.1 Merges

1. **Confirmation into note** (decision 2). Two kinds asked nothing and took no severity, and the viewer had no colour for the one it called `ok`, so a confirmation was drawn neutral on text and orange on a PDF. One kind, `note`, drawn neutral everywhere.
2. **Five nouns into "annotation"** (decision 8). `comment`, `finding`, `note`, `review record` and `annotation` named one record, and `note` was also a kind. `loom comment` becomes `loom annotate`, `loom ai findings` becomes `loom ai annotations`, the viewer says "N annotations", and `note` names only the kind.
3. **Mark, chip and superscript into one mark.** A node with an unanchored annotation grew a 9px chip inside its label; a phrase with two annotations grew a superscript beside its mark. An unanchored annotation is an underline under the node's label, and a phrase with several is one underline whose box lists them.
4. **The two outlines into one.** The active mark was outlined in the stale-state colour and the expanded one in link blue, two answers to "which is selected". The open annotation's mark takes the wash; nothing else is outlined.
5. **The three composers' defaults into one rule.** A selection defaulted to `question`, a box to `note`, a page annotation to `note` or `confirmation` by whether it had text. One default, `note`, since it asks nothing and is the safe guess; the reader changes it in one click.

### 7.2 The mark on the text

6. **Underline only; the wash is for the open one.** The wash lowered the contrast of every annotated character and, on a PDF, was the only device, so a page of annotations was a page of tints. The mark is an underline in the kind's hue at the severity's weight; the wash appears on the one annotation whose box is open and says "this is the one".
7. **One mark on every surface.** A text mark was wash-and-underline, a PDF mark tint-only, a display mark a rule, and a PDF count an orange corner number, so the same annotation had three looks. `style(kind, state, anchor, surface)` draws the underline on text and under a display, and on a PDF the same underline beneath the span's lines; a box anchor is an outline in the same hue.
8. **Settled annotations are not drawn** (decisions 3 and 4). A resolved annotation looked exactly like an open one, so a reviewed page stayed as busy as an unreviewed one. Resolved and discarded annotations are absent at rest; turned on, each keeps its hue at a 3% wash and its underline at half weight and 50% opacity, and the words it sits on are never faded.
9. **Severity is weight.** Severity was a chip whose CSS never matched, so it showed as a word in the box and nowhere on the text. The underline is 1px, 2px or 3px for minor, moderate, major; the kinds that take no severity draw at 2px.
10. **Four hues and one neutral, defined** (decision 5). Twenty-two values did the work of five, three of them undefined tokens falling back to orange. `--ann-objection` red, `--ann-suggestion` yellow, `--ann-question` blue, `--ann-citation` violet, `--ann-neutral`, each with its wash, in both themes, and every other annotation colour deleted.
11. **The session filter hides marks as it hides counts.** On text the filter hid counts but left marks drawn, so a mark could open a box for a hidden session. The filter governs the mark.

### 7.3 The box

12. **Header of two things.** Six header items restated what the hue, the mark and the state already said. The header is the author and the date; the kind is the stripe's hue, and the status is whether the box exists at rest.
13. **No quote.** The box printed, in italics under a rule, the words directly beneath it. The quote is the mark; the box begins with the body. An unanchored or detached annotation, which has no mark, keeps its quote, since there the quote is the only record of what was meant.
14. **Verbs as one quiet row, and reply in place.** Reply and edit each opened a second popup above the box, and discard a third. The verb row is one line at the foot; reply and edit expand a textarea inside the box below the body, and discard takes its reason in the same place.
15. **The box travels.** A box had no id, so double-clicking a mark landed on a "What it did" row. The box carries its id; one gesture goes from mark to box and back.
16. **A suggestion's payload in its own hue.** The proposed text was set in red whatever the suggestion's hue, and headed by an uppercase label with a mode toggle. The payload is set in the suggestion's yellow at the left rule, headed by one word (replace, after, before), rendered by default with verbatim behind a link.
17. **One popup, not three.** Reply, edit and discard were popups over the box, which is itself a popup. Everything an annotation can do happens inside its box.

### 7.4 The composer

18. **Kind as five buttons, not a select.** Six options hid in a `<select>`, and the severity select appeared and vanished as the kind changed. The five kinds are a row of buttons in their hues; severity is three buttons that are present but disabled for the kinds that take none, so the form never jumps.
19. **The words being annotated, not the key.** The header read `sy-0003`, a key the reader did not choose. It reads the quoted words, or "the whole of Theorem 2.1", or "p. 4, a box".
20. **The submit says what it does.** "note it" whatever the kind. "Annotate", or the kind's verb when one exists ("Object", "Suggest", "Ask", "Cite", "Note").
21. **Escape and × mean one thing.** × cancelled, Escape cancelled, and a third "cancel" button cancelled. × at the corner and Escape, no third button.

22. **One annotate chip.** The chip that follows a selection was drawn in the chrome's accent on text and a hard-coded orange on a PDF, with no keyboard equivalent, so the same control had two looks and one way in. One chip on every surface, in the annotation neutral at the selection's end, labelled "annotate", gone once the composer opens; Enter on a selection does what the chip does. The chip itself stays: it is what lets a selection be a copy rather than a form.

### 7.5 Dead code

23. **Remove** the margin placement's stacking code, the withdrawn-reply branch, the unused box import in the PDF reader, the `k-ok` rules, and the three undefined tokens. Each is drawn or run for nothing.

## 8. Annotations in context (prompt #3)

Settled as decision 9: a node annotation may name the document it is read in. It is marked in that document, listed on the node's own page with the document named, and absent from any other document.

## 9. Decisions for the plan

Settled with the author on 2026-09-25, closing what parts one and two left open.

10. **`loom refs note` becomes `loom refs cite`.** It accepts or rejects a citation, and `refs cite --accept ID` and `--reject ID` say so; "note" is then only the kind. The reference notes file and the manifest's `reference_notes` are about the works and keep their names.
11. **A document-qualified annotation is written with `--in DOC`** on `loom annotate`, and an `in` field on the write API's comment endpoint; either is refused when the document does not hold the node. In the viewer the document is implied by where the reader is: an annotation written while reading a document is filed with that document, and one written on the node's own page is filed without. The record carries `in` beside `target`; anchors and state are unchanged.
12. **Settled annotations are shown by a control on the rail, held for the session.** It sits beside show-all and hide-all, defaults to hidden on every visit and is not remembered, and stays on as the reader moves between documents. It has a key beside `e` and `h`. Not a setting, since it is a mode of a sitting; not per page, since it is never wanted for one theorem and not the next.

---

# Part three: the principles check

Phase 6 of plan 0.15, 2026-09-25. Each element of the revised system measured against the principles of §3, on the after screenshots under `images/0.15-annotation-revision/`: the phase 3 to 5 shots at 1440×900 (`mark-*`, `box-*`, `composer-*`, `rail-settled-on`), and fresh ones at 1440×900 and 1100×800 for what those did not cover — the page at rest (`rest-*`), the three lists (`did-*`, `tray-*`, `context-detached-*`, `context-discarded-*`), the chip (`chip-*`), a mark on a PDF page and its box (`pdf-mark-*`, `pdf-mark-open-*`), and a followed link to a settled annotation (`link-settled-*`). The `mark-*` shots were taken in phase 3 and show that phase's box, since the box changed in phase 4; the `box-*` shots are the box as built. Three faults the check found were small and were fixed in this phase; two are brought to the author (§10.1).

## 10. The principles check

Each element against A1–A6. A4 is the question in the second column; an element with no question would have failed it, and none did. A dash means the principle does not bear on the element.

| element | question (A4) | A1 | A2 | A3 | A5 | A6 |
|---|---|---|---|---|---|---|
| the text mark | what is annotated here, and what kind of thing was said? | **pass**: at rest the page is underlines and nothing else (`rest-1440`, `rest-1100`); no box, no count | **pass**: one underline per annotation; a phrase with two is one mark whose box lists both (test `one mark for two`) | **pass**: a settled mark is transparent until the control draws it (`mark-settled-hidden`, `-shown`); a quote that no longer resolves is not marked in the new text (`context-detached`: Definition 1.1's words carry no mark; its question is a mark on the label, which is the record's target and not a guess) | **partial**: travel is one gesture each way and both stay on screen (test `travel is two-way`); but a floating box at 420px stands over the paragraph after its mark (`box-objection`, `link-settled-1440`); the inline setting leaves the text whole. Brought to the author, §10.1 | **pass**: four hues, one neutral, three weights; the wash only on the open one (`box-objection`); nothing outlined |
| the PDF mark | the same, on a page of a cited work | **pass**: an underline beneath the span's lines and no tint (`pdf-mark-1440`); the orange corner count is gone | **pass**: one span is one mark, drawn once per line it crosses, and opens one box | **pass**: settled marks are not drawn (`button.mark.annotation.settled { display: none }`), and the "N notes hidden" line is gone with the filter's marks | **partial**: the box floats beside the mark and, at 1100 wide, over the line below it (`pdf-mark-open-1100`); same fault as the text mark's | **pass**: the same underline as on text, the same hue tokens, the box outline for a box anchor (test `a box anchor is an outline in the hue`) |
| the label mark | which result carries an annotation with no place in its words? | **pass**: an underline under the label's own words, in the flow; nothing added to the text (`mark-note`, `rest-1440`: Definition 1.1, Lemma 1.2) | **pass**: every unanchored annotation on the result shares its one label mark, whose box lists them (test `the label mark`); the count chip is gone | **pass**: a settled one gets its label mark only while the control is on (test `on a document it shows and hides the settled marks`) | **pass**: inline, its box opens beneath the label; floating, at it | **pass**: the neutral for a note, the kind's hue otherwise (Lemma 1.2's citation in violet) |
| the box | what does it say, who said it, when? | **pass**: none is open at rest on a document or a node; beside a comparison the open annotations' cards stand in the flow by design, and settled ones no longer do (`box-comparison`) | **pass**: no quote for an anchored annotation, no kind word (the stripe is the kind), no status word while open (`box-objection`, `box-suggestion`); beside a comparison the card is the one box, and its mark travels to it (test `beside a comparison a card in the flow is the annotation's one box`) | **pass** with one caveat: settled is drawn (stripe at 50%, body softened) and said once (`box-settled`); `accepted` comes from the reference note loom publishes, but `rejected` is held for the session only, since loom's `refs-cite` leaves no manifest trace that tells a reject from a plain resolve — after a reload the box says `resolved`. Brought to the author, §10.1 | **pass**: the box carries `ann-<id>` wherever it stands, so a double-click on the mark lands on it and one on the box lands on the mark (test `travel is two-way`) | **pass**: body, what the kind adds, one meta line; the six-item header, the red wash and the severity chip are gone |
| the verbs | what can I do with this? | — | **pass**: one row at the meta line's right; nothing behind a `⋯` | **pass**: a verb is drawn only where `GET /_api` says the publisher serves its endpoint; a settled annotation offers `reopen` alone (`box-settled`) | **pass**: reply, edit and discard open a block inside the box beneath the body (`box-question-reply`); nothing pops over the text | **pass**: `--ink-faint` until reached for |
| the payload block | what text does this suggestion propose, and where would it go? | — | **pass**: one placement word, the text rendered, `verbatim` one link away (`box-suggestion`) | **pass**: the word is the record's `placement`, `proposed` when it names none | — | **pass**: a 2px rule in the suggestion's yellow and one small-caps word; the uppercase header and its toggle button are gone |
| the citation block | which work does this propose? | — | **pass**: the work once, at a violet rule; the body is the claim (`box-citation`) | **pass** with the box's caveat: `accepted` from the manifest, `rejected` from the session | — | **pass**: accept and reject are the box's verbs; the Library's list links to the box and decides nothing |
| the composer | what do I want to say, of what kind, how severe? | — | **pass**: its header names the words being annotated, not the key, and the quote is not repeated below it — the words stay lit on the page (`composer-selection`) | **pass**: on a page loom's own `locate` answer stands beneath the header, the one line that says the anchor was found before anything is written; on text there is no such line because nothing has been asked yet | **partial**: the composer stands over the paragraph after the selection (`composer-selection`), as a floating box does; the words it is about stay lit and uncovered | **pass**: five kind buttons in their hues with `note` chosen, three severity buttons always present and greyed for the ungraded kinds, the submit the kind's verb, × and Escape and no third button (`composer-note`) |
| the annotate chip | can I annotate this selection? | **pass**: drawn only while there is a selection, and gone once the composer opens | **pass**: one chip on every surface (`AnnotateChip.svelte`) | — | **pass**: at the selection's end, off the words (`chip-1440`); Enter does what it does (test `a selection offers one annotate chip`) | **pass**: one word in the annotation neutral |
| the settled control | are the settled annotations drawn? | — | — | **pass**: it draws only what the manifest's `status` and `discarded` say, at the faint weight; its pressed state and its label say which way it is (`rail-settled-on`) | — | **pass**: off on every fresh visit, held for the sitting, `s` beside `e` and `h`; offered on a document or a node wherever there is a settled annotation to draw, so a node whose every annotation is settled can still show them (fixed this phase, §10.1) |
| the did row | what did this command do to which annotation, and where does it stand? | — | **pass**: a dot in the kind's hue, the key, a link, the state word; no kind word and no text (`did-1440`, `did-1100`); a reply's dot is a ring | **pass**: every row is a `run.log` line; the state is the manifest's | **pass**: the link opens the annotation's box beside; one to a settled annotation turns the control on and opens the box, rather than landing on a page where nothing is drawn (`link-settled-1440`; fixed this phase) | **pass**: the word became a 7px dot; severity is not shown |
| the tray row | what will my next message carry? | — | **pass**: a dot and the place's name, linked (`tray-1440`, `tray-1100`) | **pass**: rows and preview are loom's own packet | **pass**: a row's link opens beside and the Chat stays (0.14's rule) | **pass**: the kind word is gone from the row; the preview stays behind its toggle |
| the Context rows | which annotations on this node have no place in its text, or were withdrawn? | — | **pass**: a dot and a link whose text is a short preview of the body, the box one click away; the discarded list is no longer a column of boxes (`context-detached-1440`, `context-discarded-1440`) | **pass**: `detached` and `discarded` are the manifest's fields; a detached annotation's quote is kept in its box, where it is the only record of the words | **pass**: the link opens the node with the box; for a discarded annotation the settled control comes on, since the box exists only while its mark is drawn (test `a link to a settled annotation turns it on and opens the box, a discarded one included`) | **pass**: the discarded fold behind `N discarded — show` |

### 10.1 What the check found

Fixed in this phase, each small:

- **A discarded annotation's mark opened nothing.** The settled control drew a discarded mark faintly, but the box-opening code still dropped discarded annotations, a filter from before discarded meant settled; and a discarded annotation with no quote got no label mark, since the slot function read only undiscarded ones. Both now treat discarded as settled, so a discarded annotation is drawn, opened and reopened exactly as a resolved one is.
- **The settled control was missing where it was most needed.** It was offered only while a fragment held a drawn mark, so a node whose every annotation was settled — nothing drawn at rest — had no way to show them. It is now offered wherever a settled annotation exists on the item.
- **A link to a settled annotation landed on a page where nothing was drawn.** The did row and the Context rows link settled annotations; following one now turns the settled control on for the sitting and opens the box, which is what the link asked for (DR-294-ikmartin).

Brought to the author:

- **A5, the floating placement.** A floating box, and the composer, stand over the paragraph after the words they are about (`box-objection`, `composer-selection`, `pdf-mark-open-1100`). The words themselves are never covered, and the inline setting leaves the whole text in place, but the principle says *never costs the text*. The options are to make inline the default, to size the floating box by its content and cap it lower than 60vh, or to accept the reading as it is; none was decided in the study.
- **A3, the rejected outcome.** A citation's `rejected` is known only to the viewer that posted it, because loom's `refs cite --reject` writes a resolve event whose reason is not published in the manifest. After a reload the box reads `resolved`. Publishing the outcome — `accepted`, `rejected` — on the resolve event, or on the annotation row, would let the box draw what loom knows.
- **A3's wording.** An annotation whose quote no longer resolves is drawn as a mark on its node's label, which is its target and not a guessed place; the principle's sentence "it is listed as detached" reads as though it were drawn nowhere. The behaviour is DR-293-ikmartin's; the sentence should say "drawn on its target's label, never at a guessed phrase".

## 11. Decisions as designed against as built

| decision | as built | moved? |
|---|---|---|
| 1. The record is (kind, target, anchor, state); styling and interaction derived | `theme.css`'s one rule set draws every mark from `k-<kind>`, `s-<severity>` and the state classes; the box, the composer and the lists take their hue from the same seam | no |
| 2. `confirmation` merges into `note` | five kinds; an older log's `confirmation` is read as a note (DR-291-ikmartin) | no |
| 3. Settled means resolved or discarded, marked by hand | as designed; in the viewer, discarded had stayed excluded by an older filter, so a discarded annotation's mark opened nothing — made settled like a resolved one in phase 6 | refined |
| 4. Settled hidden at rest; shown at a 3% wash, half weight, 50% opacity | as designed; the plan's `data-settled` attribute from loom was not needed, since every mark is baked and the viewer reads `status` from the manifest, so a resolve needs no rebuild | mechanism moved, rule kept |
| 5. Hues: red, yellow, blue, violet, neutral | as designed, in both themes | no |
| 6. An open note is neutral at the middle weight | as designed | no |
| 7. Severity is the underline's weight and nothing else | as designed; the box shows no severity, though `edit` still sets it | no |
| 8. One noun, `annotation` | `loom annotate`, `loom ai annotations`, the endpoints `annotate` and `refs-cite` (DR-292-ikmartin); the viewer's stored `comments` preference keeps its key under an "Annotations" label | no |
| 9. A node annotation may name its document | as designed; `resolved()` detaches one whose document no longer reaches the node | no |
| 10. `loom refs note` becomes `loom refs cite` | as designed; accept and reject moved from the Library into the box (phase 4), and the outcome is held per session (§10.1) | refined |
| 11. `--in DOC` and the API's `in`; the viewer implies it | as designed; refused when the document is no master or does not hold the node; `DocumentItem` passes its master's path and the node's page passes none (DR-294-ikmartin) | no |
| 12. Settled annotations shown by a rail control held for the session, with a key | as designed, `s` beside `e` and `h`; refined in phase 6: offered wherever a settled annotation exists, and turned on by a followed link to one (DR-294-ikmartin) | refined |
| Fix 19, the composer names the words | as designed; on a page loom's `locate` line stays beneath the header, since it is the one thing loom has said before anything is written | refined |
| Fix 3, one mark for the unanchored | a mark on the node's label rather than a chip; a detached annotation, whose anchor no longer resolves, is the same case | no |

## 12. What this cannot answer

- **Whether the hues read.** No colour-blind reader looked; violet was chosen against green for that reader, and the dot in a list carries its word only in a tooltip and a label.
- **Whether a page with hundreds of settled annotations stays quiet.** Every quilt here holds a dozen; the re-wire that `s` causes was not timed on a long document.
- **Whether floating should be the default.** The A5 fault above is a placement question no screenshot settles.
- **Dark mode by eye.** The dark hues were set as tokens and checked by the tests' computed colours, not looked at on a page.
- **Whether anyone wants the discarded shown.** Discarded annotations are now reachable through the settled control and the Context; nobody has asked to see one.


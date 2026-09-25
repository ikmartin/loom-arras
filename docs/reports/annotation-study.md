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

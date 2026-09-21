# The split view and the reading view: an overhaul

Started as a sketch for a "teach view"; the design that came out of it is the split view, the Library View, sessions shared by a person and an agent, and the dispatch that carries messages between them. Plan: `docs/plans/0.13-plan-reading-layer.md`.

## Initial brainstorm
Idea: a split view with a pdf/source on the left, running chat/annotation log on the right.
- sections of the pdf are highlighted in amber/soft yellow, corresponding annotations and explanation and relevant experiments pop up on the right
- works like synctex, you can scroll through both independently, double clicking a highlight on the left takes you to the corresponding annotation/relevant material on the right
- annotation rounds are stored. By default you always see the most recent round, and it includes all previous annotation in it. But annotations aren't naively stored in one large stack, the llm can choose to modify/change an annotation. The user can also interact with the annotation by replying to it (ask for clarification for example) or by resolving it; I don't think an "accept/decline" mechanism makes sense because you're not modifying the underlying document, you're just saying the annotation shouldn't persist into future rounds. So there is a reply mechanism, an edit mechanism which allows you to edit the annotation text directly, and a remove button with a dialogue for leaving an optional message.
- user can leave annotations too, highlight anchor text and just up/to the right of the upper corner of the end of a highlight is a little popup "annotate?" clicking it let's you leave a text annotation/comment with a question or comment with math rendered by mathjax
- input is passed to the llm in two ways, either through a chat box or through annotations. each round the llm is passed a small list of the ids of the annotations which have changed (either annotations which were replied to, editted, deleted, or added by the user in the previous round) in addition to any chat messages.
- default layout of page would ideally be three panes, a wide short chat box along the bottom and then the split view above. All panels collapsible.
- would be nice to buff out the atom/node/id system: annotations and nodes in a quilt both share the need for ids and for a history. In the future it would also be nice to take an annotation and incorporate it into a quilt, for example a long annotation which is a complete example of something could be upgraded and incorporated into a quilt. This is a separate project than this learn view, but since this project is asking new features of annotations, it's possible it's worth studying how annotations and nodes might unified into a single unified id/history system first before building this view. (NOTE: I think annotations and nodes really are two different objects, and should be treated as such. The vast majority of annotations are ephemeral/temporary, and shouldn't ever be upgraded to nodes in a quilt.)
- when a pdf locator link is followed the pdf should open in split view.

## Highlights of discussion following initial brainstorm

Reverse chronological: the most recent exchange first. Distilled; the reasoning lives in the decision records where one was written.

### Rules that were in the way, and what became of them

- **Book 4.8 rule 6 amended (DR-195).** Loom holds no credentials and calls no model provider; it may dispatch a message to a local agent the author is already running. The rule was written for the proof of concept and its discussion said it might change. What it protects is loom not becoming a vendor client; dispatching to a session the author already started does not threaten that, and removes the switching between browser and terminal the rule cost them.
- **A `message` endpoint is permitted in a later version of the write API.** Plan 0.11 is implemented and complete; its refusal was about invoking the declined runner (WQ-15), which is not what this is. `specs/write-api.md` §4 now says so, and a client still detects the endpoint rather than assuming it.
- **DR-175's refusal to show the PDF is a bad rule and goes when the reading view lands.** Its premise was that a PDF has no text nodes to anchor a quote to, no elements to hang a mark on and no links to rewrite. PDF.js's text layer supplies all three, and the store's copy-once guarantee (DR-192) supplies the immutability locators need. The decision was right for the author's own paper, where a faithful HTML rendering exists; it never really covered a cited work that has no source at all.

### The PDF invariant

- **The property:** whenever there is anything to render for a reference document, loom has a complete PDF of it. If there is something to render, there is either a PDF or a TeX source, and in the latter case the PDF should have been downloaded too.
- **Not enforced today.** `refs fetch --no-pdf` exists, `refs add` files a PDF alone, a fetch can half-succeed, and a digest extracted from source never checks that a PDF arrived. Enforcement is cheap: a lint code for a work that has something to render and no PDF, reported in `refs build`'s handoff lines, with `--no-pdf` demoted to a deliberate exception.
- **Compiling the TeX is the last resort** and is not built until a work is found for which no PDF can be obtained by any other means.

### Locator behaviour

- **The real question is which coordinate system is of record**, not point versus box. Three candidates disagree: geometry (exact, immune to the text layer's mathematical mangling, meaningless without the PDF, unlistable), offsets into an extracted text stream (compact, survives without the PDF because the page text is committed), and quote plus context (robust, useless for mathematics).
- **The trap:** poppler and PDF.js produce different text streams, so offsets taken from one do not line up in the other. One extractor must be canonical.
- **Proposed anchor:** `{artifact: sha256, page, start, end, quads, text}` — offsets into loom's committed poppler page text are of record, one rect per line is what gets drawn, and the quoted text is a hint for lists and for re-finding. Arras maps offsets onto the PDF.js text layer by matching, with the normalisation `refs locate` already does for hyphenation and ligatures.
- **A span with an optional end**, so a point is a degenerate span and "jump here" and "highlight this" are one type. One rect per line, never a single bounding box over several lines, which would swallow the column.
- **Geometry-only anchors must be legal.** A reader highlighting a formula often cannot be matched into the page text at all: text-anchored when possible, box-anchored when not, never refuse to record.
- **Multi-page spans**, and **anchored to the artifact hash rather than the citekey**, since a preprint and its published version now sit side by side as sibling entries. The text hint is what lets the other copy offer "find this here".
- **Open:** whether quads are stored or computed on demand and cached beside the work like `sections.json`. Leaning cached, since the PDF is immutable so the cache is never wrong.

### PDF rendering

- **Option B, PDF.js (`pdfjs-dist`), vendored the way MathJax already is**, so the deployed site stays offline. Canvas per page plus a positioned text layer gives real selection, highlight overlays, in-page search and virtualisation. The npm Svelte wrappers are thin and stale; use the library directly in a component.
- **Today is an `<iframe>` on the browser's own viewer** with `#page=N`, which cannot draw a highlight, read a selection or emit an event. It stays as a "just open it" affordance and is a dead end for this feature.
- **Server-rendered page images (`pdftoppm`) plus boxes stay as the fallback** for a clone with no PDFs, and loom's bbox machinery stays the server-side resolver that turns a stored anchor into coordinates, so the client never re-derives a mathematical quote it cannot read.
- **Svelte itself offers nothing for PDFs**; this is entirely a library choice.

### Reading from the PDF rather than the digest

- **Agreed, with a boundary:** the PDF is better for reading — surrounding text, the paper's own typography, figures in place. The digest does not go away: it is what makes a result citable, graphable and searchable. Read and annotate in the PDF, cite through the digest.
- **Node to PDF span is half built.** A proposed or verified result already carries page, quoted source text, artifact hash and how far down the page the quotation starts. There is no stored span, and a digest extracted from LaTeX has no page anchor at all, because it never read a page — giving those nodes spans means matching each statement into the page text, with the failure modes proposals already have.
- **Annotations on reference documents carry a locator and may carry a node key**: a target union, the locator of record, the node optional.
- **A fresh clone has no PDFs.** Page text is committed, PDFs are not, so a PDF-first reading view degrades to nothing until a fetch. The fallback is the page-text view, or committing PDFs where the license allows, as the showcase quilt does by exception.

### From the first reading of this sketch

- **Annotations are not nodes, and unifying them would be a mistake** — the author's own note, agreed. Annotations already have ids and an append-only history with supersede-by-edit, so nothing blocks this view.
- **Rounds need no store.** A round is a run, runs exist, and the log records which run authored each event. "The current round, including everything before it" and "what changed since the last round" are both queries over the log.
- **Remove is not a third verb.** Today discard is the raiser withdrawing a finding; the reader saying "do not carry this forward" is resolve with a note. Two words for one act is the collision DR-183 exists to prevent.
- **A selection can cross nodes**, and loom's anchors live inside one target's text: the annotate gesture needs a rule for that — clamp or refuse.
- **Amber is spoken for.** DR-175 spent the colour budget deliberately, keeping one register no taxon can wear so a finding is visible on a coloured page. A teach highlight reuses the annotation register rather than adding a fourth hue.
- **Do not re-render the content pane per round.** Re-keying a fragment when comments changed cost 787ms and was fixed last week; update marks, never the document.

## Discussion checklist

Ordered so that an item depending on another comes after it. Not started; the author opens the discussion.

1. **The PDF invariant** — the rule, the plan for enforcement, and the condition that must be met before the no-compile stance is deprecated. Independent of everything else here.
2. **Locator behaviour** — the anchor schema above, settled: of-record coordinate system, span shape, geometry-only case, multi-page, storage of quads. Everything anchored depends on this.
3. **The discussion model** — what a discussion item is, the full extent of what appears there, and whether transcript items may carry a text anchor or whether anchored discussion is always an annotation.
4. **Where reading annotations live** — their own store or the review log, committed or not, and the target union that lets an annotation name a document rather than a node. Needs 2 and 3.
5. **The PDF viewer component** — PDF.js, portability across contexts, virtualisation, lazy loading, and the fallback when no PDF is present. Needs 2.
6. **URL addressability** — the URL form of a locator, so an annotation is linkable and a split view restorable, and whether `cited:` links (DR-123) grow to carry spans. Needs 2 and 5.
7. **Split view: geometry and behaviour** — which views enable it, where unanchored discussion items go, the movable divider for any n : 100 - n, swapping sides, collapsing either side Overleaf-style, and the collapsible left rail. Needs 3 and 5.
8. **Syncing content and discussion** — the annotation marker, double-click to travel, whether scrolling one follows the other, and what happens where there is nothing to travel to. Needs 2, 5 and 7.
9. **Retiring the gutter** — what becomes of the three Comments placements shipped last week, the stored preference, and the marker's appearance in the content pane. Needs 7 and 8.
10. **The dispatch transport** — how the chat box reaches a local agent, what happens when none is listening, and how a transcript streams back without the polling that froze the viewer. Needs 3.
11. **Authorship and the agent guard** — who the writer is on each side of the dispatch, and how DR-185's refusal under an agent marker applies. Needs 10.
12. **The static build with no PDFs** — what a published site shows when the PDFs were never committed. Needs 5.



## Detailed Discussion

One subsection per checklist item, in the order they are taken. Each is filled with the decision once that item is settled.

### 1. The PDF invariant

**Decided.**

**Scope: static content only.** A quilt holds two kinds of content. **Static** content is a document someone else fixed — a cited work — and **authoring** content is what the quilt is writing. The rule binds static content alone, and it binds the *artifact*, not the file describing it: a digest is authored in the quilt, editable and versioned, while the PDF it describes never changes. Immutability is why locators into it can be durable, which is what the word static is there to say.

**The rule.** If loom holds renderable content for a cited work, it holds a complete copy of that work's PDF. The mechanical form, which is what a check runs: every locator loom can render names an artifact present in the store whose hash matches what was recorded when it was filed.

**Renderable content** is a digest file, a recorded result, or committed page text. A bibliography entry alone is not, and a work nobody has fetched is a perfectly good state.

**Complete** means three things: present in the store, hash equal to the one recorded at filing, and a page count known and greater than zero. The copy path already records a hash; the fetch path records one the same way, and `pdfinfo` gives the page count at filing time.

**Enforcement, with three different forces.**

- **At creation, refuse.** `loom digest extract FILE` refuses a source outside the store, and names `loom refs add` / `loom refs fetch`. The obligation starts where the digest is born.
- **In the build, gate.** `refs build`'s step order is scan, resolve, fetch, extract, map, so fetching already precedes extraction; the extract step now **skips a work with no PDF** and reports it blocked, rather than making renderable content nothing can back. Where fetching is allowed the build closes the gap instead of reporting it, and `--no-pdf` warns that it leaves the work unreadable.
- **Continuously, warn.** A lint code, never an error: loom cannot fetch without consent, and a build must not fail for want of a PDF.
- **At the point of use, say so.** The reading view says the work is not available rather than showing the digest as though it were the paper.

**The build's closing report has three sections**: the entries that entered the digest; those **blocked**, each with the missing thing and the command that unblocks it (no identifier, no PDF, extraction failed, no text layer, version unverified); and those declared **unreadable**, in a section of their own, listed and not retried.

**Impossible is declared, never inferred.** Nothing in a bibliography entry says that the Stacks Project is a living work with no fixed document, so loom would chase a PDF that does not exist on every build. `loom refs unreadable CITEKEY --why "..."` records the claim — required reason, `--undo` to reverse, appended rather than edited — in a loom-side file beside the bibliography, never in the author's own `.bib`. It is the author's claim, so it refuses under an agent marker (DR-185), and it is keyed by citekey because these are exactly the entries with no identifier. It is published in the manifest, so the viewer says "declared unreadable: <why>" instead of showing an empty pane. A declaration **suppresses the lint warning** and moves the work into the report's unreadable section. Loom may print the command with the citekey filled in when an entry looks like one (`@online`, or `@misc` with a url and no identifier); the author makes the claim.

**No fresh-clone case.** The rule is about this machine's store. How an author distributes their quilt's data is their business and their liability; the default `.gitignore` is a recommendation, not a policy.

**The no-compile stance** is revisited only when a cited work exists for which loom holds source or a digest, no PDF can be obtained from any declared or candidate identifier with fetching allowed, and the author wants to read it — **and** we have an answer for how a locator into a self-compiled PDF is checkable by someone who does not have that compile. A PDF we compile has our pagination, not the publisher's, so its locators are private to the machine that made them. Count of such works today: zero across five corpora.

**Known consequence.** `demos/build.py` extracts relloc's Man12 digest from a fixture path outside the store; that line stops working, which is the instructive outcome. It must not be repaired with our own compile of the paper.

### 2. Locator behaviour

**Decided.** Mostly an extension of the `Anchor` loom already has, not a new model: it carries `kind`, `sha256`, `page`, `last`, a single `quad`, and for LaTeX a `path` and `bytes` range.

**One anchor type, shared** by results, digest nodes and annotations. The node key is optional, which is what lets an annotation name a document rather than a node.

**Basis: text when it can be had, geometry always carried.** The anchor declares `basis: "text" | "box"`. Prose gets offsets into loom's committed page text, which stay listable, searchable, verifiable offline and re-findable in another copy. A display formula gets geometry, because the text layer there is control bytes. When the basis is `box`, loom still records the best text it can for the covered area and the lines either side, in the `exact`/`prefix`/`suffix` shape annotations already use, marked unreliable — so search can reach it in principle. Recording never fails.

**Shape.** `quads`, one rectangle per line, replacing the single `quad` — a bounding box over three lines swallows the column. A **point is a span whose end equals its start**, so "jump here" and "highlight this" are one type. A span crossing a page break uses the existing `last`. An anchor names the **artifact hash**, never the citekey, because a preprint and its published version are sibling entries.

**Coordinates: points, top-left origin**, which is what `pdftotext -bbox-layout` actually emits — stated explicitly in the spec, because `Span`'s docstring today claims PDF user space (bottom-left) while holding poppler's top-left numbers, a vertical flip waiting for whoever trusts it. Per-page `width`, `height` and `rotate` are published, and the viewer converts once per page.

**Geometry is derived, and lives in a per-work sidecar** (option B). The manifest carries the anchor and a pointer, `{path, sha256}`; `build/spans/<scheme>/<id>.json` carries the page table and the quads by result or annotation id. The manifest stays small as digests multiply, a static site still works because a sidecar is a plain file, and the hash in the pointer is what busts a stale cache under `loom serve` — the one staleness risk worth mitigating, since copy-once already makes a changed PDF impossible and both files are written by the same build.

**Mapping happens server-side.** Arras sends `{page, rects, text}` from a PDF.js selection; loom maps it into the page text with the normalisation `refs locate` already does for hyphenation and ligatures, and records the canonical anchor. The client never decides what the anchor is.

**Digest nodes get an anchor best-effort**, by matching each statement into the page text at extraction time, and the node is marked when the match fails rather than pretending.

**Rendering.** Absolutely-positioned rectangles, flat colour at low alpha, no blend modes, filters or shadows. Position per page and transform only on zoom or rotation change, never per scroll frame, and materialise only the pages PDF.js has virtualised in. One canvas per page is the escape hatch if a real corpus ever strains, and only after measuring.

**Migration.** `quad` becomes `quads` everywhere, results included, and the demos are regenerated. No backwards compatibility is owed at this stage.

### 3. The discussion model

**Decided.**

**The line is lifecycle, not anchoring.** An **annotation** stands until it is resolved, appears in `loom status`, and can be replied to, edited, withdrawn and undone. A **transcript item** is a moment in a conversation and never resolves. Anchored discussion is therefore always an annotation, but a message **may carry locators**, drawn transiently — the highlight appears while the message is focused and goes when it is not. A locator in a message is a pointer; an annotation is a claim about the text. The mechanism already exists: agent bodies in the showcase carry `[page 2](cited:arxiv:2504.01234v1#page=2)` and `#quote=…` links today.

**Six kinds**: `objection`, `suggestion`, `question`, `confirmation`, `citation`, `note`. `ok` becomes `confirmation` — the other kinds are nouns, loom's own prose already says "three suggestions and one confirmation", and `good` would be praise where the claim is that something checks out; `checked` and `verified` were rejected for colliding with the anchor check and with `refs verify`. `note` is the explanation-or-aside kind, and the natural one for teaching. `--kind` accepts any unambiguous prefix, so the extra letters cost nothing.

**Severity is accepted only on `objection` and `suggestion`** and refused elsewhere: it is how bad the fault is, and the other kinds claim no fault.

**One time-ordered stream, with a by-position toggle.** Annotations and messages interleave by time, which is what a transcript is; reading a static work, a toggle re-sorts by page and position and groups everything unanchored under one heading. Position-ordering as the default was rejected because unanchored items would need a bucket in the common case.

**Three tiers of content**: conversation (messages), findings (annotations with replies, kind, severity, state and verbs), and **events** — run opened, resumed and closed, a proposal verified or discarded, a node accepted, a link made. Story events sit inline, compact and greyed; the full command log is an **alternate rendering of the same pane**, the way Overleaf swaps the PDF for the compile log, not a third column.

**The transcript refers to an annotation; it never copies it.** A message body carries a block reference — the shape loom already uses for node inclusions, `<div class="include" data-key>`, becomes `<div class="annot" data-id>` — and arras renders the live card there. Consequences, both settled: **each appearance renders the annotation as of that moment**, with only the **most recent appearance carrying the live verbs**, so the stream reads downward as a history rather than printing "resolved" above the message that resolved it; and the content marker travels to the latest appearance, which is the only actionable one.

**Everything is shown; unreferenced annotations are marked, not hidden.** An annotation nobody referenced appears at its creation time, recessed and labelled *recorded, not discussed*, so the transcript never implies the agent narrated it. Hiding was rejected because the reader's own annotations carry no run at all — a filter keyed on the agent's narration would hide your own writing and strand its markers. A density filter remains available, and following a marker overrides it.

#### 3a. Sessions and the session selector

**A session is one concept shared by an agent and a person**, grouped around a thematic goal — "revise section 2" — which both work in parallel. This is less new than it looks: agent annotations already carry `run`, a person's are already grouped into a thread by author and day (`comments/wren-halloway/2026-09-17`), `Thread.kind` is already `run | comments`, and the store calls the field "the run or comment session this belongs to". What was missing is that the grouping was derived and implicit rather than named and selectable.

- **`author` is who wrote it, `session` is where it belongs.** Today an agent annotation records the run id *as its author*; unifying the container lets the two separate, and per-event authorship is what DR-185's guard keys on.
- **A stable id with a mutable title.** Renaming forces it: a run's id is its directory name today, so a rename would dangle every reference. Sessions get `s-…` ids, the title is metadata, and `.loom/sessions/<id>/` is named by the id.
- **Sessions live in `.loom/`**, machine-maintained, with an append-only `sessions/index.jsonl` carrying `created`, `renamed`, `resumed`, `closed` and `deleted`; a directory appears only when a session has content. `ai/runs/` folds into it, and `ai/` keeps the modes and the orientation.
- **A round is the span between `opened`/`resumed`/`closed` markers**, since a resumable session can no longer be the unit for "what changed since last time".
- **Auto-created, never demanded.** Annotating with nothing active creates a session and makes it active, for a person and for an agent alike. An agent joins; it creates only when invoked with none, and records that it did.
- **One active session at a time**, global rather than per-document, and writing while the view shows `all` still lands in the active session. Sessions carry `targets`, so "touching this document" stays a cheap filter.
- **Closed sessions' annotations are hidden**, governed by `show_closed_annotations = false` in the quilt config.
- **Deletion is a tombstone**: `deleted` is an event, the session leaves the viewer, the log keeps what was written — which is what book 4.8 rules 2 and 3 require. `loom session delete --purge` really erases, is CLI-only, and carries its own warning.
- **Activity indicator.** A session shows `N open`, and beneath it a clay pill, `3 new`, counting events by anyone but you since you last opened that session — the thing a shared session needs, since an agent may work while you are away. Unread is per-viewer state and belongs in the browser, not the shared store.

The chosen design is **B + C**: C's two-line header over B's grouping and manage toggle.

```
▾ Sessions                                  RECOMMENDED
    writing to   revise section 2                 + new
    showing     [ this session | all ]           manage
   ─────────────────────────────────────────────────────
   ACTIVE
   ● revise section 2                           7 open  ✎ ✕
       tighten the rank argument                 3 new
       you, referee ⟨agent⟩, simplify ⟨agent⟩ — resumed today
   RECENT
   ○ reading Bellamy 19                         4 open  ✎ ✕
       you — Thursday
   ○ ingest Arden 25                            0 open  ✎ ✕
       ingest ⟨agent⟩ — finished Wednesday
   CLOSED (3)
   Annotations hidden · show_closed_annotations = false
```

![The session selector, B + C](images/mockup-session-selector-b-c.png)

Rejected: **A**, a flat list with hover actions, which puts a delete cross one mis-click from a session holding open annotations; and **C alone**, which makes the two controls legible but does not scale past a handful of sessions. The manage toggle is what protects the delete, and the header is the only place the write-target and showing distinction can be made visible without explaining it twice.

Two choices made in the drawing: the **goal line appears under the active session only**, because on every row it becomes a wall of prose; and **`+ new` sits in the header**, being an action on the section rather than the last item of the list.

The confirmation, with the tombstone wording:

![Deleting a session](images/mockup-delete-session.png)

#### 3b. The side panel

The panel is reworked into collapsible sections — **Documents**, **Nodes**, **Contents** (the table of contents) and **Sessions** — and **scrolls**, since everything expanded will not fit. **Documents** holds three groups: working drafts, canon, and **Library**, which lists each work as a *whole document* rather than as nodes, so a work is one click away and one declared unreadable says so in place. A **collapse control** in the panel's header hides the panel Overleaf-style, giving the content and discussion the full width. The **Indexes** group leaves the panel for a development page we keep while building: tags, taxa, threads and loose stay as routes, they are simply not furniture. Its rail item is deliberately an **obviously weird symbol** — `⚗` — rather than a designed icon, so that nobody mistakes a development shelf for part of the interface, and so it is conspicuous on the day it should be removed.

```
┌──────────────────────────────────────┐
│ Quiver polytopes                 ⟨|  │  ← collapse
│ drafting/main-atomic.tex             │
├──────────────────────────────────────┤
│ ▾ Documents                          │
│     WORKING DRAFTS                   │
│     main-atomic.tex · reading        │
│     talk.tex                         │
│     sketch.tex · conflicted          │
│     CANON                            │
│     paper-v2.tex                     │
│     paper-v1.tex                     │
│     LIBRARY                          │
│     Arden 25 · arxiv:2504.01234v1    │
│     Bellamy 19 · doi:10.4171/…       │
│     Stacks Project · unreadable      │
│ ▸ Nodes                              │
│ ▸ Contents                           │
│ ▾ Sessions                    + new  │
│      writing to revise section 2     │
│   ● revise section 2         7 open  │
│       you +2 agents — resumed  3 new │
│   ○ reading Bellamy 19       4 open  │
│   ○ ingest Arden 25          0 open  │
│      closed (3) · annotations hidden │
└──────────────────────────────────────┘
```

![The side panel](images/mockup-side-panel.png)

Live canvas with every variant, including the two that were rejected: https://claude.ai/artifact/XAiUMfLA1xFkNWMS49bbKA

### 4. Where reading annotations live

**Decided.**

**One log.** Reading annotations go in `annotations/log.jsonl` with everything else: same verbs, same kinds, same anchors, same session. An earlier position in this discussion was that they deserved their own store; item 3 overturned it, because a session is one thing shared by a person and an agent, and splitting the log by subject matter would split a single session's events across two files. The log's `target` is **already a union** — node keys, proofs, equations, whole files, digest nodes — so annotating someone else's mathematics is not a new category. Annotating a *page* rather than a rendering of it is the only new thing.

**The target is the work identifier**, `arxiv:2504.01234v1`, not the citekey: citekeys are quilt-local and get renamed, identifiers are what two quilts agree on, and a preprint and its published version are already distinct identifiers. The anchor carries the artifact hash, which pins the exact file. Both targets stay legal for a cited work: the **digest node** when you annotate the rendering, the **work** when you annotate the page, and the anchor says which surface you were on.

**`loom status` never shows them by default, and `loom status --reading` lists them by work.** Status is a per-key table — every key with its state, its cause if stale, and its review facts — and a document-targeted annotation has no key, so it has no row. There is nowhere to put it rather than a decision to hide it. Annotations on digest nodes keep appearing as they do today, because those are keys the author depends on. Reading notes also **count toward no open-finding total**: they are additions to the text and stay open by design, so "open" is their resting state and not a backlog.

Consequence for 3a's selector: there is **no such thing as a reading session** — an author reads and reviews in one sitting — so the badge is always `N open`, and it counts the annotations that **await an answer**: objection, suggestion, question, citation. `note` and `confirmation` record rather than ask, so they do not count; otherwise a session where a paper was read closely would show a number that only ever climbs, which is the same uselessness as counting notes.

**Committed by default**, like the rest of the log. There is no private-notes mechanism: how a quilt's data is distributed is the author's business and their `.gitignore`.

**Bodies publish into the per-work sidecar** that item 2 already introduces for quads, so opening a paper fetches one file carrying its annotations, their anchors and their geometry, and the manifest carries only a count. This is a departure from how node annotations publish today, and it preempts [[WQ-36]] for this class rather than waiting for a manifest to cross a few megabytes.

### 5. The PDF viewer component

**Decided.** PDF.js (`pdfjs-dist`), vendored by dynamic import the way arras already vendors MathJax, replacing the `<iframe>` on the browser's own renderer. Of today's 173-line `PdfViewer.svelte` the **refusals survive** — no copy on this machine, and a copy of a different version offered only with a warning — and so does the global catcher for `cited:` links; the iframe does not.

**A dumb renderer.** It takes an artifact, a page, spans to draw and a span to scroll to, and it emits what the reader did: selection made, box drawn, page changed, link followed. It never fetches annotations, never knows what a session is, never decides what a highlight means. That contract is what lets one component serve the split view's content pane, the modal, the proposal box and the hover preview without forking.

**Loaded only when a PDF is**, with the worker emitted by the bundler, so a reader who opens no paper pays nothing. **Standard fonts and CMaps both ship**: PDF.js fetches only the file a given document asks for, so they cost weight in the vendored package and nothing at load time — and loom is served locally, not published as a static site, so package weight is the cheap axis. Without the standard fonts an old journal PDF that references Helvetica without embedding it renders with substituted metrics; without CMaps a CJK document may not render or extract at all.

**Virtualised**: a window of pages rendered around the viewport, canvases outside it destroyed, text layers and highlight overlays built only for rendered pages. The stress case is real — the study's bibliography includes a 679-page set of lecture notes.

**Navigation is a history stack, not a modal**, wherever there is a content pane: following a `cited:` link moves the pane and leaves a back affordance, **tab-like**, so several open documents can be moved between. The modal survives only where there is no content pane — the graph, the review table, the threads index. **Hovering a locator link shows the place in the PDF**, not the digest: one page rendered at low priority, scrolled to the anchor with its highlight drawn.

**Selection is the annotate gesture; a box is the fallback.** Where a text layer exists, dragging across words yields page, rectangles and text, and loom maps it to a text-basis anchor server-side. Where it does not — a display formula, whose text layer is control bytes, a figure, a diagram or a scan — the reader drags a **box**, which records the geometry-basis anchor item 2 allows. The viewer has a **toolbar** with both tools and a **modifier key** for the box; hovering the box tool for a second shows a tooltip saying briefly what it is for and which modifier invokes it. The viewer **switches to box mode by itself when a page has no text layer**, since selection there is guaranteed to fail. **In box mode, a click without a drag leaves a point** — which is exactly item 2's degenerate span.

**The proposal box becomes a split view of its own**: the real page on the left, at the anchor with the quotation highlighted, and the agent's rendering — "rendered as" — on the right. That replaces today's arrangement, which puts `pdftotext`'s extraction of the page beside the rendering, and it is a better basis for the decision DR-179 asks for: the page's own typesetting against the LaTeX, rather than a lossy text layer against the LaTeX. **The `pdftoppm` image pipeline is retired**: the PDF is the ground truth and rendered page images are a second thing to maintain. Page *text* stays — it is what the anchor check runs against and what a coauthor with no PDF re-checks.

Consequences to carry into implementation: **DR-179 is amended**, since it mandates the page image; the manifest's `page_images` and `page_focus` fields go; and **[[WQ-40]] closes by obsolescence** — it exists because only pending proposals get an image, and with a live viewer any result, pending or verified, shows its page on demand with no build-time rendering at all.

**Feature scope**: fit-width in a pane, fit-page in the modal, zoom, page jump, and find within the document via the text layer. No thumbnails, no rotation controls, no print chrome; corpus-wide search stays `refs grep`.

### 6. URL addressability

**Decided.**

**No new route: one page per work, and reading is a mode of it.** `/library/<citekey>` is the work's record — entry, identifiers, results, proposals, links — and the same route with a `page` opens the document itself in the viewer. A `/work/<scheme>/<value>` route was proposed and dropped: the PDF is already the ground truth at `digests/storage/<scheme>/<id>/paper.pdf`, serving those bytes gets the browser's own renderer and none of the marks, and what a route adds is the *page in arras*, which the digest route can be. Every other arras route is keyed by the quilt's own names — `/node/sh-0009`, `/master/main-atomic` — so an identifier-keyed route would have been the only one that is not. The route is `/library/<citekey>` rather than `/digest/<citekey>` under the vocabulary settled in item 7.

```
/library/Bellamy19                                   the record
/library/Bellamy19?page=12                           the document, at page 12
/library/Bellamy19?page=12&span=1043-1189&annot=a-2026-09-20-0003
```

**Portable links use identifiers, local URLs use citekeys.** `cited:arxiv:2504.01234v1?page=12` means the same thing in another quilt; the app URL is this machine's view, and the manifest maps between them, as it already does.

**Everything in the query, with long key names.** `page`, `span`, `box`, `annot`, spelled out because agents and authors write them by hand. `span=1043-1189` is text offsets on that page, `box=92.4,318.7,519.6,331.2` is geometry in points with a top-left origin, and `annot=<id>` resolves through whatever anchor that annotation carries, which is the form most links should use because it survives re-anchoring. `cited:` takes the same keys — `cited:arxiv:2504.01234v1?page=12&span=1043-1189` — so there is one locator syntax with two prefixes. The fragment was considered, since `#page=` is the PDF convention and arras keeps filters in the query already; it lost because one parsing path and no rule about which half a key belongs in is worth more than the convention, and the few `cited:` links that exist are cheap to rewrite.

**A URL names a place, never an arrangement.** In it: the target, the place, the discussion focus. Out of it: pane widths, collapse state, the active tool, the set of open tabs. Restoring a whole working arrangement is a real want — handing a coauthor three papers side by side, coming back after a crash — but that is *work*, and item 3 already built the container for work: a session knows its targets and can restore them. Pane navigation pushes real history entries, so the browser's back button and the tab's back affordance are one thing.

**An orphaned document stays reachable, and heals.** `bibliography.bib` is partly seeded from the PDFs in `refs/` in the first place, so the store is a seed of last resort: `refs scan` offers an entry for **any stored document no entry names**, using the copy ledger, which records every document with the filename it arrived as. A deliberate deletion is kept deleted by a tombstone, `loom refs forget <citekey|hash> --why`, the same shape as the unreadable declaration. Until an entry exists the document is addressed by hash — `/library/?doc=sha256:9f2c…&page=3` — and the Library shows such documents in a section of their own.

**The CLI prints openable links when there is somewhere to open them.** `loom serve` writes `.loom/serve.json` with its port and pid, and commands end with an `open:` line only when that file says something is listening:

```
$ loom refs locate Bellamy19 3 "balanced at every vertex"
p.3  box 92.4,318.7 519.6,331.2  (14 words)
open: localhost:8791/library/Bellamy19?page=3&span=1043-1189
```

Records never store such a link: a body keeps `cited:`, which travels, and the printed URL is for the terminal it was printed in.

### 7. Split view: geometry and behaviour

**Decided.** Item 3 settled what is *in* the discussion pane; this is the frame around it. With the icon strip, the side panel, the content pane and the discussion pane that is four columns, which is why collapsing matters more here than in a two-pane editor.

**The vocabulary, settled here and used from here on.**

- **Library** — the collection of other people's documents and its index, whatever their relation to the paper being written. It absorbs today's `/references` and `/digest` listings. *References* was rejected as saying "things I cite" when half the pile is things merely read; *Digest* as naming the container after one optional part of it, since a dropped PDF that was never extracted is a Library entry with no digest; *Works* as colliding with the book's other sense of work; *Corpus* as spoken for by weft, and *Sources* as spoken for by a paper's LaTeX. The collision with "library quilt" (8.10) is benign: such a quilt is all Library.
- **A work** — one entry in the Library: the bibliography entry, its identifiers, the stored document, the digest if it has one, its results, its annotations and its links. A work may have **no digest**, and a preprint and its published version are **two works**, being two identifiers with two paginations.
- **Authoring View** and **Library View** — your own draft rendered from your LaTeX, and a work's document rendered from its PDF. The old names, read view and document view, said which renderer rather than whose writing; *Reading View* was tried and dropped, because you read your own draft too.
- **authoring nodes** and **digest nodes** — retiring "external node", which only ever meant "not yours". Here *digest* is exact: those nodes come from a digest file.
- *Static* stays the word for the property that makes locators durable (item 1); *reference* and *library* describe the role. Where the interface needs a word, it is Library.

**The split is a mode of a route, never a route of its own**, available where there is a single content target: the Authoring View, a node page, a work's Library View, and a session permalink. It is absent from the graph, the review table, problems and the indexes, which have nothing for the content half to be — clicking a finding there **navigates** to the node with the split open rather than splitting the table.

![The split view](images/mockup-split-view.png)

**The session keeps a permalink**, `/session/<id>`: an agent ending a run needs something to hand you, a coauthor needs to be given a conversation, and a session spanning five nodes has no single document it could be reached through. Arriving there shows that session in the discussion and puts its most recent target in the content pane; it does **not** change the write target, since item 3's rule is that selecting for viewing never redirects writes, and the pane header offers a one-click *write here*. Selecting a session in the side panel stays non-navigational.

**The divider** is free from 0 to 100 with a **single snap at the middle**, double-click to return there, and arrow-key nudges when focused, because a drag-only control cannot be used without a mouse. **Collapse chevrons sit on the divider**, Overleaf-style: fold either side to a strip, click the strip to restore. **One global ratio**, not one per view. The side panel collapses independently and is the first thing to go as width runs short.

**Below roughly 700px the split becomes a switch** between the two panes rather than two unusable columns.

**Tabs belong to the content pane only.** The discussion follows the active session and the content in front of you; it has no tabs of its own.

**Zoom persists per renderer kind**: a scale over a PDF — fit-width, fit-page, a percentage, ctrl-scroll — and a size step over your own prose, which is the text-size preference that already exists. A PDF at 140% never changes the size of your writing.

**The composer is one thing in two states**: docked in the foot of the discussion pane by default, where your typing sits beside what it produces, with an expand affordance promoting it to a **full-width bar across the bottom of both panes** — the shape the brainstorm asked for, and the one that suits talking to a session rather than to a pane. An empty discussion still shows its composer; that is how annotating a paper nobody has touched begins.

**Swap sides** is a toggle in settings for now, and is expected to be deprecated.

**Consequence to carry**: folding `/references` and `/digest` into `/library` amends DR-184, which made the digest view the seventh view deliberately.

### 8. Syncing content and discussion

**Decided.**

**The panes scroll independently.** Scrolling one never moves the other; **double-click is the only sync**. Coupled scrolling was rejected because it fights the reader the moment they want a finding in view while looking at a different page, and because independent scrolling is what the brainstorm asked for.

**Travel is a brief scroll, then a flash** on the target — not a jump, which loses your place, and not a long animation, which costs time. Double-clicking a marker in the content travels to the annotation's **latest appearance** in the stream (item 3); double-clicking an annotation travels to its place in the content.

**Where there is nothing to travel to** — an annotation anchored to another document, or a detached one — a brief *nothing to travel to* notice appears for about 1.5 seconds, anchored to what was double-clicked. Nothing moves, and no approximate destination is invented.

**The marker is a tinted highlight plus a margin tick**, the tick being the click target. A page carrying eight highlights and nothing else is unreadable, so the highlight softens as more overlap while the ticks stay legible. The tick column sits on the discussion side of the content pane, so it points at where travel leads, and it follows the panes when sides are swapped.

**Overlapping anchors carry a count.** Two annotations on one sentence is ordinary; stacked translucent highlights muddy immediately, so the tick shows how many are there. Clicking a stacked tick lists them; double-clicking travels to the most recent.

**A message's locators are transient** (item 3): hovering highlights the place, clicking travels, nothing persists in the content.

Inferred while writing, and open to correction: **single click selects and double-click travels**, on both sides, so a marker can be picked out without the pane moving; and **Enter travels** when an item has keyboard focus, since double-click is a mouse-only gesture and the rest of the viewer is reachable without one.

### 9. Annotations in the content pane

**Decided.** What retires is the gutter as the **exclusive** home for annotations — one crowded surface, and the only one. In-content display survives, because a reader will not always want the split open, and the reason the gutter was useful is real: a note beside the line it is about.

**The Comments setting stays, and its three values mean better things.** Each is now a choice of where an opened annotation sits, coexisting with the discussion pane rather than substituting for it.

| Value | What it is | Where |
|---|---|---|
| **floating box** (default) | a box over the text, free to cross into the margin and out toward the window edge | both views |
| **margin column** | boxes beside their anchors, several open at once | both views |
| **inline** | the box in the flow, under its line, pushing the text down | Authoring View only — a PDF page cannot reflow |

![Floating box](images/mockup-placement-floating.png) · ![Margin column](images/mockup-placement-margin.png) · ![Inline, authoring only](images/mockup-placement-inline.png)

**A click opens an annotation; hovering never does.** The hover placement we shipped meant a box hovering *over* the text, not a box triggered by the pointer. The only hover behaviour anywhere is item 5's locator preview, which shows a place in a PDF from a link in a message — a different object.

**Box behaviour.** Every box carries an **×** at its top right. A minimum **4px inset** from the window on every side, applied after placement, so a box anchored near an edge slides rather than being clipped. **Clicking outside backgrounds rather than collapses**: an open box stays open, clamped to two lines with a lighter shadow and a lower z, and clicking it brings it to front and expands it again. The only things that close a box are its ×, Esc on the front-most, and *hide all* — nothing you opened disappears because you looked elsewhere. In the margin column, boxes with close anchors push each other down, so its honest promise is *beside*, not *level with*.

**The session selection governs the page, not only the pane.** Whatever the side panel is showing — this session, or all — is what the content marks; a tick's count is of **visible** annotations, and closed sessions stay hidden per `show_closed_annotations`. Because a page can therefore look lightly annotated when it is not, the content pane's header carries a quiet *N hidden by the session filter*. Following a direct link to an annotation overrides the filter, as item 3 settled for the discussion pane.

**Expand all is a state, not an action.** It opens every annotation in the document **at its own mark**, so scrolling reveals them already open — most useful inline, where the paper reads as an annotated copy of itself. Being a state, it survives virtualisation: a page materialises its boxes when it renders. **Hide all** closes everything open, wherever it is, and is the escape hatch that clicking-outside no longer provides.

**Keys and buttons.** `e` expands all, `h` hides all, `Esc` closes the front-most box, all only while the content pane has focus so they never fight the composer. Because a key nobody has been told about does not exist, the same two sit as **buttons in the content pane's header**, beside the zoom and the selection and box tools, with an annotation count and the keys named in their tooltips.

**The persistent marks** are item 8's: a tinted highlight plus a margin tick carrying a count.

**Rejected: the side sheet** — a narrow overlay listing the page's annotations. It never collides and never misaligns, but it is a small discussion pane wearing another name, and once the real one is a keystroke away it has no job.

Live: https://claude.ai/artifact/25s6dgcGEBRVY9iEjupKEL

### 10. The dispatch transport

**Decided.** Loom is a **mailbox, not a caller**. The composer posts through the write API, loom appends to the session, and nothing is launched. No API key is involved anywhere: a key would matter only if loom called a model, which DR-195 forbids; the agent's own harness does the calling, exactly as it does for any other command.

**A post carries the message and the changes with it**, not just their ids. Ids alone would cost the agent a round trip — a call, a wait, and output carrying more than the delta — where a compact delta costs a few hundred tokens once. The delta is **the same text `loom session next` prints**, so the inbox and the message never disagree, and it names events rather than state, each with its id so full context can be pulled when needed:

```
message: "The counterexample doesn't say why the proof misses it. Make it more detailed."

changed since you last read (3):
  a-2026-09-16-0001  objection · sh-0009 · edited by you
      "…nothing in the statement says that a loop counts as an arrow."
  a-2026-09-16-0004  question · sh-0006/proof · replied by you
      "Only in the support — the zero-weight case is Remark sh-000D."
  a-2026-09-20-0002  note · arxiv:2504.01234v1 p.2 · created by you
      "Arden's convention section is where this is settled."
```

**Two commands, one mechanism.** `loom session watch` is a **tail for a person**: it prints events as they land so you can sit in a terminal without the browser, and it delivers nothing — it blocks on the log, prints, and keeps a heartbeat. `loom session next --wait 120 --json` is for an **agent**: it parks until something arrives, returns the moment it does, and exits, so each call is a turn. Latency is an append and a wakeup, not a poll interval. `loom session send "…"` is the symmetric verb for talking to a session from the terminal.

**Presence is explicit.** Both commands write `.loom/sessions/<id>/attached.json` — who, pid, heartbeat — which is what lets the selector say *referee ⟨agent⟩ attached* and the composer say honestly whether anyone is listening. A stale heartbeat means detached.

**A message always lands, even with nobody listening.** It waits in the inbox and the composer says *no agent is attached — start one with* `loom session watch s-…`. Refusing would lose what was typed for a reason the browser cannot fix.

**The limit is turn-taking, not transport.** A parked agent sees a post instantly; an agent mid-compile sees it when it finishes and calls `next` again; `--wait` stays under the harness's tool timeout and the agent re-parks. Nothing here is vendor-specific — no flags to track, no IPC tied to one tool's internals.

**One inbox per session, read rather than consumed.** The inbox is append-only and each reader keeps a cursor, so a message survives being read and a crashed agent resumes where it was. It is a **broadcast, not a queue with assignment**: two attached agents both see everything and neither is handed a task, which is the honest behaviour for a tool that is not orchestrating.

**Coming back**: fine events for appends, coarse for everything else, sequence-numbered so a gap makes the client resync the coarse way. A full manifest rebuild per message would reintroduce the re-render that closed open boxes under the reader. The smallest unit loom can stream is **a whole message** — it never sees the model, so a "typing" feel could only come from an agent writing partial messages.

**To do when built: the agent layer's own documents.** `ai/orientation.md` and `ai/rules.md` tell an agent how to work in a quilt, and this changes both — the session vocabulary, `session next` / `watch` / `send`, the attach ritual and the loop it implies, and the fact that a message may be waiting for it. An agent that has not been told will never park.

### 11. Authorship and the agent guard

**Decided.** DR-185 refuses `loom accept`, `refs verify` and `refs discard` under an agent marker, because an agent verified its own proposal and loom recorded the author, whose git identity the agent's shell shares. Three things since then press on that: item 3 separates `author` from `session`, the write API is no longer only the author's own click, and a session is now shared by a person and an agent — so the guard cannot key on the session, and it should not key on the environment either.

**Identity is declared, not sniffed.** An agent **names itself** when it attaches, choosing a name that fits the role it was invoked in — Referee Agent, Simplify Agent, Tutor Agent — and is instructed to include **Agent** or **AI** in it. That name rides on every event it writes, and `--as` / `--author` states it explicitly on the command line. Environment markers stay as a **safety net, not an identity**: they distinguish well today, since the author's own shell carries no `CLAUDECODE`, but an author may ask an agent to run a command and a marker can be unset. So the rule is: **an explicit identity wins, and a marker with no explicit identity refuses rather than guesses.**

**A person may write from the terminal during a session**, identified the way they always were — git, the quilt's `[author] name` (DR-189), or `--author`.

**The refusals stay**, because they protect a claim — *this transcription is faithful*, *I accept this mathematics* — rather than a channel. The guard moves from the environment to the identity: refuse the author's verbs when the writer is an agent, whichever door it came through.

**An agent asks through an annotation, not a request object.** Wanting a proposal verified, it writes a `suggestion` targeted at the result, with its reasoning as the body; that surfaces in the proposal box where the author verifies anyway. A first-class request object was rejected: it adds a lifecycle, it can become a queue that nags, and — the real danger — an agent that "requested verification" will summarise itself as having verified, which is the collision DR-183 exists to prevent. A convenience flag may write exactly that annotation so the agent need not compose it.

**The write API grows a token and an Origin check.** It is no longer only the author's click, and the exposure is not the agent — which already has a shell — but any web page: a browser blocks a cross-origin *response*, never the *request*, so a page you happen to be reading can POST to `localhost:8791` and create, resolve or discard in your quilt. Requiring an `X-Loom-Token` header, written into `.loom/serve.json` and embedded in the page arras serves, closes it, because a cross-site form post cannot set custom headers; foreign `Origin` values are rejected and `Content-Type: application/json` is required, which closes the simple-form path. This is CSRF protection, not a login.

**To do when built**: the orientation and rules must carry **the list of commands that refuse under an agent identity**, so an agent learns it from its own documents rather than from a failed call. Needless round trips are the cost of leaving it out.

### 12. The static build with no PDFs

**Decided**, and mostly already answered: loom is not aimed at a published static site — the only route there would be reuse of arras through the author's own sitegen, which is not the focus. Item 1 dropped the fresh-clone special case on the same grounds, and item 5 ships PDF.js's fonts and CMaps because package weight is the cheap axis when loom serves locally.

**The reading surfaces require a server and say so rather than degrading.** A build published without PDFs shows a work's record — entry, identifiers, digest nodes, results — and where the document would be it says the document is not available here. No page-text fallback view and no page images: item 5 retired the image pipeline precisely so that there is one renderer.

**Annotations still display**, because their bodies, anchors and geometry live in the per-work sidecar (item 4), so the marks and the discussion survive even where the PDF does not.

**Writing is off**, as it already is: arras detects `/_api` and offers nothing when it gets a 404, which now also means no composer, no dispatch and no annotate gesture.


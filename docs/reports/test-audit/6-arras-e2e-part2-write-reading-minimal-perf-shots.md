# S6 · arras e2e (part 2), write, reading, minimal, perf and shots

Scope: `arras/tests/e2e/{phase5,queue,requests,routes,shell,study,workbench,workspace}.e2e.ts`, `tests/e2e-write/`, `tests/e2e-reading/`, `tests/e2e-minimal/`, `tests/perf/`, `tests/shots/`, `tests/shots-minimal/`, the seven `playwright*.ts` configs and the `package.json` scripts. Read-only; nothing was run. Paths below are relative to `arras/` unless they start with `docs/`, `loom/` or `.github/`.

Abbreviations: **F** = the static conformance fixture `tests/fixture` (default config, `vite preview`, no write API); **mut** = the test routes `**/build/manifest.json` and edits a copy; **stub api** = the test fakes `GET /_api` (and usually one endpoint); **real** = the real `loom serve` of the write or reading config; **wait N** = `page.waitForTimeout(N)`. Parametrised tests are one row with `×N`; every instance is counted.

**Tests inventoried: 232** — default slice 156 (phase5 6, study 6, workbench 7, queue 15, requests 38, routes 47, shell 17, workspace 20), write 11, reading 20, minimal 32, perf 6, shots 6, shots-minimal 1.

## Inventory

| file › test | tests | assumes | asserts |
|---|---|---|---|
| phase5 › the context › it says nothing about absences | context of a node no document reaches | F sy-0009 carries an `*unreachable` diagnostic (checked from fixture JSON first) | local graph visible; context lacks "unreachable", "no master reaches", "depends on nothing" |
| phase5 › the context › its lists come first, named as a reader names them | context order and naming | F sy-0003 in main.tex; sy-0001 = Definition 1.1; a proof of a Lemma | first `.rail-label` above graph; link `main.tex`; "Definition 1.1", "proof of Lemma"; no `/proof`; link title sy-0001 |
| phase5 › the rail › it carries no session control | no session button in rail | F /master/main | no `open-discussion`; rail lacks "discussion" |
| phase5 › the rail › a closed session is read like any other | closed session's Chat opens and is selected | F first non-open session (s-2026-09-15-0001) | Chat in pane 1; footer name = session title |
| phase5 › annotations › show all opens every box in the flow | show-all vs a single floating mark | F sy-0003 marks; prefs comments=floating | click → 1 floating; toggle → >1 expanded, 0 floating; toggle off → 0; click → 1 floating |
| phase5 › the divider › is a 3px rule, beneath what a pane opens | divider width and stacking | F sy-0003 + context | `::before` width `3px`; every `[data-pane]` z-index > divider's (boolean) |
| study › F9: a link to a result of a cited work opens the paper at its page | `quilt:` link naming and target | stub transcript page for REFEREE; mut Kre99 pdf=true | text `Kre99 · Thm 2.1`; click → path /library/Kre99, page=4 |
| study › a \ref in a message reads as written | `\ref` not rendered `???` | stub transcript with `\ref` and inline math | one mjx-container; contains `\ref{sh-0007}`; no `???` |
| study › a Chat opens at its newest message after the mathematics is typeset | scroll-to-bottom after MathJax growth | stub 40 messages with two displays each; mut seq=40; wait 1500 | message-40 in viewport |
| study › F4: with the box tool, a drag from a mark draws a box, a click opens it | box tool vs click on a mark | stub api (comment); F sy-0003 mark | click → comment-expanded; drag → `note-at` |
| study › F13: where something keeps loom from starting the agent, the Chat says what | blocked launch status | stub api, packet, events with `agent.blocked` | `chat-status` exact sentence |
| study › F14: under a publisher the Chat opens on the newest page | paging and poll cursor | stub events seq 250, transcript pages 1–3; resize 1100×600; wait 500 | 250 in view before/after resize; 200 absent then loaded on scroll-up; contiguous run; no `since=0` |
| workbench › the documents section lists landmarks and drafts in two groups | panel Documents | F canon widgets-v1..v3, newest @5 | drafts visible; 3 canon rows, first "@5"; click → /canon/widgets-v3 |
| workbench › a landmark is a document, with no identity and nothing to review | canon page has no node machinery | F /canon/widgets-v1 | h1 "Widgets"; tab `widgets-v1 @1`; no keyed envs, margins, slots, local graph; refs `#…` only |
| workbench › the corpus is named by the project | title from `corpus.name` | F "The synthetic quilt" | document title; main contains "Canon" |
| workbench › a doubly defined id has no text | conflicted key page | F a `duplicate-id` diagnostic | "is defined by"; node shows "Defined in two files", 2 codes, problems link, no fragment |
| workbench › the problems page groups by subject and copies a fix | subjects, filter, copy | F both subjects, `loom:canon-edited`; clipboard on chromium only | headings "The source"/"The record"; filter; `copy`→`copied`; clipboard non-empty |
| workbench › a key whose text a landmark recorded says which | version badge in context | F sy-0002 recorded at @1 | context `version` contains "text of @1" |
| workbench › with nothing being worked on, every view says so | no-drafts notice | mut masters=[] | notice on /, /graph, /review, /master/main; read-icon href checked only if found |
| queue › links into cited works › a link in a comment opens the work beside at its page | `cited:` link → work beside | mut Kre99 pdf, body link in a-…0001; tiny PDF routed | beside `/library/Kre99?page=4`; pdf-doc in pane 1; no modal; node stays |
| queue › links › a paper not fetched says so and links to its source | absent-copy dialog | mut body link `#page=4`, no pdf | pdf-absent text; external href `…#page=4`; no frame |
| queue › links › a link to another version warns before opening | version mismatch | mut `works` with a DOI | "a different version"; no frame; open-anyway → frame |
| queue › links › a quote anchor travels in the URL | `#quote=` → query | mut body link with quote | beside `…?page=1&quote=Artin+stacks`; pdf-doc |
| queue › links › a digest result links its page; the viewer closes on an outside press | digest page link and modal | mut pdf=true | `p. 4`; frame; click (5,5) closes |
| queue › links › with no copy on file a digest page is plain text | digest without copy | F | "Theorem 2.1, p. 4"; no page-link |
| queue › the work graph › shows what the corpus wrote, none of the literature | /graph excludes cited | F | sy-0003 node; no Kre99/paper nodes; no `filter-cited` |
| queue › the digest view › is the seventh view, and lists the cited works | Library list | F | Kre99 listed; some nav current item visible (title stale, assertion weak) |
| queue › the digest view › merges a proposal into the page it is about | proposal box, two texts | mut proposed Kre99-thm-9.9 | one proposal; flag; source and statement; p.12; run id; heading; no explanatory prose |
| queue › the digest view › shows the page itself, and names words not on it | proposal page render | mut spans route, `not_on_page` | paper, page-1, mark; added "Deligne"; page text reachable |
| queue › the digest view › with no PDF it says there is no image | proposal without copy | mut proposal, no pdf | noimage visible; no added |
| queue › the digest view › the backlog is the same view filtered | `show=proposed` | mut one proposed result | URL; pending "1"; one row |
| queue › identity candidates › a lookup proposal is shown as unconfirmed | candidate chip | mut Har77 candidates | `doi?`, doi.org href, title /unconfirmed/; none on Kre99 |
| queue › reading study › a filed paper opens whether or not anything is anchored | Library opens on paper | mut pdf, results {}, digest null | pdf-doc; no Digest tab |
| queue › reading study › a verb that needs no panel still shows why it was refused | resolve refusal shown | stub api caps; `_api/resolve` 400 | "No session selected" before picking; publisher's "no author name" after |
| requests › comments › a mark is coloured by its comment kind in either placement | kind class on mark | F a-…0001 objection | class `k-objection` (only the default placement checked) |
| requests › comments › inline, a mark expands beneath its paragraph; clicking away closes | inline placement | prefs inline; F reply on a-…0001 | 1 box with replies; aria-expanded; next sibling of block (boolean); outside click and Escape close |
| requests › comments › inline, a comment with no mark is reached from a count | detached-comment count | F a-…0006 lost anchor on sy-0001 | `1 comment`; click → 1 box |
| requests › comments › the placement is a display setting | settings sets data-comments | F | `data-comments=inline`; no gutter slots |
| requests › comments › changing the placement re-wires without typesetting again | no re-typeset on switch | prefs floating; monkeypatches `MathJax.typesetPromise`; wait 300 | document typeset counter 0 |
| requests › comments › the drawing of a formula may be skipped, its MathML never | content-visibility CSS | F math on main | `['auto','visible']` |
| requests › the Box drawing › every edge begins and ends on a box | ELK edge endpoints | F /graph | misses `[]` (vacuous with zero edges) |
| requests › the Box drawing › a node cannot be dragged; dragging pans | Box pan | F | rect x unchanged; viewBox changed |
| requests › the local graph › a node's context opens centred on the node | context local graph | F sy-0003 | >1 circles; centre is sy-0003 |
| requests › the local graph › in the read view it opens, follows, expands, closes | float lifecycle | viewport 1440×600; F main | centre moves on scroll; dialog closes outside; remembered on reload; close restores opener |
| requests › the local graph header › reads Local Graph, depth, Dot or Box, expand | header and Box mode | F sy-0003 context | labels; 2 seps; Box rects centred; >1 layer; Dot restores |
| requests › the local graph header › the graph page offers four drawings by name | toggle labels | F | Dots, Box, Sections, Reading Order |
| requests › Sections and Reading Order › Sections draws a card per section | Sections layout | F sy-0003 in a section | >1 cards; row in its card; selects Theorem; max stroke >1 |
| requests › Sections and Reading Order › Reading Order lists in order with arcs | Reading layout | F | rows sorted; edges; selects; faded opacity `0.55` |
| requests › references › a citation with no digest result links to its reference | cite hrefs | F Har77, Kre99-thm-2.1 | `/library/Har77`; `/node/Kre99-thm-2.1` |
| requests › references › the references page links each work by identifier | work links | F Man12 arXiv, Har77 synthetic | one arxiv link, `_blank`; none for Har77; no `{` |
| requests › references › a fetched PDF is offered only when the manifest says | PDF link on Info | mut Man12 pdf | href = `artifacts.dir/paper.pdf` |
| requests › review views › All is the default and the only others are Needs review and Incoming | review tabs | F `/review?show=stale` | 3 tabs; All current; table; no filter-show |
| requests › review views › the blockers address lands on All | redirect | F | URL `/review?show=all` |
| requests › review views › the problems page filters by severity from the URL | severity filter | F error diagnostics | filter value; groups = distinct error codes |
| requests › review views › the strip panel never repeats the strip | panel on index pages | F | no "Views" label on /threads /tags /loose /library; docs or show-proposed shown |
| requests › floating boxes close › the settings panel | outside press and Escape | F | closes both ways |
| requests › floating boxes close › a help panel | outside press | F /review | closes |
| requests › there is one shell › settings offers no arrangement; a link asking for one is ignored | `?shell=a` ignored | F | no data-shell; strip; no shell-a/shell-c |
| requests › hover previews › resting on a node link shows its statement; Escape dismisses | node card | F sy-0003 context "Definition" link | card with mjx; Escape removes |
| requests › hover previews › a quick pass over a link shows nothing | show delay | wait 500 | no card |
| requests › hover previews › a citation previews the page at the place it names | citation cards | mut Har77/Kre99 pdf mid-test + reload; wait 500 ×2 | no card for Har77 either way; Kre99 p.~4 → preview-page, no prose |
| requests › the floating placement › a mark opens a box clear of every edge; hover opens nothing | floating box | prefs floating; wait 400 | hover → none; click → fixed, inset ≥3.5; Escape and outside close |
| requests › four verbs › no write API means no editing affordance | verbs absent | F static preview | no verb-row |
| requests › four verbs › a panel opens above the row | reply panel placement | stub api caps and `_api/*` ok; prefs inline | panel bottom ≤ row top (boolean poll); send disabled until text; Escape |
| requests › four settings › p1 sets the compiled page | p1 CSS | prefs p1 | run-in bold head; italic statement; no border/fill; remark italic only if present |
| requests › four settings › p2 marks page ends, p1 nothing | page-break markers | prefs p2; F `numbers.page` | >0 breaks, sorted, unique; p1 → none |
| requests › four settings › b1 and b2 keep the accent, three colours | web settings | prefs b1 | ≤3 `--taxon-tone`; b2 hides numbers |
| requests › the session selector › one selection governs the page, the view filters | selection vs filter | mut 0915 session open, a-…0006 moved | show-all on; count survives pick; picker lists 2; show-current hides; show-all restores |
| requests › a session beside › choosing a session opens its Chat beside, focus stays, URL remembers | picker → Chat | mut rounds, attached, seq | one pane at rest; Chat pane 1; pane 0 focused; close/reopen; beside URL; reload |
| requests › a session beside › the document holds it the same way | session beside master | same | fragment pane 0; Chat pane 1 |
| requests › divider and panel › the divider drags, snaps, resets, nudges | divider and <700px | F sy-0003 context; resize 640×800 at end | <40, 50, 54, 50, 50 (non-retrying); no buttons; narrow strip 2 tabs, switch |
| requests › divider and panel › the panel has a Nodes section, folded, narrowed | Nodes list | F sy-0003 "parity" | folded; 1 row; "nothing matches" |
| routes › route {path} renders ×14 | per-route smoke | F titles for 14 paths | node: fragment has text; others: `main h1` has text |
| routes › node page shows the fragment with typeset math and its proofs | node rendering | F sy-0003 two proofs, number 2.1 | env; 2 proofs; mjx; `2.1` |
| routes › master view expands inclusions in place | `\input` expansion | F sy-0002 file, sy-0300 section | included block and section h2 |
| routes › problems page lists every diagnostic code | codes rendered | F diagnostics | each code visible |
| routes › unknown state labels and codes render generically | forward compatibility | mut state `mysterious`, `other:code`; prefs ids | gutter word; problems code |
| routes › incoming review stays separate and opens a comparison | Incoming + incorporate | mut `incoming`; stub api `sync-incorporate` capture | tab count; lead text; files; order (boolean); posted body; diff; comparison |
| routes › Needs review separates the block queue, pending OK, attention | Needs review, guided review | mut `unresolved` ×3 | sentence; 3 headings; guided sy-0001 "Incoming pull"; return; no Mark OK on attention |
| routes › guided review highlights a dependent citation | guided scroll | routes fragment to insert a 1200px spacer; mut unresolved | label; class; scrollTop>0; in pane and viewport; reset on switch |
| routes › interface version mismatch shows one diagnostic | version gate | mut version 99 | h1 Problems; code; no fragment |
| routes › search finds by id, alias, title, and tag | palette data | F sy-0002, def:gadget, Parity, orbits | `ninja-keys.data` contains each (booleans) |
| routes › live reload follows the manifest only | manifest polling | route flips `root_label` | h1 changes within 5s |
| routes › a node draws no annotation list; discarded are in its context | marks, boxes, discarded | F sy-0003 2 marks; sy-000A discarded in closed session | count from fetched manifest; 2 marks; objection + reply; show all = count; discarded line after admitting closed |
| routes › review causes open rendered text beside its current context | review comparison | F "5 stale", sy-0001 cause, sy-0002 dependent | URL; typeset, changed, no `\providecommand`; right of doc, no overflow; citation target |
| routes › review panel explains itself | help copy | F | lead text; help "stale", "accept" |
| routes › review statement badges agree with proved and settled counts | badges | mut `derived` flags | "2 proved", "3 settled"; chip lists |
| routes › a missing proof is said where the proof would be | missing proof | mut `loom:missing-proof` | text; below statement; in context |
| routes › a work's page lists results with their citers | digest and ledger | F Kre99 cited by sy-000A | citer; digest "2"; used not "—"; problems message |
| routes › a session's run is read as its chat and as what it did | `/thread` alias, Chat, did | F s-…16-0001 transcript and log | Chat text, no ISO dates; did row command; no said/report |
| routes › the panes point at each other | did row ↔ mark travel | F marked annotations in main | row → mark in pane; dblclick → row in did (boolean polls) |
| routes › what a session did lists only what its log says | empty log | mut log [] | exact sentence; no rows |
| routes › see also lists both directions and says where each is reached | relations | F sy-0008/sy-0009 | link; "drafting/main.tex"; reverse "Loose"; "no document" |
| routes › an unknown relation kind renders as a labelled list | generic relation | mut relation `contradicts` | list; href |
| routes › a node can be read as it was written | source toggle | F source/sy-0003.tex | labels flip; LaTeX shown; rendering hidden; back |
| routes › a suggestion shows the text it proposes | payload | F sy-0004 suggestion | placement `replace`; text; severity |
| routes › a node page answers both closure questions | closure stack | F sy-0003 dependencies | graph link; >1 rows, last centre; depth 2 ≥ |
| routes › the viewer shows no editing affordance when the publisher serves none | static preview | F | reference-notes; no tool-select, refnote-accept |
| routes › a document carries annotations of its own | document annotation in did | F annotation on drafting/main.tex | no block; did row by id |
| routes › a node's context shows the citations suggested and accepted | reference notes | F sy-0003/sy-0002 notes | three phrases |
| routes › the setting is one switch, applied everywhere | format on master and node | localStorage edit mid-test | p1 default; b2 hides numbers on both |
| routes › two floating boxes open at once, × closes one, click away closes | multi-box floating | F sy-0003 2 marks | 1, 2, 1, 0; no `.behind` |
| routes › travel goes from a mark to its finding, or says nowhere | dblclick travel | F referee mark on sy-0003 | notice shows then clears (3s); did row `.travelled` |
| routes › e opens every annotation at its mark, and h closes them | keyboard | F main | no content-head; `e` → >1 (non-retrying count); `h` → 0 |
| routes › a citation opens the cited paper at the result | cite href by copy presence | mut Kre99 pdf, then unroute | `/library/Kre99?page=4&result=…`; then `/node/Kre99-thm-2.1` |
| routes › a proposed text opens as source, and renders on asking | payload view toggle | F a-…0002 on sy-0004 | verbatim first; toggle typesets, no `\ref`; label; no copy buttons |
| shell › the shell carries the views, documents, contents, search and problems glyph | shell parts | F main | graph link; docs; contents; Search; glyph title |
| shell › the side panel scrolls; the contents' last entry can be reached | panel scroll | viewport 1280×320 | overflow auto, overflows; last entry and footer in view |
| shell › the side panel collapses, and the column goes with it | panel fold | F | contents hidden; width < ⅓; back |
| shell › the contents tree is in document order and stops above paragraphs | contents | F | "Introduction" first; "Results"; no "paragraph" |
| shell › a contents entry scrolls instead of navigating | contents click | F sy-0200 | URL `#sy-0200`; in viewport |
| shell › the contents rail marks where the reader is and follows | scroll spy | wait 150 ×2 | one current; moves; returns (non-retrying) |
| shell › every icon in the strip is drawn, not a text glyph | SVG icons | F | each link one svg, no text; Search svg |
| shell › a heading links to its node; an equation reference lands | heading-link, ref-eq | F sy-0200 | href; eq target exists |
| shell › the display preferences survive a reload | persistence | F | theme dark, size l after reload |
| shell › no route reaches an unknown key from review or problems | link integrity | F; navigates every distinct `/node/` link | each renders an item, not "no node" (messages per href) |
| shell › the graph toggle keeps the selection; both layouts draw edges | Dots → Box | F sy-0003 | selection kept; edges >0; Box ≤ Dots |
| shell › the key gutter carries the id and the state | Show ids gutter | viewport 1440×1000; prefs ids | id, "accepted"; right of gutter ≤ env; one line |
| shell › the shell fits the window | no page scroll | viewport 1440×900 | scrollHeight ≤ innerHeight; foot controls in view |
| shell › the side panel shows its scrollbar only while in use | scrollbar colour | viewport 1440×340; Chromium `scrollbarColor` | transparent at rest; not after hover |
| shell › the settings panel puts every row on one line | settings layout | F | 7 rows; one line, label inline, no spill (per-row messages) |
| shell › the icon strip offers each destination exactly once | unique hrefs | F | unique; contains `/` |
| shell › a display block never scrolls vertically | overflow-y | wait 1500 | `['hidden']`; no scrollbar width |
| workspace › P1 › a document opens on the paper | first-screen share | viewport 1440×900 | lead ≤100px; column share ≥0.45 |
| workspace › P1 › a work opens on the paper | PDF area | mut two papers; tiny PDF; 1440×900 | pdf-doc ≥70% of window |
| workspace › P1 › a pane head carries tabs and nothing else | pane head | F main + node | every child `item-tab` (boolean) |
| workspace › P1 › no route draws a rail | no per-pane rails | mut papers; 3 arrangements | no toolbar/rail/cluster inside panes (legacy selectors) |
| workspace › P2 › a document is opened once | reveal, not re-open | F context `main.tex` link | 1 tab each; pane 0 focused; panel click adds none |
| workspace › P2 › a document's controls are drawn once | one zoom box | two works | one Zoom textbox |
| workspace › P3 › a lone tab offers no controls | tab controls | F | no tab-move, tab-close |
| workspace › P3 › the contents tree is absent for a non-document | tree follows focus | F | shown, hidden, shown |
| workspace › P3 › a node in no document says nothing about it | no `in` label | F sy-0009 `reached_by` [] | no /^in/ label; no "no document includes" |
| workspace › P4 › the global rail holds two things | rail children | F | 2 children; filter group; cluster |
| workspace › P4 › every control names its target | aria-labels | F main, sy-0003 | each label contains target name |
| workspace › P4 › a control names the destination, not the state | control text | F | "show all annotations"; source label flips |
| workspace › P5 › a link opens beside and leaves its source rendered | cite click | F Kre99-thm-2.1 (no copy) | tab `Kre99 · Thm 2.1`; source fragment; 1 tab |
| workspace › P5 › a panel click does not split | panel click | F talk.tex | no pane 1; 2 tabs |
| workspace › P5 › the preview is not clipped | card outside panes | F | one boolean (no pane ancestor and fixed) |
| workspace › P5 › open here and a click differ only in pane | `preview-open-here` | F | here: 2 tabs, same path; click: beside = that path |
| workspace › P5 › focus follows interaction | wheel focus | F | open-context appears/disappears; cluster label |
| workspace › arrangement › the URL reproduces the arrangement | reload | F | tabs; pane 1 fragment; pane 0 focused |
| workspace › arrangement › ⇄ moves a tab and focus follows | tab-move | F talk.tex | counts; focus; last move closes pane |
| workspace › arrangement › a scrolled tab is where it was left | scroll restore | F | scrollTop > half (poll) |
| e2e-write/shots › the editing surfaces | screenshots of composer and Chat | real; first listed session; wait 600, 900; writes `../records/images` | nothing; overwrites two committed images on every `test:write` |
| write › a comment from a selection lands in the log as a person, anchored across the formula | select → annotate → submit | real; synthetic sy-0003 "finite widget"; first session in picker | where; `note-pending` highlight; log kind human, target, objection, minor, TeX in exact |
| write › the publisher's refusal is shown; the whole result is offered | quote-not-found | injects text into the DOM | said "quote"; nothing logged; note-whole logs unanchored |
| write › a box drawn round an equation notes the equation itself | box tool on a display | sy-0001 `eq:fix` | "equation"; target `sy-0001#eq:fix`; display marked after rebuild (10s); no bar |
| write › a document is written on the same way | select on a master | sy-0008 in main | log target sy-0008 |
| write › a citation suggestion can be accepted from the context | refs-note accept | sy-0002 suggestion text | status "accepted"; jsonl has text and `"verified": false` |
| write › a reply written in an inline comment box leaves the box open | reply + re-wire | prefs inline; first mark on sy-0003 (may be test 1's); wait 2500, 600 | reply shown; box stays; log has reply; mark toggles |
| write › a reply written in a floating comment box leaves the box open | same, floating | prefs floating; same waits | same |
| write › the Chat posts through the publisher; the agent's answer arrives without a rebuild | message + events | execs `loom session say` | message and "sent"; agent reply with `<em>` within 3s |
| write › what the person marks goes with their next message | packet | execs `loom session next --as Test Agent` (leaves a heartbeat) | tray row; tray empties; "1 question"; next's `changed` carries body and quote |
| write › with launching on, a message starts the configured agent | launch turn | writes fake agent, ai-config, config.toml; deletes previous test's attached.json | "is working"; echo (15s); agent.json `done` |
| reading › selecting text leaves it selected, and only offers to annotate | select chip | showcase Bellamy19 p2 "incidence matrix"; `opened()` wait 1500 | no composer; selection text; chip; chip → composer |
| reading › a note is written from a selection; the page shows loom's words first | PDF text note | same | "anchored by text"; highlight; log target, basis text, page 2, exact, no quads; mark k-note (15s) |
| reading › a selection across a citation and a reference is quoted as written | node quote with `\cite`/`\ref` | sh-000C proof paragraph "Ehrhart" | target `sh-000C/proof`; exact has both; manifest recorded+anchored (poll) |
| reading › a box is recorded as drawn | PDF box note | drag at fixed fractions of page 2; pointer trace | "anchored by box"; basis box; 1 quad; mark |
| reading › a mark opens the box, Escape closes it, the note waits in the Chat | PDF mark, tray, travel | needs a `.mark.note` written by an earlier test | box opens/closes; packet row; travel-nowhere |
| reading › inline is never offered on a page | PDF box always floating | prefs inline; needs an earlier mark | box has `floating` |
| reading › the session selection governs the page | show-current on PDF | earlier notes; creates session "an empty sitting" | hidden line; fewer marks; all restores; hidden count drops |
| reading › a locator in the URL is lit; a note is focused by its id | `span=` and `annot=` | page text file path; last PDF note from an earlier test (`.at(-1)!`) | transient mark `.on`; note mark `.on`; box open |
| reading › a session is named on the spot and closed from the page | picker new and close | creates "reading Bellamy, closely" | footer name; close hidden until hover; "no session selected" |
| reading › two notes on one place are one mark carrying the count | stacking | "Boundedness holds" ×2 | `data-count` 2–9; box holds that many |
| reading › a box shows the write it fired, without being closed | resolve + undo in place | "exchange inequalities" | open → resolved → open; undo button |
| reading › a selection records the lines it covers and nothing else | sidecar quads | "rational polytope"; reads `build/spans` sidecar | marks present; every quad non-degenerate and in page bounds (messages) |
| reading › the page and the zoom are typed into | zoom/page boxes | `opened()` | 150%, 75%, Escape reverts, fit changes, page 1 |
| reading › the preview lands on its mark | card scroll to result | main-atomic, Arden24 cite | mark within preview page (boolean poll) |
| reading › a scroll inside the preview does not dismiss it | dismissal | same; wait 800, 300 | card stays after self-scroll and wheel |
| reading › a mark round a formula leaves the formula typeset | mark wraps whole mjx | sh-0009 annotation "underlying graph" | 1 mjx in mark; no `\(` |
| reading › a document never compiled shows none of another's numbers | talk master | showcase talk | no numbers; cluster lacks "not yet numbered" |
| reading › a paper opened into half a pane fits its text | landing in half pane | 1440×900; "Proposition 2.1" link | lead line inside pane (boolean poll); zoom 140% |
| reading › a result that starts mid-line lands with every line in half a pane | landing geometry | Bellamy19-thm-3.2 exactly 4 lines; wait 1200 | each line within pane (non-retrying) |
| reading › a paper drawn again at a new zoom never shows a render refused | render race | CDP CPU ×8; 90s timeout; wait 6000 ×2 | no "Cannot use the same canvas"; canvas visible |
| minimal › {path} renders against the floor ×16 | no crash on the floor | fixture-minimal; 10 fixed routes + 3 nodes, 1 tag, 2 taxa; console filter | main; no "Loading manifest…"; no console/page errors |
| minimal › {path} speaks no publisher's vocabulary ×16 | neutral copy | same 16 routes | main text lacks five words |
| perf/hostile › what the viewer does with hostile input | timings + 4 screenshots | `PERF_BUILD=demos/hostile/build`; waits 800–3000; prefs `paper`/`margin` (retired) | nothing; logs. Waits for `main h1` on a node page, which no longer draws one |
| perf/probe › where the time goes | 9 micro-timings | any corpus; wait 2500 | nothing; prints |
| perf/probe2 › what actually helps | CSS experiments | any corpus; wait 2500 | nothing; prints |
| perf/probe3 › settings rows and interactions on a real corpus | INP per setting | `PERF_BUILD` relloc; clicks `comments-hover`/`comments-margin`, which no longer exist | nothing; would hang to its 600s timeout |
| perf/reading › a page of a paper renders inside the budget | PDF render budget | a corpus with a filed paper, else skip | open <2500ms; render+text <150ms; virtualised if >5 pages; no pageerror |
| perf/reading › a page carrying twenty annotations is not dearer | overlay cost | same | 20 injected marks <16ms |
| shots › the reference figures | book 15.9 figures into `docs/book/figures` | F; prefs shell a/c (ignored), comments `margin` (coerced); waits 700–900 | nothing; `shell-a-…` and `shell-c-…` now identical |
| shots/report › a corpus that has everything | 3 report images | F | nothing |
| shots/report › a run reviewed | session images | clicks `[data-pane="1"] [data-annotation-id]` in What it did, which renders none | nothing; likely times out |
| shots/report › a node read three ways | closure, verbatim, payload, notation | waits for testid `notation`, which is gone (15.3.9) | nothing; fails at the fourth shot |
| shots/report › the graph coloured by taxon | graph image | wait 1600 | nothing |
| shots/report › the same document, set two ways | `format-paper`/`format-blog` | formats `paper`/`blog` coerce to `p1` | nothing; two identical images |
| shots-minimal › a corpus that has none of it | floor images + nav absence | fixture-minimal; shell `a` ignored | no read/review/references/threads links (`references` never exists: vacuous); home, graph, problems visible |

## Critique

### Redundant or overlapping

Within the slice (keep the first-named unless said otherwise):

- **A node in no document** — `phase5.e2e.ts:18` and `workspace.e2e.ts:123` both open `/node/sy-0009?beside=/context/sy-0009` and assert the context says nothing about absence. Keep one (phase5's has the stronger precondition and phrases); fold workspace's `/^in/` label check into it.
- **Show all annotations** — `phase5.e2e.ts:62` and `routes.e2e.ts:218` (second half) both click `toggle-annotations` on sy-0003 and count expanded boxes. Keep routes (it counts exactly against the manifest); move phase5's "no box stays floating, a single mark still floats" assertions into it.
- **Floating boxes closing** — `requests.e2e.ts:414` (floating placement), `routes.e2e.ts:543` (two boxes, ×, click away) and `phase5.e2e.ts:62` all open a floating box and close it by outside press. Merge into one floating test: hover opens nothing, click opens a fixed box clear of edges, a second mark adds a second box, × closes one, outside press closes all.
- **The divider** — `phase5.e2e.ts:80` (3px, z-order) and `requests.e2e.ts:652` (drag, snap, keys, narrow) are both "the divider". One describe, two tests at most.
- **The source toggle** — `routes.e2e.ts:440` and `workspace.e2e.ts:157` (second half) flip `source-toggle` on sy-0003 and assert the same two labels. Keep routes (it also checks the LaTeX is shown and the rendering hidden); drop the source half of workspace P4.
- **Citation hrefs** — `requests.e2e.ts:254` asserts `/node/Kre99-thm-2.1` for the Kre99 cite with no copy; `routes.e2e.ts:602` asserts the same href in its second half. Keep routes (it covers both copy states); drop the Kre99 line from requests.
- **No write API, no affordance** — `requests.e2e.ts:467` (no verb-row) and `routes.e2e.ts:485` (no tool-select, no refnote-accept) are the same rule (DR-161). One test on sy-0003 with a mark opened and the context beside covers all three absences.
- **Format switch** — `routes.e2e.ts:522` (one switch; b2 hides numbers on master and node) overlaps `requests.e2e.ts:545` (b2 hides numbers). Move routes' test into the "four settings" describe and drop the duplicated b2 assertion from one of them.
- **Travel** — `routes.e2e.ts:567` second half (dblclick a mark beside the session's did → `.travelled`) is a subset of `routes.e2e.ts:363` "the panes point at each other". Keep the first half of `:567` (travel-nowhere) and delete its second half.
- **Payload** — `routes.e2e.ts:456` and `routes.e2e.ts:626` both open sy-0004, toggle all annotations and read the same `payload`. Combine: placement, text, severity, verbatim-first, render on asking.
- **The strip** — `shell.e2e.ts:12`, `:121` and `:331` each load `/` or `/master/main` to inspect the icon strip. One test: each view once, each an SVG with no text, search present, problems glyph titled.
- **The settings panel** — `requests.e2e.ts:322` (closes outside/Escape), `requests.e2e.ts:343` (no arrangement), `shell.e2e.ts:293` (rows on one line). One settings test.
- **Graph edges** — `shell.e2e.ts:193` (Box keeps selection and draws edges) and `requests.e2e.ts:113` (every Box edge on a box). The latter passes vacuously with zero edges; merging gives it the `>0` guard it lacks.
- **`/blockers`** — the routes table (`routes.e2e.ts:14`) and `requests.e2e.ts:295` both visit it; the requests test is the stronger (asserts the redirect URL). Drop it from the table.
- **Problems page** — tested in four places: `routes.e2e.ts:48`, `requests.e2e.ts:300`, `workbench.e2e.ts:42` and `:55`. Not redundant assertion-for-assertion, but they belong in one `problems.e2e.ts`.
- **Contexts** — sy-0003's context is opened by 10 tests across phase5, requests, routes, workbench and workspace, each paying a full load with MathJax. Keep them separate if wanted, but in one `context.e2e.ts`.
- **The routes smoke table** (`routes.e2e.ts:8`, ×14) — 9 of the 14 paths are loaded by stronger tests elsewhere; only `/node/sy-0200`, `/tag/orbits`, `/taxa`, `/taxon/lemma` are unique. It is cheap, so trim it rather than delete it.

Against other files (outside this slice, noted for S5):

- `requests.e2e.ts:620` "choosing a session opens its Chat beside, focus stays, and the URL is what remembers" and `chat.e2e.ts:88` "the picker opens the Chat beside, focus stays, and the URL remembers it" have near-identical names and flows; `phase5.e2e.ts:52` is a third variant (closed session). Keep chat.e2e's, add the closed-session case to it, delete the other two.
- `routes.e2e.ts:345` "a session's run is read as its chat and as what it did" and `phase3.e2e.ts:56` "a session reads as its Chat and as what it did" are the same test. `routes.e2e.ts:363`/`:404` overlap `did.e2e.ts` and `phase3.e2e.ts:72`.
- `study.e2e.ts:44` (newest after typesetting) and `:88` (F14 paging) overlap `chat.e2e.ts:49` and `:58`.
- `queue.e2e.ts:280` ("No session selected" before the publisher is asked) overlaps `panel.e2e.ts:71` "a refusal names its condition".
- `phase5.e2e.ts:28` overlaps `phase4.e2e.ts:45`; `shell.e2e.ts:49` overlaps `phase4.e2e.ts:88`; `workspace.e2e.ts:214` overlaps `phase4.e2e.ts:155`.

Within the write and reading suites:

- `reading.e2e.ts:79` is a strict prefix of `reading.e2e.ts:91` apart from the `getSelection()` check. Add that check to `:91` before the chip is clicked and delete `:79`: one `opened()` (≥1.5s fixed plus a PDF load) saved.
- `reading.e2e.ts:394` and `:414` share the same setup (hover the Arden24 cite on main-atomic, wait for `mark-_stmt`); combine.
- `write.e2e.ts:190`/`:191` are parametrised correctly and should stay two tests; the fixed waits are the problem, not the duplication.

**Plan-named files.** `phase5.e2e.ts` and `study.e2e.ts` are both lists of fixes from one plan or study, and so are `requests.e2e.ts` ("Plan 0.6: the running requests") and `queue.e2e.ts` ("Plan 0.7"). A reader looking for the tests of the divider, the Chat or the context has to know which plan touched them. Suggested homes:

- phase5 › context ×2 → `context.e2e.ts`; rail ×2 → `workspace.e2e.ts` P4, where "the global rail holds two things" already stands (the closed-session test → `chat.e2e.ts`); annotations → an `annotations.e2e.ts` holding the floating, inline and show-all tests from requests and routes; divider → next to `requests.e2e.ts:652`.
- study F9 → `links.e2e.ts`; `\ref`, newest-after-typeset, F13, F14 → `chat.e2e.ts`; F4 → `annotations.e2e.ts` (tools).
- queue → `library.e2e.ts` (links into cited works, digest, identity) and `graph.e2e.ts` (work graph).
- requests and routes → `graph.e2e.ts`, `settings.e2e.ts`, `review.e2e.ts`, `node.e2e.ts`, `session.e2e.ts`. At 47 tests, `routes.e2e.ts` is a grab-bag whose name promises only the smoke table at its top.

The test names are good ("named for the rule it holds"). The fix-ids (`F9`, `F13`) are worth keeping in a comment, not in the file name.

### Long or slow

Estimates only. Playwright was not run, per the instructions, and no timing is recorded in `docs/`. Vite build times are unmeasured, so treat the webServer figures as ranges.

**webServer cost per config:**

| config | webServer | cost | runs in |
|---|---|---|---|
| default | `build:fixture` (pdfjs copy, stage, `vite build`) + `vite preview :4173` | one full vite build, ~20–60s | CI, local full verification |
| minimal | `build:fixture-minimal` + preview `:4176` | a second full vite build | CI |
| write | `npm run build` + `cp -R` synthetic + `loom serve :4178` (initial quilt build, `--no-compile`) | a vite build plus loom start-up (timeout 180s suggests it can be tens of seconds) | local only |
| reading | `npm run build` + `cp -R` showcase + `loom serve :4177` | the same again, and showcase is the bigger quilt (PDF, digests) | local only |
| perf | `stage-fixture $PERF_BUILD` + `vite build` + preview `:4179` | a vite build | nowhere |
| shots / shots-minimal | `build:fixture[-minimal]` + preview `:4173`/`:4177` | a vite build | manual |

Local full verification (default, write, reading) therefore does **three vite builds**, and the write and reading bundles are byte-identical. Build once: a `globalSetup`, or an npm script that runs `npm run build` and then invokes both configs with the build step removed from their `webServer.command`. That saves one build per verification, and a second if the default suite served the clean build plus the fixture (by staging the fixture beside it at serve time rather than baking it into `build/`). CI does two builds for the same reason, plus a third plain `npm run build` step whose output is immediately overwritten (see Other).

**Fixed sleeps:**

- Default slice ≈5.5s: `study.e2e.ts:56` 1500 and `:109` 500; `requests.e2e.ts:96` 300, `:373` 500, `:383` 500, `:400` 500, `:428` 400; `shell.e2e.ts:112` 150, `:117` 150, `:347` 1500.
- Write ≈7.7s: `write.e2e.ts:176` 2500 and `:185` 600 in both `inPlace` tests, plus 1.5s in `e2e-write/shots.e2e.ts`.
- Reading ≈33s: `opened()` at `reading.e2e.ts:27` sleeps 1500 and is called by 12 tests (18s); `:422` 800, `:427` 300, `:475` 1200, `:502` 6000 twice (12s).

The absence-after-delay sleeps are legitimate: the hover card's 300ms delay (`requests.e2e.ts:373`, `:383`, `:400`) and hover-opens-nothing (`:428`). The rest wait for something that has an observable end state and should wait on that instead:

- `opened()`: the text layer redrawn after the Chat narrows the pane. Poll the canvas width until it is stable, as the box test does at `reading.e2e.ts:160`, or expose a `data-rendered-zoom` on the page element.
- `study.e2e.ts:56`: every `.math` has an `mjx-container`, as `requests.e2e.ts:80` already does with `waitForFunction`.
- `shell.e2e.ts:347`: typeset complete, by the same `waitForFunction`.
- `reading.e2e.ts:475`: the smooth scroll. Replace the sleep and the non-retrying loop with `expect.poll` over the lines' boxes.
- `write.e2e.ts:176`: "several publisher polls". Wait for a second manifest response (`page.waitForResponse('**/build/manifest.json')` twice), which states the intent.

**Slow individual tests:**

- `reading.e2e.ts:483`: 8× CPU throttle, 90s budget, 12s of sleep. Probably the slowest test in any suite. It hunts a race, so its value is real, but it could run once rather than on two routes.
- `reading.e2e.ts:224`: two notes' worth of 15s mark waits.
- `write.e2e.ts:242`: waits up to 10 + 15 + 10s for the fake agent, which itself sleeps 2s.
- `shell.e2e.ts:168`: one full `page.goto` per distinct `/node/` link on /review and /problems, tens of loads. Checking each href's key against `manifest.nodes`/`keys`, and navigating to one sample, gives the same guarantee for a fraction of the cost.
- `routes.e2e.ts:263`: three navigations with typesetting.
- minimal: 32 page loads where 16 would do (see below).

### Delete or combine

- **minimal: combine the two loops** (`minimal.e2e.ts:33` and `:49`) into one test per route that renders, checks errors, then checks vocabulary. Both assert on the same loaded page and neither mutates anything, so it is safe, and it halves the suite's page loads.
- **Delete** the second half of `routes.e2e.ts:567`, the source half of `workspace.e2e.ts:157`, the Kre99 line of `requests.e2e.ts:254`, `/blockers` from the routes table, `reading.e2e.ts:79` (after moving its selection assertion), and one of each pair listed under Redundant. Each is a strict subset of a kept test, so nothing is lost.
- **Dead code:** `phase5.e2e.ts:7` `REFEREE` and `:9` `serve()` are unused; `queue.e2e.ts:13` `kreschPdf` is unused.
- **"The old thing is gone" guards** — `phase5.e2e.ts:48` (`open-discussion`), `requests.e2e.ts:351` (`shell-a`/`shell-c`), `routes.e2e.ts:648` (`source-copy`), `workspace.e2e.ts:76` (`.rail, aside.right, …`), `queue.e2e.ts:127` (`filter-cited`). They can fail only if a removed testid or class is reintroduced verbatim, so they pass forever by construction. They are cheap; delete them once each removal is settled, or keep only the ones guarding a decided rule (DR-266's "no session control in the rail" is worth keeping as a positive assertion: the rail has exactly two children, which `workspace.e2e.ts:135` already asserts).
- **Dead or never-run configs and suites:**
  - `playwright.perf.config.ts` has no npm script, is not in CI, and is not in the full verification. Its five files expect five different corpora from one `PERF_BUILD`. `perf/hostile.e2e.ts:16` waits for `main h1` on `/node/hx-0001`, but a node draws no heading any more (`routes.e2e.ts:28`), so it times out. `perf/probe3.e2e.ts:80` clicks `comments-hover`/`comments-margin`, which `Settings.svelte:33` no longer renders, and hangs to its 600s timeout. `probe`/`probe2` are one-off experiments whose conclusion shipped (content-visibility on formulas, which `requests.e2e.ts:100` now guards). **Delete** probe, probe2, probe3 and hostile, or fix hostile and move it to a documented manual script. **Keep** `perf/reading.e2e.ts`: it is the only perf file with thresholds, and plan 0.13 §11 calls it a floor. But run it: point it at `tests/fixture` plus a filed PDF, or at the showcase build, from the reading config.
  - `playwright.shots.config.ts` (`npm run shots`, `shots:report`) is manual. `shots/report.spec.ts:71` waits for `[data-testid="notation"]`, which 15.3.9 says is gone, so it fails. `:40` clicks `[data-annotation-id]` in What it did, which renders none (`SessionDid.svelte` uses `did-annotation` links), so it very likely fails. `:86` photographs formats `paper`/`blog`, which `prefs.spec.ts:88` shows coerce to `p1`, producing two identical images. `shots.spec.ts:41` photographs `shell-a-rail-sections.png` with a shell preference that is ignored (DR-226), so the file is now a Shell C image under a Shell A name. It is not referenced by the book, but it sits in `docs/book/figures/`.
  - `playwright.shots-minimal.config.ts` (`shots:floor`) is manual, pins port 4177, which the reading config also pins, and its comment ("the other three configs pin 4173 and 4176") is stale. `floor.spec.ts:26` photographs `shell: 'a'`, which is ignored, and `:31` asserts no `references` link, which never exists.
  - `tests/e2e-write/shots.e2e.ts` is not dead but misplaced. Its name matches `**/*.e2e.ts`, so every `test:write` run overwrites `records/images/composer.png` and `document-annotations.png` in the repository and leaves a dirty tree. Rename it `*.spec.ts` and give it its own script, or move it under `tests/shots/` with a write-API config.

### Missing

Behaviour chapter 15 or `docs/specs/write-api.md` states, which no test in `tests/` covers (checked by grepping all e2e directories for the testids and endpoints). Most need a real publisher, so they belong in the write or reading suite.

1. **Writes land in the selected session.** No write or reading test asserts the logged entry's `session` field, although every log line carries one (`loom/tests/quilts/synthetic/annotations/log.jsonl`). Plan 0.13.1 Part 6 asked `test:write` for exactly this ("assert the note landed in the selected session and not the most recent"). Add `expect(mine[0].session).toBe(selectedId)` to `write.e2e.ts:66`, with a second open session made most-recent first.
2. **The rest of plan 0.13.1's `test:write` list**: with nothing selected the composer is disabled and the tip shows; the delete modal's count matches the row; ⟳ reopens; a rename appears before the rebuild. Rename and reopen exist only against stubs (`panel.e2e.ts:131`, `:151`). **`session-delete` is called by `SessionFooter.svelte:25` and tested nowhere.**
3. **edit, discard, undo discard, and a reply's own discard** (15.3.4a) have no test with any publisher. `verb-edit`, `verb-discard` and `verb-undo-discard` appear in no test. Only reply (write), resolve with undo (reading, on a PDF note) and a stubbed resolve refusal are covered. Add one write test on a sy-0003 annotation: edit, assert the `edited` event and the new text in the box; discard with a reason, assert `undo discard` stands where the button was; undo, assert the event.
4. **`digest-verify` and `digest-discard`**: `ProposalBox.svelte:103-111` posts them, and `proposal-verify`/`proposal-edit`/`proposal-discard` appear in no test, stubbed or real. The queue tests render proposals with no write API only. The synthetic quilt would need a proposed result, or one can be staged into the scratch copy before `loom serve` starts.
5. **`refs-note` reject** (`write.e2e.ts:141` covers accept only).
6. **Review decisions**: `review-finish` (`review/+page.svelte:92`) has no test, and `review-decision` is stubbed only (`panel.e2e.ts:167`). `sync-incorporate` is stubbed only (`routes.e2e.ts:69`). A real one needs a git remote in the scratch quilt, which is loom's to test, but review-decision and review-finish need nothing but the served quilt.
7. **`agent-stop` against a real `loom serve`**: stubbed in `chat.e2e.ts:243`. `write.e2e.ts:242` already launches a real turn; clicking `agent-stop` while the fake agent sleeps would cover it for the cost of one assertion.
8. **Closed-selection refusal**: `reading.e2e.ts:264` closes the selected session but asserts only the footer text. 15.3.10 says the write control is then disabled with the sentence beside it; assert that.
9. **Picker controls**: `session-find` and `session-none` ("select none, the one way to detach", 15.2.3) are never exercised.
10. **Box via Alt-drag from select** (15.3.10; `FragmentNotes.svelte:87`). Also "a box drawn stays drawn while the composer is open" is unasserted in both box tests (`write.e2e.ts:102`, `reading.e2e.ts:151`); the selection highlight is asserted (`note-pending`), the box is not.
11. **Scrolling up in the Chat under a real publisher** (15.3.9, specs/manifest.md §10.1): only stubbed (`study.e2e.ts:88`, `chat.e2e.ts:58`). The write suite could post enough messages with `loom session say` to span two pages.
12. **The divider stops short of about 420px while a cited work is in a pane** (15.2.4): no test.
13. **Hover card grace** (15.3.6): 200ms to move into the card, the card staying while the pointer is in it, and its links working. The "a link to what its own pane shows previews nothing" rule was not found in this slice.
14. **Keyboard focus into a pane takes focus** (15.2.4, "a tab into it"): only press and wheel are tested (`workspace.e2e.ts:214`).
15. **The problems glyph takes the colour of the worst severity** (15.2.3): only its title is checked (`shell.e2e.ts:22`).
16. **A display block's overflow edge carries a shadow** (15.3.1, DR-104): only "never vertical" is tested.
17. **PDF dialog** (15.3.7): Escape closes it, the `#quote=` "look for …" line, and the "open the file in a tab" link are unasserted (`queue.e2e.ts:99` checks outside press only).
18. **Write-suite regression for the manifest being current when a POST returns** (plan 0.13.1 Part 2): the tests wait up to 10–15s for marks, which would hide a regression to "eventually". Asserting the mark appears within one poll interval (about 1–2s) would catch it.

### Failure diagnostics

The pattern to fix is a boolean computed in `evaluate()` or `expect.poll`, which fails as "Expected: true, Received: false" with no numbers. Return the values and assert on them, or use a web-first matcher.

- `routes.e2e.ts:99-104` (incorporation before change) → `expect(await page.locator('[data-testid=incoming-incorporation], [data-testid=incoming-sy-0003]').evaluateAll(els => els.map(e => e.dataset.testid))).toEqual(['incoming-incorporation', 'incoming-sy-0003'])`, which prints the actual order.
- `requests.e2e.ts:40-44` (`follows`) → return `block?.nextElementSibling?.className ?? '(none)'` and `expect(...).toContain('expanded')`.
- `requests.e2e.ts:488-494` (panel above row) → poll `rb.y - (pb.y + pb.height)` and `.toBeGreaterThanOrEqual(-2)`, so the failure says by how many pixels.
- `routes.e2e.ts:397` and `:401` (`inPane`/`inDid`), `reading.e2e.ts:402-411` (preview mark) and `:456-461` (lead line): same fix, poll the offset (for example `Math.max(b.top - a.top, a.bottom - b.bottom)`) and assert `≤ 2`. Or use `toBeInViewport()`, which is scroll-container aware for the pane cases.
- `workspace.e2e.ts:62` → `expect(kinds).toEqual(kinds.map(() => 'item-tab'))` prints the list. `:193` → `await expect(card).toHaveCSS('position', 'fixed'); await expect(page.locator('[data-pane] [data-testid=link-preview]')).toHaveCount(0)`.
- `phase5.e2e.ts:87` → `expect(Math.min(...z)).toBeGreaterThan(dz)`.
- `routes.e2e.ts:198-202` (search) → `expect(data.map(d => d.id)).toContain('sy-0002')` and `expect(data.map(d => d.keywords).join(' ')).toContain('def:gadget')`, so the failure shows what the palette holds.
- **Non-retrying assertions after an action** can race the UI:
  - `shell.e2e.ts:103`, `:113`, `:114`, `:118` → `await expect(contents.locator('a[aria-current="true"]')).toHaveCount(1)` and `await expect.poll(marked).not.toBe(first)`, which also removes both 150ms sleeps.
  - `requests.e2e.ts:665-681` (`expect(await at())`) → `await expect(divider).toHaveAttribute('aria-valuenow', '54')`.
  - `routes.e2e.ts:594` (`boxes.count()` right after `e`) → `await expect.poll(() => boxes.count()).toBeGreaterThan(1)`.
  - `routes.e2e.ts:482` and `reading.e2e.ts:476-480` → poll.
- **Conditional assertions** silently vanish when a selector drifts: `workbench.e2e.ts:92` (`if (await read.count())`) and `requests.e2e.ts:526` (`if (await remark.count())`). The fixture is fixed, so assert the precondition (`await expect(read).toHaveCount(1)`) and drop the `if`.
- **Order-dependent reading and write tests** fail with messages that point the wrong way:
  - `reading.e2e.ts:257` (`log().filter(...).at(-1)!`) — run alone with `--grep`, `mine` is undefined and the failure is `TypeError: Cannot read properties of undefined (reading 'id')`, with nothing saying it needed a PDF note from an earlier test.
  - `reading.e2e.ts:198` and `:219` wait 15s for `.mark.note` with the comment "the sidecar, after the publisher's rebuild", so run alone they blame the publisher.
  - `write.e2e.ts:275` deletes `attached.json` because of `:233`.

  Better, in order of preference: (a) each test writes its own note first. `page.request.post('/_api/comment', …)` with the served token is one call; the UI path is already covered by the test whose subject it is. (b) Failing that, declare the dependency with `test.describe.configure({ mode: 'serial' })`, so a failure skips the dependents instead of cascading, and guard with a message: `expect(mine, 'needs a PDF note written by an earlier test in this file').toBeDefined()`.
- `reading.e2e.ts:105`, `:136`, `:188`, `:310` and `write.e2e.ts:227` take `log().at(-1)`. That is the newest line of an append-only log that other actors in the same `loom serve` can also write to (session events, a fake agent). Filter by the body each test just typed, as `write.e2e.ts:66` and `reading.e2e.ts:337` already do.
- Good examples to copy: `shell.e2e.ts:185` (message names the href), `shell.e2e.ts:323-327` (per-row messages), `reading.e2e.ts:183` (the pointer trace in the message), `reading.e2e.ts:347-348`, and `minimal.e2e.ts:40`.
- `queue.e2e.ts:208` (`getByRole('group').or(getByText("the page's text")).first()`) clicks whichever matches first. A failure there does not say which control was meant; pick one.

### Other

**Fragility and ports**

- Ports: default and shots both pin 4173; reading and shots-minimal both pin 4177. With `reuseExistingServer: false`, any two of these cannot run at once. Give shots-minimal its own port and fix its comment.
- **Shared build output.** Every config writes `arras/build/`, and the fixture configs stage into `static/build/`. The write and reading `npm run build` begins with `stage-fixture --clean`, which deletes `static/build`. So two configs in one checkout cannot run concurrently: starting write or reading while the default suite's preview is serving replaces the build under it. This matters for the parallel job currently timing Playwright.
- **CI uploads the wrong bundle.** `.github/workflows/arras-ci.yml` builds with `npm run build`, then `test:e2e` rebuilds with the fixture staged, then `test:minimal` rebuilds with `fixture-minimal` staged, then it uploads `arras/build` as the artifact `bundle`. The uploaded bundle is the floor-fixture build (`build/build/manifest.json` included), not the production build. Upload before the tests, or rebuild after them. The same trap exists locally: `npm run build:pip` after `npm test` copies a fixture-laden `build/` (`scripts/copy-bundle.mjs` checks only for `index.html`).
- **Shared mutable quilt.** Write and reading run `workers: 1` against one scratch quilt, and notes and sessions accumulate. `intoASession` picks "the first listed session", which changes as tests create sessions (`reading.e2e.ts:230` makes "an empty sitting" most-recent, so later notes land there). `write.e2e.ts:242` edits `config.toml`, restores it in `finally`, but leaves `ai/ai-config.toml` and `.fake-agent.py` behind. Retries (none configured today) or `--repeat-each` would double-write. The honest fix is per-test setup through the API, or `mode: 'serial'` to make the chain explicit.

**Hermeticity of the write and reading suites**

- Both webServers `cp -R ../loom/tests/quilts/{synthetic,showcase}` from loom's **working tree**. Right now that tree is dirty: `git status` shows modified `showcase/annotations/log.jsonl`, `.loom/sessions/*/run.log` and `inbox.jsonl` in both quilts, untracked `.loom/history/texts/*` and `.codex/`, and ignored `digests/storage/cache/`. So the suite's starting state is not the committed one, and a local `loom serve` on those quilts leaks into it. Copy tracked files only, for example `git -C .. archive HEAD loom/tests/quilts/showcase | tar -x --strip-components=4 -C .tmp-reading-quilt`, after checking that the Bellamy19 PDF is tracked and not just present.
- The suites hard-code loom's quilt content:
  - reading: the phrases "incidence matrix", "Boundedness holds", "exchange inequalities", "rational polytope" and "totally unimodular"; `sh-000C`, `sh-0009`, `main-atomic`, `talk`, Arden24's "Proposition 2.1"; Bellamy19-thm-3.2 spanning exactly 4 lines; and `digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt`.
  - write: "finite widget", `eq:fix`, sy-0008, and sy-0002's "a textbook reference would do".

  A loom-side edit to either quilt breaks arras tests that CI never runs, so the break surfaces only in someone's local verification. Either (a) add a CI job that sets up loom's venv and runs `test:write`/`test:reading` on changes to `arras/**` or `loom/tests/quilts/**`, or (b) put a short "arras relies on" list in each quilt's README so a loom author sees the contract.
- The same ids (sy-0003 and others) mean different data in `tests/fixture` (static, default suite) and the synthetic quilt (write suite). If the fixture is regenerated from the quilt, say so in the write config's comment; if not, the two can drift apart silently.
- The suites also run whatever `../loom/.venv/bin/loom` is installed, so an arras change can fail on loom work in progress. That is acceptable for an integration suite, but the config comment should say it.

**Tests of implementation rather than behaviour**

- `requests.e2e.ts:76` monkeypatches `window.MathJax.typesetPromise` and depends on its signature.
- `requests.e2e.ts:100` asserts `content-visibility` values; `:549` reads an inline `--taxon-tone`; `:249` expects opacity `0.55`; `phase5.e2e.ts:82` reads the `::before` width and z-indices; `shell.e2e.ts:280` compares an exact `rgba` `scrollbarColor`, which is also Chromium-only.
- `routes.e2e.ts:198` reads `ninja-keys`' internal `.data`.
- `requests.e2e.ts:79`/`:419` wait on `data-comments-wired`, a test-only attribute.

Some of this is the only way to reach the behaviour (typeset once, MathML stays accessible). The CSS-value ones would be better as observable outcomes: a result carries no coloured rule in `p1`; the faded row is visibly lighter than a selected one.

**Stale text and possible doc drift**

- `queue.e2e.ts:132` "is the seventh view": the Library left the strip (`views.ts:44`), and the assertion (some nav item is current) holds for any page.
- Book 15.2.3 still says "seven at most, the seventh being `digest`", but `viewsOf` yields five.
- Book 15.3.1 says comments stand "In the margin, the default", but `prefs.svelte.ts:42` defaults to `floating` and offers only `inline` and `floating`.
- `write.e2e.ts:154` says "`hover` floating", and `:162` is mis-indented.
- `routes.e2e.ts:424` asserts the see-also list says "no document" for sy-0008, while `workspace.e2e.ts:123` and 15.3.2 say absences are omitted. The first is about a *related* node's location, so both can be right, but the book should say which rule governs a relation row.
- `docs/reports/new-features-0.9-0.11.md:3` says shot images are stored in `docs/reports/images/`; the harness writes `records/images/`.
- A stray scratch quilt `arras/.tmp-rq/` (a showcase copy with a `build/`) is referenced by nothing.

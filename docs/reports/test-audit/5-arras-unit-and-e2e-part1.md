# S5 · arras unit tests and e2e (part 1)

Scope: all 24 vitest files (120 tests; the parallel timing run reports `Tests 120 passed`) and 8 Playwright files in `arras/tests/e2e/` (61 tests). 181 tests in all. Durations quoted below are from the parallel job's `scratchpad/audit/arras-e2e.json` (4 workers, whole e2e suite 217 tests, 102 s of test time, 36 s wall); this slice is 31.1 s of that test time. Nothing was run or edited by this audit.

Paths are relative to `arras/`. `REFEREE` = `s-2026-09-16-0001` (open, title `referee`, seq 1 in the fixture); `QUICK` = `s-2026-09-15-0001` (closed, `quick`). Default Playwright viewport is 1280×720 (config sets none). Every e2e test gets a fresh page; no test depends on another's order.

## Inventory

| file › test | tests | assumes | asserts |
|---|---|---|---|
| unit/forbidden-words › src/ contains none of the forbidden words | loom-only verbs and `loom <cmd>` absent from src | cwd = `arras/` (relative `src` walk) | offender list equals [] |
| unit/host-neutrality › src/lib/ assumes nothing about the host | six regex rules over src/lib | cwd = `arras/`; exemptions for prefs.svelte.ts, paths.ts | offender list equals [] |
| unit/host-neutrality › fails when an absolute build path is added | the build-dir regex itself | rule found by its name string | regex matches `'/build/'`, not `dataUrl(path)` (booleans) |
| unit/host-neutrality › fails when a token is declared on the document root | the `:root` regex | rule found by name | matches `:root {…}`, not `.arras {…}`; exempt undefined |
| unit/host-neutrality › still forbids a publisher scheme | the `'loom:` regex | rule found by name | matches `'loom:'`, not `'cited:'`; exempt undefined |
| unit/sessions › is one selection, shared by open and closed | select moves a single selection | inline 3-session manifest; `sessionView` singleton reset in beforeEach | selected id follows open then closed pick |
| unit/sessions › keeps the selection when picked again; clearing detaches | re-select idempotent; clear resets view | as above | selected kept; clear → null and view `all` |
| unit/sessions › admits closed sessions when one is selected | select closed sets showClosed | as above | showClosed false → true |
| unit/sessions › clears, and widens the view, when the selected session goes | `dropped()` | as above | other id leaves selection; own id clears, view `all` |
| unit/sessions › refuses with nothing selected | `writable()` no selection | as above | exact refusal sentence |
| unit/sessions › refuses a closed session with the other sentence | `writable()` closed | as above | exact closed sentence |
| unit/sessions › allows it only with an open session selected | `writable()` open | as above | '' |
| unit/sessions › under `current`, only the selected session | `visible()` current view | as above | true for selected, false for others (booleans) |
| unit/sessions › under `current` with nothing selected, nothing | `visible()` current, none selected | as above | false |
| unit/sessions › under `all`, every open session but no closed one | `visible()` all view | as above | open true, closed false |
| unit/sessions › under `all` with closed admitted | `visible()` with showClosed | as above | closed true |
| unit/sessions › counts what it is keeping off the page | `hidden()` | as above | 1 |
| unit/sessions › separates open from closed and never filters by the view | `grouped()` | all sessions share one timestamp, so recency sort unexercised | open ids, closed ids |
| unit/sessions › says it the way a person would | `when()` today/yesterday/weekday/last week/'' | fixed `now`, local-time stamps | five exact strings |
| unit/sessions › says of a closed session that it closed then | `touched()` | fixed `now` | `today` / `closed today` |
| src/badges › keeps date-only observations on their calendar day | `shortDate` UTC for date-only | expected computed by re-running the same toLocaleDateString call | equality (mirrors implementation) |
| src/badges › shows the state label and the stale modifier | `stateBadge` stale | inline states | ['accepted','stale'] |
| src/badges › renders an unknown state label generically | unknown state | inline | [{mysterious, neutral}] |
| src/badges › incomplete overrides everything | `nodeBadge` incomplete | inline | ['incomplete'] |
| src/badges › combines statement, best proof, and derived labels | `nodeBadge` composition | inline keys a, a/proof, a/proof/2 | four exact parts |
| src/badges › shows recorded and derived state in statement rows… | `reviewRowBadge` | inline nodes a, b | three exact part lists |
| src/badges › reads as a verified transcription | external accepted node label | inline Kre99-thm-2.1, sy-0001 | 'transcription verified' vs 'accepted' |
| src/contents › is in document order with depth from level | `contentsOf` | inline inclusion tree | exact entry list |
| src/contents › drops units below the cap and keeps them when raised | level cap | inline | s3 absent at default, present at 4 |
| src/contents › is empty for a master with no inclusion tree | missing master | inline | [] |
| src/diagnostics › groups by code, errors first, unknown generic | `groupDiagnostics` | inline | [code, count, affordance] tuples |
| src/fragments/pages › reads the publisher's own numbers | `pagesOf` | inline stub, fake querySelectorAll | [4,4,6] |
| src/fragments/pages › gives nothing for a node never numbered | unnumbered key | inline | [null,null] |
| src/fragments/pages › gives nothing for another master, or for none | wrong/absent master or manifest | inline | [null] ×3 |
| src/graph/local › holds the centre and its direct neighbours at depth 1 | `neighbourhood` depth 1 | reads tests/fixture/manifest.json; picks first node with an edge | distances; each neighbour linked (boolean in loop) |
| src/graph/local › grows with depth and never loses a node | monotone depth | fixture | depth-1 ⊂ depth-2 (boolean loop); depth 0 = [id] |
| src/graph/local › draws a proof as its statement | proof maps to owner | fixture has a proof key | nodes[0] = owner |
| src/graph/local › draws nothing for an unknown key | unknown key | fixture | [] |
| src/graph/local › draws each cited work as one node… | `graphInput` papers mode | fixture: Kre99 digested and used, Har77 cited | paper ids present; no external; edges closed (booleans) |
| src/graph/local › contracts a digest section into its paper | section contraction | fixture Kre99 digest, sy-0003 | section absent; edge re-pointed (booleans) |
| src/graph/local › is the expanded graph minus externals, plus papers | papers vs none | fixture | sorted id lists equal |
| src/library › counts a digest, and of it what the corpus leans on | `ledgerRow` | fixture Kre99 digest has exactly 2 nodes | digest 2; 0<used≤digest; filed false |
| src/library › says what needs work | `needsWork` via results / reading | fixture Kre99 clone | unvouched 1, open 1, needsWork flips |
| src/library › claims no digest for a work nothing was read off | Har77 | fixture Har77 undigested | digest 0, used 0 |
| src/manifest/loader › hashes text deterministically | `hashText` | none | equal, different, `startsWith` boolean |
| src/manifest/loader › believes a declared capability, derives absent | `publishes` derivation | minimal inline manifest | five booleans |
| src/manifest/loader › accepts interface version 1 | version 1 | minimal | corpus.name 'x' |
| src/manifest/loader › rejects a version it does not accept | `checkVersion` | none | code `arras:interface-version` ×2 |
| src/manifest/loader › rejects unreadable JSON | parse failure | none | manifest null; diagnostic code |
| src/math/delimit › turns a display into a display | `$$…$$` → `\[…\]` | none | exact string |
| src/math/delimit › leaves an escaped dollar alone | `\$` kept | none | exact string |
| src/math/delimit › keeps line breaks and text without math | passthrough | none | exact string |
| src/pdf/document › is placed from the top | `asPercent` top-origin | none | exact percents |
| src/pdf/document › is a fraction of its own page | per-page size | none | exact percents |
| src/prefs › defaults to serif, medium, mid… | `DEFAULTS` snapshot | none | exact object |
| src/prefs › keeps the divider inside the range…, hover → floating | `coerce` clamps divider, zoom, comments | none | clamped values |
| src/prefs › ignores a stored shell | `shell` key dropped | none | `'shell' in` false |
| src/prefs › round-trips through storage | read/write | stubbed localStorage | read equals written |
| src/prefs › narrows a stored blob field by field | `coerce` junk | none | equals DEFAULTS+face |
| src/prefs › survives storage that throws and nonsense | defensive read/write | throwing stub, 'not json' | DEFAULTS; no throw |
| src/prefs › sets no theme attribute when theme follows system | `attributes` | none | null / 'dark' |
| src/prefs › sends a stored `paper` or `blog` back to the default | legacy format names | none | p1 for old names; four valid kept |
| src/reached › is what the corpus depends on, plus what that rests on | `reachedExternal` | inline rl-0001 corpus | two ids |
| src/reached › is stable when a digest brings in unused results | 93 spare externals | inline | same set |
| src/reached › does not count external→external as reached | own node removed | inline | [] |
| src/review/run › knows a document from a node | `isDocument` | one master | true / false |
| src/state › maps every colour class the interface declares | `toneOf` | none | six exact tones |
| src/state › falls back for a class it has never seen | fallback | none | 'loose', 'tone-loose' |
| src/taxonomy › gives a taxon the colour of its style | `taxonTone` by style | inline taxa | four CSS vars |
| src/taxonomy › draws an unknown style as a result | unknown style | inline | result var |
| src/taxonomy › keeps a colour as the corpus grows | stability | inline | equal tones |
| src/taxonomy › says nothing about a taxon the corpus lacks | missing taxon/null | inline | `--rule-strong` ×3 |
| src/taxonomy › offers a legend in a stable order | `taxonLegend` | inline | sorted names; [] |
| src/workbench › sends a landmark to its own page, a draft to read view | `canonUrl`/`docUrl` | inline masters/canon; empty base | four exact paths |
| src/workbench › tells conflicted from incomplete | `stateTone`/`stateClass` | inline labels | exact tones/class |
| src/workbench › falls back for a state it has never seen | `stateTone` fallback | inline | 'loose' |
| src/workbench › names the step a key's text was recorded at | `versionLabel` | none | four exact strings |
| src/workbench › treats a diagnostic naming no subject as source | `subjectOf` | none | 'source' / 'record' |
| src/workbench › groups source first, then record, then else | `groupBySubject` | none | order; first group size 2 |
| src/worklink › names an identifier and a page or a quote | `parseWorkLink` | none | six parse results |
| src/worklink › spells an identifier one way | `normalId` | none | two exact strings |
| src/worklink › opens the copy on file only when it is the linked artifact | `locate` | inline Man12 ref | local/external/otherCopy |
| src/worklink › has nowhere local when nothing fetched or not cited | `locate`, `externalUrl` | inline | undefined ×3 |
| src/worklink › carries the page extraction wrote | `pageOf` | none | 13, 18, 4, undefined |
| src/worklink › links to that page only in the extracted artifact | `digestPageLink` | inline | link / null / null |
| src/works › resolves each scheme, whatever its case | `resolve` | none | four hrefs |
| src/works › links nothing for a synthetic id | `work:` ids | none | null; [] |
| src/works › adds bib url and fetched PDF, no unfetched PDF | `workLinks` | inline | labels, PDF href |
| src/works › falls back to bibliography fields | legacy bib fields | inline | two hrefs |
| src/works › drops protective braces | `bibText` | none | exact string |
| src/works › turns accent commands into letters | `bibText` accents | none | two exact strings |
| src/works › keeps what a font command sets | `bibText` \textit/\emph | none | two exact strings |
| src/works › leaves mathematics for the typesetter | `$…$` kept | none | exact string |
| src/workspace/divider › snaps at the middle and nowhere else | `settle` snap | none | five values |
| src/workspace/divider › keeps both panes usable | `settle` clamp | none | 0.8 / 0.2 |
| src/workspace/divider › is one ratio, remembered, half by default | DEFAULTS.divider, coerce | none | 0.5; 0.42 |
| src/workspace/links › names each kind of thing the quilt owns | `itemForQuilt` node/doc/session/unknown | inline manifest mirroring fixture ids | item shapes |
| src/workspace/links › opens an annotation at its target, with its box | annotation → target, region, reply thread | inline | item shapes incl. thread root note |
| src/workspace/links › goes to a place in a node | region / proof anchor | inline | 'sy-0003-eq-fix'; proof anchor `toBeTruthy` |
| src/workspace/links › is named as a reader names the thing | `linkName` | inline | nine exact names |
| src/workspace/links › is revealed in the document on screen | `holding()` | global `workspace` singleton, reset() | item+pane; note carried |
| src/workspace/links › prefers the link's document, then on screen, then last looked at | `holding()` ranking | singleton; activate order | three chosen ids |
| src/workspace/links › is nothing for a document not holding it | `holding()` negatives | singleton | null ×2 |
| src/workspace/names › drops the page and abbreviates the taxon | `shortLocator` | none | three strings |
| src/workspace/names › keeps a locator that names no taxon | `shortLocator` passthrough | none | two strings |
| src/workspace/store › round-trips every kind, with its place | `itemFromPath`∘`pathFor` | inline masters/canon; empty base | 11 hrefs round-trip |
| src/workspace/store › resolves a stem, tells landmark from draft | stem → path | inline | two items |
| src/workspace/store › names nothing for a non-reading route | null routes | none | null ×4 |
| src/workspace/store › reads a run's old address as its session | `/thread/` alias | none | session item |
| src/workspace/store › is one item whatever its place | `itemKey` ignores place | none | keys equal |
| src/workspace/store › opens a panel choice in the focused pane (S4) | `here()` never splits | fresh Workspace | 1 pane, 2 items |
| src/workspace/store › opens a link beside (W7) | `beside()` | fresh | panes, actives, focus |
| src/workspace/store › opens an item once, revealing it (W8) | reveal in place | fresh | no duplicate; focus; place |
| src/workspace/store › stamps a reveal | seq increments | fresh | seq greater |
| src/workspace/store › moves a tab to the other pane (W6) | `move()` | fresh | panes/focus/order |
| src/workspace/store › will not move the lone tab of a lone pane (W5) | `move()` no-op | fresh | 1 pane |
| src/workspace/store › closes a tab to its neighbour, closes empty pane | `close()` | fresh | active, panes, focus |
| src/workspace/store › writes the two active items to the URL | `canonical`/`apply` | fresh | exact URL; restored items; focus 0 |
| src/workspace/store › takes a URL from outside into the focused pane | `apply()` non-empty | fresh | pane 1 active, 2 items |
| src/workspace/store › keeps state for an item until its last tab closes | `stateOf` lifetime | fresh | same object; recreated after close |
| e2e/base-path › every route and URL is composed from configured roots | hrefs relative; data under /build/ | empty base; `/node/sy-0003`; home has no `cited:`/`quilt:` hrefs | hrefs match `^[/#]`; fetched paths (booleans) |
| e2e/chat › Chat opens on the newest message, no heading | initial scroll to bottom | fakes manifest seq=40 + transcript pages | message-40 in view, message-1 not; no h1/h2 |
| e2e/chat › scrolling to the top loads the page before | paging + scroll anchoring | 150 fake events | 100 absent then present; 101 in view |
| e2e/chat › a body is rendered…, agent messages carry a rule | agent styling | fixture transcript text 'hostile review…' | text; class agent; border-left solid (evaluate) |
| e2e/chat › with no publisher, the Chat is the transcript alone | P3 no status/composer | no `/_api` route | message-1 visible; status, composer count 0 |
| e2e/chat › the picker opens the Chat beside, focus stays, URL remembers | picker → openChat | `/node/sy-0003`, REFEREE | pane-1 chat; pane-0 focused; `beside` param |
| e2e/chat › opening a second session's Chat closes the first | soleSession + select | QUICK closed, under show-closed | one tab 'quick'; footer 'quick' |
| e2e/chat › the status line says who is listening; message arrives next poll | publisher poll + send | fakes /_api, events, message; 1 s poll | status texts; message-2, message-3; in view (2.35 s) |
| e2e/chat › with nobody listening, it says the message waits | no attached | fakes publisher; Enter sends | default text; 'sent · it waits in the inbox' |
| e2e/chat › the tray lists what the next message carries | packet rows + preview | fake packet ids reuse fixture annotation ids with other kinds | kinds, names, verbatim preview (textContent one-shot) |
| e2e/chat › the preview is read whole, however long the transcript | tray height cap, stay pinned | 60 fake events | evaluate [own,holds,chat] numeric; message-60 in view |
| e2e/chat › with nothing marked there is no tray | empty packet | fake packet [] | status visible; tray 0; send disabled |
| e2e/chat › a row opens its annotation beside, and the Chat stays | packet link → holding doc | `/master/main` beside session; a-2026-09-16-0001 on sy-0003 | 1 tab; comment-expanded; chat visible |
| e2e/chat › a packet goes without words… says what it carried | empty-text send | fake message route | tray gone; 'carried 1 question, 1 note'; posted body |
| e2e/chat › a running turn says what it last ran, and stop ends it | agent running + stop | fakes agent-stop; waits for 1 s poll | status texts; stop gone; stops=1 (1.56 s) |
| e2e/chat › a failed turn says why, with nothing to stop | agent failed | fake events agent | status text; no stop (1.52 s) |
| e2e/chat › where loom starts agents and none is running | launch, no state | fake events agent | 'Claude Agent starts when you send' (1.54 s) |
| e2e/chat › where it does not, the line is who is listening | launch false | fake events agent | default 'nobody is attached…' text (vacuous: same as before poll) |
| e2e/chat › a turn that fails after a send says so | F7 regression | own routes; `started` = test clock + 1 s | 'could not run: Session ID is already in use.' |
| e2e/did › rows are the log, in order, opens on newest | did list order + scroll | manifest route prepends 60 log lines; 1280×720 | count; last in view, first not; first text |
| e2e/did › a row names what its annotation is on by key, says where it stands | did row content | fixture log mentions a-…-0001 (objection on sy-0003) and `--resolve a-…-0002` | kind, key, no 'Theorem', states, no id on later row |
| e2e/did › a row's annotation opens beside, with its box open | did link → holding doc | `/master/main` beside did view | box for a-…-0001 in pane 0; did stays |
| e2e/home › home page renders the fixture manifest | h1 + problems glyph | fixture root_label | h1 text; glyph title `^problems: ` |
| e2e/home › four metric cards which open the complete review table | card hrefs + click | none | 4 visible; three hrefs; click → /review?show=all, All current |
| e2e/home › lists the documents and what needs attention | documents list, heading | `main ul` first is the documents list | link visible; heading visible |
| e2e/links › an empty link reads as the viewer names the thing | linkName in Chat | fakes REFEREE transcript page 1 (relies on fixture seq ≤100) | four link texts |
| e2e/links › what is open is revealed where it is, no tab added | reveal document at anchor | main beside session | pane-0 focused; 1 tab; `.travelled`; in view |
| e2e/links › what is not open opens as a new tab in the other pane | new tab rule | sy-999A only in talk.tex | 2 tabs; selected 'sy-999A'; chat stays |
| e2e/links › a node an open document holds is revealed there (DR-280) | holding() in browser | sy-0003 reached by main | 1 tab; travelled; in view; chat stays |
| e2e/links › behind another tab, the document is brought forward | holding() background tab | side-panel link found by `a` hasText /^talk\.tex$/ `.first()` | selected tab talk then main; in view |
| e2e/links › a document's link to its own content takes the same path | `#` link in document | first `a.ref[href^="#"]` in main | 1 tab; travelled; in view |
| e2e/links › a link to an annotation opens what it is on, box open | annotation link | a-…-0001 on sy-0003 | box visible, one article; `note` param (poll) |
| e2e/links › a quilt: link previews what it names… | hover card via registry | fixture sy-0003 text contains 'widget'; 300 ms delay ×2 | card text; gone on mouse move; env in card (1.73 s) |
| e2e/panel › the write target is stated once | footer is sole naming | manifest route retitles REFEREE; main beside node | footer text; DOM text-node count =1 (evaluate) |
| e2e/panel › annotations are filtered from one control | single filter control | three full navigations in a loop | show-current count 1; group 1; none in picker |
| e2e/panel › a refusal names its condition | writable() sentence + footer tone | fakes /_api ['comment']; selection via evaluate+mouseup | disabled; tip text; aria-label; `.footer.refused`; flips after pick |
| e2e/panel › the session picker is not in the column | picker is a popover | `.panel .sections` class locator | list absent in column; picker opens outside |
| e2e/panel › contents hang open under a document, nowhere else | contents tree presence | two navigations | nav + toggle expanded; absent on node |
| e2e/panel › the contents bar follows the reader | aria-current tracks scroll | viewport 1280×500 | one current; text changes (poll) |
| e2e/panel › a session rename shows at once | optimistic rename | fake rename route sleeps 3 s | row + footer text within 1 s; edit button hidden until hover |
| e2e/panel › ⟳ reopens and selects | reopen endpoint | fakes `session-reopen` (absent from write-api.md) | posted session QUICK; footer 'quick'; picker closed |
| e2e/panel › a review decision needs no session | review-decision without selection | manifest route adds `unresolved` row for sy-0001 | footer refused; OK enabled; posted key |
| e2e/phase3 › the library list has one home | ledger vs panel list | /library | ledger visible; no main list; panel list links |
| e2e/phase3 › the ledger says what needs work | ledger filters | manifest route edits Kre99, Man12 | filter labels; URL; row counts 2 then 1; open count |
| e2e/phase3 › a work's counts are stated once | panel rows carry no counts | regex filter /ledger\|more\|nothing/ over li texts | each row text lacks trailing number |
| e2e/phase3 › a session reads as its Chat and as what it did | two readings | fixture transcript text | text; no h1/h2; no raw ISO; tab-chat pressed; did; view=did |
| e2e/phase3 › a finding opens its target beside | did row link opens pane 1 | /session?view=did alone | pane 1 visible; did stays |
| e2e/phase3 › a link to a kind with no preview opens no card | P3 no card for document | context of sy-0003 has 'main.tex' link; `waitForTimeout(600)` | link-preview count 0 (857 ms) |
| e2e/phase4 › a node draws its statement and proofs, nothing about them | bare node | /node/sy-0003 | env visible; no h1/h2, list, closure, notes; bbox gap < 60 px |
| e2e/phase4 › Show ids puts id and state in the gutter | node gutter | prefs {ids:true} via init script | margin visible, contains id |
| e2e/phase4 › what the node is about stands in its context | context contents | sy-0002 version step @1 | 'text of @1'; reference-notes; closure-open |
| e2e/phase4 › a context is marked by a glyph and named by its node | context tab | node beside context | one svg; aria-label `^context of `; no 'context ·' |
| e2e/phase4 › a name that does not fit ends in an ellipsis | tab CSS | name 'Theorem 2.1' fits, so no truncation happens | padding-right ≥36; text-overflow ellipsis (evaluate) |
| e2e/phase4 › a work's tools stay, greyed, off the paper | work controls disabled on info | manifest route sets Kre99 pdf=true | enabled/disabled states |
| e2e/phase4 › the panel goes first, the rail keeps parts apart | narrow window | viewport 1100×800; Kre99 pdf=true | `.panel.away`; 2 parts; boxes don't overlap; stored panel not false |
| e2e/phase4 › when parts cannot fit, filter goes behind ⋯ | rail overflow | viewport 760×800 | toggle, zoom visible; filter moved into rail-more |
| e2e/phase4 › the chosen session is still chosen after a load | selection persisted | reload | footer aria-label twice; chat in pane 1 |
| e2e/phase4 › a stored session the corpus no longer lists is let go | stale stored selection | init script stores 's-gone' | footer 'no session selected'; storage cleared (poll) |
| e2e/phase4 › one local graph on screen | float stands down beside context | `arras.localGraph`='open'; two navigations | panel in pane 1; none in pane 0; float back alone |
| e2e/phase4 › a context's link follows the one rule | context link → other pane | sy-0005's context links /node/sy-0002 | context stays; 2 tabs; pane 0 focused; pathname |
| e2e/phase4 › the focused pane is marked by its shadow | focus styling | main beside node | class focused; head box-shadow none; pane shadow not none (evaluate) |

## Critique

### Redundant or overlapping

Pairs are "keep ← drop/merge".

- `e2e/did › a row's annotation opens beside, with its box open` ← `e2e/phase3 › a finding opens its target beside`. Same click (`did-annotation`), phase3 only checks that a pane 1 exists; did checks which annotation's box opened. Drop phase3's.
- `e2e/routes › a session's run is read as its chat and as what it did` (routes.e2e.ts:345, outside slice) ← `e2e/phase3 › a session reads as its Chat and as what it did`. Same fixture text, same no-raw-ISO check, same `tab-did` click. Move phase3's two unique assertions (`tab-chat` aria-pressed, `view=did` in URL) into routes' and drop phase3's.
- `e2e/requests › choosing a session opens its Chat beside the node…` (requests.e2e.ts:620) ← `e2e/chat › the picker opens the Chat beside, focus stays, and the URL remembers it`. Identical opening, same three assertions; requests' also covers close, re-pick and reload. Drop chat's (or move requests' into chat.e2e and drop it there, since the Chat file is the natural home).
- `e2e/shell › the contents rail always marks where the reader is…` (shell.e2e.ts:91) and `e2e/panel › the contents bar follows the reader`. Same rule (DR-112). Keep panel's form, which polls instead of `waitForTimeout(150)` ×2, and add shell's "scroll back restores the first mark" assertion; drop shell's.
- `e2e/workspace › the contents tree is absent for a non-document` (workspace.e2e.ts:113) and `e2e/panel › the contents hang open under a document on screen, and nowhere else`. Both: contents present on a document, absent on a node. Workspace's is stronger (the tree follows focus within one load); panel's adds only `contents-toggle` aria-expanded. Merge into one test.
- `e2e/shell › the key gutter carries the id and the state…` (shell.e2e.ts:221, on a master) and `e2e/phase4 › Show ids puts the id and state in the gutter`. Phase4's distinct claim is "on a node too", so keep it but assert the state as well (its title says "and state"; it checks only the id).
- `e2e/routes › a node draws no annotation list…` (routes.e2e.ts:218) and `e2e/phase4 › a node draws its statement and proofs, and nothing about them`. The `annotation-list` absence is asserted in both. Phase4's title promises proofs but no proof is asserted.
- Three e2e tests walk the same path (a `quilt:a-2026-09-16-0001` link in pane 1, main.tex in pane 0, `holding()`, box opens): `links › a link to an annotation opens what it is on`, `did › a row's annotation opens beside`, `chat › a row opens its annotation beside`. Keep the links one as the rule's test; in did and chat assert only that the row's link has `href="quilt:<id>"` (cheap, no navigation) and that the Chat/did stays. The rule has one test and the renderers each have one.
- `e2e/links › what is open is revealed where it is` (document link) and `links › a node an open document holds is revealed…` (node link) have identical assertions but exercise different branches (`paneOf` vs `holding`). Keep both, share an `expectRevealed(page, id)` helper.
- `e2e/phase4 › a context's link follows the one rule` and `links › what is not open opens as a new tab in the other pane`. The same rule from two link sources; keep both but move phase4's into links.e2e's "the one rule" describe.
- `e2e/chat › opening a second session's Chat closes the first` and `e2e/phase5 › a closed session is read like any other…` (phase5.e2e.ts:52). Both select a closed session and assert the footer name; chat's is the superset. Drop phase5's.
- `e2e/home › home page renders the fixture manifest` asserts `problems-glyph` title, also in `shell › the shell carries the views…` (shell.e2e.ts:12). Drop the glyph line from home.
- `chat › the Chat opens on the newest message, with no heading of its own` repeats the no-heading check of `phase3 › a session reads as its Chat` and the newest-in-view check of `study › a Chat opens at its newest message after the mathematics…` (study.e2e.ts:44). Keep chat's.
- Unit: `src/workspace/divider › is one ratio, remembered…, half by default` duplicates `src/prefs › defaults…` (DEFAULTS.divider) and `prefs › keeps the divider inside the range` (coerce). Drop it.
- Unit: `src/prefs › ignores a stored shell` is contained in `prefs › narrows a stored blob field by field`, which already passes `shell: 'z'` and expects DEFAULTS+face. Drop it.
- Unit: `src/state › falls back for a class it has never seen` and `src/workbench › falls back for a state it has never seen` test the same fallback in `state.ts` through two entry points. `workbench.spec.ts` is a grab-bag (nav, state, badges, diagnostics) named for a plan feature, which is the unit-test version of the phase files. Move each describe to the spec of the module it imports: `routing` → a new `nav.spec.ts`, `states` → `state.spec.ts`, `version label` → `badges.spec.ts`, `subjects` → `diagnostics.spec.ts`. Then delete `workbench.spec.ts`.
- `src/workspace/links.spec.ts › names each kind…` and `src/workspace/store.spec.ts` both exercise `itemFromPath` through `itemForQuilt`. They overlap, but at different layers, so both are fine.

**Should the phase files become feature files?** Yes. They are named for when they were written, which is also why their tests duplicate files written since. Where each test belongs:

- phase3 `the Library` (3 tests) → a new `library.e2e.ts`, which could also take `routes › a work's page lists results…` and `queue › digest view` pieces later.
- phase3 `the session` (2): drop both as above.
- phase3 `the hover card` (1) → `links.e2e.ts › previews` (see "Long or slow" for a better form).
- phase4 `the node` (3) → a new `node.e2e.ts`, with `routes.e2e.ts`'s node tests.
- phase4 `tabs` (2) → `workspace.e2e.ts`.
- phase4 `the work` (1) and `a narrow window` (2) → `workspace.e2e.ts › P4` (rail) or `shell.e2e.ts`.
- phase4 `sessions` (2) → `panel.e2e.ts`, where the picker and footer live.
- phase4 `panes`: the local-graph test → `requests.e2e.ts › the local graph`; the context link → `links.e2e.ts`; the focus shadow → `workspace.e2e.ts › focus follows interaction`.

The file headers ("plan 0.13.3 phase 4: what human testing of phases 1–3 asked for") are changelog text. Once the tests move, that text goes away with the files.

### Long or slow

Measured, from the parallel run (test time, not wall):

- **The 1 s poll dominates chat.e2e.** `the status line says who is listening…` 2.35 s; `a running turn…` 1.56 s; `a failed turn…` 1.52 s; `where loom starts agents…` 1.54 s. The rest of the file runs 0.25–0.55 s per test. The cause is in the product, not the test. `ChatView.svelte:116-121` calls `poll()` as soon as `live` is true, but `poll()` returns early while `landed` is false (`ChatView.svelte:106`), and `landed` is set only after `land()`'s two fetches (`:86-91`). So the first poll is always skipped, and the status line shows the default text for up to a second, until the `setInterval` tick. Polling once at the end of `land()` when `live` would cut about 4 s from these tests and fix a real one-second wrong status line.
- `links › a quilt: link previews what it names…` 1.73 s. Two hovers, each paying the 300 ms show delay plus the 200 ms grace to dismiss. This is inherent to the rule; acceptable. It could use `page.clock` to fast-forward if it grows.
- `phase3 › a link to a kind with no preview opens no card` 0.86 s, of which 0.6 s is `waitForTimeout(600)`. A negative assertion needs some wait, but make it meaningful. In the same context, hover a node link first and `expect(link-preview).toBeVisible()`, then hover `main.tex` and assert count 0 after `page.clock.runFor(600)`. Or keep the fixed wait but put a positive control first, so the test cannot pass because previews are broken everywhere. As written, it passes if hover cards never work at all.
- `chat › the preview is read whole` 1.67 s (60 events and two fetch routes). Fine.
- `panel › annotations are filtered from one control` 0.61 s for three full navigations with picker open/close. Cheap in absolute terms, but split it into three parametrised tests (`for (const at of …) test(…)`) for diagnostics, not for speed.
- Repeated setup: `serve()` (manifest route + deep clone) is redefined in panel.e2e.ts:12, phase3.e2e.ts:8, phase4.e2e.ts:9 and did.e2e.ts:10 (as `longLog`). `chat.e2e.ts` defines `publisher`, `packet`, `starting`, plus a fourth hand-rolled set of routes in the top-level F7 test (chat.e2e.ts:276-282). Move `serve` into `tests/workspace.ts` (or a `tests/fixture.ts`) and fold the F7 test into `an agent loom starts` using `starting()` with a message route added.
- The slice as a whole is 31 s of test time; deleting the drops above (phase3 ×2, chat picker, phase5 closed, shell contents, divider/prefs unit) removes about 2 s. The poll fix is worth more than all deletions combined.
- Unit tests: 120 tests, 170 ms of test time. Nothing slow. `graph/local.spec.ts` and `library.spec.ts` each parse the fixture manifest once per file, which is fine.

### Delete or combine

Safe to delete, each covered at equal or greater strength elsewhere:

- `e2e/phase3 › a finding opens its target beside`: strictly weaker than `did › a row's annotation opens beside` (same click, weaker assertion).
- `e2e/phase3 › a session reads as its Chat and as what it did`: after moving its two unique assertions into `routes.e2e.ts:345`.
- `e2e/chat › the picker opens the Chat beside…`: a subset of `requests.e2e.ts:620`.
- `e2e/base-path › every route and every corpus URL is composed…`: it cannot fail for the reason it exists. With an empty base, a hard-coded `'/node/' + key` and a composed `route('/node/' + key)` produce the same string, and `fetched.every(p => p.startsWith('/build/'))` holds for a hard-coded `/build/` too. The real guard is `unit/host-neutrality`. Replace it with unit tests of `paths.ts` under a mocked base (`vi.mock('$app/paths', () => ({ base: '/sub' }))`): `route`, `dataUrl`, `setDataRoot('https://x/corpus/build')`, `artifactUrl`, plus `itemFromPath('/sub/master/main')` (item.ts:74). Or build once under `ARRAS_BASE` in its own config, as reading/write already have.
- `src/workspace/divider › is one ratio, remembered…`: duplicate of prefs tests.
- `src/prefs › ignores a stored shell`: contained in `narrows a stored blob field by field`.
- `src/prefs › the format rename`: it tests that two retired names (`paper`, `blog`) fall back. No stored value in any quilt needs this (no-backwards-compatibility rule), and "an unknown value falls back to the default" is already the `narrows…` test. Keep one line, `coerce({format: 'zzz'}).format === 'p1'`, inside that test.
- `src/review/run.spec.ts`: a one-assertion test of a one-line function. Keep it only if extended to the canon case below, which is where the function is interesting.

Combine:

- `panel › the contents hang open…` with `workspace › the contents tree is absent for a non-document`.
- `shell › the contents rail always marks…` into `panel › the contents bar follows the reader`.
- `unit/host-neutrality` tests 2–4 into one table-driven test over every rule: `{rule, bad, good}`. Today only three of six rules have a positive/negative self-test; `writes an origin-absolute route` and `returns an origin-absolute path` have none, and they are the subtlest regexes.
- `src/workbench.spec.ts` split into its modules' specs, as above.
- The three `holding()` e2e tests (links, did, chat): keep one navigation, assert `href` in the other two.

### Missing

Behaviour with no test in this slice, and (by grep of `tests/`) none elsewhere unless noted.

**Likely bug surfaced by a missing test.** `isDocument` (review/run.ts:6-8) checks `masters` only. `itemForQuilt` (workspace/links.ts:60) therefore does not treat a canon path as a document: `quilt:canon/widgets-v1.tex` falls through to `itemFromPath(keyUrl(m, key))` (links.ts:63), i.e. a *node* item with id `canon/widgets-v1.tex`, which renders "Unknown key". `linkName` (names.ts:105) names canon paths correctly, so the link reads right and opens wrong. `noteItem` (links.ts:98) has the same gap for an annotation on a landmark. Add to `links.spec.ts`: `itemForQuilt(m with canon, 'canon/widgets-v1.tex')` → `{kind:'document', id:'canon/widgets-v1.tex'}`.

workspace/links.ts:

- `itemForHref` `cited:` branch (links.ts:30-36): a local copy gives a work item with `page` defaulting to 1; no local copy gives null (then `pdf.open`). This is pure with a stub manifest; queue.e2e covers it only end to end.
- `paperAt` (links.ts:74-79): a digest result with a filed PDF and a page opens the paper at `{page, result}`. study.e2e F9 covers it e2e only.
- `threadOf` cycle guard (links.ts:82-92): a reply chain with a cycle must terminate.
- `follow` / `soleSession` / `openChat` (links.ts:117-175): pure against the `workspace` singleton. Test that `openChat` restores focus to the reader's pane after `beside` (line 173), that `soleSession` closes sessions in both panes, and that `from = -1` opens in the focused pane (line 122).
- `interceptLinks` (links.ts:186-230): modifier-click, `target=_blank` and `download` pass through (line 188-191). A `quilt:` link to an unknown key is still `preventDefault`ed (line 221). None tested. One e2e with `click({modifiers:['Meta']})` on a quilt link, or a jsdom unit test.
- `itemForQuilt` region-vs-key place (links.ts:67-68): `links.spec.ts:47` asserts the proof anchor only `toBeTruthy()`; assert `'sy-0003-proof'`.

workspace/store.svelte.ts:

- `update()` (line 125) keeps `seq`, so a scroll-driven update does not re-reveal.
- `#replace` keeps the old `view` when revealing without one (line 224).
- `apply()` on a non-empty workspace with `?beside`, where focus returns to the pane it was in (lines 198-203).
- `#drop` focus arithmetic when `focus > pane` (line 234).
- `canonical()` returns '' when empty (line 171).

workspace/names.ts and registry.ts:

- `nodeName`/`keyName` for a proof (`proof of Theorem 2.1`, names.ts:49,72), a digest result (`Kre99 · Prop 2.1`, :50), a region with no number (label fallback, :69), and a `cited:` link with `#page=` (only `?page=` is tested, :94).
- `registry.ts` `documentTab` for a landmark (`widgets-v1 @1`, registry.ts:42-47), `tabOf`, `nameOf`, and the work tab `Arden24 · Prop 2.1` (:63-67). None has a unit test; chapter 15.2.4 states each of these names. `nodeTab` (registry.ts:50-57) and `nodeName` (names.ts:45-55) are two implementations of "a node as a reader names it" that differ: nodeTab capitalises the taxon, handles no proof and no title. A test comparing them would expose the drift.

sessions:

- `Transcript` (transcript.svelte.ts:62-162), all untested at unit level: `load()` replacing a non-adjacent page instead of merging (the `meets` rule, :110); `poll()` gap resync (:153-156); `older()` guard while loading; `latest()` null without a publisher. A fetch stub makes these pure.
- `carried()` (transcript.svelte.ts:170-179): replies counted apart and pluralised `replies`. e2e covers only `1 question, 1 note`.
- `isAgent()` (:165): `\b(agent|ai|bot|assistant)\b`. Test that "Aidan" is not an agent and "A. Author" is not.
- `sessions.svelte.ts`: `grouped()` recency sort (:116; the existing test uses equal timestamps, so the sort never runs); `summary()` (:124-132, open/who/fresh counts, untested); `titleOf` with a pending rename; `load()` with corrupt storage.
- `when()` date fallback past 14 days, and an invalid stamp (when.ts:15,22).
- "A stored session the corpus no longer lists is let go" lives inline in `routes/+layout.svelte:44`, so only e2e can reach it. Extract it to `sessionView.reconcile(m)` and unit-test it.

ChatView status line (ChatView.svelte:145-160): nine branches in a `$derived` inside a component. e2e covers running, failed-before-send, failed-after-send, launch-idle, attached, sent-with-attached, sent-nobody, and `blocked` (study.e2e:79). Untested: `sent · <name> will start` (:155), `was stopped` after a send (:152), and a `done` agent filtered out of the attached names (:153). Extract to `statusLine(agent, attached, sent, sentAt)` in transcript.svelte.ts and table-test it. That also lets `where it does not…` (chat.e2e:266) assert something (see "Other").

write.ts:

- 403 → forget the probe and retry once (write.ts:103-106), the restarted-publisher case.
- The `SESSIONED` refusal before any request, returning `no-session` (:79-82).
- An unaccepted `write_api` version gives no capabilities (:38).
- The `X-Loom-Token` header (:93).

All pure with a fetch stub; none is tested anywhere.

Other untested modules:

- `review/closure.ts:23` `stack()`: dependency order with the result last, seeded from the result's proofs (15.3.2 "what this rests on"). Pure; only a routes.e2e smoke test reaches it.
- `fragments/quote.ts:8` `texOf`: `\(x\)` → `$x$`, display → `$$x$$`. The quote form loom matches on (15.3.10). Testable with the same element stub `pages.spec.ts` uses.
- `fragments/expand.ts:44` `leadComments`, `annotations.ts:39-61` (`on`, `openOn`, `repliesTo`), `graph/order.ts:19` `documentOrder`, `graph/reading.ts:53` `readingOrder`, `workspace/views.ts:11` `workViews`, `shell/views.ts:20` `viewsOf`: all pure, all untested.

Chapter 15 rules with no test (grep across all e2e dirs found no reference to their test ids):

- The picker's find field (`session-find`).
- `select none` (`session-none`), "the one way to detach".
- Remove (`session-delete-*`).
- The input growing from two to eight lines (`composer-expand`).
- `composer-refused`.
- The Chat's empty state ("Nothing has been said in this session yet.", ChatView.svelte:194).
- What it did's empty state ("Nothing done through loom in this session yet.", SessionDid.svelte:70; 15.3.9 "A session whose log is empty says so in one line").
- A reader scrolled up is not pulled down by a new message (ChatView.svelte:107,111).
- The footer's count of events since last opened (15.2.3).

### Failure diagnostics

Computed booleans and one-shot `evaluate` reads fail as "expected true, received false" or a bare number, and they do not retry.

- base-path.e2e.ts:25-26 `expect(fetched.some(…)).toBe(true)` / `.every(…)`. Better: `expect(fetched.filter(p => !p.startsWith('/build/'))).toEqual([])`, which lists the offenders. Line 16's per-href loop stops at the first offender; `expect(hrefs.filter(h => !/^[/#]/.test(h))).toEqual([])` shows all.
- panel.e2e.ts:48-54 `expect(naming).toBe(1)` on an `evaluate` count. On failure you learn "2", not where. Return descriptors (`el.tagName + [data-testid]`) and `expect(list).toEqual(['DIV[session-footer-name]'])`, wrapped in `expect.poll` so it retries while the picker closes.
- chat.e2e.ts:184-185 `[own, holds, chat]` from one `evaluate`, then arithmetic. It is not retried, and the tray may still be growing after the click, so it can flake. Use `await expect.poll(() => tray.evaluate(t => ({own: t.clientHeight, holds: t.scrollHeight, chat: t.parentElement!.clientHeight}))).toSatisfy(…)` or name the numbers in the message argument.
- chat.e2e.ts:76 `expect(await first.evaluate(… borderLeftStyle)).toBe('solid')` → `await expect(first).toHaveCSS('border-left-style', 'solid')` (retries, names the property).
- phase4.e2e.ts:67-69 → `toHaveCSS('text-overflow', 'ellipsis')`.
- phase4.e2e.ts:158-159 → `toHaveCSS('box-shadow', 'none')` / `not.toHaveCSS('box-shadow', 'none')`.
- phase4.e2e.ts:33-34 `expect(statement.y - (head.y + head.height)).toBeLessThan(60)` → add a message: `expect(gap, 'statement top below the tab strip, px').toBeLessThan(60)`.
- phase4.e2e.ts:95-96: an overlap loop over anonymous `[left, right]` pairs. Return `{name: el.dataset.testid, left, right}` and assert with the pair's names in the message.
- phase4.e2e.ts:98 `.not.toBe(false)` on a parsed localStorage value passes for `undefined`, `null` and `'yes'`. Assert the exact stored object, or `toBeUndefined()` if nothing should be written.
- chat.e2e.ts:170 `expect(await preview.textContent()).toBe(TEXT)` is one-shot. Use `expect.poll(() => preview.textContent()).toBe(TEXT)` (exact whitespace matters, so not `toHaveText`).
- phase3.e2e.ts:63-64 `innerText()` then `not.toMatch` → `await expect(chat).not.toContainText(/\d{4}-\d{2}-\d{2}T/)` (retries). The same pattern is at routes.e2e.ts:352.
- panel.e2e.ts:58-68: a loop over three routes with no `test.step`, so a failure does not say which route. Use `test.step(at, …)` or three generated tests.
- src/graph/local.spec.ts:17, 25, 48, 52: `expect(a && b).toBe(true)` inside loops. Use `expect(edges.filter(e => !ids.has(e.from) || !ids.has(e.to))).toEqual([])` and `expect([...one].filter(x => !two.has(x))).toEqual([])`.
- unit/host-neutrality.spec.ts:89-90, 95-96, 102-103 `rule.re.test(s)).toBe(true)` → `expect(s).toMatch(rule.re)` / `not.toMatch`, which prints both pattern and string.
- src/manifest/loader.spec.ts:13 `a.startsWith('sha256:')).toBe(true)` → `toMatch(/^sha256:/)`.
- src/workspace/links.spec.ts:47 `toBeTruthy()` → the exact anchor.
- unit/sessions.spec.ts:84-102 has a dozen `visible(...)).toBe(true/false)`. Readable thanks to the test names, but an `it.each` table (`[view, showClosed, selected, run, expected]`) would name the failing cell.

Good examples to copy: `forbidden-words` and `host-neutrality` collect offenders and `toEqual([])`; did.e2e and links.e2e use test ids and `expect.poll` on URL params.

### Other

**Vacuous tests.**

- `chat › where it does not, the line is who is listening, as before` (chat.e2e:266). With `{launch:false, name:''}` the expected text is exactly the default shown before any poll (`agent` null → ChatView.svelte:159). The test passes in 0.4 s, which is before the first poll could land, so it never observes the `agent` field at all.
- `chat › with nobody listening` (chat.e2e:127): its first assertion has the same defect; only its post-send assertion is real.

Fix both by first waiting for a poll-dependent signal (e.g. serve an event with seq 2 and wait for `message-2`), or unit-test the status function.

- `phase3 › a link to a kind with no preview opens no card` passes if hover cards are broken everywhere (no positive control).
- `phase4 › a name that does not fit ends in an ellipsis` never has a name that does not fit (`Theorem 2.1` in a 148 px tab). It checks two CSS values, not the rule. Serve a manifest with a long session title or taxon and assert that the label's right edge is ≤ the controls' left edge.

**Fixture-coupled values that move when the synthetic quilt is regenerated.**

- `library.spec.ts:12` (`digest` = 2).
- `did.e2e.ts:37` (the literal command `--resolve a-2026-09-16-0002` from run.log) and `:33-34` (the log names `sy-0003`, not `Theorem`).
- `phase4.e2e.ts:48` (`text of @1` for sy-0002).
- `phase4.e2e.ts:145` (sy-0005's context links sy-0002).
- `links.e2e.ts:40` (sy-999A in talk.tex only) and `:102` (`widget` in sy-0003's statement).
- `chat.e2e.ts:74` and `phase3.e2e.ts:61` ('hostile review of the parity theorem').
- `home.e2e.ts:5,25` (the root label).

Most are documented in comments, which helps. The robust pattern already exists in `routes.e2e.ts:218` and `workspace.e2e.ts:124` (derive or `expect` the precondition from `manifest.json` first, so a regenerated fixture fails on the precondition line with a clear message). Apply it to the ones above.

**Fake data that contradicts the fixture.** `chat.e2e.ts:140-141` builds packet rows with fixture ids:

- `a-2026-09-16-0001` is an **objection** on sy-0003 in the fixture, faked as a `question`.
- `a-2026-09-16-0004` is a resolved **citation** on sy-0003, faked as a `note` on `drafting/main.tex`.

The row's `quilt:` link resolves through the real manifest, so `a row opens its annotation beside` opens an objection from a row labelled "question". Use fixture-consistent kinds and targets, or ids the fixture lacks with a manifest route that adds them. `links.spec.ts:19-23` likewise reuses real ids with invented kinds and targets. That is harmless in a unit stub, but misleading beside the fixture.

**Fake routes vs the API.**

- The `/_api/events`, `/_api/packet`, `/_api/message`, `/_api/agent-stop`, `/_api/session-rename` and `/_api/review-decision` fakes match `docs/specs/write-api.md` §2 and §4 and `loom/src/loom/render/serve.py:280-293`.
- `panel › ⟳ reopens and selects` fakes `/_api/session-reopen`. Loom serves it (`loom/src/loom/render/api.py:36`, with `session-purpose` at :37), but `write-api.md`'s endpoint table lists neither. That is spec drift (review pass 2, missing fact), not a test fault. The spec should gain both rows.
- `panel › a review decision needs no session` checks only the posted `key`. Assert the whole body `{key: 'sy-0001', status: 'ok'}`, since `status` is the spec'd field.
- `links.e2e.ts:9` `saying()` fakes only `transcripts/REFEREE/1.json` and relies on the fixture's `seq` being ≤ 100. Pin `seq` with a manifest route, as `chat.e2e.ts`'s `transcript()` does.
- `chat.e2e.ts:280` sets `started` from the test process's clock + 1 s and depends on the browser's `sentAt` (floored to the second) being earlier. It holds on one machine; state it in a comment or use `page.clock`.

**Implementation-coupled locators.**

- `panel.e2e.ts:98` (`.panel .sections`).
- `panel.e2e.ts:88` (`.footer.refused`, a CSS class, beside an aria-label that says the same thing).
- `links.e2e.ts:65` (`page.locator('a', {hasText: /^talk\.tex$/}).first()`). Prefer `getByTestId('docs-drafts').getByRole('link', {name: 'talk.tex'})`.
- `home.e2e.ts:25` (`main ul` first).
- `panel.e2e.ts:21-30` synthesises a selection with `evaluate` + a dispatched `mouseup`, which bypasses the real pointer path. Acceptable, but note that it does not prove a drag-select works.

**Misleading titles.**

- `chat › a body is rendered, links and mathematics, and the agent's messages carry a rule` asserts neither links nor mathematics.
- `home › …four metric cards which open the complete review table`: one of the four opens `/problems`.
- `phase4 › a node draws its statement and proofs` asserts no proof.
- Titles and comments carrying change history: `prefs › ignores a stored shell, now that there is only one arrangement`, `host-neutrality › still forbids a publisher scheme, now that nothing is exempt from it`, `links.spec.ts:40,42` ("the 0.14 study opened …"). CLAUDE.md's "current state only" rule targets docstrings, but these read as changelog too.

**Order and state.**

- No e2e test depends on order.
- Unit specs share module singletons (`workspace` in links.spec.ts, `sessionView` in sessions.spec.ts) and reset them per test. `sessionView.renamed` is not reset, which is harmless today.
- `forbidden-words`, `host-neutrality`, `graph/local` and `library` read paths relative to the cwd (`src`, `tests/fixture/manifest.json`), so they pass only when vitest runs from `arras/`. `new URL('../../tests/fixture/manifest.json', import.meta.url)` would remove that.

**Formatting (review pass 10).** `tests/unit/host-neutrality.spec.ts:1-12` and `tests/unit/sessions.spec.ts:1-3` hard-wrap their header comments, against CLAUDE.md's no-hard-wrap rule.

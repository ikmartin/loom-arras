# v0.1 study: the viewer (`arras/src` and its build)

Auditor: viewer. Branch `v0.1-study` at 71621877 (equal to main). Code read, not run, except: one production build and one `svelte-check` in a scratch copy, and a Node micro-benchmark of parsing relloc's manifest. All paths below are relative to the repository root unless they start with `/`.

Source size: 36,044 lines in `arras/src` excluding 3,752 lines of `*.spec.ts`; 154 Svelte components; 27 route files. `svelte-check` on `src` is clean (strict TypeScript, two `any`).

## Findings at a glance

| id | finding | weight | effort | rec |
|---|---|---|---|---|
| VIEW-1 | The viewer tells humans to type loom commands in nine places | blocks | hours to a day | fix |
| VIEW-2 | Every publish re-downloads, re-parses and re-derives the whole manifest (10.8 MB on relloc) | hurts | hours (raw state) / a week+ (split) | fix / defer |
| VIEW-3 | The viewer cannot say whether an agent is attached, what it last did, or what it can see | hurts | a day (needs a loom field) | fix |
| VIEW-4 | The session footer is amber by default and gates only two endpoints | hurts | hours | hide + fix |
| VIEW-5 | Duplicate entry points: PDF, suggested edits, versions, sessions, library, problems | hurts | days | remove / hide |
| VIEW-6 | Tabs cannot be dragged; reload loses every tab but the two in front | hurts | a day + hours | fix |
| VIEW-7 | Where a click opens depends on where the link stands; following a link splits the screen | hurts | hours to a day | fix |
| VIEW-8 | The toolbar has one size and clips from the left | hurts | hours (medium) / days (narrow) | fix |
| VIEW-9 | Beside an agent app on a laptop, the viewer drops into its folded and one-pane modes | hurts | hours | fix |
| VIEW-10 | Almost nothing explains itself; search has no visible control | hurts | a day | fix |
| VIEW-11 | Review has five sections; the author wants two; AI edits are split across two of them | hurts | days | fix |
| VIEW-12 | Static-host and host-neutral legacy (~500 src lines, plus test infrastructure) | hurts (dev, perf ceiling) | a day or two | remove |
| VIEW-13 | A viewer change needs build, restart and reload; dev server cannot write; bundle churns git | hurts (dev) | hours | fix |
| VIEW-14 | Accept is refused until a reviewer name is chosen in Settings | hurts | hours | fix |
| VIEW-15 | Graph page and local graph: 2,460 lines and a 1.4 MB layout engine, reachable from one button | irrelevant | hours to hide | hide |
| VIEW-16 | Development shelf routes (threads, tags, taxa, loose) reachable from Settings | cosmetic | hours | remove |
| VIEW-17 | Dead code: `TexHtml.svelte`; rail and panel stores used only by `/graph` | cosmetic | hours | remove |
| VIEW-18 | Two MathJax distributions shipped (2.2 MB and 1.8 MB chunks) | cosmetic | a day | defer |
| VIEW-19 | Module headers are long prose citing plans and DR numbers (168 references) | hurts (dev) | days, incremental | fix |
| VIEW-20 | About 20 global singleton stores and 58 per-component capability probes | cosmetic (dev) | with VIEW-12 | fix |
| VIEW-21 | CSS: 1,472-line global theme, tool-button styles redefined in six components | cosmetic | with VIEW-8 | defer |
| VIEW-22 | Manifest types are hand-mirrored from the spec (784 lines) | cosmetic | a day | defer |

## 1. Map

### Shell and routing

The app is a SvelteKit single-page app (`arras/src/routes/+layout.ts:2-3`, adapter-static with an `index.html` fallback, `arras/vite.config.ts:19-21`). Everything visible is drawn by the root layout, `arras/src/routes/+layout.svelte` (186 lines): it starts the manifest poll and stream (`:35-40`), installs the one capture-phase link interceptor (`:124-129`), starts `here` reporting (`:132-137`), and renders the left column (`Column`) around either the workspace or the routed page (`:145-171`), then the overlays (`:181-186`: Palette, LinkPreview, PdfViewer, DeletedBar, OutOfStep, Toast).

"Reading mode" is nine route ids whose pages are one-line stubs (`arras/src/routes/{master,canon,pdf,node,context,library,session,page,file}/.../+page.svelte`); the layout sees the route is in `READING` (`+layout.svelte:73`) and draws `Workspace` instead. The URL is synchronised both ways with the workspace store (`+layout.svelte:106-121`): a URL the workspace did not write is applied, every workspace change is written back with `replaceState`.

### Directories (non-spec lines)

| directory | lines | holds |
|---|---|---|
| `lib/review/` | 6,150 | annotating (bar, popups, side lists, history/undo), Review page parts (changes, proposals, copies, pulls, library rows) |
| `lib/pdf/` | 4,212 | pdf.js rendering, marks on pages, drawing tools, PDF bar and menu, page editor, PDF import/export of annotations |
| `lib/workspace/` + `items/` | 3,838 + 2,519 | panes, tabs, toolbar, compare, versions, per-kind renderers and controls, link rule |
| `lib/components/` | 2,537 | shared widgets: AddWork, LinkPreview, PdfViewer, Palette, Popover, Diagnostics, HelpDot, job progress |
| `lib/fragments/` | 2,429 | the HTML fragment renderer: fetch, in-place patch, MathJax, marks, gutter, quoting |
| `lib/shell/` + `settings/` | 1,764 + 1,305 | left column, file tree, Settings window and its ten panes |
| `lib/graph/` + `routes/graph/` | 1,696 + 764 | local graph panel, whole-graph page, ELK and d3-force layouts |
| `lib/manifest/` | 1,100 | manifest types (784), loader, store, stream, compile states |
| `lib/sessions/` | 1,044 | session selection, picker, footer, transcript paging |
| `lib/theme.css` | 1,472 | every token and every global rule, including the HTML dialect's typesetting |
| `routes/review/` | ~1,800 | the Review pages |

Largest files: `routes/graph/+page.svelte` 764, `lib/shell/Column.svelte` 719, `lib/fragments/Fragment.svelte` 669, `lib/pdf/PdfPage.svelte` 554, `lib/components/AddWork.svelte` 535, `lib/pdf/portable.ts` 527, `lib/review/AnnotationPopup.svelte` 508, `lib/shell/settings/Annotations.svelte` 482, `lib/pdf/PdfDoc.svelte` 462, `routes/review/+page.svelte` 457, `lib/workspace/CompareLayer.svelte` 455, `lib/workspace/items/WorkItem.svelte` 453.

### Where each visible thing is made

| on screen | made in |
|---|---|
| left column (name, ⚙, fold, Docs/Review tabs, Review sections, Files, Library shelf, Outline, session footer, edge drag) | `lib/shell/Column.svelte` |
| project tree, PDF row under a document, agent copies, AI marks | `lib/shell/FileTree.svelte`, `lib/shell/AgentMark.svelte`, `lib/shell/access.ts` |
| outline | `lib/shell/Contents.svelte` |
| Settings window and panes | `lib/shell/Settings.svelte`, `lib/shell/settings/*.svelte`, words in `settings/catalog.ts` |
| session footer and picker | `lib/sessions/SessionFooter.svelte`, `SessionPicker.svelte` |
| panes, divider, narrow strip | `lib/workspace/Workspace.svelte`, `Pane.svelte` |
| tab strip | `lib/workspace/PaneHead.svelte` |
| toolbar rows, view ▾, Annotate toggle | `lib/workspace/ItemToolbar.svelte`, `ToolbarMenu.svelte`, `ToolbarItem.svelte`, `annotationRow.svelte.ts` |
| per-kind toolbar | `lib/workspace/items/{Document,Work,File,Node,Plain}Controls.svelte` |
| annotate tools, stepper, Comments, Notes, format menu | `lib/review/AnnotateBar.svelte` |
| Changes ▾ (Markup/Final, Keep all) | `lib/review/ChangesMenu.svelte` |
| history ▾, version bar, compare counter | `lib/workspace/HistoryMenu.svelte`, `VersionControls.svelte`, `CompareControls.svelte`, `CompareLayer.svelte` |
| PDF bar, PDF ▾, zoom/page, drawing tools | `lib/pdf/PdfBar.svelte`, `PdfMenu.svelte`, `PdfTools.svelte`, `DrawTools.svelte` |
| document text | `lib/workspace/items/DocumentItem.svelte` → `lib/fragments/Fragment.svelte`, `FragmentNotes.svelte` |
| annotation popup / change popup | `lib/review/AnnotationPopup.svelte`, `ChangePopup.svelte` via `lib/fragments/popup.ts` |
| Quote and Add comment chips | `lib/review/QuoteChip.svelte`, `AtSelection.svelte` |
| Comments / Notes side list | `lib/review/SideList.svelte`, `SideHost.svelte` |
| cited work (Text · Info) | `lib/workspace/items/WorkItem.svelte`, `lib/pdf/Reading.svelte`, `MarkedDoc.svelte` |
| compiled PDF | `lib/workspace/items/CompiledItem.svelte` |
| project file | `lib/workspace/items/FileItem.svelte`, `HtmlFrame.svelte` |
| node / context | `lib/workspace/items/NodeItem.svelte`, `ContextItem.svelte` |
| transcript / what it did | `lib/workspace/items/ChatView.svelte`, `SessionDid.svelte` |
| research state | `lib/workspace/items/PageItem.svelte` |
| hover cards | `lib/components/LinkPreview.svelte` + each kind's `preview` in `lib/workspace/registry.ts` |
| ⌘K search | `lib/components/Palette.svelte` (ninja-keys) |
| Review pages | `routes/review/**`, parts in `lib/review/` |

### Item kinds a tab can hold

Eight, registered in `lib/workspace/registry.ts:62-106` (the only place that knows them): `document` (a draft or a landmark), `work` (cited paper; views Text · Info), `node`, `context` (a node's surroundings), `session` (views Transcript · What it did), `page` (research state), `file` (project file of any kind), `pdf` (a document's compiled PDF). Address codec in `lib/workspace/item.ts:67-166`.

### Where state lives

| where | what | evidence |
|---|---|---|
| URL path | left pane's active item, its anchor (`#`), `?note=`, a document's `?review= ?cause= ?incoming=`, a work's `?view=` and place keys, a session's `?view=` | `lib/workspace/item.ts:67-166` |
| URL query | `?beside=` right pane's active item, `?compare=1` | `lib/workspace/store.svelte.ts:269-277` |
| URL query, Review | `?document=`, `?record=1`, `?show=`, `?severity=`, `?code=`, `?copy=`, `?pull`, `?work=` | Review routes |
| localStorage | `arras.prefs` (divider, outline split, column width, column shown, zoom, ids, hideAux, hideAgentConfig, face, size, width, theme, format); `arras.workspace` (last canonical URL per quilt: the two front items only); `arras.tree` (folded dirs per quilt); `arras.settings` (last pane); `arras.annotation-row`; `arras.places` (PDF positions); `arras.localGraph`; `arras.session-view` (selected session); `arras.annotate.hand` (type and look in hand) | `lib/prefs.svelte.ts:23`, `lib/workspace/remember.ts:6`, `lib/shell/FileTree.svelte:25`, `lib/shell/Settings.svelte:23`, `lib/workspace/annotationRow.svelte.ts:5`, `lib/pdf/position.ts:5`, `lib/workspace/items/DocumentItem.svelte:48`, `lib/sessions/sessions.svelte.ts:17`, `lib/review/annotating.svelte.ts:88` |
| memory | panes, every tab, focus, compare pair, scroll places, per-item state (`store.svelte.ts:24-44`); undo history; `here`; show settled; job progress; compile states; toasts; Settings drafts | about 20 singletons, VIEW-20 |
| manifest | all content and records: documents, nodes, keys, annotations, changes, contributions, references, diagnostics, sessions, threads with command logs, config, files, history | `lib/manifest/types.ts` |
| stream | compile state per document | `lib/manifest/compiles.svelte.ts` |
| loom's memory | the last `here` report | `lib/here.svelte.ts:1-3` |

## 2. Inventory of every place and control

D = duplicate of another row (see VIEW-5).

### Routes

| route | does | file |
|---|---|---|
| `/` | redirects to the last reading address, else a "Nothing to read yet" page listing commands | `routes/+page.svelte` |
| `/master/…`, `/canon/…` | a draft or a version as a document tab | stub; `DocumentItem.svelte` |
| `/pdf/…` | a document's compiled PDF tab (D) | stub; `CompiledItem.svelte` |
| `/node/…`, `/context/…` | a node; its context | `NodeItem.svelte`, `ContextItem.svelte` |
| `/library/[citekey]` | a cited work | `WorkItem.svelte` |
| `/session/[id]` | transcript and what it did (D) | `ChatView.svelte`, `SessionDid.svelte` |
| `/page/state` | research state | `PageItem.svelte` |
| `/file/…` | a project file (D for a .pdf beside its .tex) | `FileItem.svelte` |
| `/review` | Your Changes | `routes/review/+page.svelte` |
| `/review/proposed` (`?copy= ?pull ?work=`) | Proposed Changes; copy review; pull review; proposed-results queue | `routes/review/proposed/+page.svelte` |
| `/review/problems` | Problems | `routes/review/problems/+page.svelte` |
| `/review/library` | library ledger (D) | `routes/review/library/+page.svelte` |
| `/review/record` | Versions (D) | `routes/review/record/+page.svelte` |
| `/review/record/sessions` | Sessions table (D) | `routes/review/record/sessions/+page.svelte` |
| `/review/record/acts` | Everything recorded | `routes/review/record/acts/+page.svelte` |
| `/graph` | whole graph | `routes/graph/+page.svelte` |
| `/threads` (D), `/tags`, `/tag/…`, `/taxa`, `/taxon/…`, `/loose` | development indexes | `routes/{threads,tags,tag,taxa,taxon,loose}/` |

### Left column (`lib/shell/Column.svelte`)

| control | does | line |
|---|---|---|
| quilt name | goes to `/` | 179 |
| ⚙ | opens Settings | 180; `Settings.svelte:83` |
| « / » | folds the column; below 1200 px it is folded regardless | 173, 181; 43-54 |
| Docs / Review | the two primary views; Review opens on the first section with a count | 185-194; `review/sections.ts:47-50` |
| Review sections ×5 with counts | Your Changes, Proposed Changes, Problems, Library (D), The Record | 201-209; `review/sections.ts:24-37` |
| Files ▾ | folds the tree | 222-229 |
| tree: directory, file, document, research state rows | open in the focused pane; an included .tex opens its document at that place | `FileTree.svelte:150-180`; `item.ts:176-190` |
| tree: PDF row under each document, with compile status | opens the compiled PDF (D) | `FileTree.svelte:133-143` |
| tree: agent copies under their document, AI mark | open the copy; the mark explains who may edit | `FileTree.svelte:171-176`, `AgentMark.svelte` |
| Agent documents / Closed agent documents | copies whose document is not listed | 254-269 |
| Documents, Research state (only when no files list) | legacy branch, VIEW-12 | 230-253 |
| Library ▾, count, + | folds the shelf; + opens Add a work (D) | 270-276 |
| library filter, work rows | narrows; opens the work | 280-289 |
| Manage the library, "N need you" | Review › Library (D) | 290 |
| Outline divider, Outline | resizes; jumps to sections | 297-323 |
| session footer | "writing in X" or amber "not writing in a session"; opens the picker | 327-329; `SessionFooter.svelte:52` |
| picker: + new, find, rename, read, write here, close, reopen, delete, show closed | session verbs (D) | `SessionPicker.svelte` |
| column edge | drag or arrow keys to resize | 333-349 |

### Pane and tabs

| control | does | file:line |
|---|---|---|
| tab label | activates the tab | `PaneHead.svelte:68` |
| ⇄ on a tab | moves it to the other pane, making one if needed | `PaneHead.svelte:73-79` |
| × on a tab | closes it | `PaneHead.svelte:81` |
| wheel over the strip | scrolls tabs sideways | `PaneHead.svelte:45-49` |
| divider | drag, arrows, Home, double-click to centre | `Workspace.svelte:134-150` |
| empty workspace | "Nothing is open. Choose a document in the panel." | `Workspace.svelte:116` |

### Toolbar (first row, every kind: `ItemToolbar.svelte:59-81`)

| control | does | file |
|---|---|---|
| views (Text · Info; Transcript · What it did) | switch the item's reading | `PaneViews.svelte` |
| Annotate ▾ | shows or hides the annotation row, in every pane at once | `ItemToolbar.svelte:63-67`; `annotationRow.svelte.ts` |
| Changes ▾ (document with pending changes) | Markup / Final; Keep all / Discard all (D) | `review/ChangesMenu.svelte` |
| ‹ n of N › | steps through annotations and changes; J / K | `AnnotateBar.svelte:223-228` |
| Comments (n) | side list of annotations and changes (D for Keep/Discard) | `AnnotateBar.svelte:230`; `SideList.svelte` |
| Notes (n) | side list of annotations of note types | `AnnotateBar.svelte:231` |
| history ▾ (document) | record this version…, live text, 12 versions each with compare, "older, in Review › The Record", compare with agent copies (D) | `HistoryMenu.svelte` |
| version bar (landmark) | ‹ older, newer ›, live text, compare with now, restore… (D) | `VersionControls.svelte` |
| compare counter, ‹ ›, stop | while two panes are compared; [ and ] | `CompareControls.svelte` |
| PDF ▾ (work, project PDF) | Save a copy, Take in from a PDF…, Take in N from this PDF, Edit pages…, Open in its application | `pdf/PdfMenu.svelte` |
| fit width, −, zoom %, +, page | PDF view | `pdf/PdfTools.svelte` |
| view ▾ | show/hide settled annotations; turn annotations off/on; node: open its context beside, show verbatim code; work: open the PDF in a browser tab (D) | `ItemToolbar.svelte:71-79`, `*Controls.svelte` |

### Annotation row (second row)

| control | does | file |
|---|---|---|
| Annotate (highlighter + sample) | toggles marking on selection | `AnnotateBar.svelte:211` |
| Comment (pin) | next click leaves a comment | `AnnotateBar.svelte:212` |
| format ▾ | Type list (Add new…), Look, Changed from / Reset / Update, Save as new type…, Customize… (opens Settings › Annotations) | `AnnotateBar.svelte:235-246` |
| Undo, Redo | annotation writes; ⌘Z, ⇧⌘Z | `AnnotateBar.svelte:216-217` |
| freehand, words on page, box, oval, arrow | PDF drawing tools | `pdf/DrawTools.svelte:21-27` |
| hint at right | what the tool in hand does | `review/annotating.svelte.ts:244-255` |

### In the text

| control | does | file |
|---|---|---|
| select words (no tool) | Quote chip: copies words plus source link, toast "Paste it to your agent" | `QuoteChip.svelte:36` |
| select words (Annotate on) | marks them; Add comment chip; typing starts a comment | `FragmentNotes.svelte:1-5, 92-106` |
| Alt-drag | box round an equation or block | `FragmentNotes.svelte:262`; `PdfPage.svelte:289` |
| click a mark | annotation popup (type, look, comment, replies, Resolve, Delete, version) or change popup (Keep / Discard) (D) | `fragments/popup.ts` |
| hover a link | preview card with "open here" (hover devices only) | `LinkPreview.svelte:209-219` |
| click a link | opens beside, or reveals (VIEW-7) | `workspace/links.ts:152-159` |
| graph icon | local graph panel; "the whole graph" link | `DocumentItem.svelte:165`; `LocalGraphPanel.svelte:68` |
| double-click a block while comparing | sends the other pane to it | `CompareLayer.svelte:305-313` |
| Accept in side panel (opened from Review) | accepts the block (D) | `review/ReviewPanel.svelte` |

### Review sections

| section | controls | file |
|---|---|---|
| Your Changes | help ?, summary, Undo discard, To do toggle, document select, groups Changed / Taken in / Never accepted / Accepted with selection and Accept N / Clear, per document Keep all / Discard all (D), change cards (D) | `routes/review/+page.svelte:210-292` |
| Proposed Changes | cards: Review the pull, Review the copy, Check them; suggested edits on a copy (D); copy review Take it / Leave it / Apply; pull review; results queue (↑ ↓ v e d) | `routes/review/proposed/+page.svelte:84-140`; `ContributionReview`, `IncomingPull`, `ProposalQueue` |
| Problems | help ?, severity filter, search, groups by whose, fixes as buttons or commands to copy | `routes/review/problems/+page.svelte`; `Diagnostics.svelte:34-39` |
| Library | search, + (D), seven filters, select all, bulk run / ask / delete, row ⋯ (Open its info, Fetch and digest it, Digest it again, Upload a PDF…, Ask an agent for an overview, Copy BibTeX, Ask for its paper again…, Stop asking…, Delete from the library…, Delete its copy…) | `routes/review/library/+page.svelte`; `LibraryRow.svelte:170-195` |
| The Record | tabs Versions (D) / Sessions (D) / Everything recorded | `routes/review/record/+layout.svelte:12-18` |

### Settings panes (`lib/shell/settings/catalog.ts:34-45`)

| pane | rows |
|---|---|
| Profile | Your name (also the reviewer name, VIEW-14) |
| Appearance | Typeface, Size, Width, Theme, Document format (p1/p2/b1/b2), Show ids |
| Files | Hide aux LaTeX files, Hide agent config documents |
| General | Name, Id prefix, TeX engine, History folder |
| Documents | Front door, Default document, Research state |
| Annotations | annotation types editor |
| Agents | Where agents may not write, Always protected, Review edits made in place, Apps (with commands to run), Update Claude Code |
| Library (D) | Use the network, Contact address |
| Problems (D) | Silenced |
| Overleaf | pairing (a command to run) |
| Development shelf | threads, tags, taxa, not in a document (`Settings.svelte:93-106`) |

### Overlays

Palette ⌘K (`Palette.svelte`), hover cards (`LinkPreview.svelte`), PDF modal for a cited link with no local item (`PdfViewer.svelte`), delete undo bar (`DeletedBar.svelte`), out-of-step banner (`OutOfStep.svelte`), toast (`Toast.svelte`), Settings window, Add a work dialog (`AddWork.svelte`), network question (`NetworkAsk.svelte`). There are no context menus anywhere (no `contextmenu` handler in `src`).

### Keyboard and gestures

⌘K search; J / K next and previous annotation; ⌘Z / ⇧⌘Z undo and redo annotation writes; Delete / Backspace deletes the open annotation; 0–9 choose a type while Annotate is on; typing after a mark starts its comment; Esc closes a popup, menu or tool; [ and ] step compare differences; ↑ ↓ v e d in the proposed-results queue; arrows and Home on the dividers; arrows, Home, End in toolbar menus; Alt-drag draws a box; double-click the divider recentres it; double-click a block in compare. Sources: `AnnotateBar.svelte:171-204`, `Workspace.svelte:60-67, 103-109`, `ProposalQueue.svelte:61-65`, `FragmentNotes.svelte:92-106, 262`, `ToolbarMenu.svelte:62`. None of these is listed anywhere a person can read except the tooltips of the stepper and undo buttons.

## 3. How the viewer talks to loom

**Manifest.** One JSON file, fetched whole (`lib/manifest/loader.ts:51-67`) with `If-None-Match`; polled every 1 s, or every 5 s while the publisher's SSE stream is open, the stream saying only "a new manifest exists" (`lib/manifest/stream.ts:11-12, 22-24`; `client.svelte.ts:115-135`). relloc's is 10.76 MB (nodes 1.95 MB, keys 1.57, contributions 1.39, annotations 0.93, search 0.77, references 0.76, edges 0.64). On each publish the client decodes, `JSON.parse`s, SHA-256s the bytes, then `JSON.stringify`s the whole object again to detect "only adoption choices changed" (`client.svelte.ts:8-17, 93-97`): 80–145 ms in Node on this Mac before any rendering. It then assigns a deep `$state` (`client.svelte.ts:20`), so every one of 138 `store.manifest` reads in 90 files re-runs through proxies. The spec makes this the only allowed trigger: "React to changes only by detecting that `manifest.json` changed; never assume kinds of change" (`docs/specs/README.md:31`).

**Fragments.** Document and node HTML is fetched lazily per path and cached per manifest hash; any new manifest drops the whole cache (`lib/fragments/fetch.ts:7-11`), so every open document re-fetches its fragment after any write, then patches changed blocks in place so formulas are not re-typeset (`lib/fragments/patch.ts:1`).

**Writes.** `POST /_api/<endpoint>` with an `X-Loom-Token` from `GET /_api`, re-probed once on 403 (`lib/write.ts:89-130`). Before showing a control, components ask `can(endpoint)` (58 call sites in 38 files). The viewer uses 45 of the 47 endpoints loom lists, all but `session-use` and `session-purpose` (`loom/src/loom/render/api.py:23-70`; `open` is added where the platform can open files). Reads: `/_api/jobs` (1 s while a library run is active, `jobs.svelte.ts:68`), `/_api/events` (1 s while a transcript tab is open, `ChatView.svelte:113`), transcript pages from the build.

**What the viewer knows about agents.**
- It *reports* the person's place to loom as `here` after 300 ms of stillness and on focus: route, both panes' items, the block at the top, selected words or a drawn region, the PDF page, the open annotation, the session (`lib/here.svelte.ts:55-120, 147-212`). Nothing on screen says this happens or that an agent can read it.
- Sessions in the manifest carry title, purpose, state, created, opened, rounds, `seq` and `last` (when last written in) (`types.ts:501-518`); threads carry a command log (`types.ts:520-531`), shown as "What it did" (`SessionDid.svelte`). Transcripts hold only what an agent chose to post with `loom session say` (`ChatView.svelte:1`).
- Who may edit which file: AI marks in the tree (`access.ts`, `AgentMark.svelte`); whether the quilt has an agent layer and which apps are set up (`settings/Agents.svelte:44, 72-83`).
- Nothing says whether an agent is connected now, which one, or what it did last across sessions: no field in the manifest or `/_api` carries it (no match for attached, connected, heartbeat in `src`).

## 4. Legacy of the static, host-neutral design

| machinery | where | lines |
|---|---|---|
| capability probe per endpoint, `can`/`known`, and the `writes`/`served` booleans every control carries | `lib/write.ts:33-77`; 58 call sites | ~250 |
| static branches: Problems "every fix is a command to copy", Settings "Shown as published", Your Changes "This copy of the quilt only reads", ChatView "in a static one it is the only signal", HtmlFrame no-frames path, CompareLayer "for good on a static host" | `problems/+page.svelte:38`, `Settings.svelte:119`, `review/+page.svelte:231`, `ChatView.svelte:89`, `HtmlFrame.svelte:3`, `CompareLayer.svelte:4` | ~80 |
| a host-movable data root, never set by anything | `lib/paths.ts:1-48` (`setDataRoot` has no caller), `client.svelte.ts:35` (`url` never set) | ~30 |
| `.arras` class scoping for embedding in someone else's page | `app.html:2-3`; 84 selectors in `theme.css` | 0 lines saved; one less concept |
| `publishes.{review,discussions,documents}` switches | `Column.svelte:194`, `review/sections.ts:38`, `shell/views.ts:40-45`, `record/+layout.svelte:15`, `NoDrafts.svelte:15`, `ContextItem.svelte:161` | ~20 |
| the column's no-files-list branch | `Column.svelte:230-253` | ~25 |
| development indexes for a published corpus | `routes/{threads,tags,tag,taxa,taxon,loose}`, `shell/views.ts:36-49` | ~110 |
| publisher-neutral diagnostic namespaces (`ns:name`, `arras:` codes) | `lib/diagnostics.ts:13` | ~15 |
| test and dev infrastructure: `vite dev` on a staged static fixture, `serve-static.mjs` answering `/_api` with 404, three byte-identical fixture copies | `package.json` "dev"; `arras/scripts/serve-static.mjs`; `scripts/checks/fixtures.py` PAIRS | outside `src` |

Deleting it saves roughly 500 lines in `src`, one async state per control, and the "detected, never assumed" reasoning a contributor must hold. The larger prize is spec obligation 2: once the viewer may assume it is talking to loom, the manifest can be split (content that changes on every annotation apart from nodes, keys, search, references) or updated by delta over the stream, which is what VIEW-2 needs.

## 5. Panes and tabs

**Why a tab cannot be dragged.** No drag code exists: `PaneHead.svelte:61-85` renders a label button, ⇄ and ×, nothing `draggable` and no pointer-drag. The store can already move (`store.svelte.ts:231-249`) but only appends at the end of the other pane, has no reorder, and refuses to move a lone pane's lone tab.

**What it would take.** A pointer-based drag on `.tab` (HTML5 drag-and-drop looks poor in Safari and gives no live insertion marker), drop zones on each strip with an insertion index and on each pane body's left/right half to split, and one new store method `place(key, pane, index)` that `move` becomes a case of; the `?beside` URL needs no change. About 150–250 lines; a day with tests.

**How a split opens today.** (a) Following any link inside a pane opens it in the other pane, making the second pane if needed (`links.ts:152-159`, `store.svelte.ts:148-162`); (b) ⇄ on a tab; (c) a node's view ▾ › open its context beside; (d) history ▾ › compare; (e) choosing a session in the picker opens its transcript beside and closes every other session tab (`links.ts:184-210`); (f) a URL with `?beside=`. There is no split button.

**How predictable it is.**
- The same item opens in different places by where the link stood: the column and ⌘K open in the focused pane, a link in text opens in the other pane, a hover card's "open here" opens in the link's own pane, and anything already open is revealed where it is, moving focus there (`links.ts:1, 152-159`; `LinkPreview.svelte:209-219`).
- A node link may open a different item: the open document that holds the node, at the node (`links.ts:166-179`).
- Reload keeps only the two front items: `canonical` writes only them and `remember` stores only that (`store.svelte.ts:269-277`, `workspace/remember.ts`). Every background tab is lost.
- Below 700 px the two panes become one with a merged tab strip (`Workspace.svelte:16, 117-125`).
- The focused pane is marked only by a shadow and a white strip; the other pane's toolbar is dimmed to 0.72 (`Pane.svelte:174-197`).

**What would make it obvious.** Persist every tab of both panes per quilt; a plain click opens in the same pane (as a browser does) and "beside" is an explicit act (⌥-click, hover card, drag to the other pane, a right-click menu "Open beside"); tab drag with an insertion marker; one visible split control in the strip; and a stronger focus mark. Any of these is a design decision for the author; the code supports each without a rewrite.

## 6. The toolbar

**How it is built.** Each pane draws `ItemToolbar` for its active item via the kind's controls component (`Pane.svelte:147-149`, `registry.ts:62-106`). Row one is fixed at 32 px: views on the left, then at the right the Annotate toggle, the kind's `bar` snippet, `history`, compare controls, and view ▾ (`ItemToolbar.svelte:59-81`). Row two is the annotation row, the "write" half of the same components (`AnnotateBar` and `PdfBar` render twice, once with `part="read"` and once with `part="write"`). Whether row two shows is one global flag for every pane, stored in localStorage, shown by default (`annotationRow.svelte.ts:9-27`).

**How it responds to width.** It does not reflow. `.end` has `overflow: hidden` and `.bar` uses `direction: rtl` so the bar is clipped from its left edge, keeping view ▾ whole (`ItemToolbar.svelte:120-141`): in a narrow pane the Changes menu and the stepper silently vanish. The pane is already a CSS container named `pane` (`Pane.svelte:170`) but no toolbar rule queries it.

**Three sizes.**
- Medium: container queries on `pane` hide the words (Annotate, Comments, Notes, history, view) and keep icons with counts and tooltips. CSS only, plus `aria-label`s that already exist. Hours.
- Narrow: the reading half (stepper, Comments, Notes, Changes) under one list icon; PDF tools under a page icon; history and view merged into ⋯; the annotation row folded into the Annotate button's own dropdown. `ToolbarMenu` and `ToolbarItem` already provide menus with keyboard handling, but `AnnotateBar`, `PdfBar`, `PdfTools`, `ChangesMenu`, `HistoryMenu`, `VersionControls` each render their own buttons, so each needs a menu-line form. Two to four days. Doing it once via a declarative list of actions (icon, label, group, priority, run) rendered by one component with an overflow menu is about a week and would also remove the six duplicated `.tool` styles (VIEW-21).

## 7. Self-explanation

What exists: tooltips on most icon buttons (Annotate, Comment, format, undo, stepper, drawing tools, zoom); the hint line at the annotation row's right while a tool is in hand (`annotating.svelte.ts:244-255`); a help "?" on exactly two pages, Your Changes and Problems (`routes/review/+page.svelte:211`, `routes/review/problems/+page.svelte:142`), whose texts are single long paragraphs (about 170 words for Your Changes); Review section blurbs (`review/sections.ts:28-32`); a "Nothing to read yet" start page made of commands (`routes/+page.svelte:17-28`). No tour, no first-run state, no help page, no list of keys.

Where a first-time user gets nothing:

| question | what the viewer says |
|---|---|
| how do I highlight text? | nothing until Annotate is pressed; with no tool, selecting words offers Quote, which is unexplained until pressed |
| what does Quote do? | after pressing: a toast "Copied with where it came from. Paste it to your agent." (`QuoteChip.svelte:36`) |
| what does Annotate do? | its tooltip, then the hint line; number keys and typing-to-comment are only in the hint |
| does my agent see my annotations? | nothing anywhere; the `here` report is invisible |
| where did my agent's work go? | nothing: copies appear in the tree, suggested edits as marks, proposals in Review, messages in a session tab; no single place or notice |
| how do I accept a suggested edit? | the change popup and cards say Keep / Discard; nothing says a suggestion is an AI's proposal until one is opened |
| versions and comparing | history ▾ lists versions with "compare"; nothing explains what a version is or that compare needs two panes |
| transcripts | a session tab; nothing says the transcript is only what an agent chose to post, not the conversation |
| search | ⌘K only, deliberately with no control (`Palette.svelte:11`) |
| what is the amber session footer? | "not writing in a session" (`SessionFooter.svelte:52`), which reads as broken (VIEW-4) |

## 8. Build and vendoring

After changing viewer code, for `loom serve` to show it: `npm run build` in `arras/` (5.1 s wall measured, Vite 8, 929 modules), then either `uv run python scripts/vendor_arras.py ../arras/build` in `loom/` (refuses a dirty arras tree unless `--allow-dirty`, `loom/scripts/vendor_arras.py:59-68`) or set `LOOM_ARRAS_BUNDLE=…/arras/build` (`loom/src/loom/arras_bundle.py` `find_bundle`), then **restart** `loom serve`, because the server copies the bundle aside at start and serves the copy (`loom/src/loom/render/serve.py:209-227`), then reload the tab. `scripts/checks/bundle.py` then warns until the vendored copy is committed.

`npm run dev` serves a static copy of the fixture with no write API (`arras/package.json` "dev"; `arras/vite.config.ts` has no proxy), so every write control is hidden in development.

The vendored bundle is 12 MB and 303 files in `loom/src/loom/assets/arras` (8 MB `_app`, 3.5 MB pdf.js assets). File names are content hashes, so each vendoring replaces most of them; 160 commits have touched it, 7,071 historical blobs, about 44 MiB packed and 166 MiB raw in history.

The step can disappear in development: a Vite proxy for `/_api`, `/build`, `/_files`, `/digests` to a running `loom serve` gives hot reload against a real quilt with writes (hours); `loom serve` run from a checkout can serve `arras/build` live instead of a held copy (hours). Vendoring can then happen only when tagging a release, which keeps `pipx install git+https://…` working without Node; the bundle could leave `main` and live only on release tags.

## 9. Code health

- **Largest components**: listed in §1. `Column.svelte` (719) mixes the tree, the library shelf, two draggable dividers and Review navigation; `WorkItem.svelte` (453) and `Fragment.svelte` (669) are the dense centres.
- **Duplicated components**: three PDF render paths with different chrome (`CompiledItem` draws `PdfTools` inside its body under a plain toolbar, `CompiledItem.svelte:48-53`; `FileItem` and `WorkItem` put them in the toolbar via `MarkedDoc`; `PdfViewer` modal and `ProposalCard` use `PdfDoc` again); two graph engines (`LocalGraph` with d3-force, `LocalBoxGraph` and `/graph` with ELK); two MathJax builds (`math/mathjax.ts:49` loads `mathjax/es5/tex-svg-full.js`, `math/scoped.ts:2-7` imports `mathjax-full`), shipped as 2.2 MB and 1.8 MB chunks; session lists in the picker, `/review/record/sessions` and `/threads`.
- **Dead**: `lib/math/TexHtml.svelte` has no importer; `shell/rail.svelte.ts`, `shell/panel.svelte.ts`, `PageRail`, `PagePanel` and the Column's `rail`/`panel` props exist only for `/graph`.
- **CSS**: `theme.css` is 1,472 global lines covering tokens, chrome and the whole HTML dialect's typesetting; components add about 7,900 lines of scoped style with 132 `:global(` escapes; `.tool` is redefined in six files, `.sep` in four, `.badge` in six; z-index values range over twelve levels from 1 to 70.
- **Types**: strict, clean under `svelte-check`; two `any`, thirteen `as unknown as`. Manifest types are hand-written from `docs/specs/manifest.md` and declared open ("unknown fields are ignored", `types.ts:1`), so a field loom renames fails silently.
- **First trip for a new contributor**: every module opens with a long paragraph that cites plan sections, DR numbers and design letters ("plan 0.13.3 W1–W11", "DR-254-ikmartin", "(V3)"; 168 such references), which point into history that is declared non-normative; about 20 module singletons (`workspace`, `store`, `prefs`, `ui`, `here`, `hand`, `history`, `sessionView`, `annotationRow`, `comparison`, `compiles`, `jobs`, …) that any component may read or write; and the rule that the dev server cannot exercise writes.

## Findings

### VIEW-1 The viewer tells humans to type loom commands

Evidence: start page steps show `f.command` (`routes/+page.svelte:23-25`); every Problems fix that is not an endpoint is "a command to copy" (`components/Diagnostics.svelte:9, 34-39`, `routes/review/problems/+page.svelte:38`); Settings › Agents "run `{agents.command}` in a terminal" and per-app commands (`shell/settings/Agents.svelte:44, 79`); Overleaf pairing "in a terminal" (`shell/settings/Overleaf.svelte:22`); research state "an agent writes one with `loom write state`" (`workspace/items/PageItem.svelte:20`); out-of-step "Stop it and run it again" (`components/OutOfStep.svelte:11`); Settings read-only "Stop `loom serve` and run it again" (`shell/Settings.svelte:119`); Add a work "loom library add FILE on the command line" (`components/AddWork.svelte:171`). For users whose agent app starts loom, "restart loom serve" has no meaning. Weight: blocks. Effort: hours for wording ("Ask your agent to …", with a copy-the-request button), a day where a button needs a new endpoint. Recommendation: fix.

### VIEW-2 Every publish costs the whole manifest

Evidence: §3. Whole-file fetch (`loader.ts:51-67`), parse plus SHA-256 plus a full re-stringify (`client.svelte.ts:8-17, 93`), 80–145 ms per publish on relloc's 10.76 MB before rendering; deep `$state` (`client.svelte.ts:20`) re-derived across 90 files; fragment cache dropped on every hash (`fragments/fetch.ts:7-11`); the spec forbids anything finer (`docs/specs/README.md:31`). Only adoption choices are mutated in place (`client.svelte.ts:42-46`), so `$state.raw` with an immutable update there is safe. Weight: hurts (part of relloc slowness; another auditor owns loom's side). Effort: hours for `$state.raw` and dropping `contentOf` (compare an adoption-free hash sent by loom instead); a week or more to split the manifest or stream deltas. Recommendation: fix now (raw state), defer (split) until measured.

### VIEW-3 No sign of an agent

Evidence: §3; no attachment, client or last-call field in `types.ts` or `Capabilities` (`write.ts:15-28`); `here` is posted silently (`here.svelte.ts:147-212`); the only per-agent history is per session (`SessionDid.svelte`). Weight: hurts; it is one of the author's complaints and the thing a first-time user most needs to trust. Effort: a day if loom records, per MCP client, the last call time and tool (loom side) and the viewer shows a column line "Claude Desktop · active 2 min ago · last: annotated Lemma 3" with a popover listing what `here` currently tells it. Recommendation: fix.

### VIEW-4 The session footer

Evidence: only `library-verify` and `library-discard` require a session (`write.ts:13, 98-101`); with none selected the footer is permanently amber, "not writing in a session" (`SessionFooter.svelte:52`, `sessions.svelte.ts:82-86`), though annotations and every Review act work. The selection machinery is the footer (143), picker (408), store (110), delete dialog (73), actions (44), plus `/review/record/sessions` (146). Choosing a session also opens its transcript beside and closes other session tabs (`links.ts:184-210`). Weight: hurts. Effort: hours (loom files a verification under the newest open session or none; the viewer hides the footer and keeps sessions as items to read). Recommendation: hide the footer, fix the requirement.

### VIEW-5 Duplicate entry points

Evidence:
- PDF of a document: tree PDF row (`FileTree.svelte:133-143`) opening `CompiledItem`; a person's own `.pdf` beside the `.tex` in the tree opening `FileItem` (annotatable, toolbar tools) while `CompiledItem` is not (tools in its body, `CompiledItem.svelte:48-53`); for works, view ▾ › open the PDF in a browser tab (`WorkControls.svelte:45`) and the PDF modal (`PdfViewer.svelte`).
- Keeping a suggested edit: its popup, the Comments list card, Changes ▾ Keep all, Review › Your Changes card and Keep all, and on an agent copy's card in Review › Proposed (five).
- Versions: history ▾, the version bar, Review › The Record › Versions, Everything recorded.
- Sessions: footer picker, Review › The Record › Sessions, `/threads`.
- Library: column shelf, Review › Library, Settings › Library, a work's Info.
- Problems: Review › Problems, Settings › Problems, compile status in the tree.
Weight: hurts. Effort: days. Recommendation: remove the second and later of each for v0.1; a candidate shape is a document with views Text · PDF, suggested edits kept in the text and listed in one Review list, versions only in history ▾, sessions only as items.

### VIEW-6 Tabs

Evidence: §5; no drag (`PaneHead.svelte:61-85`); `move` appends only (`store.svelte.ts:231-249`); reload keeps two items (`store.svelte.ts:269-277`, `workspace/remember.ts`). Weight: hurts. Effort: a day for drag with insertion; hours to persist every tab per quilt. Recommendation: fix.

### VIEW-7 What opens where

Evidence: §5 (`links.ts:152-179`, `LinkPreview.svelte:209-219`, `store.svelte.ts:148-162`). Weight: hurts; following a reference splits the screen, which a first-time user experiences as the layout changing by itself. Effort: hours to change the default to same-pane with ⌥-click and the hover card for beside; a day for a right-click menu on links and tabs. Recommendation: fix, after the author picks the rule.

### VIEW-8 Toolbar width

Evidence: §6 (`ItemToolbar.svelte:120-141`, `Pane.svelte:170`, `annotationRow.svelte.ts:9`). Weight: hurts. Effort: hours for the medium size, two to four days for the narrow one, a week for a declarative toolbar. Recommendation: fix (medium now, narrow with the panes work).

### VIEW-9 Side by side with the agent app

Evidence: the column folds below a 1200 px window (`Column.svelte:43-50`); the workspace shows one pane below 700 px (`Workspace.svelte:16`). A browser beside Claude Desktop or Codex on a 13–14 inch Mac is roughly 700–860 px wide, so users will mostly see the folded, single-pane viewer. Weight: hurts. Effort: hours (lower the thresholds, test at 800 px). Recommendation: fix.

### VIEW-10 Self-explanation

Evidence: §7. Weight: hurts. Effort: a day for one "How loom works" panel behind a "?" in the column head (highlight, Quote, Annotate, what the agent sees, where agent work appears, keeping edits, versions, transcripts, keys), a visible search control, and empty-state text that names the next act. Recommendation: fix.

### VIEW-11 Review

Evidence: five sections (`review/sections.ts:24-37`); the two things the author wants are "Waiting to be accepted" in Your Changes (`routes/review/+page.svelte:229-257`) and AI edits, which are split between "Changes to keep" in Your Changes (`:259-292`) and agent copies and proposed results in Proposed Changes (`routes/review/proposed/+page.svelte:2, 84-140`); the lead paragraph is about 100 words (`routes/review/+page.svelte:227`). Weight: hurts. Effort: days. Recommendation: fix: two sections, "Mathematics that changed" and "Proposed by AI" (suggested edits, copies, proposed results), with Problems, Library and The Record moved out of Review's navigation. Another auditor may own the semantics; this is the viewer's share.

### VIEW-12 Static and host-neutral legacy

Evidence: §4. Weight: hurts (development speed; blocks VIEW-2's real fix). Effort: a day or two in `src`, more in tests. Recommendation: remove, together with spec obligation 2.

### VIEW-13 Development loop and vendoring

Evidence: §8. Weight: hurts (development). Effort: hours each for the Vite proxy and live serving from `arras/build`; vendoring moves to the release checklist. Recommendation: fix.

### VIEW-14 Accept needs a reviewer name first

Evidence: "Choose your reviewer name in Settings to accept." (`routes/review/+page.svelte:230`); the name is Settings › Profile. Weight: hurts on first use of the one Review act the author wants. Effort: hours (default to the author name loom already has, or ask inline). Recommendation: fix.

### VIEW-15 Graphs

Evidence: `routes/graph/+page.svelte` (764) and `lib/graph/` (1,696), ELK in a 1.4 MB chunk and d3-force; reached only by the graph icon on a document (`DocumentItem.svelte:165`) and "the whole graph" in its panel (`LocalGraphPanel.svelte:68`). Weight: irrelevant for v0.1. Effort: hours to hide. Recommendation: hide; decide after users.

### VIEW-16 Development shelf

Evidence: `Settings.svelte:93-106`, `shell/views.ts:36-49`, six routes (~110 lines). `/threads` duplicates the Sessions table. Weight: cosmetic. Effort: hours. Recommendation: remove.

### VIEW-17 Dead code

Evidence: `lib/math/TexHtml.svelte` (no importer); `shell/rail.svelte.ts`, `shell/panel.svelte.ts`, `PageRail.svelte`, `PagePanel.svelte` used only by `/graph`. Weight: cosmetic. Effort: hours. Recommendation: remove (with VIEW-15).

### VIEW-18 Two MathJax builds

Evidence: §9. Both load lazily, so the cost is bundle and git weight and two typesetting paths to keep consistent. Weight: cosmetic. Effort: a day. Recommendation: defer.

### VIEW-19 Module headers

Evidence: §9; the repository's own `CLAUDE.md` asks for brief docstrings about the current state. Weight: hurts development and agents working on the viewer. Effort: days, best done file by file as each is touched. Recommendation: fix.

### VIEW-20 Singletons and capability state

Evidence: about 20 `export const x = new …` stores (`reading`, `ui`, `jobs`, `pdf`, `prefs`, `here`, `outOfStep`, `rail`, `panel`, `draft`, `annotationRow`, `workspace`, `comparison`, `store`, `compiles`, `acted`, `sessionView`, `hand`, `commentSeed`, `history`), plus `strips` and `settingsAsked`; 58 `can()` probes each held in a component's own `$state`. Weight: cosmetic. Effort: comes with VIEW-12 (one `served` flag read synchronously after boot). Recommendation: fix with VIEW-12.

### VIEW-21 CSS

Evidence: §9. Weight: cosmetic. Effort: comes with VIEW-8. Recommendation: defer.

### VIEW-22 Hand-mirrored manifest types

Evidence: `lib/manifest/types.ts` (784 lines, "Types mirroring docs/specs/manifest.md"). Weight: cosmetic now; a rename on loom's side fails silently. Effort: a day to generate from loom's Python. Recommendation: defer.

## Ten changes for a first-time user, ranked by benefit per hour

1. Replace every command shown to a human with a button or "ask your agent to …" (VIEW-1). Hours.
2. Hide the session footer and stop requiring a session for verify and discard (VIEW-4). Hours.
3. Lower the fold and one-pane thresholds so the viewer works beside an agent app (VIEW-9). Hours.
4. Persist every tab of both panes per quilt (VIEW-6). Hours.
5. Hide the graph, the development shelf and their routes (VIEW-15, VIEW-16, VIEW-17). Hours.
6. Default the reviewer name so Accept works on first use (VIEW-14). Hours.
7. Medium toolbar via container queries, so nothing is clipped silently (VIEW-8). Hours.
8. One "How loom works" panel, a visible search control, and empty states that name the next act (VIEW-10). A day.
9. An agent status line with what the agent can see (VIEW-3). A day, half of it in loom.
10. Same-pane links by default, beside as an explicit act, and tab drag (VIEW-7, VIEW-6). A day or two.

Then, larger: collapse duplicate entry points (VIEW-5) and reduce Review to two sections (VIEW-11), days each.

## Five changes that would speed up viewer development

1. A Vite proxy from `npm run dev` to a running `loom serve` (`/_api`, `/build`, `/_files`, `/digests`), so hot reload works against a real quilt with writes (VIEW-13). Hours.
2. In a checkout, `loom serve` serves `arras/build` live rather than a held copy, and vendoring happens only at release (VIEW-13). Hours.
3. Delete the static-host legacy and the per-endpoint capability probes: one `served` flag, no static fixture mode (VIEW-12, VIEW-20). A day or two.
4. `$state.raw` for the manifest and no full re-stringify per publish, so working against relloc is not slow for the developer either (VIEW-2). Hours.
5. Replace plan-citing module headers with short current-state docstrings and keep §1's map as the viewer's one-page architecture note (VIEW-19). Days, incremental.

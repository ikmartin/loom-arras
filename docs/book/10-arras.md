# 10. Arras

Arras is the viewer. It is a static bundle that reads a build directory conforming to `specs/` and renders it; it has no server, writes nothing, and knows nothing about LaTeX, org, loom, or mathematics. This chapter specifies what it shows, how it behaves, how it is built and deployed, and the boundary it must never cross.

## 10.1 Architecture

**[decided]**

1. Arras is a single-page application built with Svelte 5 and SvelteKit using `adapter-static` (`fallback: 'index.html'`, configured in `vite.config.ts`). It runs as an SPA loading `manifest.json` and fetching fragments on demand; for deployment, `npm run build:prerender` writes one `index.html` per route named by the manifest, so a static host serves pretty URLs, but the pages are the shell and content loads in the browser, so a site is not yet crawlable (DR-54).
2. Arras is served as files. `loom serve` serves the bundle at `/` and the build directory at `/build/`, answering every path that is not a bundle file or an asset with `index.html` (DR-78); any static server with the same fallback works. Routing is path-based and opening the bundle from `file://` is not supported, because SvelteKit's router type is a build-time choice (DR-57).
3. Arras is distributed from one build. Loom vendors `build/` under `src/loom/assets/arras/` through `scripts/vendor_arras.py`, which stamps `VERSION` with the arras commit and the interface version, so loom users never install Node; `npm run build:pip` copies the same build into the optional `arras` pip wrapper under `python/`, whose `arras.bundle_path()` loom also honours; the npm package is private. Publishing to PyPI and npm is the user's step (M7).
4. Arras has no runtime dependency on the publisher. It polls the manifest; the write API is deferred, arras has no client for it yet, and `loom serve` answers `/_api` with 404.
5. The manifest is loaded whole; fragments are fetched lazily per page and cached in memory under the manifest's hash, and a new hash empties the cache.

**[decided]** Runtime libraries bundled: MathJax 3 with SVG output, the full `tex-svg-full` component so that no extension loads from the network (DR-55, M7), configured from the manifest's macro sets with a per-fragment set applied inside the fragment's math (DR-56), loaded while the browser is idle once the manifest's macros are known; ELK.js (`elkjs`) for the layered graph layout, **[decided]** chosen at implementation over dagre (`src/lib/graph/layout.ts`; the fixture's graph renders in the M2 suite); `d3-force` for the force layout and the local graph; ninja-keys for the search palette. Nothing loads from a CDN at runtime; a deployed site works offline.

**[decided]** A fragment with more than 160 formulas is typeset in batches: everything up to the element the URL points at, or the first screen and a half, before the page is revealed and scrolled there, and the rest in batches that yield to the page. Everything above the reader is typeset before the reveal, so nothing above them changes height afterwards. All typesetting shares one queue (DR-120).

## 10.2 Pages

Each page is a route; the manifest supplies everything but the fragment text.

### 10.2.1 Node page

**[decided]** `/node/<key>` for any node, digest node, or labelled proof (the key travels in a rest segment, so `sy-0003/proof` and ids with dots are routes). Shows:

- Header line: taxon, id (with aliases on hover), number in the default master (or "not yet compiled"), created date, author(s), tags as links. Sitegen's meta line, extended.
- The review badge (10.3).
- The node fragment: statement, then each proof as a collapsible block with its own badge.
- Margin marks and comment boxes (10.4).
- In `<document>`: the chain of including nodes up to each master that reaches it ("document › The residue map › Independence"), or "loose". The section was headed "Context" in design; it is the breadcrumb and is named for what it shows.
- Depends on and used by: one line per node rather than one per edge, each with the kinds that established it, since a statement and its two proofs all using the same lemma is one dependency. "Dependents" was the design's name for the second; it is now "used by". For digest nodes, "cited by".
- See also: the nodes this one is related to by a `see:` declaration (5.11.3), both directions, each with its taxon, title, and the masters that reach it. A relation is never a dependency, and the list is separate from the dependency lists for that reason. A relation kind the viewer does not know renders as a labelled list of links.
- The statement's closure as a "Read first" list of links.
- Discussions: threads whose targets include this key.
- Detached annotations, listed with their quotes.
- Diagnostics concerning this key.
- For a section node: its children in order, each linked, with the child fragments expandable in place.
- The local graph, heading the rail: the node's neighbourhood one or two dependency steps out, live, each node a link (15.5.1, DR-116).

**[decided]** Every link to a node or a cited work, on this page and every other, previews what is behind it on hover (15.3.6, DR-117).

### 10.2.2 Master view

**[decided]** `/master/<stem>` for each master. Renders the master fragment as a document: headings, prose, every node in place with its id in the margin linking to its node page (the Stacks pattern), review badges in the margin, marks in the text, a table of contents built from the master's section nodes in a rail. Numbers come from the manifest. A master that is not yet compiled renders with ids only and says so. A citation opens the digest result it names, or the cited work's page when it names none (DR-119). The local graph can be opened over the document and follows the result being read (DR-116).

### 10.2.3 Digest view

**[decided]** `/digest/<citekey>`: the page for a cited work, digested or not. Its title and authors with BibTeX's braces and accent commands made readable; its outward links — each identifier at the service that resolves it (`doi:` at doi.org, `arXiv:` at arxiv.org, `mr:` at MathSciNet, `zbl:` at zbMATH), the bibliography's `url`, and the fetched PDF under `/refs/` when the manifest says it is there (DR-119), or, for a work stating no identifier, a lookup's candidate marked as unconfirmed (DR-122); then the digest fragment as a document (the reference's table of results), with provenance from the manifest's `references` entry, `requires`, version mismatch if any, and the list of keys in the quilt that cite each result. A result's page, in its locator (`Theorem 2.1, p. 4`), opens the fetched paper at that page when the copy on file is the version the digest was extracted from (10.4.1).

### 10.2.4 Review panel

**[decided]** `/review`: the read-only view of the ledger and the review records. A header with counts (accepted, stale, draft, incomplete, proved, settled). A table of keys with: state badge, since when, cause if stale (with a link to the diff under `build/diffs/`), latest review and open annotations by kind, detached count, incomplete text, reached-by. Filters: accepted, stale, draft, incomplete, loose, previous-key matches (retired keys), cited results, by master, by author, by tag; they live in the URL (`/review?show=stale&document=…`) and each header count toggles its own. With `show=incomplete` the table says what each gap blocks, expandable to the list (DR-118). Undigested citekeys are listed below the unfiltered table (M3). A list of runs and comment sessions with their discard flag. `loom status` prints the same information; the two must agree because both read the manifest.

### 10.2.5 Problems page

**[decided]** `/problems`: every diagnostic, grouped by code, filterable by severity and code from the left panel and the URL (`/problems?severity=error`), each with its message, linked locations, and linked keys. Reserved codes get their specific affordances (10.6); unknown codes render generically. Counts appear in the header of every page.

### 10.2.6 Blockers

**[decided]** `/blockers` opens the review table's incomplete view, `/review?show=incomplete`: every key with `\incomplete`, with its text, the masters that reach it, and how many results rest on it, expandable to the list. This is the "incomplete" backlink page of the author's org practice, made from the manifest; it is a view of the review table rather than a page of its own shape (DR-118).

### 10.2.7 Graph

**[decided]** `/graph`: the dependency graph, force-directed by default and layered on a toggle (15.5). In the layered drawing (ELK.js), dependencies sit above what uses them, statements are grouped by section, and nodes stay where the layout put them; nodes are coloured by state and freshness, shaped by style class; edges by kind (statement solid, proof dashed, prose dotted); inclusion shown as grouping, not as edges (DR-115). Controls: highlight downstream of a node (the unravel set), highlight closure, filter by master, by taxon, by tag, state, depth around the selection, and which cited results to draw: those used here, all, none, or each cited work contracted to a single node (15.5.2, DR-124). Click highlights, double-click opens the node page, or a paper's reference page.

### 10.2.8 Threads

**[decided]** `/threads` lists threads newest first; `/thread/<id>` shows a chat-shaped page: participants, messages in order, attachments listed with name, kind, and count (bundles, drafts, proposals, notes, annotation counts), the run log collapsed, targets linked, the discard flag. Read-only in the MVP.

### 10.2.9 Indexes and search

**[decided]** `/tags` and `/tag/<tag>`; `/taxa` and `/taxon/<slug>`; `/references` (every cited work with or without a digest, its outward links, and who cites it, the digest's own results left out; DR-119); `/loose`. A search palette (ninja-keys) over the manifest's search entries (nodes, masters, and threads), grouped by taxon, reachable by keyboard shortcut (⌘K) from every page.

### 10.2.10 Home

**[decided]** `/`: the corpus title, four metric cards (accepted, stale, incomplete, errors), each opening the table of exactly what it counts (DR-118), the documents, what needs attention, what is blocked, what is loose, and what is recent. Every line links. It is the landing route, and its shape is 15.3.4.

## 10.3 Badges

**[decided]** A key that has no page of its own is not linked. An unlabelled proof resolves through the node that owns it, so its link lands on that node's page at the proof; a key that resolves to nothing at all, such as the file container a `double-inclusion` names, is rendered as plain text (DR-94).

**[decided]** A key's badge shows its state label with the publisher's colour class and, for accepted keys, the stale modifier; then the review facts in small type: "reviewed clean 16 Sep" or "2 open objections". A node's header badge combines its statement's badge and the best of its proofs' ("statement accepted · proof accepted, stale"), plus the derived `proved` or `settled` label when the manifest reports it, plus `incomplete` overriding everything. Arras renders whatever labels and colours the manifest declares; it has no built-in notion of what "accepted" means.

**[decided]** A key with an acceptance and many detached annotations shows the acceptance badge and a detached count; detached annotations never change a badge (`src/lib/badges.ts`; M3 shows the detached count beside the badge).

## 10.4 Annotations

**[decided]** Marks in fragments render as highlighted spans coloured by the kind of their leading comment; a block-level annotation colours its block's left edge. Where the box with the annotation's author label, date, kind, body, status, and replies threaded beneath appears is a display preference: beside the node in the margin, where selecting a mark brings its box into view, or in place, where selecting a mark expands the box beneath the text and a press outside closes it (15.3.1, DR-114). A filter by kind and by author is available on every page with marks. Discarded records are hidden by default with a toggle to show them dimmed (M3).

### 10.4.1 Links into cited works

**[decided]** A link `loom:<scheme>:<value>#page=N` or `#quote=TEXT` in a comment, a thread message or a report names a place in a cited work by its global identifier (specs/dialect.md §2.13). Selecting it opens the viewer of 15.3.7 without leaving the page. The fetched PDF is opened only when it is filed under the identifier the link names; when the copy on file is another artifact of the same work, the viewer says the pages may not match and opens it only on request, and when nothing is fetched it says so and links to the identifier's own service, arXiv's PDF at the page where it can (DR-123).

When the write API is present (deferred), the same boxes gain reply and resolve controls, and selecting text offers "comment"; the selection is mapped to a quote per `specs/write-api.md`.

## 10.5 Live reload

**[decided]** Arras polls `/build/manifest.json` every second with `If-None-Match` (**[decided]** `src/lib/manifest/client.svelte.ts`; `loom serve` answers 304 while the manifest is unchanged, so the poll costs nothing) and re-renders the current page when the manifest's content hash changes (M2). While the tab is hidden it does not poll, and it polls at once when the tab is shown again (DR-120). That is its only trigger. It does not know what changed or why; a new hash empties the fragment cache and the page re-fetches what it shows. The interface version is checked on every load; a mismatch shows the problems page with one diagnostic and nothing else.

## 10.6 Affordances for reserved diagnostics

**[decided]** `duplicate-id`: both locations linked side by side. `dangling-link`: the source location linked, the missing target named. `missing-include`: the site linked. `double-inclusion`: both inclusion paths rendered as breadcrumbs. `inclusion-cycle`: the cycle listed as a chain. `unreachable`: a filter on the indexes and a "loose" mark on the node page. Everything else: severity, message, locations, keys.

## 10.7 Static deployment

**[decided]** `npm run build:prerender <build-dir> [<out>]` builds the SPA, writes an `index.html` for every route the manifest names (home, the index pages, every node, master, digest, tag, taxon, and thread) plus a `routes.json`, and copies the build directory beside them, ready for GitHub Pages or any static host. The pages are the single-page shell: content loads in the browser from `build/manifest.json`, fragments are not inlined, MathJax is bundled; a crawlable, server-rendered site needs a second data path and is deferred (DR-54; M2 prerendered the fixture's 50 routes). This is how the author's site will be published once sitegen publishes to the interface. Prerendering is a deploy-time step and never runs during `loom serve`.

## 10.8 What arras must never know

**[decided]** Arras never contains: a LaTeX or org parser; the word "quilt", the loom-only operations "atomize" and "unravel", or any `loom <command>` phrase in its code (they may appear in fixture data and in labels the manifest supplies); any assumption about which state labels exist beyond the reserved colour classes; any knowledge of event kinds; any write path other than the write API client; any loom code, imported or copied. The words "digest" and "proof" are exempt from the word list because the manifest's own field names, the spec's route `/digest/<citekey>`, and the Web Crypto API's `digest()` use them (DR-39). A pull request that adds any of these is rejected by review, `tests/unit/forbidden-words.spec.ts` enforces the word list over `src/`, and the fixture with synthetic unknown labels and codes is the test that generic rendering still works.

## 10.9 Accessibility and print

**[decided]** Every page is navigable by keyboard and the master view prints as a document with badges suppressed; marks carry `aria-describedby` to their boxes in the margin placement and `aria-expanded` in place (implemented). Not MVP-gating.

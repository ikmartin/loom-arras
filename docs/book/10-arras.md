# 10. Arras

Arras is the viewer. It is a static bundle that reads a build directory conforming to `specs/` and renders it; it has no server, writes nothing, and knows nothing about LaTeX, org, loom, or mathematics. This chapter specifies what it shows, how it behaves, how it is built and deployed, and the boundary it must never cross.

## 10.1 Architecture

**[decided]**

1. Arras is a single-page application built with Svelte 5 and SvelteKit using `adapter-static`. Locally it runs as an SPA loading `manifest.json` and fetching fragments on demand; for deployment it can prerender every route in the manifest to static files so a site is crawlable and has pretty URLs.
2. Arras is served as files. `loom serve` serves the bundle at `/` and the build directory at `/build/`; any static server or `file://` (with hash routing, **[assumed]** enabled automatically when not served over HTTP) works.
3. Arras is distributed twice from one build: an npm package for people who build sites, and the `arras` pip package, which vendors the built bundle so that loom users never install Node.
4. Arras has no runtime dependency on the publisher. It polls the manifest; it calls the write API only if `GET /_api` answers.
5. The manifest is loaded whole; fragments are fetched lazily per page and cached in memory keyed by the manifest's hash.

**[decided]** Runtime libraries bundled: MathJax 3 (configured from the manifest's macro sets), a layered graph layout (ELK.js or dagre, **[deferred]** choose at implementation by rendering the fixture's graph), ninja-keys for the search palette. Nothing loads from a CDN at runtime; a deployed site works offline.

## 10.2 Pages

Each page is a route; the manifest supplies everything but the fragment text.

### 10.2.1 Node page

**[decided]** `/node/<key>` for any node, digest node, or labelled proof. Shows:

- Header line: taxon, id (with aliases on hover), number in the default master (or "not yet compiled"), created date, author(s), tags as links. Sitegen's meta line, extended.
- The review badge (10.3).
- The node fragment: statement, then each proof as a collapsible block with its own badge.
- Margin marks and comment boxes (10.4).
- Context: the chain of including nodes up to each master that reaches it ("in main.tex: §3 The residue map › §3.2 Independence"), or "loose".
- Dependencies (statement-edges and proof-edges separately, each a linked list with taxa and titles) and dependents (the reverse), and, for digest nodes, "cited by".
- Discussions: threads whose targets include this key.
- Detached annotations, listed with their quotes.
- Diagnostics concerning this key.
- For a section node: its children in order, each linked, with the child fragments expandable in place.

### 10.2.2 Master view

**[decided]** `/master/<stem>` for each master. Renders the master fragment as a document: headings, prose, every node in place with its id in the margin linking to its node page (the Stacks pattern), review badges in the margin, marks in the text, a table of contents built from headings in a rail. Numbers come from the manifest. A master that is not yet compiled renders with ids only.

### 10.2.3 Digest view

**[decided]** `/digest/<citekey>`: the digest fragment as a document (the reference's table of results), with provenance from the manifest's `references` entry, `requires`, version mismatch if any, and the list of keys in the quilt that cite each result.

### 10.2.4 Review panel

**[decided]** `/review`: the read-only view of the ledger and the review records. A header with counts (accepted, stale, draft, incomplete, proved, settled). A table of keys with: state badge, since when, cause if stale (expandable to the diff from `diffs/`), latest review, open annotations by kind, detached count, incomplete text, reached-by. Filters: stale, draft, incomplete, loose, unmatched citations, undigested, retired, by master, by author, by tag. A list of runs and comment sessions with their discard flag. `loom status` prints the same information; the two must agree because both read the manifest.

### 10.2.5 Problems page

**[decided]** `/problems`: every diagnostic, grouped by code, filterable by severity and code, each with its message, linked locations, and linked keys. Reserved codes get their specific affordances (10.6); unknown codes render generically. Counts appear in the header of every page.

### 10.2.6 Blockers page

**[decided]** `/blockers`: every key with `\incomplete`, grouped by master, each with the text and a link; for the default master, the set of incomplete keys on paths from any incomplete key to the master's top-level results. This is the "incomplete" backlink page of the author's org practice, made from the manifest.

### 10.2.7 Graph

**[decided]** `/graph`: the dependency graph as a layered drawing, layered by section then by longest path; nodes coloured by state and freshness, shaped by style class; edges by kind (statement solid, proof dashed, prose dotted); inclusion shown as grouping, not as edges. Controls: highlight downstream of a node (the unravel set), highlight closure, filter by master, by taxon, by tag, hide external nodes. Click opens the node page.

### 10.2.8 Threads

**[decided]** `/threads` lists threads newest first; `/thread/<id>` shows a chat-shaped page: messages in order, attachments in the margin (bundles, drafts, proposals, annotation counts), the run log collapsed, targets linked, the discard flag. Read-only in the MVP.

### 10.2.9 Indexes and search

**[decided]** `/tags` and `/tag/<tag>`; `/taxa` and `/taxon/<slug>`; `/references` (every citekey with or without a digest); `/loose`. A search palette (ninja-keys) over the manifest's search entries, grouped by taxon, reachable by keyboard shortcut from every page.

### 10.2.10 Home

**[decided]** `/`: the corpus title, links to the default master view, the review panel, the problems page, the graph, the indexes, and the counts.

## 10.3 Badges

**[decided]** A key's badge shows its state label with the publisher's colour class and, for accepted keys, the stale modifier; then the review facts in small type: "reviewed clean 16 Sep" or "2 open objections". A node's header badge combines its statement's badge and the best of its proofs' ("statement accepted · proof accepted, stale"), plus the derived `proved` or `settled` label when the manifest reports it, plus `incomplete` overriding everything. Arras renders whatever labels and colours the manifest declares; it has no built-in notion of what "accepted" means.

**[assumed]** A key with an acceptance and many detached annotations shows the acceptance badge and a detached count; detached annotations never change a badge.

## 10.4 Annotations

**[decided]** Marks in fragments render as highlighted spans; hovering or clicking opens a box with the annotation's author label, date, kind, body, status, and replies threaded beneath. Block-level annotations render as a marker in the margin of the block. A filter by kind and by author is available on every page with marks. Discarded records are hidden by default with a toggle to show them dimmed.

When the write API is present (deferred), the same boxes gain reply and resolve controls, and selecting text offers "comment"; the selection is mapped to a quote per `specs/write-api.md`.

## 10.5 Live reload

**[decided]** Arras polls `/build/manifest.json` (**[assumed]** every second, with `If-None-Match` when the server supports it) and re-renders the current page when the manifest's content hash changes. That is its only trigger. It does not know what changed or why; it diffs consecutive manifests only to decide which cached fragments to drop (any whose node's `src` or hash changed) and to keep scroll position when possible. The interface version is checked on every load; a mismatch shows the problems page with one diagnostic and nothing else.

## 10.6 Affordances for reserved diagnostics

**[decided]** `duplicate-id`: both locations linked side by side. `dangling-link`: the source location linked, the missing target named. `missing-include`: the site linked. `double-inclusion`: both inclusion paths rendered as breadcrumbs. `inclusion-cycle`: the cycle listed as a chain. `unreachable`: a filter on the indexes and a "loose" mark on the node page. Everything else: severity, message, locations, keys.

## 10.7 Static deployment

**[decided]** `arras build --prerender <build-dir>` (npm) or the same through the pip package's CLI produces a directory of static files: every route in the manifest prerendered, fragments inlined into pages, MathJax bundled, ready for GitHub Pages or any host. This is how the author's site will be published once sitegen publishes to the interface. Prerendering is a deploy-time step and never runs during `loom serve`.

## 10.8 What arras must never know

**[decided]** Arras never contains: a LaTeX or org parser; the word "quilt", "digest", "proof", or any loom command in its code (they may appear in fixture data and in labels the manifest supplies); any assumption about which state labels exist beyond the reserved colour classes; any knowledge of event kinds; any write path other than the write API client; any loom code, imported or copied. A pull request that adds any of these is rejected by review, and the fixture with synthetic unknown labels and codes is the test that generic rendering still works.

## 10.9 Accessibility and print

**[assumed]** Every page is navigable by keyboard; marks have `aria-describedby` to their boxes; the master view prints as a document with badges suppressed. Not MVP-gating.

## Open questions

- Route scheme: pretty paths versus hash routes when served from `file://`. **[assumed]** Pretty paths under a server; hash fallback otherwise.
- Whether the graph should be drawn client-side for a five-thousand-node quilt or precomputed by the publisher. **[deferred]**; measure on the ACGS fixture; the manifest may gain optional layout hints later.
- Whether a dark theme is in the MVP. **[assumed]** Yes; sitegen's tokens carry over.
- Whether the node page should show the bundle's closure as a "what you need to read first" list. **[assumed]** Yes, it is the closure from the manifest, already available.

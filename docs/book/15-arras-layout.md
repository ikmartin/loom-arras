# 15. Arras layout and visual design

Chapter 10 says what arras shows. This chapter says what it looks like and how it is arranged: the three navigation shells, the regions every page has, what each rail holds per view, the graph's two layouts and its toggle, the token and typography rules, and the reference figures. It is arras's own design document and is not part of the loom–arras interface: nothing here changes what loom publishes, and a change here needs no manifest change. Chapter 10 remains authoritative on which pages exist and what data they show.

Markers as elsewhere. Most of this chapter is **[decided]** in arrangement and **[assumed]** in exact numbers; the numbers are given anyway, because an implementation given "narrow rail" will choose something else and a review will follow.

## 15.1 Principles

**[decided]**

1. One persistent left rail, always present, always in the same place. The user never hunts for navigation.
2. A right rail appears only where there is context to show: node pages, the read view when a reached node carries comments, the review panel's explanations, the graph's inspector. It is absent elsewhere, and its absence is not a gap.
3. The shell renders no page content; the page renders no navigation. A page that reaches into the shell is a bug.
4. Nothing in arras writes to the quilt. Every control is navigation, filtering, or display.
5. Density is comfortable only. **[decided]** No compact mode in the MVP.
6. Below 900px the layout is undefined. **[decided]** Mobile is deferred; the rule is that shells collapse to no rail with a disclosure control, and nothing else is specified.

## 15.2 The three shells

**[decided]** Three navigation shells are built and shipped together as an experiment; the user picks one. They differ only in arrangement: every shell contains the same elements (quilt name, view switcher, document picker, contents, search) and no shell contains anything another lacks. The default is C.

**[decided]** The choice is a per-viewer preference stored in arras's own settings (browser `localStorage`), never in the quilt, plus a `?shell=` URL parameter so two shells can be compared by sending a link. Preferences are arras's: shell, typography, theme.

**[decided]** Deletion rule: if after a few weeks of real use nobody switches away from the default, two shells are deleted. The rule exists so that the experiment ends.

### 15.2.1 Shell A: rail sections

![Shell A](figures/shell-a-rail-sections.png)

**[assumed]** A 178px rail, `--leaf`, hairline right border, holding four stacked sections separated by 10px and small-caps 9px muted labels: the quilt name (13px, no label); `VIEW` (the five views as 13px rows with a 15px leading icon, the current one on `--link-wash` with `--link` text); `DOCUMENT` (a select, full rail width minus 2×14px); `CONTENTS` (the heading tree of the current document, indent 10px per level, the current section marked by a 2px `--link` bar on the left edge and `--ink` text). No top bar. Page content begins at 206px.

### 15.2.2 Shell B: top bar and tabs

![Shell B](figures/shell-b-topbar-tabs.png)

**[assumed]** A 30px top bar, `--leaf`, hairline bottom border: quilt name (12px) at the left; a breadcrumb beside it that is the document picker in read and graph views (`/ main.tex ▾`) and the position in others (`/ main.tex › §3 › Lemma 3.4`); view tabs pushed right, the current one on `--link-wash`; a search affordance at the far right. The rail below is 160px and holds contents only. Page content begins at 188px, 39px from the top.

### 15.2.3 Shell C: icon strip and panel

![Shell C](figures/shell-c-icon-strip.png)

**[assumed]** A 44px icon strip, `--leaf`, holding six 19px icons at 38px vertical pitch (read, graph, review, problems, references, search), the current one on a 32×26px `--link-wash` with `--rad-control`; every icon has an `aria-label` and a tooltip. Beside it a 168px panel whose contents depend on the view: read and graph show the document picker above the contents tree; review shows the filter list and queue; problems shows the code filters; references shows the citekey list; search shows results. Page content begins at 221px. Default shell.

## 15.3 Page anatomy

**[decided]** Every page is: an optional header block (title, id, badges, tags), the content region, and an optional right rail. Pages never draw their own navigation, never place a title in the shell, and never assume a shell.

**[assumed]** Right rail width `--rail-right`, `--leaf`, hairline left border, 12px padding, sections labelled like the left rail's.

### 15.3.1 Read view (a master)

![Read view](figures/page-read-master.png)

**[assumed]** The document rendered as a document. Prose in the body typeface at 11–16px depending on the user's type setting, `line-height: 1.7`. Each node is a row: a 86px right-aligned margin column holding the id in mono accent and the state word beneath it in the state colour at 9px, then a hairline vertical rule, then the node's rendered text indented 10px past the rule. Numbers come from the manifest and appear in the statement's label ("Lemma 3.4."). Proofs render collapsed with a disclosure marker, matching sitegen's `details.env-proof` treatment: no box, a left rule, a ▸/▾ marker. Environment boxes follow sitegen's `environments.css` convention: a per-taxon left-border accent, no filled background.

**[decided]** The right rail appears in the read view only when a node on screen carries non-discarded comments, and then holds them, aligned as closely as layout allows to the node they target.

### 15.3.2 Node page

![Node page](figures/page-node.png)

**[assumed]** Header: title and number (15px), id (mono, 9px), state badge (a 14px pill, tinted background, state-coloured text, 9px), tags (muted). Body: statement; then each proof as its own block with its own state line, in manifest order, the detailed proof (reached by another master) included and labelled with the master that reaches it; marks rendered inline on `--mark`. Left panel in shell C shows an on-this-page list. Right rail sections in this order: in `<master>` (the inclusion breadcrumb, one per master that reaches it), depends on, used by, see also, comments (objection cards on the `--state-incomplete` wash, others on `--sheet`), detached comments, diagnostics.

### 15.3.3 Graph

![Graph, force](figures/page-graph-force.png)

![Graph, layered](figures/page-graph-layered.png)

See 15.5.

### 15.3.4 Home

![Home](figures/page-home.png)

**[assumed]** Four metric cards (48px tall, `--leaf`, `--rad-control`, 9px muted label, 18px value in the state colour), then cards for needs-attention, blockers, and views. Every line links. This is the landing route.

### 15.3.5 Review panel, problems, blockers, threads, indexes

**[assumed]** Table-shaped pages: a header with counts, filter controls in the left panel (shell C) or above the table (A and B), rows with state badge, id, taxon, title, cause, counts. A row expands in place to show the stale cause and its diff, rendered as a two-column diff with added and removed tinted by `--state-accepted` and `--state-incomplete` washes. No right rail except on an expanded row, where the explanation occupies it.

**[decided]** The workbench layout (a node list, node body, and context pane as one screen) explored in design is dropped; the review panel plus the node page cover it.

## 15.4 Rails by view

**[assumed]**

| view | left (shell C panel; A and B equivalents) | right |
|---|---|---|
| home | documents, recent | none |
| read | document picker, contents tree | comments, when present |
| node | on-this-page | context and comments |
| graph | layout toggle, colour, scope, filters | inspector |
| review | filters, saved queries | expanded explanation |
| problems | severity and code filters | none |
| references | citekeys, digested or not | none |
| search | results | none |

## 15.5 The graph

**[decided]** One graph page with two layouts and a toggle; the toggle preserves the selection, the filters, and the scope, and animates node positions between the two so it reads as one view rather than two pages.

**[decided]** Force is the default, in the spirit of org-roam-ui: a force-directed neighbourhood with circular nodes, labels beneath, node radius larger for the selection, and no direction encoded. It answers what sits near what.

**[decided]** Layered is the alternative: dependency direction on the vertical axis, upstream above, nodes as rounded rectangles in layers by longest path, edges as curves. It answers what this rests on and what breaks if it changes.

**[assumed]** Shared by both: colour encodes state (15.6); statement edges solid, proof edges dashed, prose edges dotted; `see` relations hidden by default; inclusion is not drawn as edges (grouping only, in layered); external nodes drawn with a dashed border; scope controls are master, local depth around the selection (default 2, 0 meaning the whole scope), and filters by taxon, tag, and state; clicking selects and fills the inspector; double-clicking opens the node page.

**[deferred]** The layout library (ELK or dagre for layered; a force implementation or d3-force) and the node count above which the page switches to a scoped view by default.

## 15.6 Tokens and vocabulary

**[decided]** Arras defines its own token vocabulary. It does not adopt the names used in these design documents or in any other product's design system: borrowing names would imply a shared system that does not exist, and arras's vocabulary should describe what it renders, which is a page of mathematics rather than application chrome. The names below are drawn from print. Every colour, measure, and typeface is a variable; no component hardcodes a value.

**[decided]** Visual character: a warm off-white page, hairline rules rather than borders, generous line height, no shadows, no filled chrome, colour used only to carry meaning. Claude's web interface is a reasonable reference for that character; nothing is copied from it.

**[assumed]** The vocabulary, with light-mode values:

| token | value | use |
|---|---|---|
| `--paper` | `#fbfaf8` | the page |
| `--leaf` | `#f4f2ed` | rails, panels, metric cards |
| `--sheet` | `#ffffff` | content cards, raised surfaces |
| `--rule` | `#d8d5cd` | hairlines, 0.5–1px |
| `--rule-strong` | `#b4b2a9` | emphasised dividers, graph edges |
| `--ink` | `#2c2c2a` | body text |
| `--ink-soft` | `#5f5e5a` | supporting text |
| `--ink-faint` | `#888780` | rail labels, ids in lists, captions |
| `--link` | `#185fa5` | links, ids, the current item |
| `--link-wash` | `#e6f1fb` | the tint behind a current or selected item |
| `--mark` | `#faeeda` | annotation highlight behind marked text |
| `--gap-hair` `--gap-tight` `--gap` `--gap-wide` | 4, 8, 12, 20px | spacing scale |
| `--rad-pill` `--rad-control` `--rad-card` | 4, 8, 12px | radii |
| `--rail-left` `--rail-right` `--strip` | 168, 159, 44px | the fixed widths of 15.2 |
| `--measure` | 34rem, 42rem, 50rem by setting | body line width |

**[decided]** State tokens are a second group, named for the state rather than for a role, because arras's states are loom's and not a generic severity scale:

| token | text | wash | use |
|---|---|---|---|
| `--state-accepted` | `#0f6e56` | `#e1f5ee` | accepted; settled uses the same pair with a filled dot and 500 weight |
| `--state-stale` | `#854f0b` | `#faeeda` | the modifier on accepted; the badge reads "accepted, stale" |
| `--state-draft` | `#5f5e5a` | `#f1efe8` | neutral, not a warning |
| `--state-incomplete` | `#a32d2d` | `#fcebeb` | overrides everything |
| `--state-loose` | `#888780` | none | a mark, not a badge |

**[decided]** The manifest declares state labels with colour classes (`neutral`, `positive`, `positive-strong`, `warning`, `negative`, `info`; specs/manifest.md §8). Arras maps those classes onto the state tokens above in one file, so a publisher that declares states arras has never heard of still renders: `positive` to accepted, `warning` to stale, `negative` to incomplete, `neutral` to draft, `info` to loose, anything unknown to `--ink-soft` with no wash. The mapping is the only place the interface's vocabulary and arras's meet.

**[deferred]** Dark-mode values, defined once as a second block in the same file; `--paper` near `#17171a`, inks inverted, washes at low alpha over the paper rather than tinted solids.

## 15.7 Typography

**[decided]** Serif by default for mathematical content: statements, proofs, prose, digests. Sans for chrome: rails, badges, labels, tables, buttons. Mono for ids.

**[decided]** The serif is the stack the author's site generator uses; read it from that project's `tokens.css` and copy it, so a quilt page and a note page look like the same publication. **[deferred]** The exact stack; the figures use a generic serif as a placeholder.

**[decided]** A settings control, in arras's own settings and written to arras's preferences, offers: body typeface (serif or sans), body size (three steps), line width (three steps), and theme (light, dark, system). Nothing else is user-adjustable in the MVP.

**[assumed]** Type scale: page title 15px/500, section heading 13px/500, body 11–16px by the size setting with `line-height: 1.7`, rail labels 9px uppercase muted with 0.04em tracking, rail items 10–13px, ids 9px mono, badges 9px. Sentence case everywhere. Two weights, 400 and 500.

## 15.8 Component contracts

**[decided]** The shells are one component tree with three arrangements:

```
NavShell({ views, currentView, masters, currentMaster, contents, counts, search })
  renders one of RailSections | TopBarTabs | IconStrip
  renders <slot> for the page, and <slot name="rail"> for the right rail
```

Rules: pages receive no shell props and import no shell module; a page that needs a right rail fills the named slot; a page's title lives in the page, never in the shell; the three arrangements differ only in placement, never in what they contain. Adding an element to one shell means adding it to all three or to none.

**[assumed]** Shared components: `StateBadge(state, fresh, derived)`, `IdChip(id, aliases)`, `NodeCard`, `MarginComment`, `RelationList(kind, items)`, `DiagnosticRow`, `DiffView`, `GraphCanvas(layout, nodes, edges, selection)`, `Inspector`.

## 15.9 Reference figures and their status

**[decided]** The schematic drawings this chapter was designed against have been superseded, as they said they would be. The figures are now screenshots of the viewer rendering the conformance fixture, generated by `npm run shots` in `arras/` and committed: `page-home.png`, `page-read-master.png`, `page-node.png`, `page-node-dark.png`, `page-review.png`, `page-problems.png`, `page-graph-force.png`, `page-graph-layered.png`, and one page in each shell as `shell-a-rail-sections.png`, `shell-b-topbar-tabs.png`, `shell-c-icon-strip.png`. They are regenerated on any change to the chrome, and the release checklist carries "screenshots regenerated".

The original `.svg` drawings remain beside them for the record of what was intended. Where a screenshot and this chapter's numbers disagree, the screenshot is what exists and the chapter is corrected.

## 15.10 Accessibility

**[assumed]** Every icon-only control carries an `aria-label`; the icon strip is a `nav` with a list; marks are `mark` elements with `aria-describedby` pointing at their comment; the contents tree is a `nav` with `aria-current` on the current section; focus order runs shell then page then right rail; the graph canvas is preceded by a visually hidden summary and is not the only route to any information. Contrast: every state text colour on its tint meets AA at 11px.

## Open questions

- The serif stack, pending a read of sitegen's `tokens.css`. **[deferred]**
- Whether the read view's right rail should push the text column or overlay it when comments appear. **[assumed]** Push, so the text never moves under the cursor while reading.
- Whether shell B's breadcrumb should be the document picker on node pages too. **[assumed]** No; it shows position and the picker moves into the page's context rail.
- Dark-mode values. **[deferred]**, derived from the light set in one file.
- Whether the graph inspector and the node page's right rail should be the same component. **[assumed]** Yes, with a compact variant.

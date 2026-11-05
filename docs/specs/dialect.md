# Dialect: the semantic HTML of fragments

A fragment is an HTML file with no page shell. It carries structure through a fixed vocabulary of elements, classes, and `data-` attributes. Everything visual (layout, colour, fonts, math rendering) belongs to the viewer. Interface version 1.

## 1. Envelope

**[decided]**

1. A fragment is a sequence of block elements; no `<html>`, `<head>`, `<body>`, `<script>`, `<style>`, `<link>`, `<iframe>`, or inline event handlers. A fragment containing any of these is invalid.
2. No external resources: images are `img` with `src` relative to the build directory (`svg/<hash>.svg`), or inline `svg`.
3. Encoding UTF-8. Void elements self-closed or not; both are valid.
4. Every block element that originates in source carries `data-src="FILE:START:END"` where `START` and `END` are character offsets in the file.

**[decided]** A **file's body** (manifest §1, `files`) is not a fragment, and the rules above do not bind it: it is a Markdown file drawn by the publisher, and it alone among published bodies may hold the HTML its author wrote. An annotation, a message, a page and an overview escape theirs (manifest §9, §10.1). A viewer inserts a body into its own page, which holds the write token (write-api §3), and agents write Markdown files, so a publisher writes that HTML back out through an allowlist, with every attribute value and run of text escaped, and never passes it through as written. The lists are `loom/src/loom/raw_html.py`:

- Kept: what an ordinary README uses (paragraphs and headings, lists, tables, `details`, `figure`, `img`, inline elements such as `kbd`, `sub` and `abbr`), with `audio`, `video` and `iframe`; `id`, `title`, `lang` and `dir` on any of them, and what each element needs (`colspan`, `open`, `alt`, `align`). A player always has `controls` and never `autoplay`.
- A URL is either relative, resolved against the shown files as Markdown's own are, or on a scheme for its use: `http`, `https`, `mailto`, `quilt`, `cited` or `app` for a link, `http` or `https` for anything fetched, and for an `img` also `data:` of a bitmap image. Any other URL is dropped.
- Never kept: a handler, `class`, `style`, `name`, and tags such as `script`, `style`, `svg`, `math`, `form`, `object`, `embed`, `base`, `meta` and the viewer's own landmarks (`nav`, `aside`, `main`).
- A refused tag shows as its own text, so nothing goes silently missing and a word in angle brackets stays a word. A refused attribute is dropped, and a comment is not shown.

**[decided]** An `<iframe>` in a file's body loads only an `https:` address on a named host, a protocol-relative one being taken as `https:`, and is otherwise shown as text. It keeps its `src`, `width`, `height` and the attributes any element may keep, and everything else about it is the publisher's: `sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms allow-presentation"`, so a player runs and the frame cannot navigate the viewer; `allow="fullscreen; encrypted-media; picture-in-picture"`; `allowfullscreen`; `referrerpolicy="strict-origin-when-cross-origin"`; `loading="lazy"`. It is written shut, so nothing after it is read as its contents. A viewer draws it at the column's width, in the shape its `width` and `height` name, at a fixed height where it names only `height`, and at 16:9 where it names neither.

**Open.** Any `https:` host is drawn, not a named list. An HTML file of the project can already embed anything from the frames origin, and a list would decide for a reader which sites may teach them, but a frame stands inside the viewer's own page where a page of an HTML file stands in a frame of its own.

## 2. Structure

### 2.1 Fragment kinds

**[decided]** The manifest says which kind a fragment is; the fragment itself carries `data-fragment="node|master|digest|canon"` on its first element as a courtesy, not as authority.

**[decided]** A **report's blocks** are marked in the message that carries it, not in a fragment of their own: in a transcript message's `body_html` (specs/manifest.md §10.1), each bracketed heading an agent wrote opens a `<section data-block="NAME">` holding the heading and what follows it, up to the next. `NAME` is the block's name without its brackets, and the heading shows that name, or what the agent wrote after the brackets. Anything before the first heading stands outside every section. A message with no bracketed heading has none.

### 2.2 Headings

**[decided]** Sectioning renders as `h1`–`h6` by level. A sectioning unit that is a node wraps its heading and own text in `section` with `id`, `data-id` (or `data-key` for untagged units) and `data-level`. Heading text may include a number in `span.number`.

```html
<section id="rl-0020" data-id="rl-0020" data-level="1" data-src="drafting/main.tex:1204:1298">
  <h1><span class="number">3</span> The residue map</h1>
  <p>We construct ...</p>
  <div class="include" data-key="rl-0011"></div>
</section>
```

**[decided]** Every element that is a node — `section`, `div.env`, `details.env-proof` — carries a real `id`, the element's `data-key` slugged by `[^A-Za-z0-9]+` to `-`, trimmed and lowercased, which is the rule display equations already use. It is the anchor a link into a document lands on; without it a fragment has no anchor targets and every in-document link dead-ends. Ids are unique within a fragment unless the document includes the same file twice, which is itself reported as `double-inclusion`.

### 2.3 Inclusions

**[decided]** In a node fragment, a child inclusion is `<div class="include" data-key="KEY"></div>`, empty; the viewer may expand it from the child's fragment or link it. In a master fragment, inclusions are expanded in place: the child's elements appear where the placeholder would be, wrapped in `div.included` with `data-key` and `data-file`.

### 2.4 Theorem-like environments

**[decided]**

```html
<div class="env env-lemma" id="rl-0004" data-id="rl-0004" data-key="rl-0004" data-taxon="Lemma"
     data-style="plain" data-src="nodes/rl-0004.tex:104:611">
  <p class="env-label"><span class="taxon">Lemma</span> <span class="number">3.4</span>
     <span class="title">(Residue independent of embedding)</span></p>
  <p>Let <span class="math inline">\(\iota\)</span> be ...</p>
</div>
```

Rules: the class `env-<taxon-slug>` uses the lowercased, hyphenated taxon (`env-lemma`, `env-main-theorem`); `data-taxon` carries the display name; `data-style` one of `plain`, `definition`, `remark`; `number` omitted when unknown; `title` omitted when absent. Untagged nodes have `data-key` only.

**[decided]** A node whose key names an id also carries `data-pair`, its key with any derived id made plain (`rl-0004` for `rl-0004-ai`), and `data-hash`, the `sha256:` hash compare pairs by: the node's own text with its display-name directives dropped and every derived label made plain. A landmark's environments carry the two as well, taken from the versions its stamp kept, and still no `data-key` or `data-id`, so no live wiring reaches them; a proof in a landmark takes the pair of the statement before it, `<statement>/proof`, then `/proof/2`.

### 2.5 Proofs

**[decided]**

```html
<details class="env env-proof" id="rl-0004-proof" data-key="rl-0004/proof" data-of="rl-0004"
         data-src="nodes/rl-0004.tex:612:1420" open>
  <summary class="env-label">Proof<span class="title"> of Theorem 3.4</span></summary>
  <p>...</p>
</details>
```

A labelled proof node carries `data-id` as well, and a proof of a statement with an id carries `data-pair` and `data-hash` as a statement does (2.4). `open` is a hint the viewer may ignore.

### 2.6 Paragraphs and inline markup

**[decided]** `p`; `em`, `strong`, `code`, `span.smallcaps`, `u`; `a.url[href]`; `span.footnote` containing the note text, with `data-n`; `blockquote`; `pre`, `code` for verbatim; `ul`, `ol`, `dl` with `li`, `dt`, `dd`; `hr`.

**[decided]** A paragraph whose only content is empty inline math and space — `$ $` on a line of its own, which LaTeX is given to start a list on the line after a theorem's heading — is not emitted: a list in HTML starts on its own line already, and drawn it was a blank line between the heading and the list (DR-317-ikmartin).

**[decided]** `\textcolor{NAME}{text}` in prose is `<span class="tex-color" data-color="NAME">text</span>`. The colour's LaTeX name travels as written, because a publisher cannot know a document's colour definitions and a viewer knows only the names it chooses to; a name the viewer does not know inherits the surrounding colour. Dropping the colour instead loses an author's own convention, and an author who writes `\red{...}` to mark unverified text means it to be visible.

### 2.7 Math

**[decided]** Inline: `<span class="math inline">\(...\)</span>`. Display: `<div class="math display" id="LABEL-ID" data-label="eq:main" data-number="3.2">\[...\]</div>`, the id being the qualified key slug. TeX is passed through inside, save for what the viewer's typesetter cannot read: `\label` is removed, `\ref` is replaced by its number or label, and a macro of the author's used inside a `\text{…}` is written between dollars (DR-130). The viewer renders it with the macro set from the manifest (plus a per-fragment set if the fragment's first element carries `data-macros="NAME"` naming a set in the manifest).

### 2.8 References and citations

**[decided]**

```html
<a class="ref" data-target="rl-0004" href="#rl-0004">Lemma 3.4</a>
<a class="ref ref-eq" data-target="rl-0004#eq:main" href="#rl-0004-eq-main">(3.2)</a>
<span class="cite" data-citekey="Man12" data-postnote="Theorem 4.1" data-target="Man12-thm-4.1">[Man12, Theorem 4.1]</span>
<a class="ref ref-dangling" data-target="rl-0099">??</a>
```

`href` values are hints for in-page anchors; the viewer resolves `data-target` through the manifest. `data-target` on `cite` is present only when a postnote resolved. A `cite`'s text is the label the compiled document prints for the key (`[GP99]` for `graber-pandharipande_LocalizationVirtualClasses1999` under an alphabetic style), or the citekey when no compile records one; `data-citekey` is always the key.

### 2.9 Marks

**[decided]** `<mark class="annotation" data-annotation="ID">...</mark>` around resolved quotes; `data-annotation` on a block with class `annotation-block` when a quote could not be located within converted markup; a viewer draws it as it draws a `mark.annotation`, by kind, severity and state. A block may carry several ids space-separated.

Review comparison fragments may mark changed prose with `<mark class="review-changed">`, a changed inline or display formula with the `review-changed` class on its math element, and a zero-width insertion or deletion with `<span class="review-change-point">`. These classes occur only in comparison fragments; ordinary reading fragments keep their original markup.

### 2.10 Incomplete markers

**[decided]** `<span class="incomplete" data-key="KEY">TEXT</span>` where the source had `\incomplete{TEXT}`.

### 2.11 Figures and diagrams

**[decided]** `figure` with optional `figcaption`; contents either `img[src]` (relative to the build directory) or inline `svg`. Diagrams from tikz are inline `svg` inside `figure.diagram`. Fallbacks are `figure.fallback` containing inline `svg` and `data-src-text` holding the original LaTeX.

### 2.12 Tables

**[decided]** `table`, `thead`, `tbody`, `tr`, `th`, `td`; cell content limited to inline markup and math. Anything else falls back.

### 2.13 Links

**[decided]** `<a href="quilt:KEY">` or `quilt:KEY#PLACE` names something the corpus itself owns by its fixed key (DR-268-ikmartin): `quilt:state` the research state (manifest §1, plan 0.21.3), a node, or any key it holds — a proof, a labelled equation — as the manifest's `keys` and `regions` write them; a document by its path, with a key it reaches after `#`; an annotation by its id; a session by its id; a project file the viewer shows (manifest §1, `files`) by its path with its suffix, percent-encoded, with a heading's `id` after `#` in a Markdown file or notebook, `page=N` in a PDF, or an anchor in an HTML page (`quilt:notes/day1.md#setup`). A `.tex` file is linked by its document or its keys, never as a file. A note, a quote among them, is linked by its id (`quilt:n-2026-11-02-0001`), and a viewer opens what it is on. It appears in annotation and message bodies, written in their Markdown as `[text](quilt:sh-0009)` or, with no text, `[](quilt:sh-0009)`, which a viewer names itself as a reader names the thing — `Theorem 3.1` — so the name follows a renumbering. A viewer opens what the link names and, for an annotation, opens what it is on with the annotation shown. A publisher refuses such a link from an agent when it names nothing a viewer shows; a viewer shows a key it does not know as the key.

**[decided]** **Links into cited works.** `<a href="cited:SCHEME:VALUE?page=N&quote=TEXT">` names a place in a cited work by its global identifier — `SCHEME` one of `doi`, `arxiv`, `mr`, `zbl`, compared case-insensitively, and `VALUE` as the manifest's `works` writes it — never by a citekey, so a link survives a bibliography re-export and means the same thing in a collaborator's corpus. It appears in annotation and message bodies, written in their Markdown as `[text](cited:arxiv:0805.2065v2?page=9)`. The keys are the viewer's own place keys: `page` is 1-based; `quote` is URL-encoded text to look for, on `page` when one is given and across the work when not; `result` names one of the work's results by its digest node's id, and with no `page` opens at that result's page. The same keys after `#` are read too. A viewer resolves the identifier through the manifest's references and opens a fetched copy only when it is filed under that identifier (DR-123).

**[decided]** **Links to applications** (plan 0.22.7). `<a href="app:NAME">` asks the publisher to open the application `NAME` on this machine (`write-api.md`, `open`), on the reader's click; a viewer with no publisher to ask leaves it unfollowed and says why. A link in any other scheme a viewer does not read (`zotero:`, `vscode:`, `https:` to another site) opens outside the viewer, never in its tab, and `javascript:`, `data:`, `file:`, `vbscript:` and `blob:` are never followed.

### 2.14 Task items

**[decided]** A list item of a project's Markdown file or a notebook's Markdown cell whose words open with `[ ] ` or `[x] ` is `<li class="task" data-done="false">`, or `data-done="true"`, with the box taken out of its words. In a Markdown file it also carries `data-task="LINE:HASH"`, its 1-based source line and a hash of that line less its box, which a tick sends back (`write-api.md`, `file-tick`) and which refuses a line that has since changed. A viewer draws the box: one that cannot write, or an item with no `data-task`, draws a box that cannot be changed. Annotations, messages and pages keep the brackets as text.

## 3. Forbidden

**[decided]** Scripts, styles, external stylesheets or fonts, iframes, forms, inline event attributes, absolute URLs except in `a.url`, and any element or class not listed here. A viewer must ignore unknown classes and render unknown elements as generic blocks; a validator must reject them. The ban is on fragments and on every body a publisher draws except a Markdown file's, which §1 governs: a frame belongs to a project's HTML file shown as a file (`write-api.md` §3) or to a Markdown file that embeds one, never to rendered mathematics, a note or a message.

## 4. Validation

**[decided]** The workspace provides `specs/tools/validate-dialect.py` (a small standalone script, not shared code in the sense of P11 since it is a test tool consumed by both codebases) that checks a fragment against sections 1–3: the envelope, the allowed elements, classes, and attributes, `data-src` on blocks, and the forbidden elements. Each codebase's test suite vendors it (loom at `tests/tools/`, arras through the fixture check); `refresh-fixture.sh` runs it on every regenerated fragment (settled at M2).

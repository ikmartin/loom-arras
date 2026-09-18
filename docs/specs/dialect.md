# Dialect: the semantic HTML of fragments

A fragment is an HTML file with no page shell. It carries structure through a fixed vocabulary of elements, classes, and `data-` attributes. Everything visual (layout, colour, fonts, math rendering) belongs to the viewer. Interface version 1.

## 1. Envelope

**[decided]**

1. A fragment is a sequence of block elements; no `<html>`, `<head>`, `<body>`, `<script>`, `<style>`, `<link>`, `<iframe>`, or inline event handlers. A fragment containing any of these is invalid.
2. No external resources: images are `img` with `src` relative to the build directory (`svg/<hash>.svg`), or inline `svg`.
3. Encoding UTF-8. Void elements self-closed or not; both are valid.
4. Every block element that originates in source carries `data-src="FILE:START:END"` where `START` and `END` are character offsets in the file.

## 2. Structure

### 2.1 Fragment kinds

**[decided]** The manifest says which kind a fragment is; the fragment itself carries `data-fragment="node|master|digest|canon|report"` on its first element as a courtesy, not as authority.

**[decided]** A **report** fragment is an agent's notes file rendered: `<section data-fragment="report" data-run="RUN">` holding one `<section data-block="NAME">` per bracketed heading the agent wrote, in order, with an unnamed leading section for anything before the first heading. `NAME` is the block's name without its brackets. A finding — any element ending in an annotation's id — carries `id="finding-<id>"` and `data-annotation-id="<id>"`, so a viewer can scroll to it and highlight the annotation's quote in the document beside it. Every element carries `data-src` into the notes file as usual, because a report originates in a file like anything else loom publishes. A notes file with no bracketed heading is one unnamed section, which is a report that could not be parsed rather than an error.

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

### 2.5 Proofs

**[decided]**

```html
<details class="env env-proof" id="rl-0004-proof" data-key="rl-0004/proof" data-of="rl-0004"
         data-src="nodes/rl-0004.tex:612:1420" open>
  <summary class="env-label">Proof<span class="title"> of Theorem 3.4</span></summary>
  <p>...</p>
</details>
```

A labelled proof node carries `data-id` as well. `open` is a hint the viewer may ignore.

### 2.6 Paragraphs and inline markup

**[decided]** `p`; `em`, `strong`, `code`, `span.smallcaps`, `u`; `a.url[href]`; `span.footnote` containing the note text, with `data-n`; `blockquote`; `pre`, `code` for verbatim; `ul`, `ol`, `dl` with `li`, `dt`, `dd`; `hr`.

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

`href` values are hints for in-page anchors; the viewer resolves `data-target` through the manifest. `data-target` on `cite` is present only when a postnote resolved.

### 2.9 Marks

**[decided]** `<mark class="annotation" data-annotation="ID">...</mark>` around resolved quotes; `data-annotation` on a block with class `annotation-block` when a quote could not be located within converted markup. A block may carry several ids space-separated.

### 2.10 Incomplete markers

**[decided]** `<span class="incomplete" data-key="KEY">TEXT</span>` where the source had `\incomplete{TEXT}`.

### 2.11 Figures and diagrams

**[decided]** `figure` with optional `figcaption`; contents either `img[src]` (relative to the build directory) or inline `svg`. Diagrams from tikz are inline `svg` inside `figure.diagram`. Fallbacks are `figure.fallback` containing inline `svg` and `data-src-text` holding the original LaTeX.

### 2.12 Tables

**[decided]** `table`, `thead`, `tbody`, `tr`, `th`, `td`; cell content limited to inline markup and math. Anything else falls back.

### 2.13 Links into cited works

**[decided]** `<a href="cited:SCHEME:VALUE#page=N">` or `#quote=TEXT` names a place in a cited work by its global identifier — `SCHEME` one of `doi`, `arxiv`, `mr`, `zbl`, compared case-insensitively, and `VALUE` as the manifest's `works` writes it — never by a citekey, so a link survives a bibliography re-export and means the same thing in a collaborator's corpus. It appears in annotation and message bodies, written in their Markdown as `[text](cited:arxiv:0805.2065v2#page=9)`. `page` is 1-based; `quote` is URL-encoded text to look for. A viewer resolves the identifier through the manifest's references and opens a fetched copy only when it is filed under that identifier (DR-123).

## 3. Forbidden

**[decided]** Scripts, styles, external stylesheets or fonts, iframes, forms, inline event attributes, absolute URLs except in `a.url`, and any element or class not listed here. A viewer must ignore unknown classes and render unknown elements as generic blocks; a validator must reject them.

## 4. Validation

**[decided]** The workspace provides `specs/tools/validate-dialect.py` (a small standalone script, not shared code in the sense of P11 since it is a test tool consumed by both repositories) that checks a fragment against sections 1–3: the envelope, the allowed elements, classes, and attributes, `data-src` on blocks, and the forbidden elements. Each tool's test suite vendors it (loom at `tests/tools/`, arras through the fixture check); `refresh-fixture.sh` runs it on every regenerated fragment (settled at M2).

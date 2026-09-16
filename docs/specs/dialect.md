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

**[decided]** The manifest says which kind a fragment is; the fragment itself carries `data-fragment="node|master|digest"` on its first element as a courtesy, not as authority.

### 2.2 Headings

**[decided]** Sectioning renders as `h1`–`h6` by level. A sectioning unit that is a node wraps its heading and own text in `section` with `data-id` (or `data-key` for untagged units) and `data-level`. Heading text may include a number in `span.number`.

```html
<section data-id="rl-0020" data-level="1" data-src="drafts/main.tex:1204:1298">
  <h1><span class="number">3</span> The residue map</h1>
  <p>We construct ...</p>
  <div class="include" data-key="rl-0011"></div>
</section>
```

### 2.3 Inclusions

**[decided]** In a node fragment, a child inclusion is `<div class="include" data-key="KEY"></div>`, empty; the viewer may expand it from the child's fragment or link it. In a master fragment, inclusions are expanded in place: the child's elements appear where the placeholder would be, wrapped in `div.included` with `data-key` and `data-file`.

### 2.4 Theorem-like environments

**[decided]**

```html
<div class="env env-lemma" data-id="rl-0004" data-key="rl-0004" data-taxon="Lemma"
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
<details class="env env-proof" data-key="rl-0004/proof" data-of="rl-0004"
         data-src="nodes/rl-0004.tex:612:1420" open>
  <summary class="env-label">Proof<span class="title"> of Theorem 3.4</span></summary>
  <p>...</p>
</details>
```

A labelled proof node carries `data-id` as well. `open` is a hint the viewer may ignore.

### 2.6 Paragraphs and inline markup

**[decided]** `p`; `em`, `strong`, `code`, `span.smallcaps`, `u`; `a.url[href]`; `span.footnote` containing the note text, with `data-n`; `blockquote`; `pre`, `code` for verbatim; `ul`, `ol`, `dl` with `li`, `dt`, `dd`; `hr`.

### 2.7 Math

**[decided]** Inline: `<span class="math inline">\(...\)</span>`. Display: `<div class="math display" id="LABEL-ID" data-label="eq:main" data-number="3.2">\[...\]</div>`, the id being the qualified key slug. TeX is passed through verbatim inside; the viewer renders it with the macro set from the manifest (plus a per-fragment set if the fragment's first element carries `data-macros="NAME"` naming a set in the manifest).

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

## 3. Forbidden

**[decided]** Scripts, styles, external stylesheets or fonts, iframes, forms, inline event attributes, absolute URLs except in `a.url`, and any element or class not listed here. A viewer must ignore unknown classes and render unknown elements as generic blocks; a validator must reject them.

## 4. Validation

**[decided]** The workspace provides `specs/tools/validate-dialect.py` (a small standalone script, not shared code in the sense of P11 since it is a test tool consumed by both repositories) that checks a fragment against sections 1–3: the envelope, the allowed elements, classes, and attributes, `data-src` on blocks, and the forbidden elements. Each tool's test suite vendors it (loom at `tests/tools/`, arras through the fixture check); `refresh-fixture.sh` runs it on every regenerated fragment (settled at M2).

## Open questions

- Whether footnotes should be `span.footnote` inline or collected at the end. **[assumed]** Inline; the viewer decides placement.
- Whether `data-src` should include the master path for expanded inclusions in master fragments. **[decided]** Yes, `data-file` on `div.included` plus each element's own `data-src`.
- Whether to permit a `nav.toc` block in master fragments. **[assumed]** No; the viewer builds a table of contents from headings.

# 9. Build and interface

This chapter specifies what loom produces for a viewer and how. The product boundary (P11) is a directory: loom writes `build/`, arras reads it, and the two share no code. The normative definitions of what is in that directory are the specification files in `specs/`; this chapter says how loom fills it, what the LaTeX-to-HTML converter promises, how numbering is obtained, and what `loom serve` does. It also names the two deferred specifications, the write API and the runner contract.

## 9.1 `loom build`

**[decided]** `loom build` scans the quilt, derives files, renders fragments, and publishes the build directory. It is run explicitly, and by `loom serve` on every source change. Steps, in order:

1. Scan: read every file per Chapter 5, producing nodes, keys, regions, edges, inclusion trees, diagnostics.
2. Read records: the ledger, snapshots, every review record; compute states, causes, facts (Chapter 7).
3. Read numbering: for every master, the `.aux` in `build/<master-stem>/` if present, else beside the master, else nothing (9.6).
4. Derive: per-key statement and proof files (9.7), bundles on demand.
5. Render: each node's own text and each master's expanded text to a fragment in the dialect (9.3, 9.4); each SVG needed by fallbacks and diagrams; annotation marks placed (9.5).
6. Write the manifest.
7. Publish atomically (9.2.2).

`loom build --keys KEY...` limits rendering to the fragments those keys affect (and their masters); the manifest is always complete. **[assumed]** Rendering is cached by content hash so a full build after a one-line edit renders one fragment and its masters.

## 9.2 The build directory

### 9.2.1 Layout

**[decided]**

```
build/
  manifest.json              the manifest (specs/manifest.md)
  fragments/
    nodes/<id>.html          one per node with an id
    keys/<qualified>.html    one per unlabelled node, by qualified key (URL-encoded)
    masters/<stem>.html      one per master, expanded, with marks
    digests/<citekey>.html   one per digest file, its outline expanded
  svg/<hash>.svg             rendered fallbacks and diagrams, content-addressed
  derived/
    <id>.statement.tex       statement only, for \transcludestatement-style use later
    <id>.proof.tex, <id>.proof.2.tex
  bundles/<key>.tex          written by loom bundle
  <master-stem>/             latexmk output directory per master (.aux, .pdf, .log)
  cache/                     converter and render caches
```

Everything under `build/` is derivable and gitignored. Deleting it and running `loom build` reproduces it.

### 9.2.2 Atomic publish

**[decided]** A viewer must never read a half-written state. Loom writes fragments and SVGs to `build/.staging/`, moves each into place, and writes `manifest.json` last, by writing `manifest.json.tmp` and renaming. Arras's only trigger is the manifest changing (10.7), so a new manifest always refers to fragments that already exist.

## 9.3 Fragments

**[decided]** A fragment is one HTML file in the dialect (`specs/dialect.md`) with no page shell: no `<html>`, `<head>`, `<body>`, stylesheet, or script. Three kinds:

1. Node fragment: the node's own text rendered, with each child inclusion replaced by a placeholder element `<div class="include" data-key="..."></div>` that the viewer may expand or link. Statement and proofs are separate top-level elements so a page can show or collapse proofs.
2. Master fragment: the master's full document rendered with every inclusion expanded in place, sectioning as headings at their shifted levels, every node wrapped in its `env` element with `data-id`, numbers from the `.aux` written into the labels, and annotation marks placed. This is the master view; arras assembles nothing.
3. Digest fragment: the digest file rendered as a document, the same way.

**[decided]** Every element that comes from a source region carries `data-src` giving the file, start offset, and end offset (9.5), which is what makes marks and future editors possible.

## 9.4 The LaTeX contract of the converter

Without pandoc (a decided constraint), loom's converter is a restricted translator with an exact fallback. The subset it converts is the contract; anything outside it renders exactly but as an image.

### 9.4.1 Converted constructs

**[decided]** In own text (statements, proofs, master prose, digest overviews):

- Paragraphs (blank-line separated), `\par`.
- Sectioning commands to headings `h1`–`h6` by level after shifts, with `data-id` and the number.
- `\emph`, `\textit`, `\textbf`, `\texttt`, `\textsc`, `\underline`, `\footnote` (rendered as a sidenote element), `\url`, `\href`.
- `itemize`, `enumerate`, `description`, with `\item` and optional labels.
- Inline math `$...$`, `\(...\)`; display math `\[...\]`, `equation`, `equation*`, `align`, `align*`, `gather`, `multline`, `split` inside them: passed through as TeX inside `<span class="math inline">` / `<div class="math display">` for MathJax, with `\label` inside display math turned into an `id` and a `data-label` on the div, and the number from the `.aux` attached.
- Theorem-like environments to `div.env.env-<taxon-slug>` with the label element, title, `data-id`, `data-key`, style class; `proof` to `details.env.env-proof` with a summary.
- `\ref`, `\eqref`, `\cref`, `\autoref`, `\pageref` to `a.ref` with `data-target` (an id or qualified key) and the number as text; `\cite` to `span.cite` with `data-citekey`, `data-postnote`, and `data-target` when a postnote resolved.
- `\uses` and `\incomplete`: `\uses` renders nothing (the manifest carries the edges); `\incomplete` renders `span.incomplete` with the text.
- `\includegraphics` to `img` with the file copied under `build/svg/` (PDF figures converted to SVG with `dvisvgm` via a standalone wrapper, **[assumed]**; PNG and JPEG copied).
- `tikzcd`, `tikzpicture`, and `\begin{center}` wrappers around them to inline SVG (the sitegen `tikz.py` route: standalone class, `latex`, `dvisvgm --no-fonts --exact-bbox`, ids namespaced, width in em).
- `tabular` and `array` to `table` for simple cell content; complex tables fall back.
- `verbatim`, `lstlisting`, `\verb` to `pre`/`code`.
- Text-mode macros without arguments defined in the preamble closure are expanded (`\newcommand{\Res}{\mathrm{Res}}` is a math macro and is left to MathJax; `\newcommand{\GW}{Gromov--Witten}` in text is expanded).
- Common ligatures and punctuation: `--`, `---`, `` ` `` and `'` quotes, `~`, `\,`, `\ `.

### 9.4.2 Fallback

**[decided]** Any block the converter cannot handle (an unknown environment, a text-mode macro with arguments, a `\parbox`, a complex table, anything that fails to parse) is rendered exactly as SVG through the standalone route and emitted as `figure.fallback` with the source text in a `data-src-text` attribute and a diagnostic `loom:converter-fallback` (info) naming the construct. The fallback is per block, never per fragment: the rest of the fragment converts normally.

### 9.4.3 Math and macros

**[decided]** Math is left as TeX. The manifest carries a macro set extracted from the preamble closure by the `macros.py` parser (`\newcommand`, `\renewcommand`, `\providecommand`, `\DeclareMathOperator`, zero-argument `\def`), plus per-fragment macro sets for digests with macro blocks. Arras configures MathJax from the manifest. **[assumed]** MathJax 3; KaTeX is a later option and the manifest's macro format is the same for both (name, argument count, body).

### 9.4.4 What the converter promises

**[decided]** For any quilt that compiles: every fragment is produced; every construct outside the contract is rendered exactly by fallback; nothing is silently dropped; and every element from source carries `data-src`. The converter does not promise that a fragment is beautiful; it promises that it is complete and honest.

## 9.5 Annotation marks

**[decided]** For every non-discarded annotation with a selector, loom resolves the selector against the target's current own text (7.5.2), obtains a source span, finds the fragment block(s) whose `data-src` cover the span, and searches the quote inside those blocks' rendered text. If found, it wraps the matched text in `<mark class="annotation" data-annotation="ID">`; if the quote crosses converted markup and cannot be located, the whole block gets `data-annotation` and a class `annotation-block`. Detached annotations get no mark; the manifest lists them.

Marks are placed in node fragments and in master fragments (where the node appears expanded).

## 9.6 Numbering

**[decided]** Loom never computes theorem or section numbers. After `loom compile MASTER`, `build/<stem>/<stem>.aux` contains `\newlabel{ID}{{NUMBER}{PAGE}...}` for every id and alias; the scanner reads number and page for each and stores them per master in the manifest. Equations get their numbers the same way. Before the first compile, numbers are absent; arras shows ids alone and the panel says "not yet compiled". `loom build` compiles nothing; `loom check` and `loom compile` do. **[assumed]** `loom serve` compiles the default master when its source changes, after publishing, so numbers refresh within one cycle; the fragment build does not wait for LaTeX.

hyperref's `.aux` format (`\newlabel{ID}{{NUMBER}{PAGE}{TITLE}{ANCHOR}{}}`) and the plain format are both read.

## 9.7 Derived files and bundles

**[decided]** `build/derived/<id>.statement.tex` and `<id>.proof.tex` are the node's statement region and each proof region alone, written by `loom build`, so that a future `\transcludestatement`-style macro or an external tool can input them. **[assumed]** Not used by any MVP command besides `bundle`.

**[decided]** `loom bundle KEY [--to FILE]` writes `build/bundles/<key>.tex`: the master's preamble closure (verbatim, with `\usepackage{loom}` present), a `\begin{document}`, a heading "Bundle for KEY", the statements of the closure in dependency order (each with its environment, id label, and, for digest nodes, its macro block group), then the key's own region (a statement, or a statement and the proof) with inclusions expanded, then `\end{document}`. With the `bundle` note, every theorem's number is followed by its id in small type: **[assumed]** implemented by a `\loombundle` switch inside `loom.sty` that redefines `\@thmcounter` display; if this proves fragile, a comment with the id after each `\begin` line suffices for readers.

`loom bundle KEY --with FILE` builds the same bundle with a proposed diff applied or a substitute file in place of the key's text, and `loom bundle --draft FILE` builds one for a not-yet-promoted node from its `\ref`s and `\uses`; neither touches the quilt, and both exist so that an agent's proposal or draft can be compiled before a person promotes it. `loom compile KEY` compiles the bundle. A bundle that fails to compile or reads incomplete is the operational failure of self-containedness and is reported as `loom:bundle-failed` with the LaTeX log's first error.

## 9.8 `loom serve`

**[decided]** One loop with three jobs:

1. Watch: poll mtimes of every scanned file, `config.toml`, the ledger, snapshots, and review records every second (as sitegen does); on change, run `loom build` for the affected keys (the changed file's nodes, their masters, and any fragment whose marks depend on a changed record), then publish.
2. Serve: a static HTTP server on `localhost:<port>` (default 8791, **[assumed]**) serving the arras bundle at `/` and `build/` at `/build/`. The arras bundle is located from the `arras` pip package's installed assets.
3. Compile: after publishing, if the changed file is reached by the default master, run `loom compile` on it in the background so numbers refresh.

**[decided]** Loom never notifies arras. Arras polls `/build/manifest.json` and re-renders when its hash changes (10.7). If watching proves too slow, the fallback is a `POST /_refresh` endpoint arras may call carrying nothing but "refresh", which preserves arras's ignorance of event types; **[deferred]** and not built unless needed.

`loom serve --no-compile` skips step 3; `--port`; `--open` opens the browser.

## 9.9 The interface files

The normative interface is `specs/`:

- `specs/dialect.md`: the HTML dialect of fragments.
- `specs/manifest.md`: the manifest schema.
- `specs/diagnostics.md`: diagnostic codes, reserved and namespaced.
- `specs/fixture.md`: the conformance fixture.
- `specs/write-api.md` and `specs/runner.md`: deferred; specified so the CLI is designed with them in mind.

Every manifest carries `interface_version`. Loom and arras each declare the versions they produce and accept; a mismatch is reported by arras on its problems page (10.5), never silently.

## 9.10 Sitegen as a second publisher

**[decided]** The author's org-mode site generator becomes a publisher by emitting fragments in the dialect and a manifest, and dropping its own templates, link rewriting, backlinks, and search. Its `export.el` already emits most of the dialect's classes; the additions are `data-id`, `data-key`, `data-src`, the manifest, and the reserved diagnostics. This is not part of the MVP; it is the test that the interface is generic and the reason arras must never know what a proof is.

## Open questions

- The exact `data-src` encoding (file, start, end as characters or bytes). **[deferred]**; characters, UTF-8 file offsets recorded alongside.
- Whether PDF figures should be converted to SVG at build or served as PDF objects. **[assumed]** Converted.
- Port number and whether `serve` should choose a free port. **[assumed]** Fixed default, `--port` to change, fail if busy.
- Whether `loom build` should compile the default master when no `.aux` exists at all. **[assumed]** No; `loom check` or `loom compile` does, and the panel says "not yet compiled".
- The bundle id-beside-number mechanism. **[deferred]** to implementation, with the comment-based fallback stated.

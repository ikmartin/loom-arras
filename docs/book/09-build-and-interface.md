# 9. Build and interface

This chapter specifies what loom produces for a viewer and how. The product boundary (P11) is a directory: loom writes `build/`, arras reads it, and the two share no code. The normative definitions of what is in that directory are the specification files in `specs/`; this chapter says how loom fills it, what the LaTeX-to-HTML converter promises, how numbering is obtained, and what `loom serve` does. It also names the two deferred specifications, the write API and the runner contract.

## 9.1 `loom build`

**[decided]** `loom build` scans the quilt, derives files, renders fragments, and publishes the build directory. It is run explicitly, and by `loom serve` on every source change. Steps, in order:

1. Scan: read every file per Chapter 5, producing nodes, keys, regions, edges, inclusion trees, diagnostics.
2. Read records: the ledger, snapshots, every review record; compute states, causes, facts (Chapter 7).
3. Read numbering: for every master, the `.aux` in `build/<master-stem>/` if present, else beside the master, else nothing (9.6).
4. Derive: per-key statement and proof files (9.7), bundles on demand.
5. Render: each node's own text, each master's expanded text, each digest file, and each canon document to a fragment in the dialect (9.3, 9.4); each SVG needed by fallbacks and diagrams; each graphic published under `build/svg/`; annotation marks placed (9.5).
6. Write the manifest.
7. Publish atomically (9.2.2).

`loom build --keys KEY...` limits rendering to those keys, their proofs, and the masters that reach them; the manifest is always complete. Exit status is 1 when any error-severity diagnostic exists, and the build is published all the same. **[decided]** Rendering is cached by an input hash per fragment (loom's version, the text of every file the fragment draws on, the numbering, and the marks it carries), recorded in `build/cache/fragments.json`, so a build after a one-line edit renders one node fragment and its masters (M2: two fragments re-rendered after an edit to a node). **[decided]** A loom whose version says `dev` hashes its own rendering code as well, since a checkout's version does not move between edits and a changed converter would otherwise leave the HTML it was meant to replace on disk; the code is read once per process, and `loom build --force` renders everything regardless (DR-131).

## 9.2 The build directory

### 9.2.1 Layout

**[decided]**

```
build/
  manifest.json              the manifest (specs/manifest.md)
  fragments/
    nodes/<id>.html          one per node with an id (labelled proofs included)
    keys/<qualified>.html    one per unlabelled node, by qualified key (URL-encoded)
    masters/<stem>.html      one per master, expanded, with marks
    digests/<citekey>.html   one per digest file, rendered as a document
    canon/<stem>.html        one per canon document, rendered as a document (17.1)
  svg/<hash>.<ext>           graphics from \includegraphics, content-addressed (PDF converted to SVG; PNG, JPEG, SVG copied)
  diffs/                     the unified diffs behind stale causes, written when the records are applied (7.5)
  derived/
    <id>.statement.tex       statement only, for \transcludestatement-style use later
    <id>.proof.tex, <id>.proof.2.tex
  bundles/<key>.tex          the closure document loom compile KEY runs latexmk on
  <master-stem>/             latexmk output directory per master (.aux, .pdf, .log)
  cache/                     fragments.json (the render index) and svg/ (fallback and diagram SVGs by content hash)
```

Fallback and diagram SVGs are inlined into their fragments (specs/dialect.md §2.11) and cached under `cache/svg/`; `svg/` holds only the published graphics. Everything under `build/` is derivable and gitignored. Deleting it and running `loom build` reproduces it.

### 9.2.2 Atomic publish

**[decided]** A viewer must never read a half-written state. Loom writes every fragment and asset by writing `<name>.tmp` beside it and renaming it into place, removes fragments the manifest no longer names, and writes `manifest.json` last the same way (`manifest.json.tmp`, then rename). Arras's only trigger is the manifest changing (10.5), so a new manifest always refers to fragments that already exist.

## 9.3 Fragments

**[decided]** A fragment is one HTML file in the dialect (`specs/dialect.md`) with no page shell: no `<html>`, `<head>`, `<body>`, stylesheet, or script. Its first element carries `data-fragment="node|master|digest|canon"` as a courtesy. Four kinds:

1. Node fragment: the node's own text rendered, with each child inclusion replaced by a placeholder element `<div class="include" data-key="..."></div>` that the viewer may expand or link. Statement (`div.env`) and proofs (`details.env-proof`) are separate top-level elements so a page can show or collapse proofs; a digest node's element carries `data-macros` naming its citekey's macro set (DR-56).
2. Master fragment: an `h1` with the master's `\title`, then the master's full document rendered with every inclusion expanded in place inside `div.included`, sectioning as headings at their shifted levels, every node wrapped in its `env` element with `data-id`, numbers from the `.aux` written into the labels, and annotation marks placed. This is the master view; arras assembles nothing. A master's preamble yields no fragment content (M2).
3. Digest fragment: the digest file rendered as a document, starting after its `% !LOOM end macros` line: the macro block is loaded around every statement that needs it and is never rendered as text (DR-80).
4. Canon fragment: a landmark (17.1) rendered as a document. It carries no identity at all — every theorem-like environment is a plain `div.env` with a taxon and a style and no `data-id` or `data-key`, because nothing in a landmark is a node — no marks and no numbers loom did not compile itself. Its own labels become element ids and its own references become in-page links, so a landmark reads as the self-contained document it is. Its first element carries `data-macros="canon:<stem>"` when its preamble's macros differ from the corpus's: a landmark renders with the macros it compiled with, whatever the drafting documents have since become.

**[decided]** Every element that comes from a source region carries `data-src="FILE:START:END"`, `START` and `END` being character offsets into the file (specs/dialect.md §1; 9.5), which is what makes marks and future editors possible.

## 9.4 The LaTeX contract of the converter

Without pandoc (a decided constraint), loom's converter is a restricted translator with an exact fallback. The subset it converts is the contract; anything outside it renders exactly but as an image.

### 9.4.1 Converted constructs

**[decided]** In own text (statements, proofs, master prose, digest overviews):

- Paragraphs (blank-line separated), `\par`; `\\` to `br`.
- Sectioning commands to headings `h1`–`h6` by level after shifts, with `data-id` and the number.
- `\emph`, `\textit`, `\textbf`, `\texttt`, `\textsc`, `\underline`, `\footnote` (rendered inline as `span.footnote` with `data-n`; the viewer decides placement), `\url`, `\href`. `\textcolor` and `\color` render their content and drop the colour, since the dialect has no colour element (M2).
- `itemize`, `enumerate`, `description`, and the paralist and enumitem variants (`compactitem`, `inparaenum`, and so on), with `\item` and optional labels.
- Inline math `$...$`, `\(...\)`; display math `\[...\]`, `equation`, `equation*`, `align`, `align*`, `gather`, `multline`, `split` inside them: passed through as TeX inside `<span class="math inline">` / `<div class="math display">` for MathJax, with `\label` inside display math turned into an `id` and a `data-label` on the div, the number from the `.aux` attached as `data-number` and as a `\tag`, and `\ref` inside math replaced by its number or label so MathJax never sees it. A comment inside a formula is removed before the TeX is published, since MathJax reads `%` to the end of the line as TeX does and a commented-out line of an `align` otherwise swallows the `\end` after it, and a commented-out `\label` is not the block's number; `\qedhere` is dropped, the viewer having no tombstone to move. A macro of the author's used inside a `\text{…}` is written between dollars — `\text{nodes of $\ul C$}` for `\text{nodes of \ul C}` — because LaTeX lets such a macro open math itself where the viewer's text mode has no `\underline` and refuses the whole formula (DR-130).
- Theorem-like environments to `div.env.env-<taxon-slug>` with the label element, title, `data-id`, `data-key`, style class; `proof` to `details.env.env-proof` with a summary.
- `\ref`, `\eqref`, `\cref`, `\Cref`, `\autoref`, `\pageref`, `\vref` to `a.ref` with `data-target` (an id or qualified key) and the number as text, a label no node carries becoming `a.ref.ref-dangling` reading `??`; `\cite` and its natbib and biblatex variants to `span.cite` with `data-citekey`, `data-postnote`, and `data-target` when a postnote resolved, reading as the compiled paper prints it — `[GP99, Theorem 1]` — from the label the master's `.aux` (`\bibcite`) or `.bbl` (biblatex's `labelalpha`) records, and as the citekey before a compile or under a numeric biblatex style, which records no label.
- `\uses` and `\incomplete`: `\uses` renders nothing (the manifest carries the edges); `\incomplete` renders `span.incomplete` with the text.
- `\includegraphics` to `figure > img` with the file published under `build/svg/` by content hash: **[decided]** PDF figures are converted to SVG with `pdftocairo -svg`, or with `dvisvgm --pdf` when pdftocairo is absent; PNG, JPEG, and SVG are copied (M2: the fixture's PDF figure).
- `tikzcd`, `tikzpicture`, `xy`, and `xymatrix` to inline SVG in `figure.diagram` (the sitegen `tikz.py` route: standalone class, `latex`, `dvisvgm --no-fonts --exact-bbox`, ids namespaced, width in em). `center` and the other layout containers (`flushleft`, `small`, `minipage`, beamer's `frame`, ...) render their contents transparently; `quote`, `quotation`, and `abstract` become `blockquote`.
- `tabular`, `array`, and `longtable` to `table` when every cell is inline content; a table using `\multicolumn`, `\multirow`, `\cline`, `\cmidrule`, `\parbox`, or a nested environment falls back.
- `verbatim`, `lstlisting`, `\verb` to `pre`/`code`.
- Text-mode macros defined in the default master's preamble closure, aliases included (DR-73), are expanded with their arguments and the expansion converted; an expansion that is plainly math (`\mathrm`, `\frac`, `^`, `_`, ... with no `$`) becomes inline math, so `\newcommand{\Res}{\mathrm{Res}}` reaches MathJax and `\newcommand{\GW}{Gromov--Witten}` reaches the text.
- Definitions (`\newcommand`, `\def`, `\let`, `\newtheorem`, `\newenvironment`, ...) and layout commands (`\vspace`, `\noindent`, `\frametitle`, `\title`, ...) render nothing; `\iffalse ... \fi` is skipped.
- Common ligatures and punctuation: `--`, `---`, `` ` `` and `'` quotes, `~`, `\,`, `\ `, accents, and the usual text symbols.

### 9.4.2 Fallback

**[decided]** Any block the converter cannot handle (an unknown environment, a paragraph using a command the closure does not define, a `\parbox`, a complex table, anything that fails to parse) is rendered exactly as SVG through the standalone route and emitted as `figure.fallback` with the source text in a `data-src-text` attribute and a diagnostic `loom:converter-fallback` (info) naming the construct and the key. The fallback is per block, never per fragment: the rest of the fragment converts normally. A theorem-like environment or proof written inline in a container is **not** a fallback case: it converts to `div.env` (or `details.env.env-proof`) with the markup a node fragment carries, minus the node identity (DR-86). A block that cannot be compiled keeps its source in a `pre` and carries `data-error`, so it is reported as a fault rather than read as the paper's text, and the failure is remembered in the cache so a later build does not pay for it again (DR-85).

**[decided]** How the fallback document is built (DR-79): the block is compiled in `standalone` (`dvisvgm` option, 2 pt border) from a scratch directory with the quilt root first on `TEXINPUTS`, so `loom.sty`, `preamble.tex`, and the author's `.sty` files load as the master loads them. The preamble is the reaching master's own text before `\begin{document}` (never the closure's concatenation, which would define every macro twice), with `\documentclass`, comment lines, and the page-layout packages (`geometry`, `microtype`, `fancyhdr`, `titlesec`, `setspace`, `lineno`) removed, `\title`, `\author`, and their kin gobbled with loom's own `\loomgobble` (never `\@gobble`: a preamble that loads xypic through `\input xy` leaves `@` an ordinary character, and every compile then dies on the gobbler), `amsmath` and `amsthm` supplied when the preamble does not load them and the stripped class would have, `\bibname` and its kin provided for the same reason (DR-84), `geometry` passed `pass` and `microtype` told not to protrude in case an `\input` preamble loads them, the whole wrapped in `\makeatletter`/`\makeatother`. The body sits in a 16 cm `minipage`, so lists and displays are allowed and dvisvgm crops to the ink; `latex` runs twice, then `dvisvgm --no-fonts --exact-bbox`. A node the default master reaches uses that master's preamble, another node its first reaching master's, a loose node (a digest's) the default master's. A digest statement's document also carries the digest's macro block and the packages its header requires that the preamble lacks. Three attempts are made: as described, then without the added packages, then with a minimal preamble (`amsmath`, `amssymb`, `amsthm`, `tikz` with `cd`) plus the macro block. When every attempt fails, the figure is emitted as `figure.fallback.failed` holding the source in a `pre`, and `loom:converter-fallback` is raised to a warning naming the node and every attempt's first error; `LOOM_SVG_KEEP=DIR` keeps the failing documents and logs for inspection (M7: 33 blocks of the migrated paper failed until each part of this was fixed; none fail now). Results are cached by content hash under `build/cache/svg/`, ids inside each SVG are namespaced so several fit on one page, and widths are expressed in em so the viewer scales them with the text.

### 9.4.3 Math and macros

**[decided]** Math is left as TeX. The manifest carries a default macro set extracted from the default master's preamble closure by the `macros.py` parser (`\newcommand`, `\renewcommand`, `\providecommand`, `\DeclareMathOperator`, zero-argument `\def`, and definitions made through aliases such as `\nc`, DR-73, and `\DeclarePairedDelimiter`), with `\let` bindings and loom's own `\uses`, `\incomplete`, and `\nest` left out, plus one macro set per digest citekey parsed from the digest's macro block. Arras configures MathJax from the manifest. **[decided]** MathJax 3 with the `tex-svg` output, bundled: no font files ship and a deployed site works offline (DR-55); arras bundles the full component, so `\color` and the other extensions never load from the network (M7). A fragment whose element names a set in `data-macros` has that set applied as `\renewcommand` lines prepended to its first math element before typesetting; the default set is global (DR-56). The manifest's macro format (name, argument count, body) would serve KaTeX equally should it ever be wanted.

**[decided]** A display environment or `\[…\]` block whose content names an environment outside the allowlist of what a mathematics renderer handles, or uses a drawing command such as `\xymatrix`, `\tikz` or `\includegraphics`, is compiled by LaTeX as a figure. The allowlist decides, so an environment nobody anticipated goes to LaTeX, which can always render it, rather than to a renderer that cannot. A numbered display is compiled starred with its `\label` removed and the document's number travels on the figure, since a standalone compile would begin counting again (DR-100).

**[decided]** An alphabet declared with `\DeclareMathAlphabet` is published as the nearest alphabet the renderer has, and commands it does not implement but that a macro body may use — `\ensuremath`, `\scalebox`, `\resizebox`, `\raisebox`, `\mbox`, `\hbox` — are published as definitions keeping the content and giving up only presentation, when a published body uses one (DR-101). A command a loaded package defines and the renderer lacks is published as its nearest equivalent when the preamble loads that package (`PACKAGE_COMMANDS` in `scan/macros.py`): `old-arrows`' `\longhookrightarrow`, `bm`'s `\bm`, the double-struck alphabets of `bbm` and `dsfont`, `esint`'s integrals as their Unicode characters, `stmaryrd`'s brackets, `nicefrac` and `xfrac`'s sliced fractions, and amsmath's capitalised accents `\Tilde`, `\Hat` and their kin. A package that loads another — `mathtools` loads `amsmath` — brings the inner package's stand-ins too. A paired delimiter declared with `\DeclarePairedDelimiter` is published as that declaration followed by the command it defines, so MathJax's own mathtools implementation handles the starred and sized forms that no fixed-arity macro reproduces.

**[decided]** Whether an expanded macro is set as mathematics is decided from the macro's body, not from the expansion with the author's text substituted in: an argument holding a citekey's underscore is not a reason to set a paragraph as a formula (DR-102).

**[decided]** A macro body's TeX conditionals are resolved before publication, because a viewer's math renderer implements none. `\ifinner A\else B\fi` becomes `\mathchoice{B}{A}{A}{A}`, which selects on exactly the distinction `\ifinner` tests, and `\ifmmode A\else B\fi` becomes `A`, since a macro body inside a formula is always in math mode. Any other conditional is published as written: guessing a branch would silently change the mathematics. Without this the ACGS paper's own `\newcommand\arr{\ifinner\to\else\longrightarrow\fi}` reached every page as the words `\ifinner`, `\else` and `\fi` in error red beside two arrows (DR-95).

**[decided]** A title keeps its mathematics. The plain text a node's `title` carries preserves `$…$` and `\(…\)` spans as written and cleans only the prose around them; a viewer typesets what it can and shows the source otherwise. Stripping control sequences had turned a section called `Structure of $\Sigma$` into `Structure of $ $` (DR-96).

### 9.4.4 What the converter promises

**[decided]** For any quilt that compiles: every fragment is produced; every construct outside the contract is rendered exactly by fallback; nothing is silently dropped; and every element from source carries `data-src`. The converter does not promise that a fragment is beautiful; it promises that it is complete and honest.

### 9.4.5 What a client needs from a scan

**[decided]** `scan(quilt, overlay)` takes an optional map of quilt-relative paths to the text of unsaved editor buffers, which stand in for what is on disk; a path that exists only in a buffer resolves as an inclusion, so a file written and not yet saved is scanned. Nothing is written anywhere. Reference and `\uses` sites carry the character offset and column of the command, and a node records the offset of each of its `\label`s, so a diagnostic points at a command rather than at a line and a definition site is a range. `kpsewhich` is memoised per name, since it is a subprocess run once per unresolved inclusion and a paper's unresolved names repeat (DR-97).

## 9.5 Annotation marks

**[decided]** For every non-discarded annotation with a selector, loom resolves the selector against the target's current own text (7.5.2), obtains a source span, finds the fragment block whose `data-src` covers the span, and searches the quote in that block read as a projection: inline math as `$tex$`, the simple text macros as their text, other tags as nothing. If found, it wraps the match in `<mark class="annotation" data-annotation="ID">` — one mark round balanced markup, else one per run of text — and **never puts a tag inside a formula**: a match touching inline math takes the whole `span.math`, and a quote inside a displayed formula marks the display as a block (DR-244-ikmartin). A quote that still cannot be located gives its whole block `data-annotation` and a class `annotation-block`. An annotation on an equation's region key with no quote marks that display. Detached annotations get no mark; the manifest lists them.

Marks are placed in node fragments (a proof's marks in its statement's fragment, and in the proof's own when it has a page) and in master fragments (where the node appears expanded).

## 9.6 Numbering

**[decided]** Loom never computes theorem or section numbers. After `loom compile MASTER`, `build/<stem>/<stem>.aux` contains `\newlabel{ID}{{NUMBER}{PAGE}...}` for every id and alias; the scanner reads number and page for each and stores them per master in the manifest. Equations get their numbers the same way. **A master's fragment is numbered from that master's own table** — result numbers, equation tags, reference text and citation labels — so a document shows the numbers its compile gave and none before its first; a reference it cannot number names its target's title. A node's own fragment carries the default master's numbers (DR-245-ikmartin). `loom build` compiles nothing; `loom check` and `loom compile` do. **[decided]** After publishing, `loom serve` compiles the default master in the background whenever a `.tex`, `.sty`, `.cls`, or `.bib` file changed, and republishes when the compile succeeds, so numbers refresh within one cycle; the fragment build never waits for LaTeX (`render/serve.py`; no record beyond the code).

hyperref's `.aux` format (`\newlabel{ID}{{NUMBER}{PAGE}{TITLE}{ANCHOR}{}}`) and the plain format are both read; cleveref's `@cref` entries are skipped. Citation labels are read from the same compile in the same spirit: loom never computes one.

## 9.7 Derived files and bundles

**[decided]** `build/derived/<id>.statement.tex` and `<id>.proof.tex` were planned as the node's statement and proof regions written out alone by `loom build`. They are not written: bundles and fragments take a key's region straight from the scan (`tex/bundle.py`, `region_text`), so nothing consumed the files. The directory is reserved for a future `\transcludestatement`-style macro or an external consumer, and will be filled when one exists (DR-82).

**[decided]** Compiling a key writes `build/bundles/<key>.tex` and runs latexmk on it: a header comment, the master's preamble (its own text before `\begin{document}`, verbatim, with `\usepackage{loom}` inserted after `\documentclass` when the master does not load it), `\begin{document}`, a heading `\section*{Bundle for KEY}`, the statements of the closure in dependency order (each preceded by a comment `% id: <key>`; a digest node's statement wrapped in `\begingroup`/`\endgroup` around its macro block), then the key's own region (a statement and its proofs, or the statement and the one proof), then `\end{document}`. **[decided]** **The closure covers what is printed** (DR-169): a statement's bundle prints the statement and its proofs, so its closure is the union of the statement's closure and each printed proof's. A proof's dependencies are usually declared inside the argument, so the statement's own closure alone leaves every `\ref` the proof makes pointing at a statement the document does not contain. **[decided]** A reader finds each theorem's id in the `% id:` comment before its environment: the `\loombundle` switch inside `loom.sty` considered at design time was not built, and the comment form named as its fallback is what ships (`tex/bundle.py`; the bundles compiled at M2 and M7 carry it).

**[decided]** `loom compile KEY --with FILE` compiles the same document with a proposed diff applied or a substitute file in place of the key's text, and `loom compile --draft FILE` compiles a not-yet-promoted node from its `\ref`s and `\uses`; neither touches the quilt, and both exist so an agent's proposal or draft can be checked before a person applies it. **[decided]** `--with` takes a file first and then an annotation's id, whose payload is the proposed text: the payload **is** the proposal, so copying it into a file before compiling it is a step with nothing in it. A value that is neither is refused by name, never as a traceback. **[decided]** The document is an artifact of compiling, not something a reader asks for: `loom source KEY --closure` prints the same statements to stdout, which is how an agent or a person reads a result and its dependencies. There is no `loom bundle` command (DR-148); what it wrote into a run went stale against the author's next edit, and what it wrote into `build/` is still written here. A bundle that fails to compile or reads incomplete is the operational failure of self-containedness and is reported as `loom:bundle-failed` with the LaTeX log's first error.

**[decided]** **A compile has three outcomes, not two** (DR-169). `compiled` when latexmk exits zero and a PDF exists; `compiled with warnings`, exit 0, when latexmk exits nonzero but a PDF exists and the log holds no `!` line, with every `LaTeX Warning:` and `Package … Warning:` line printed; `FAILED`, exit 1, otherwise. latexmk exits nonzero on an undefined reference and still writes a readable PDF, and a reader told FAILED there cannot tell a document their change broke from one that was already like that. The error named is the log's first `!` line; when there is none, loom says the exit code and which log it read, rather than printing the last line of latexmk's closing advice as though it were the error.

## 9.8 `loom serve`

**[decided]** One loop with three jobs:

0. Listen and report: bind the port and start serving before the first build, print the URL, then build, reporting `building the quilt ...` and then the fragment count, the elapsed time, and the error count with `run loom lint` when the quilt has errors. Until the first publish `/build/manifest.json` is a 404, which arras reports as `arras:manifest-missing` and recovers from on its next poll. A cold first build compiles every block the converter cannot translate, so it can take a while and must not be silent (DR-87).
1. Watch: poll mtimes of every `.tex`, `.sty`, `.cls`, and `.bib` file under the root outside `build/` — the canon directory included, since a landmark is rendered though it is never scanned — of `config.toml`, of the acceptance ledger, the history and the session files under `.loom/` (a session's inbox excepted, which is read live), of the annotation log under `annotations/`, and of `ai/` once a second (as sitegen does); on change, run `loom build`, whose render cache limits re-rendering to the fragments whose inputs changed (the changed file's nodes, their masters, and any fragment whose marks depend on a changed record), then publish (M2: a new manifest 0.88 s after an edit).
2. Serve: a static HTTP server on `127.0.0.1:<port>` (default 8791; `--port` changes it, and the command fails if the port is busy) serving the arras bundle at `/` and `build/` at `/build/`. Every response carries an `ETag` and `If-None-Match` is answered with 304, so the viewer's poll of the manifest costs nothing while it is unchanged. Any path that is not a file of the bundle is answered with the bundle's `index.html`, unless it lies under `_app/` or ends in an asset suffix (`.js`, `.css`, `.svg`, `.png`, `.json`, fonts, ...), which stay 404, so viewer routes work with dots in keys (DR-78); `/_api` is 404, the write API being deferred. The bundle is found through `LOOM_ARRAS_BUNDLE`, then the installed `arras` pip package (`arras.bundle_path()`), then the copy vendored inside loom under `src/loom/assets/arras/`; `loom doctor` reports which one and its `VERSION` line. The vendored copy is refreshed by `scripts/vendor_arras.py ../arras/build`, which refuses an arras whose interface version differs from loom's and stamps `VERSION` with the arras commit; Vite's chunk hashes are not reproducible across installs, so that commit, not byte equality with a fresh build, is what ties a bundle to its source (M7).
3. Compile: after publishing, if a `.tex`, `.sty`, `.cls`, or `.bib` file changed, run `loom compile` on the default master in the background and republish when it succeeds, so numbers refresh.

**[decided]** Loom never notifies arras. Arras polls `/build/manifest.json` and re-renders when its hash changes (10.5). If watching proves too slow, the fallback is a `POST /_refresh` endpoint arras may call carrying nothing but "refresh", which preserves arras's ignorance of event types. It is not built; polling has never been too slow.

`loom serve --no-compile` skips step 3; `--port`; `--open` opens the browser.

## 9.9 The interface files

The normative interface is `specs/`:

- `specs/dialect.md`: the HTML dialect of fragments.
- `specs/manifest.md`: the manifest schema.
- `specs/diagnostics.md`: diagnostic codes, reserved and namespaced.
- `specs/fixture.md`: the conformance fixture (DR-58: the synthetic quilt's missing include sits inside `\iffalse`, and its beamer talk declares `proposition`, so both masters compile for numbering).
- `specs/write-api.md`: deferred, and `specs/runner.md`: declined (WQ-15). Both were specified so the CLI is designed with them in mind.

Every manifest carries `interface_version`. Loom and arras each declare the versions they produce and accept (both 1 today); a mismatch is reported by arras on its problems page as one diagnostic and nothing else (10.5, M2), never silently.

## 9.10 Sitegen as a second publisher

**[decided]** The author's org-mode site generator becomes a publisher by emitting fragments in the dialect and a manifest, and dropping its own templates, link rewriting, backlinks, and search. Its `export.el` already emits most of the dialect's classes; the additions are `data-id`, `data-key`, `data-src`, the manifest, and the reserved diagnostics. This is not part of the MVP; it is the test that the interface is generic and the reason arras must never know what a proof is.

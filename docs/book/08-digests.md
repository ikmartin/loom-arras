# 8. Digests

A digest is loom's index of a cited paper: the paper's results as external nodes, under the paper's own outline, in a LaTeX file that obeys the source contract. It exists so that a citation with a locator becomes a checkable edge, so that a review bundle contains the statements it cites, so that an assistant reads the digest instead of the paper, and so that a person can learn what results exist in a paper without opening it.

## 8.1 What a digest is

**[decided]** A file `digests/<citekey>.tex` (the citekey is the bibliography key the paper is cited under) containing:

1. A provenance header of directives (8.4).
2. An optional macro block (8.3).
3. An overview: prose, as the digest's author (a person or an agent) wrote it.
4. The paper's outline as sectioning units (section nodes), each containing the paper's results as external nodes, in the paper's order.

Example, abbreviated:

```tex
% !LOOM digest: Man12
% !LOOM prefix: Man12
% !LOOM extracted-from: arXiv:0805.2065v2
% !LOOM published-as: doi:10.1090/S1056-3911-2011-00606-1
% !LOOM method: extract
% !LOOM created: 2026-09-16
% !LOOM requires: mathrsfs, xy

\section*{Overview}
Manolache constructs a virtual pullback for a DM-type morphism $f\colon X\to Y$ equipped with a perfect obstruction theory relative to $Y$, proves functoriality, and compares it with ...

\begin{theorem}[{\cite[Standing assumptions]{Man12}}]\label{Man12-setup}
Throughout, all stacks are of finite type over a field $k$, ...
\end{theorem}

\section{Preliminaries}\label{Man12-sec-2}

\begin{definition}[{\cite[Definition 2.1, p.~4]{Man12}}]\label{Man12-def-2.1}
\label{Man12-dm}
Let $f\colon X \to Y$ be a morphism of Deligne--Mumford stacks. A \emph{perfect obstruction theory for $f$ relative to $Y$} is ...
\end{definition}

\section{Virtual pullback}\label{Man12-sec-4}

\begin{theorem}[{\cite[Theorem 4.1, p.~12]{Man12}}]\label{Man12-thm-4.1}
\uses{Man12-prop-3.2, Man12-lem-2.7, Man12-setup}
\label{Man12-main}
Let $f\colon X\to Y$ be a DM-type morphism with a perfect obstruction theory $E_f$ relative to $Y$. Then there is a well-defined virtual pullback $f^!\colon A_*(Y)\to A_*(X)$ ...
\end{theorem}
```

The id prefix is the citekey's slug, the citekey with everything but letters and digits removed: `Man12` is its own slug, while `manolache_VirtualPullbacks2012` keeps its verbatim form in the `digest:` directive and in every `\cite` and prefixes its ids as `manolacheVirtualPullbacks2012-` (DR-45). The second `\label` in each node above is the paper's own label (`dm`, `main`), prefixed and kept inside the node as an alias, so a `\ref` in another digest node or in the overview reaches the result under either name (M5).

Rules:

1. **[decided]** A digest is scanned like any file (5.1). Its nodes are nodes of the quilt with ids `<slug>-<paperlocal>`, where the slug is the citekey's slug and `paperlocal` is letters, digits, dots, and hyphens; its section nodes have ids `<slug>-sec-<n>` (DR-45, DR-62). The first label inside a node is its id when it has this shape; every further label of the node is an alias. Two citekeys with one slug are `loom:citekey-slug-collision` (error) (DR-45).
2. **[decided]** Digests are never reached by a master (they are loose by construction), so lint reports neither `unreachable` for a digest file (DR-51) nor `loom:reference-to-loose` for a reference whose target is a digest node or a digest's section node (DR-76). They are never compiled as documents on their own; their statements are compiled inside bundles (8.11), and blocks of their statements that the viewer cannot typeset are compiled in fallback documents carrying the macro block (8.3.5).
3. **[decided]** A digest node is an external node: `plain` style, no proof, a citation in its title. Its title is the locator in the form `{\cite[LOCATOR]{citekey}}` (braces because the locator contains commas), where `LOCATOR` is the paper's own address for the result.
4. **[decided]** Standing assumptions, conventions, and notation that a paper states outside numbered results go in one node with id `<slug>-setup` and title `{\cite[Standing assumptions]{citekey}}`, so that `\uses` has something to point at and the postnote `Standing assumptions` resolves to it (8.7).
5. **[decided]** `\uses` inside a digest node records the paper's internal dependencies (which results its proof invokes). Optional; the ingest contract asks for it where the paper states it.
6. **[decided]** Every `\label` and `\eqref` inside a digest is prefixed with `<slug>-` at extraction time, so that two papers' `eq:main` coexist in one bundle (DR-45).
7. **[decided]** Theorem environments in a digest use the quilt's own environment names. The extractor maps the reference's environments by display name (`\begin{thm}` in Manolache becomes `\begin{theorem}` if the quilt declares `theorem` with display name Theorem); when the quilt declares a display name twice (`thm` and `thm*` both display Theorem), the numbered environment is chosen, then the one whose name is the lowercased display name, then the first declared (DR-69). A display name the quilt does not declare keeps the paper's environment name: the extractor's report suggests a `\newtheorem` line for it, and lint reports `loom:unknown-environment` (error) when the name is one of the common theorem-like names, whose fix is a `% !LOOM environment:` directive in a master (M5: `convention`, `condition`, `setting` for Manolache). **[decided]** `digest import` does not remap environments; it reports the ones the quilt does not declare and leaves the author to declare them (8.10). Digests in a library quilt use the library's minimal declared set.

## 8.2 Verbatim statements

**[decided]** Statements in a digest are verbatim by default. A theorem's exact wording is its content; the audit's citation check is "does the cited statement, as stated, cover the use," and a paraphrase would be a second reading of the hypotheses. Verbatim restatement with a locator is ordinary scholarly practice, and the mechanical route produces it for free.

**[decided]** Proofs are never copied into digests under any policy.

**[decided]** The overview and any restatement in the quilt's own notation are the digest author's and are written in their words.

**[decided]** Redistribution is a license question, not a tool constraint: a verbatim digest is unproblematic in a private quilt and becomes a question only when a library quilt is shared or published, at which point the sharer consults each paper's license (arXiv submissions carry various licenses; journal versions belong to publishers). This is policy recorded by provenance, not enforced by loom. The book is not legal advice.

## 8.3 Macro policy

The problem: a verbatim statement uses the reference paper's macros, which are not in the quilt's preamble; importing the reference's macro file would let two definitions of `\Hom` collide and the quilt's silently win.

**[decided]** Two mechanisms, used together:

1. Expansion. The extractor expands the reference's simple macros (parameterless and parametered `\newcommand`/`\renewcommand`/`\providecommand`, with an optional-argument default, `\DeclareMathOperator`, zero-argument `\def`) textually in the extracted statements, using the scanner's macro table. A control word the paper declares as an alias of `\newcommand`, `\renewcommand`, or `\providecommand` (`\newcommand{\nc}{\newcommand}`, `\let\nc\newcommand`, or `\def`), transitively, is read as that command, so a preamble that defines its macros through `\nc` and `\renc` is expanded like any other (DR-73). `\xspace` is dropped from expanded bodies, since it is a no-op in math and breaks before `^` or `_` (DR-74). What can be expanded is expanded, so the digest is macro-free where possible.
2. The macro block. What the digest's text uses and cannot be expanded (definitions with delimiters or conditionals, `\let`, `\NewDocumentCommand`, or anything the parser refuses) is placed verbatim in a region, together with every `\newenvironment` and every enumitem `\newlist` (with its `\setlist` lines) that the statements use (DR-74). Only names and environments the statements, locators, or overview use are copied.

```tex
% !LOOM begin macros
\let\Hom\undefined
\newcommand{\Hom}{\operatorname{Hom}}
\let\weird\undefined
\def\weird#1.{[#1]}
\newlist{thmlist}{enumerate}{1}
\setlist[thmlist,1]{label={\em(\roman*)}, ref={(\roman*)}}
% !LOOM end macros
```

   Wherever a digest statement is compiled (a bundle, a fallback document), loom emits `\begingroup`, the block, the node text, `\endgroup`. `\let\NAME\undefined` before each macro definition lets the paper's meaning hold inside the group even when the quilt defines the same name, and the quilt's meaning returns at `\endgroup`. `\DeclareMathOperator` is preamble-only under amsmath and is rewritten to `\newcommand{...}{\operatorname{...}}`; `\NewDocumentCommand` takes the same `\let\undefined` treatment; environment and list definitions are copied as written. The block is loaded, never shown: the digest's document view starts after `% !LOOM end macros` (DR-80).

3. Packages cannot be scoped. `% !LOOM requires:` lists the packages the digest's statements need beyond amsmath, amsthm, and loom. The extractor writes it as the reference's `\usepackage` names minus those three, minus presentation packages that a statement never needs (encoding, fonts, page layout, colour, graphics, hyperlinks, cross-referencing, bibliography: `inputenc`, `geometry`, `hyperref`, `cleveref`, `natbib`, `setspace`, and the like) (DR-74), and minus what the quilt's default master's preamble closure already loads (M5); `enumitem` is added back when a `\newlist` is copied into the block (DR-74). Lint reports `loom:missing-package` (warning) for any listed package the default master's preamble closure does not load. The fix is a line in the author's preamble; when a required package clashes with one the quilt loads (`MnSymbol` against `amssymb`), the author strikes it from `requires:` instead (M7). After the packages are added, re-extraction writes no `requires:` line, and the lint check is what catches a later change of preamble (M5).
4. **[decided]** A digest with an empty macro block is macro-free; one with a nonempty block is scoped. The contract does not distinguish; porting is still a copy.
5. Rendering. MathJax's macro table is global, so arras cannot give each page its own set; instead loom parses the block's definitions into a per-citekey macro set in the manifest, every digest node's fragment names its set, and arras prepends `\renewcommand` lines for that set to the fragment's first math element before typesetting (DR-56). A block MathJax cannot render takes the SVG route (Chapter 9): a digest statement's fallback document carries the digest's macro block and the packages its header requires that the master's preamble lacks; a second attempt drops the added packages, a third uses a minimal preamble (DR-79).

## 8.4 Provenance

**[decided]** The header directives:

- `digest: CITEKEY` (required, within the file's first twenty lines; marks the file as a digest and names the citekey verbatim, which must exist in the quilt's bibliography or lint reports `loom:digest-without-bib`, warning).
- `prefix: NAME` (optional; defaults to the citekey's slug). The id prefix every node of this digest carries, so that `\uses{Man12-prop-3.2}` stays typeable when the citekey is a thirty-character Zotero key, and so that the ids survive a citekey rename. It is what the scanner registers for the id grammar of 5.2, which is why declaring one is what makes `Man12-prop-3.2` an id rather than a human alias (DR-109).
- `extracted-from: IDENT` (required for `method: extract`; `arXiv:0805.2065v2`, `doi:10.1090/...`, `work:<hash>`, or `local:<file>`) and `published-as: IDENT` (optional). Two facts, not two spellings of one: the statements and their numbers come from the artifact that was parsed, and the work a reader will open is whatever the bibliography cites. They differ whenever a digest is extracted from a preprint of a published article, which is the common case, and then every locator and page number in the digest is unverified against the version a reader has — `loom:unverified-locators` (warning) says so. The extractor resolves both from the bibliography entry in the order `doi` > `eprint` > `mrnumber` > `zbl` > `url`, taking the artifact from the path when the source sits under `refs/`. `source:` is the pre-0.5 spelling of `extracted-from:` and is still read (DR-109).
- `method: extract | ingest | manual`.
- `created: YYYY-MM-DD`.
- `author:` (the person or run that produced it; optional; an ingested digest names the agent).
- `requires:` (8.3).
- `numbering: emulated` (written by the extractor only when no `.aux` could be produced, 8.5.2).

`method: extract` implies verbatim statements from the named source. `ingest` means an agent produced or completed the file, verbatim where it had the source and faithful where it had only the PDF; `manual` means a person wrote it.

## 8.5 Extraction: `loom digest extract CITEKEY SRC`

**[decided]** Mechanical production of a digest from the reference paper's LaTeX source (its arXiv e-print unpacked locally, or `refs/src/<citekey>/` after `digest fetch`). It is `loom import` applied to someone else's paper with proofs dropped and ids prefixed by the citekey's slug:

1. Resolve the reference's closure from `SRC` (as 6.2.1), read its preamble closure for `\newtheorem` declarations and macro definitions (through definition aliases, DR-73).
2. Compile the reference in its own directory with `latexmk`, the output going to a scratch directory, to obtain its `.aux`; the engine is `--engine`, else the paper's `% !TEX program` comment, else pdflatex. The amsthm counter emulation (shared counters, `[section]` resets, `\newtheorem*`, `\appendix` lettering) always runs in document order, and whenever the `.aux` numbers a labelled result that number replaces the emulated one and resynchronises the counters, because an `.aux` names only labelled results; `numbering: emulated` is written only when no `.aux` was produced, by a failed compile or `--no-compile` (DR-68). **[decided]** The emulator was verified on the Manolache fixture, where unlabelled results between labelled ones take the right numbers (DR-68; M5).
3. For every theorem-like environment: build an external node with id `<slug>-<abbrev>-<number>`, where `abbrev` is a fixed map from display name (`thm`, `lem`, `prop`, `cor`, `def`, `rem`, `ex`, `constr`, `conj`; any other display name uses the lowercased environment name) and `number` is the result's number (`4.1`); a result of a `\newtheorem*` environment gets `<slug>-<abbrev>-star-<n>`, `n` counting unnumbered results in document order (DR-67). Title `{\cite[<Name> <number>, p.~<page>]{citekey}}`, with the paper's own optional title in parentheses after the number (`Theorem 3.1 (Main)`), `(unnumbered)` in place of the number for a starred result (DR-67), and the page when the `.aux` gives one. Body: the environment's contents with macros expanded (8.3.1), labels and `\eqref`s prefixed, `\ref`s to the paper's own results rewritten to the corresponding digest ids and `\ref`s to anything else replaced by the number the `.aux` gives it; nested theorem-like environments and proofs are cut out; the paper's own labels stay inside the node, prefixed, as aliases (M5). Proofs are dropped, except that each `\ref` (or `\cref`, `\eqref`, `\autoref`) inside a dropped proof that names one of the paper's results becomes a `\uses` entry on the node, so the paper's internal dependencies are recorded mechanically. A second result carrying a number already used is skipped and reported.
4. Sectioning: the paper's `\section`s and `\subsection`s that contain results become section nodes `<slug>-sec-<number>`; prose between results is dropped, except that the first two paragraphs of the introduction (or of the first section) are placed under `\section*{Overview}` as a seed the human rewrites. **[decided]** This rule; a paper with no introduction gets `\section*{Overview}` with `\incomplete{Overview not extracted; the paper has no introduction.}` (M5).
5. Standing assumptions: text the extractor cannot attribute to a numbered result is not guessed; it writes an empty `<slug>-setup` node titled `{\cite[Standing assumptions]{citekey}}` with `\incomplete{Standing assumptions not extracted; see the paper.}` for ingest or a person to fill. **[decided]** (M5: the Manolache digest carries the node.)
6. Write the macro block from the unexpandable residue and the environments the statements use, and `requires:` as 8.3.3 (DR-74).
7. Write `digests/<citekey>.tex` and report: results extracted by taxon, sections, `\uses` recorded, the macros expanded by name, the macro block's definitions, packages required, the numbering source (`from the paper's .aux`, or `emulated` with the compile error), each environment the quilt does not declare with a suggested `\newtheorem` line, and anything skipped; then lint runs on the new file and its diagnostics are printed (M5).

`digest extract` refuses if `digests/<citekey>.tex` exists (`--to` writes elsewhere). A citekey absent from the bibliography is a warning (`loom:digest-without-bib`), not a refusal. A paper that declares its results with `\newenvironment` wrappers around a counter rather than with `\newtheorem` (Romagny) yields zero extracted results, and the report says so; ingest (8.6) is the route for such papers (M7).

## 8.6 Ingest

**[decided]** Ingest is an AI mode (Chapter 11; `ai/modes/ingest.md`), not a command. It has two uses:

1. **[decided]** Checking what extraction produced, never replacing it (DR-173). Ingest mode runs `loom digest extract CITEKEY SRC --to ingest-<citekey>.tex` in the run directory and reads the paper against it, reporting what the extractor cannot see: standing assumptions stated in prose, hypotheses dropped from a statement, `\uses` edges a proof invokes without citing, locators left `\incomplete`, and macros it could not expand. Its output is the extractor's file unedited, a `proposal-<citekey>.diff` of the corrections, a notes file, and a finding per defect that matters. **A work with no LaTeX source cannot be digested**: the mode says so and stops, because a typed digest is exactly the unverifiable artefact the extraction route exists to avoid (M7: Romagny, seven results and a setup node).
2. Completing an extracted digest: the agent reads the extracted file and the paper, and fills what extraction could not: the `-setup` node, missing `\uses` (a theorem's proof invokes lemmas it never `\ref`s, which the extractor could not see), the overview, and locators the extractor left `\incomplete`. The output is `proposal-<citekey>.diff` against `refs/<citekey>.tex`, applied by the person.

The `\uses` completeness check is the audit mode's uses-ledger (Chapter 11) applied to the reference paper's proofs before they are dropped; the extractor records what `\ref` says, ingest adds what the prose says.

## 8.7 Postnote edges

**[decided]** `\cite[POSTNOTE]{citekey}` in any region creates an edge (`via: postnote`) to each digest node whose locator matches `POSTNOTE`, when a digest for `citekey` exists, except inside the digest of that citekey itself: every digest node's title is such a citation, and matching it would make a node depend on itself or on its section, so those citations create neither an edge nor a diagnostic (DR-66).

Matching:

1. Normalize both the postnote and every digest node's locator: lowercase; expand abbreviations and plurals (`thm`, `theorem`, `theorems`; `lem`, `lemma`, `lemmata`; `prop`; `cor`; `def`, `defn`; `rem`, `rmk`; `ex`; `sec`, `sect`, `subsec`; `eq`, `eqn`; `conj`; `constr`; `cond`; `conv`; `notn`; `ch`, `chap`; `app`; `ass`; `hyp`; `q`; `para`; `fig`; `tab`); read `\S` and `§` as `section`; reduce `\href` to its text and drop other control words; remove `~`, braces, parentheses, the period after an abbreviation, a trailing part selector (`(2)`, `(ii)`, `(a)`), page references (`p.~12`, `pp.~12--14`), and the filler words `see`, `cf`, `also`, `eg`, `ie`, `the`, `of`, `in`, `compare`, `esp`, `especially`; a Roman numeral after a taxon word becomes a digit; collapse whitespace.
2. A node's forms are its normalized locator, each part of that locator, and `<taxon> <number>` read off its id and off every id-shaped alias, so a node labelled `ro-thm-1.0.1` and `ro-thm-1.2.1` answers citations under both numberings (DR-75); the `-setup` node also answers `standing assumptions`. Match if any part of the postnote equals one of the forms.
3. **[decided]** A postnote naming several results is split on `,`, `;`, `and`, and `&`, and a bare number takes the taxon of the part before it, so `Theorems 4.1 and 4.3` creates an edge to each (M5).
4. No match while a digest exists: `loom:unmatched-postnote` (warning) with the postnote text. A citekey cited with a locator that has no digest: `loom:undigested-citekey` (info), once per citekey, naming the citing keys.
5. `\uses{<slug>-thm-4.1}` is the explicit fallback and always works.

Examples: `\cite[Theorem 4.1]{Man12}` matches `Man12-thm-4.1`; `\cite[Thm.~4.1, p.~12]{Man12}` and `\cite[Theorem 4.1(2)]{Man12}` match the same; `\cite[Section 4]{Man12}` matches `Man12-sec-4` without a `loom:reference-to-loose` (DR-76); `\cite{Man12}` with no postnote creates no edge (it is a citation of the paper, not of a result) and no diagnostic. On the relative localization paper every postnote resolves: six to Manolache (M5), eleven to the virtual localization paper and six to Romagny (M7).

## 8.8 Versioning

**[decided]** The digest's `extracted-from:` names the version it was made from. The bibliography entry's version is its `version` field or, **[decided]**, the trailing `vN` of its `eprint` (M5). When both are known and differ, lint reports `loom:version-mismatch` (warning), since numbering may have changed between versions, and the references index marks the entry. When the entry carries no version the check cannot fire: the relative localization paper cites Romagny under an earlier arXiv version's numbering and its entry has no version, so the digest carries both numberings, the source's as ids and the cited version's as aliases, and postnotes resolve under either (DR-75; M7). When a cited paper has no digest, `status --undigested` lists every citekey cited with a locator that lacks one; this list is the ingest trigger an agent acts on, and `loom ai orient` repeats it.

## 8.9 Fetching

**[decided]** Loom fetches nothing unless `[refs] fetch = true`. Then `loom digest fetch CITEKEY` retrieves the e-print source into `refs/<scheme>/<identifier>/src/` (gitignored; a gzipped tar, a gzipped single file, or a PDF is unpacked, paths that would escape the directory refused) and, with `--pdf`, the PDF beside it as `paper.pdf`. The directory is named by the work's global identifier rather than by the citekey, because a work reached through another paper's bibliography has no citekey at all, and because two quilts citing one paper should name one directory (DR-108). `loom refs path CITEKEY` prints it; `loom refs add CITEKEY FILE` files a PDF obtained by hand, which is how a published article gets in, since its PDF sits behind a subscription loom cannot and should not automate past, then names the `digest extract` command to run next. Apart from `loom refs resolve` (8.9.1), no other command touches the network. **[decided]** The identifier is the bib entry's `eprint`, used only when `eprinttype` or `archiveprefix` is absent or `arXiv` (a JSTOR eprint is refused); requests go to arXiv's e-print and PDF URLs with a `User-Agent` naming loom and its version; a request answered 406, 429, or 5xx is retried twice after a pause; when the source cannot be fetched but `--pdf` was asked, the PDF is still fetched and the source failure reported (DR-77). Fetched sources and PDFs are not the quilt's text: the scanner skips `refs/src/` and `refs/pdf/` (DR-70).

### 8.9.1 Identity candidates

**[decided]** A work whose bibliography entry states no identifier is filed under a synthetic `work:<hash>` (8.4): consistent, but impossible to fetch or to join with another corpus's copy. `loom refs resolve [CITEKEY...]` looks such works up, and only with `[refs] resolve = true`, since it sends titles and authors to two outside services. With no citekeys it takes every cited entry that states no identifier.

**[decided]** zbMATH Open is asked first, searched by title and first author, since it covers mathematics best and returns a Zbl number for works with no DOI, together with any DOI and arXiv identifier it knows. Crossref's `query.bibliographic` is asked when zbMATH found nothing strong or found a strong match without a DOI. Neither needs a key. Requests to each service are at least a second apart, which is Crossref's public limit; zbMATH Open asks only for a reasonable rate, and licenses its data CC-BY-SA 4.0. When `[refs] contact` is set, it is sent to Crossref as `mailto`, which routes the requests to its polite pool; otherwise nothing identifying is sent. A 404 is no match, not a failure, and one service failing does not fail the lookup (DR-122).

**[decided]** Loom scores every returned record itself rather than trusting a service's own score, so a confidence means the same thing whichever service answered: three quarters for the title, compared as folded words and forgiving a subtitle one side omits, 0.15 for the first author's surname, 0.10 for a year within one. `strong` is 0.9 and above, `possible` from 0.75; below that a record is dropped. Records of one work from both services — the same identifier, or the same title and year — are pooled into one candidate whose lead identifier is the most useful: a DOI, then an arXiv identifier, then MR, then Zbl.

**[decided]** A candidate is never the work's identity and loom never writes the bibliography: it prints the field the author would add, and the work's identity changes only when the author's own entry states it, at which point it is `declared` like any other. Candidates are recorded in the work's own directory, `refs/work/<hash>/resolved.json`, which is named by the entry's authors, title and year, so editing the entry forgets them; raw answers are cached under `refs/cache/resolve/`, so a second run asks nothing unless given `--refresh`. `loom lint` reads the record and names the candidate in `loom:unresolved-work`, still without touching the network; the manifest carries it as the reference's `candidates` list, which arras shows as unconfirmed (DR-122).

## 8.10 The library quilt and porting

**[decided]** A library quilt is a quilt with no masters: `config.toml`, `loom.sty`, a minimal preamble-like file declaring the standard taxa for lint's benefit (`library.tex` at the root containing only `\newtheorem` declarations and `% !LOOM ignore`, or a `[quilt] library = true` flag; the decision is deferred), `refs.bib`, and `refs/`. It is where digests are kept once per paper, viewable in arras like anything else, and the source of every port.

**[decided]** `loom digest import PATH [--as CITEKEY]` copies a digest into the quilt's `digests/<citekey>.tex`, never overwriting. With `--as` it rewrites the `digest:` directive, the slug prefix in every `\label`, `\ref`, `\eqref`, `\cref`, `\Cref`, `\autoref`, and `\uses` entry, and the citekey in every `\cite`, and reports the number of rewrites. It does not remap environment names; it reports the `requires:` packages the quilt's default master does not load (`loom:missing-package`), the theorem-like environments with a locator title that the quilt does not declare (`loom:unknown-environment`), and a citekey absent from the bibliography (`loom:digest-without-bib`), leaving the author to declare and load them. Exporting is `cp`.

## 8.11 Digests in bundles and closures

**[decided]** An external node reached by a postnote edge or `\uses` is in the referencing key's closure like any node. A bundle includes its statement, wrapped in the digest's macro block group (8.3.2), one group per digest statement. Its `requires:` packages must be loaded by the bundle's preamble, which is the master's; a missing one fails the bundle compile, and `loom compile` prints the `loom:missing-package` lines for the digests in the closure before the failure (M5). `loom check` reports a failed bundle as `loom:bundle-failed` (M7).

## 8.12 Digests in arras

Digest nodes are nodes: a page each, with the locator in the header, links from every `\cite[postnote]` that resolves to them (the rendered citation carries its target), and dependents listing the quilt's keys that use them; their fragments name the digest's macro set (8.3.5, DR-56). The digest file's outline renders as a document view (the reference's table of results) that starts after the macro block (DR-80), reachable from a References index listing every citekey in the bibliography and every digest, with the digest's result count and method, a version-mismatch mark (8.8), and the keys that cite it (M5). Ids with dots (`ro-thm-1.0.1`) are served as pages like any other (DR-78). Arras builds all of this from the manifest's references, section nodes containing nodes, an index of a taxon, and edges; it knows nothing of extraction or verbatim statements.

## 8.13 A corpus is another tool's business

Loom reaches one level out from the paper: it fetches a work its own bibliography cites, and it stops there. Following citations for their own sake — a library built by depth and subject, filtered by MSC family and arXiv category, downloaded under a cap — was built here and has been taken out again (DR-144). That work belongs to **weft**, a separate tool for other people's results at corpus scale, whose boundary with loom is written down in `docs/plans/weft-and-loom.md`: weft knows nothing about quilts, loom knows nothing about corpora, and what crosses between them is an identifier and a bibliography entry, both formats that predate either tool. Nothing in a quilt depends on weft having run, so a quilt stays self-contained and compiles years later with no corpus in sight.

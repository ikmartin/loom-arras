# 8. Digests

A digest is loom's index of a cited paper: the paper's results as external nodes, under the paper's own outline, in a LaTeX file that obeys the source contract. It exists so that a citation with a locator becomes a checkable edge, so that a review bundle contains the statements it cites, so that an assistant reads the digest instead of the paper, and so that a person can learn what results exist in a paper without opening it.

## 8.1 What a digest is

**[decided]** A file `refs/<citekey>.tex` (the citekey is the bibliography key the paper is cited under) containing:

1. A provenance header of directives (8.4).
2. An optional macro block (8.3).
3. An overview: prose, as the digest's author (a person or an agent) wrote it.
4. The paper's outline as sectioning units (section nodes), each containing the paper's results as external nodes, in the paper's order.

Example, abbreviated:

```tex
% !LOOM digest: Man12
% !LOOM source: arXiv:0805.2065v2
% !LOOM method: extract
% !LOOM created: 2026-09-16
% !LOOM requires: amsmath, amsthm

\section*{Overview}
Manolache constructs a virtual pullback for a DM-type morphism $f\colon X\to Y$ equipped with a
perfect obstruction theory relative to $Y$, proves functoriality, and compares it with ...

\section{Preliminaries}\label{Man12-sec-2}

\begin{definition}[{\cite[Definition 2.1, p.~4]{Man12}}]\label{Man12-def-2.1}
Let $f\colon X \to Y$ be a morphism of Deligne--Mumford stacks. A \emph{perfect obstruction theory
for $f$ relative to $Y$} is ...
\end{definition}

\begin{theorem}[{\cite[Standing assumptions, Section 2]{Man12}}]\label{Man12-setup}
Throughout, all stacks are of finite type over a field $k$, ...
\end{theorem}

\section{Virtual pullback}\label{Man12-sec-4}

\begin{theorem}[{\cite[Theorem 4.1, p.~12]{Man12}}]\label{Man12-thm-4.1}
\uses{Man12-prop-3.2, Man12-lem-2.7, Man12-setup}
Let $f\colon X\to Y$ be a DM-type morphism with a perfect obstruction theory $E_f$ relative to $Y$.
Then there is a well-defined virtual pullback $f^!\colon A_*(Y)\to A_*(X)$ ...
\end{theorem}
```

Rules:

1. **[decided]** A digest is scanned like any file (5.1). Its nodes are nodes of the quilt with ids `<citekey>-<paperlocal>`; its section nodes have ids `<citekey>-sec-<n>`.
2. **[decided]** Digests are never reached by a master (they are loose by construction) and never compiled as documents on their own; they are compiled only inside bundles.
3. **[decided]** A digest node is an external node: `plain` style, no proof, a citation in its title. Its title is the locator in the form `{\cite[LOCATOR]{citekey}}` (braces because the locator contains commas), where `LOCATOR` is the paper's own address for the result.
4. **[decided]** Standing assumptions, conventions, and notation that a paper states outside numbered results go in one node with id `<citekey>-setup`, so that `\uses` has something to point at.
5. **[decided]** `\uses` inside a digest node records the paper's internal dependencies (which results its proof invokes). Optional; the ingest contract asks for it where the paper states it.
6. **[decided]** Every `\label` and `\eqref` inside a digest is prefixed with `<citekey>-` at extraction time, so that two papers' `eq:main` coexist in one bundle.
7. **[decided]** Theorem environments in a digest use the quilt's own environment names. The extractor maps the reference's environments by display name (`\begin{thm}` in Manolache becomes `\begin{theorem}` if the quilt declares `theorem` with display name Theorem); a display name the quilt does not declare is `loom:unknown-environment` with a suggested `\newtheorem` line. **[assumed]** Digests in a library quilt use the library's minimal declared set; `digest import --as` remaps on the way in.

## 8.2 Verbatim statements

**[decided]** Statements in a digest are verbatim by default. A theorem's exact wording is its content; the audit's citation check is "does the cited statement, as stated, cover the use," and a paraphrase would be a second reading of the hypotheses. Verbatim restatement with a locator is ordinary scholarly practice, and the mechanical route produces it for free.

**[decided]** Proofs are never copied into digests under any policy.

**[decided]** The overview and any restatement in the quilt's own notation are the digest author's and are written in their words.

**[decided]** Redistribution is a license question, not a tool constraint: a verbatim digest is unproblematic in a private quilt and becomes a question only when a library quilt is shared or published, at which point the sharer consults each paper's license (arXiv submissions carry various licenses; journal versions belong to publishers). This is policy recorded by provenance, not enforced by loom. The book is not legal advice.

## 8.3 Macro policy

The problem: a verbatim statement uses the reference paper's macros, which are not in the quilt's preamble; importing the reference's macro file would let two definitions of `\Hom` collide and the quilt's silently win.

**[decided]** Two mechanisms, used together:

1. Expansion. The extractor expands the reference's simple macros (parameterless and parametered `\newcommand`/`\renewcommand`/`\providecommand`, `\DeclareMathOperator`, zero-argument `\def`) textually in the extracted statements, using the same parser as `macros.py`. What can be expanded is expanded, so the digest is macro-free where possible.
2. The macro block. What cannot be expanded (definitions with conditionals, delimiters, `\@ifnextchar`, or anything the parser refuses) is placed verbatim in a region:

```tex
% !LOOM begin macros
\let\Hom\undefined
\newcommand{\Hom}{\operatorname{Hom}}
\let\Tr\undefined
\newcommand{\Tr}{\operatorname{Tr}}
% !LOOM end macros
```

   At every extraction site (a bundle, a rendered fragment), loom emits `\begingroup`, the block, the node text, `\endgroup`. `\let\NAME\undefined` before each definition lets the paper's meaning hold inside the group even when the quilt defines the same name, and the quilt's meaning returns at `\endgroup`. `\DeclareMathOperator` is preamble-only under amsmath and is rewritten to `\newcommand{...}{\operatorname{...}}`; `\NewDocumentCommand` takes the same `\let\undefined` treatment.

3. Packages cannot be scoped. `% !LOOM requires:` lists the packages the digest's statements need beyond amsmath and amsthm; lint reports `loom:missing-package` (warning) for any not loaded by the quilt's preamble closure. The fix is a line in the author's preamble.
4. **[decided]** A digest with an empty macro block is macro-free; one with a nonempty block is scoped. The contract does not distinguish; porting is still a copy.
5. Rendering: arras takes one macro set per page. Loom expands block macros into fragment math where it can, passes the residue as a per-fragment macro set in the manifest, and falls back to the SVG route (Chapter 9) for anything still unrenderable.

## 8.4 Provenance

**[decided]** The header directives:

- `digest: CITEKEY` (required; marks the file as a digest and names the citekey, which must exist in the quilt's bibliography or lint reports `loom:digest-without-bib`, warning).
- `source: IDENT` (required; `arXiv:0805.2065v2`, a DOI, or `manual`).
- `method: extract | ingest | manual`.
- `created: YYYY-MM-DD`.
- `author:` (the person or run that produced it; optional).
- `requires:` (8.3).

`method: extract` implies verbatim statements from the named source. `ingest` means an agent produced or completed the file; `manual` means a person wrote it.

## 8.5 Extraction: `loom digest extract CITEKEY SRC.tex`

**[decided]** Mechanical production of a digest from the reference paper's LaTeX source (its arXiv e-print unpacked locally, or `refs/src/<citekey>/` after `digest fetch`). It is `loom import` applied to someone else's paper with proofs dropped and ids prefixed by the citekey:

1. Resolve the reference's closure from `SRC` (as 6.2.1), read its preamble closure for `\newtheorem` declarations and macro definitions.
2. Compile the reference in its own directory with `latexmk` to obtain its `.aux`; if compilation fails, emulate the amsthm counters from the parsed declarations (shared counters, `[section]` resets, `\newtheorem*`) to number results, and record `method: extract` with `numbering: emulated` in the header. **[deferred]** The emulator's fidelity on unusual numbering; verify on the Manolache fixture.
3. For every theorem-like environment: build an external node with id `<citekey>-<abbrev>-<number>` where `abbrev` is a fixed map from display name (`thm`, `lem`, `prop`, `cor`, `def`, `rem`, `ex`, `constr`, `conj`) and `number` is the `.aux` number (`4.1`); title `{\cite[<Name> <number>, p.~<page>]{citekey}}`; body the environment's contents with macros expanded (8.3.1), labels and `\eqref`s prefixed, and `\ref`s to the paper's own results rewritten to the corresponding digest ids; proofs dropped, except that each `\ref` inside a dropped proof becomes a `\uses` entry on the node (so the paper's internal dependencies are recorded mechanically).
4. Sectioning: the paper's sections become section nodes `<citekey>-sec-<number>` containing their results; prose between results is dropped, except that the first section's or introduction's opening paragraphs are placed under `\section*{Overview}` as a starting point the human will rewrite. **[assumed]** This rule; the overview is the digest author's and the extractor only seeds it.
5. Standing assumptions: text the extractor cannot attribute to a numbered result is not guessed; it writes an empty `<citekey>-setup` node with a `\incomplete{Standing assumptions not extracted; see Section 2 of the paper.}` marker for ingest or a person to fill. **[assumed]**
6. Write the macro block from the unexpandable residue and `requires:` from the reference's `\usepackage` lines minus amsmath and amsthm and minus packages the quilt already loads.
7. Write `refs/<citekey>.tex`, run lint on it, and report: results extracted by taxon, `\uses` recorded, expanded macros, block size, packages required, and anything skipped.

`digest extract` refuses if `refs/<citekey>.tex` exists (`--to` writes elsewhere).

## 8.6 Ingest

**[decided]** Ingest is an AI mode (Chapter 11), not a command. It has two uses:

1. Producing a digest when only a PDF exists: the agent reads `refs/pdf/<citekey>.pdf` (or its extracted text), writes `refs/<citekey>.tex` in the run directory following this chapter's format, with `method: ingest`, and the person promotes it. The mode's instructions require: full statements including hypotheses; the paper's own numbering as locators; a `-setup` node; `\uses` where the paper states dependencies; macro-free LaTeX; no proofs.
2. Completing an extracted digest: the agent reads the extracted file and the paper, and fills what extraction could not: the `-setup` node, missing `\uses` (a theorem's proof invokes lemmas it never `\ref`s, which the extractor could not see), and the overview. The output is a proposed diff against `refs/<citekey>.tex`, applied by the person.

The `\uses` completeness check is the audit mode's uses-ledger (Chapter 11) applied to the reference paper's proofs before they are dropped; the extractor records what `\ref` says, ingest adds what the prose says.

## 8.7 Postnote edges

**[decided]** `\cite[POSTNOTE]{citekey}` in any region creates an edge to the digest node whose locator matches `POSTNOTE`, when a digest for `citekey` exists.

Matching:

1. Normalize both the postnote and every digest node's locator: lowercase; expand abbreviations (`thm`, `theorem`; `lem`, `lemma`; `prop`, `proposition`; `cor`, `corollary`; `def`, `defn`, `definition`; `rem`, `remark`; `ex`, `example`; `sec`, `section`; `eq`, `equation`); remove `~`, periods after abbreviations, parentheses, and the words `see`, `cf`, `also`; drop page references (`p.~12`, `pp.~12--14`); collapse whitespace.
2. Match if the normalized postnote equals the normalized locator, or equals `<taxon> <number>` for the node.
3. A postnote naming several results (`Theorems 4.1 and 4.3`) creates an edge to each that matches; **[assumed]** split on `and`, `,`, `;`.
4. No match, or a citekey with no digest: `loom:unmatched-postnote` (warning) with the postnote text, or `loom:undigested-citekey` (info) for the citekey.
5. `\uses{<citekey>-thm-4.1}` is the explicit fallback and always works.

Examples: `\cite[Theorem 4.1]{Man12}` matches `Man12-thm-4.1`; `\cite[Thm.~4.1, p.~12]{Man12}` matches the same; `\cite[Section 4]{Man12}` matches `Man12-sec-4`; `\cite{Man12}` with no postnote creates no edge (it is a citation of the paper, not of a result) and no diagnostic.

## 8.8 Versioning

**[decided]** The digest's `source:` names the version it was made from. The bibliography entry's `eprint` (and `version` if present; **[assumed]** also a trailing `vN` on the eprint) names the version the paper cites. When both are known and differ, lint reports `loom:version-mismatch` (warning), since numbering may have changed between versions. When a cited paper has no digest, `status --undigested` lists it; this list is the ingest trigger an agent acts on.

## 8.9 Fetching

**[decided]** Loom fetches nothing unless `[refs] fetch = true`. Then `loom digest fetch CITEKEY` retrieves, by the arXiv identifier in the bib entry, the e-print source into `refs/src/<citekey>/` (gitignored) and, with `--pdf`, the PDF into `refs/pdf/<citekey>.pdf` (gitignored). No other command touches the network. **[assumed]** arXiv's e-print URL and rate limits are followed; a `User-Agent` naming loom is sent.

## 8.10 The library quilt and porting

**[decided]** A library quilt is a quilt with no masters: `config.toml`, `loom.sty`, a minimal preamble-like file declaring the standard taxa for lint's benefit (**[assumed]** `library.tex` at the root containing only `\newtheorem` declarations and `% !LOOM ignore`, or a `[quilt] library = true` flag; the decision is deferred), `refs.bib`, and `refs/`. It is where digests are kept once per paper, viewable in arras like anything else, and the source of every port.

**[decided]** `loom digest import PATH [--as CITEKEY]` copies a digest into the quilt's `refs/`, rewriting the id prefix, all prefixed labels, and the `digest:` directive if `--as` renames the citekey (because the two quilts' bibliographies use different keys), remapping environment names by display name, and reporting `requires:` against the quilt's preamble. Exporting is `cp`.

## 8.11 Digests in bundles and closures

**[decided]** An external node reached by a postnote edge or `\uses` is in the referencing key's closure like any node. A bundle includes its statement, wrapped in the digest's macro block group (8.3.2). Its `requires:` packages must be loaded by the bundle's preamble, which is the master's; a missing one fails the bundle compile with `loom:missing-package` named first in the diagnostics.

## 8.12 Digests in arras

Digest nodes are nodes: a page each, with the locator in the header, links from every `\cite[postnote]` that resolves to them, and dependents listing the quilt's keys that use them. The digest file's outline renders as a document view (the reference's table of results), reachable from a "References" index listing every citekey with a digest and every citekey without one. Arras knows none of this as "digests"; it renders section nodes containing nodes, an index of a taxon, and edges.

## Open questions

- Whether a library quilt should be a flag in config or recognized by having no masters. **[deferred]**; both are trivial; decide when the first library exists.
- The abbreviation map for extracted ids (8.5.3) and whether an author may override it. **[assumed]** Fixed map; unknown display names use the lowercased environment name.
- Whether extraction should keep proofs in a separate, gitignored `refs/src/` form for ingest to read. **[assumed]** Ingest reads the fetched source or PDF directly; no third form.
- How the overview should be seeded when a paper has no introduction. **[assumed]** Empty `\section*{Overview}` with an `\incomplete` marker.
- Locator normalization for non-English abbreviations and for results numbered by letters (`Theorem A`). **[deferred]**; the matcher is a table and the table grows.

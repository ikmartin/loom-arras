# 5. The source contract

This chapter specifies what loom reads from LaTeX and what an author must do for loom to read it. It is the longest chapter because it is the whole of what an author has to know, and the README's contract page is a one-page summary of it. Principle P1 governs: everything here is a label, an environment, a citation, a comment, or one of three macros.

## 5.1 What is scanned

1. **[decided]** Every file with extension `.tex` under the quilt root is scanned, at any depth, except files under `build/`, `.loom/`, `.claude/`, and tooling directories at any depth, files under `ai/`, `refs/src/`, and `refs/pdf/` at the root (4.1.2, DR-70), and files with `% !LOOM ignore` in their first twenty lines. A file is decoded as UTF-8, else as Mac Roman, else as Latin-1, and a fallback is reported as `loom:non-utf8-source` (warning) (DR-47). Comments are then blanked to spaces of equal length, so that offsets are stable and no later stage sees a comment; directives are read from the raw text (DR-48).
2. **[decided]** Files reached from a master through `\input`, `\nest`, or `\include` are scanned in the context of that master (5.9). Files reached from no master are scanned on their own, sectioned per file (5.9.2), and reported as loose: one `unreachable` (info) per file, listing its node keys. Digest files are loose by construction and are not reported (DR-51).
3. **[decided]** Local `.sty` and `.cls` files that a master's preamble closure loads, transitively (a local style may load another), are read for declarations (5.5) and macro definitions (Chapter 9) only. They never contain nodes (DR-46).
4. **[decided]** The scanner is a restricted parser, not a TeX interpreter. It recognizes the constructs in this chapter by their surface form, reading by character offset rather than by line, and treats what it does not recognize as prose (DR-40).

## 5.2 Nodes

A node is one of:

- a theorem-like environment: `\begin{ENV}` ... `\end{ENV}` where `ENV` is declared by `\newtheorem` (or `\declaretheorem`) in the preamble closure of any master, or by a `% !LOOM environment:` directive (5.5);
- a sectioning unit: the span from a sectioning command (`\part`, `\chapter`, `\section`, `\subsection`, `\subsubsection`, `\paragraph`, `\subparagraph`, starred or not) to the next sectioning command of equal or higher level, or to `\end{document}`, or to the end of the including region (5.9).

Rules:

1. **[decided]** A theorem-like environment is a node whether or not it has a label. With an id-shaped first label it has an id; otherwise it has a qualified key (5.3.4) and lint reports `loom:unlabelled-node` (info).
2. **[decided]** A sectioning unit is a node whether or not it has a label. `loom id` and `loom import` label sectioning commands as well as environments.
3. **[decided]** Line anchoring: `\begin{ENV}` and `\end{ENV}`, and those of `proof`, each stand alone on their line (leading whitespace permitted; a trailing comment permitted; the optional argument and any `\label`s may follow `\begin{ENV}` on the same line, and the optional argument may span lines if it is bracket-balanced). The scanner does not need it: it reads by character offset, and a statement whose `\begin` shares a line with body text is read correctly. It is enforced where whole lines are moved: `atomize` refuses a file that violates it, naming the lines (`loom:line-anchoring`), and `import` refuses unless `--fix-anchoring` is given, in which case it rewrites the copy it makes by inserting line breaks, which does not change the typeset output (DR-40).
4. **[decided]** Environments may nest: a lemma inside a proof, a remark inside a theorem. The scanner walks a tree. A theorem-like environment inside a proof is a node in its own right, and the enclosing proof receives an implicit proof-edge to it (`via: nested`) (DR-41). A theorem-like environment must be entirely inside one file; one that opens in one file and closes in another is an error `loom:environment-spans-files`.
5. **[decided]** `proof` is not a node unless it carries an id-shaped label (5.6); it is the proof of a node.
6. **[decided]** Masters are not nodes; they are roots.

Example of a node with an id, an alias, a title, and tags:

```tex
% !LOOM tags: localization, residue
\begin{lemma}[Residue independent of embedding]\label{rl-0004}\label{lem:res-indep}
Let $\iota\colon \widetilde M \hookrightarrow P$ be an embedding as in Definition~\ref{rl-0002}. Then
$\mathrm{Res} = S \circ \sigma$ does not depend on $\iota$.
\end{lemma}
```

## 5.3 Ids

### 5.3.1 Grammar

**[decided]**

```
id      := prefix "-" local
prefix  := [A-Za-z0-9]+                 (no hyphen)
local   := loomlocal | paperlocal
loomlocal  := [0-9A-Z]{4}               (uppercase base-36, zero-padded, 0001..ZZZZ)
paperlocal := [A-Za-z0-9.]+ ("-" [A-Za-z0-9.]+)*   (a cited paper's own label, e.g. thm-4.1, setup)
```

A label is id-shaped if it matches `id`. Since `paperlocal` is broad, the scanner decides which form applies by prefix: a prefix that is the slug of a citekey (the citekey with everything but letters and digits removed) in the quilt's bibliography or in a digest header takes `paperlocal`; any other prefix takes `loomlocal`. Digest ids use the slug rather than the citekey because real citekeys contain hyphens, colons, and spaces, which the grammar forbids; two citekeys with one slug are `loom:citekey-slug-collision` (error), and the `% !LOOM digest:` directive keeps the verbatim citekey (DR-45). A label like `lem:res-indep` is not id-shaped (it contains a colon). A label like `sec-intro` is id-shaped by grammar (`sec` prefix, `intro` local) only if `sec` is a citekey slug; otherwise `intro` fails `loomlocal` and the label is an alias. **[assumed]** This rule; it keeps human labels with hyphens from being mistaken for ids.

### 5.3.2 Allocation

1. **[decided]** `loom new` allocates the next id under a prefix: the maximum, in base-36 order, over every id it can see under that prefix, plus one. The set it sees: ids defined in the source; ids that are ledger keys; ids targeted by annotations; ids referenced anywhere in the source by `\ref`, `\eqref`, `\cref`, `\autoref`, `\uses`, or a matched postnote, including references that dangle; and, when git is present, ids referenced anywhere in the repository's history.
2. **[decided]** Nothing is stored. The maximum is recomputed on every call.
3. **[decided]** Consequence: an id is reused only when nothing can point at it. A node created and deleted without ever being referenced, accepted, or annotated frees its number; a node that anything ever pointed at never does.
4. **[decided]** `--prefix P` allocates under `P`; otherwise `[quilt] prefix`.
5. **[decided]** Lint reports `loom:prefix-is-citekey` (warning) when the quilt's prefix equals a citekey in the bibliography, since digest ids use citekeys as prefixes.
6. **[deferred]** The git history check's exact query (`git log -S` per candidate is slow; a single pass building the referenced-id set may be needed). Implement the simple form; optimize if allocation takes more than a second.

Example: ids visible under `rl` are `rl-0001` through `rl-000Z` and a dangling `\ref{rl-0012}`. `loom new lemma` creates `rl-0013`.

### 5.3.3 Permanence

1. **[decided]** Ids are never renamed. Renaming is deletion plus creation, and lint reports the dangling references that result.
2. **[decided]** An id is unique across the quilt: defined by at most one node in all scanned files together, including digests and loose files. Two definitions are `duplicate-id` (error), naming both locations.

### 5.3.4 Qualified keys

**[decided]** Things without ids are addressed internally by qualified keys, never written to source:

- an unlabelled theorem-like node: `<file>#<env>:<n>` (`drafts/main.tex#lemma:3`, the third lemma in that file);
- an untagged sectioning unit: `<file>#<label>` if it has any label, else `<file>#<command>:<n>` (`drafts/main.tex#subsection:2`, the second subsection in that file);
- a labelled equation or other labelled region: `<container key>#<label>` (`rl-0004#eq:main`, `drafts/main.tex#eq:intro`);
- an unlabelled proof: `<id>/proof`, `<id>/proof/2`, ... in document order.

Qualified keys are stable only while the structure they name is stable; ids are the stable address.

## 5.4 Labels and aliases

1. **[decided]** The first `\label` in a theorem-like environment or immediately after a sectioning command is the node's identity if id-shaped. All other `\label`s in the same environment or on the same sectioning command are aliases. Multiple labels on one environment are legal LaTeX; each refers to the same number. Labels are read as TeX reads them: runs of whitespace inside the braces, a line break included, collapse to one space (DR-45).
2. **[decided]** A `\label` "immediately after" a sectioning command means on the same line as the heading, else on the next non-blank line, unless that line opens an environment or another heading, in which case the heading has no label and the label belongs to what that line opens (DR-43). `loom id` and `loom import` insert a heading's id label directly after the heading's arguments, ahead of any label the author already placed there, so that the id is the first label under this rule (DR-64).
3. **[decided]** References through an alias resolve to the node. Lint never asks an author to change an alias.
4. **[decided]** Labels inside an environment nested in a node's text (equation labels, item labels) are free-form and belong to the node as regions (5.8). No namespacing is required; `loom new` skeletons use `<id>-eq-<name>` by convention.
5. **[decided]** Merging node B into node A is: delete B's region, add `\label{B}` inside A's environment. B becomes an alias of A; the ledger's rows for B remain as history; `status` shows B as an alias.

## 5.5 Taxa and style classes

### 5.5.1 Discovery

1. **[decided]** Taxa are discovered from the preamble closure of each master: the master's text before `\begin{document}`, every `\input` in it, every `\usepackage` or `\RequirePackage` that resolves to a local `.sty` (comma lists and lists spanning lines included), a local `.cls` named by `\documentclass`, and, transitively, whatever those local files load in turn. The scanner does not read system packages (DR-46).
2. **[decided]** Recognized declarations: `\newtheorem{ENV}{Name}`, `\newtheorem{ENV}[counter]{Name}`, `\newtheorem{ENV}{Name}[section]`, `\newtheorem*{ENV}{Name}`, and thmtools' `\declaretheorem[name=Name, ...]{ENV}` and `\declaretheorem{ENV}` (name defaults to `ENV` capitalized). The taxon is `Name`. When `Name` is a zero-argument macro of the closure, it is expanded; otherwise `ENV` capitalized is used and lint reports `loom:taxon-name-macro` (info) (DR-46). The environment name `ENV` is the author's private abbreviation; two authors writing `\begin{lem}` and `\begin{lemma}` produce nodes of the same taxon `Lemma`.
3. **[decided]** The style class is the argument of the most recent `\theoremstyle{...}` before the declaration, defaulting to `plain`. thmtools' `style=` key is honoured. A style other than `plain`, `definition`, or `remark` is treated as `plain`; lint reports `loom:unknown-theoremstyle` (warning) unless `\newtheoremstyle` in the closure declared it (DR-46).
4. **[decided]** Style class `plain` means the node owes a proof; `definition` and `remark` mean it does not.
5. **[decided]** An environment no master declares is prose, since without a declaration nothing says it is theorem-like. The exception is a list of common theorem-like names (`theorem`, `thm`, `lemma`, `lem`, `proposition`, `prop`, `corollary`, `cor`, `definition`, `defn`, `remark`, `rmk`, `example`, `conjecture`, `claim`, `question`, `notation`, `construction`, `convention`, `assumption`, `fact`, `observation`, `setting`, `condition`, `problem`, `exercise`, and their usual abbreviations): a node using one of these that no master declares is `loom:unknown-environment` (error), once per environment name per file (DR-53). The fallback is a directive in the master: `% !LOOM environment: ENV = Name, style` (one per line; `style` defaults to `plain`), which declares the taxon unless the closure already does. This is the only taxon configuration.
6. **[decided]** Different masters may declare different taxa. A node reached by two masters has the taxon each master declares; if they disagree, lint reports `loom:taxon-conflict` (warning) and the default master's declaration is used in the manifest.
7. **[decided]** The same closure supplies the macro table (Chapter 9). Definitions are read from `\newcommand`, `\renewcommand`, `\providecommand`, `\DeclareRobustCommand`, `\def`, `\let`, `\DeclareMathOperator`, and xparse's `\NewDocumentCommand` family, and through any alias of a definition command declared by `\newcommand{\nc}{\newcommand}`, `\let\nc\newcommand`, or `\def`, resolved transitively, so that a preamble defining its macros through `\nc` and `\renc` is read in full (DR-73).

### 5.5.2 Consequences for lint

- A `plain` node with no attached proof, no `\incomplete`, and no citation in its title or as its first body token is a gap: `loom:missing-proof` (warning).
- A `plain` node with no proof whose title contains `\cite`, or whose body begins with `\cite` (`\begin{theorem}\cite[Theorem 4.1]{Man12} ...`, the form every real instance takes), is an external node (Chapter 8), not a gap (DR-42).
- A `definition`- or `remark`-style node with a proof is `loom:unexpected-proof` (info).

Example, from an author's `math-thms.sty`:

```tex
\theoremstyle{plain}
\newtheorem{thm}{Theorem}[section]
\newtheorem{lem}[thm]{Lemma}
\newtheorem{prop}[thm]{Proposition}
\theoremstyle{definition}
\newtheorem{defn}[thm]{Definition}
\newtheorem{constr}[thm]{Construction}
\theoremstyle{remark}
\newtheorem{rmk}[thm]{Remark}
```

Taxa: Theorem, Lemma, Proposition (plain); Definition, Construction (definition); Remark (remark).

## 5.6 Proofs

### 5.6.1 Attachment

**[decided]** A `proof` environment is attached to a node by the first of these rules that applies:

1. Reference: its optional argument contains `\ref{X}` (or `\cref`, `\Cref`, `\autoref`, `\eqref`) where `X` is an id or alias of a theorem-like node; the proof may be anywhere in the quilt. Example: `\begin{proof}[Proof of Theorem~\ref{rl-0003}]`. When the argument names several nodes, the proof attaches to the first that resolves and lint reports `loom:multi-target-proof` (warning). When every label it names is unknown, each is reported as `dangling-link` and the proof attaches by position, as if the argument were absent, since a deferred proof with a typo in its `\ref` still sits where the author put it (DR-63).
2. Adjacency: it immediately follows a theorem-like node among its siblings in the same file (only blank lines, comments, or directives between `\end{ENV}` and `\begin{proof}`), or immediately follows a proof that itself attached by adjacency, in which case it attaches to the same statement (5.6.2).
3. Enclosure: it sits directly inside a theorem-like node with no theorem-like sibling before it, as a proof inside an `example` environment does; it attaches to the enclosing node (DR-41).

A `proof` that no rule places is `loom:unattached-proof` (error).

### 5.6.2 Multiple proofs

1. **[decided]** A node may have any number of proofs. Unlabelled proofs are keyed `<id>/proof`, `<id>/proof/2`, `<id>/proof/3`, ... in document order of the default master (or of the file, for loose material).
2. **[decided]** Positional keys are fragile under deletion or reordering. Lint reports `loom:positional-proof-key` (info) whenever a node has more than one unlabelled proof, suggesting labels.
3. **[decided]** A `proof` environment whose first `\label` is id-shaped is a node of taxon `Proof`, keyed by its id, attached to its statement by rule 5.6.1, and may live in its own file.
4. **[decided]** Edges inside a proof belong to that proof, so the graph records which lemmas each proof uses.
5. **[decided]** Loom recovers from positional shifts by hash: an acceptance row whose recorded hash equals the current text of a differently keyed proof is reported by `status` as "acceptance recorded under a previous key; re-accept to confirm".
6. **[decided]** A more detailed proof of the same statement is a second labelled proof; a more detailed node with a different statement is linked with `% !LOOM see:` (5.11.3).

### 5.6.3 Proof files

**[decided]** `atomize` writes an adjacent proof into the same file as its statement, and a deferred proof into `nodes/<id>.proof.tex` (`nodes/<id>.proof.2.tex` for the second), containing the proof environment unchanged. No label is inserted. With `--proofs separate`, every proof goes to its own file.

## 5.7 Edges

### 5.7.1 Sources of edges

**[decided]** An edge goes from a region (a statement, a proof, or the prose of a section or master) to a node. Edges are read from each region's own text from `\begin{document}` on; a master's preamble yields none, since macro bodies there contain `\ref{#1}` and the like (DR-50). Its sources:

1. `\ref{X}`, `\eqref{X}`, `\autoref{X}`, `\pageref{X}`, `\vref{X}`, which take one label each, however it is spelled (a label may contain a comma), and `\cref{X, Y}` and `\Cref{X, Y}`, which take a comma-separated list (DR-50). `X` resolves to a node's id or alias, or to a labelled region inside a node (5.8), in which case the edge goes to the node that owns the region (the proof key, when the region lies in a proof).
2. `\uses{X, Y, ...}`: each item resolves as above. `\uses` is the way to record a dependency the text does not express.
3. `\cite[postnote]{citekey}`, in any of the natbib and biblatex spellings (`\citep`, `\citet`, `\parencite`, `\textcite`, `\autocite`, ...), where a digest for `citekey` exists and the postnote matches the locator of one of its nodes (Chapter 8). The edge goes to that digest node, a result or one of the digest's section nodes.
4. Nesting: a theorem-like node directly inside a proof gives the proof an implicit proof-edge to it, `via: nested` (DR-41).

A node never has an edge to itself, and a proof has none to its own statement (DR-50).

### 5.7.2 Classification

1. **[decided]** An edge is a statement-edge if it occurs in a statement's own text, a proof-edge if in a proof's own text, and a prose-edge if in a section's own text or in master prose outside every section.
2. **[decided]** The closure of a key is the transitive closure over statement-edges from the key's statement (for a proof key, from its statement) together with the direct proof-edges of the proof. Definitions and setup nodes reach a bundle through statement-edges; lemmas a proof cites reach it through proof-edges. Relations declared with `see:` are not edges and enter no closure.
3. **[decided]** An `\eqref` to an equation inside another node's proof is a proof-dependency on that node's proof; lint reports `loom:equation-in-proof-referenced` (warning) because a proof may be rewritten and take the equation with it. It is never an error.

### 5.7.3 Resolution

1. **[decided]** A reference to a label that is neither a node's id or alias nor a labelled region in any scanned file is `dangling-link` (error), with the file, line and column of the command (DR-97).
2. **[decided]** A reference to a node that the referencing master does not reach is `loom:reference-to-loose` (error for masters, since the PDF will have an undefined reference; info for loose files), unless the target lives in a digest file, whether it is a result or one of the digest's section nodes, because digests are loose by construction (DR-76).
3. **[decided]** Lint reports, as information, `\ref`s in a proof not listed in that proof's `\uses` (`loom:uses-missing`) and `\uses` entries never mentioned in the proof's text (`loom:uses-unused`), so an author may adopt either discipline.

Example of the three edge sources in one proof:

```tex
\begin{proof}
\uses{rl-0002}
By Lemma~\ref{lem:res-indep} and \cite[Theorem 4.1]{Man12}, the pullback commutes with ...
\end{proof}
```

Edges from this proof: to `rl-0002` (uses), to `rl-0004` (through the alias), to `Man12-thm-4.1` (postnote, if the digest exists; otherwise `loom:undigested-citekey`, info; a digest that exists but has no node matching the postnote is `loom:unmatched-postnote`, warning).

## 5.8 Equations and other labelled regions

1. **[decided]** A labelled display equation (`equation`, `align`, `gather`, `multline`, and their starred forms with `\tag`, or any environment containing `\label` that is not theorem-like or sectioning) is a region belonging to the node whose own text contains it, addressed by the qualified key `<container>#<label>`.
2. **[decided]** Labels are free-form. `\label{eq:main}` is fine. Lint enforces uniqueness of all labels across the whole quilt (`duplicate-id` for ids, `loom:duplicate-label` for others), which is stricter than LaTeX, because bundles and pages combine regions the master never compiles together.
3. **[decided]** Referencing an equation from another node creates an edge to the containing node (5.7.2). The bundle for the referencing key includes the equation's containing statement; if the equation is in a proof, the bundle includes the equation region itself.
4. **[decided]** Equations in master prose are regions of the master. A node referencing one creates a prose-dependency; the bundle includes the equation region.
5. **[decided]** Figures, tables, and `\item` labels are treated identically: free-form labels, container-qualified, referenceable.
6. **[decided]** Equations are annotation targets (Chapter 7) but never ledger keys.

## 5.9 Inclusion

### 5.9.1 Mechanisms

**[decided]** A node includes another when the child's region lies inside the parent's, arising from:

1. `\input{path}`: the file at `path`, root-relative, is spliced at that point. The path is resolved as TeX resolves it: as written first, then with `.tex` appended; the primitive braceless form `\input path` is accepted. A name that resolves to no file in the quilt but that `kpsewhich` finds is a system file and is ignored; a file that is not `.tex` (a `\input{fig.pspdftex}` figure) is an opaque inclusion, recorded in the tree but never scanned for nodes (DR-44).
2. `\nest{path}`: as `\input`, with every sectioning command in the file, and in files it includes, shifted one level down (`\section` becomes `\subsection`, and so on; `\chapter` becomes `\section`). Shifts compose.
3. `\include{path}`: as `\input` for the scanner's purposes; loom never writes it.
4. Sectioning nesting: a `\subsection` unit lies inside the preceding `\section` unit, on the expanded document.

### 5.9.2 Regions on the expanded document

1. **[decided]** Theorem-like environments and proofs are found per file, since they may not span files.
2. **[decided]** The sectioning hierarchy is computed on the expanded text of each master, because sectioning is linear: a `\subsection` in the master after an `\input` line belongs to the section the input file opened. The scanner expands a master with a source map (file and offset per character) and computes sectioning levels with level shifts applied. A section's parent and children are therefore per master; its own text is not (5.9.3) (DR-49).
3. **[decided]** Files reached from no master are sectioned per file, the file path standing in for the master, so that their headings are section nodes too: a digest's headings are its `<slug>-sec-<n>` nodes (8.3.1), and `loom id` can label a heading in a file no master includes (DR-62).
4. **[decided]** A file reached from two masters may have different sectioning contexts in each; the hierarchy is computed per master, while ownership (5.9.3) is per file and the same under every master (DR-49).
5. **[decided]** The source map is a list of segments (file, start offset in the file, length, start offset in the expansion, level shift); the expanded text keeps every reached file's text exactly once, each child spliced right after its inclusion command. A full scan of the imported ACGS paper (4567 lines, 23 files in the closure) takes about a second and well under 100 MB (settled at M4).

### 5.9.3 Ownership

**[decided]** Ownership is a partition of each file. The claimants are the theorem-like environments, proofs, and sections of the file, and the file itself as the outermost claimant (a master owns its preamble and every character outside all sections); every character belongs to the innermost claimant containing it, and a node's own text is its region minus its children's regions. A section's region runs from its heading to the next heading of equal or higher level whose heading is in the same file, or to the file's end (`\end{document}` in a master); its parent and children come from the expanded master (5.9.2). Ownership therefore never depends on which master reached a file, and neither do the hashes taken over own text (5.13) (DR-49). Annotations anchor into own text; hashing uses own text with inclusions replaced by their inclusion lines.

### 5.9.4 Uniqueness and cycles

1. **[decided]** Within one master's inclusion tree, every node appears at most once. A node reachable under two parents in the same master is `double-inclusion` (error), naming both paths. LaTeX itself defines the label twice and numbers the theorem twice; the paper is already wrong.
2. **[decided]** The same node reached by two different masters is fine.
3. **[decided]** Inclusion is acyclic. A cycle is `inclusion-cycle` (error); the scanner stops expanding where the cycle closes and continues with the rest of the quilt.
4. **[decided]** An `\input` whose file does not exist is `missing-include` (error), unless `kpsewhich` knows the name (5.9.1); an absolute path or one containing `..` is missing by definition.

### 5.9.5 Numbering

**[decided]** Loom never computes theorem or section numbers. After a master compiles, its `.aux` contains `\newlabel{rl-0004}{{3.4}{12}}`; loom reads the number and page for every id and alias from it. A node reached by several masters has a number per master. Before the first compile, numbers are absent in the manifest and arras shows ids alone.

### 5.9.6 `% !TEX root`

**[deferred]** A file that is not a master and contains `% !TEX root = <path>` in its first twenty lines was to be recorded as belonging to that master, so that a loose file could say which master it was written for without changing reachability. The directive is parsed (`scan/directives.py`) and nothing consumes it yet; the manifest has no field for it (M7).

## 5.10 Digest nodes

Digests are specified in Chapter 8. For the source contract, a digest node is an external node: every theorem-like environment in a file with a `% !LOOM digest:` header is external, with no proof, a title carrying `\cite[LOCATOR]{citekey}`, and an id of the form `<slug>-<paperlocal>`, where the slug is the citekey stripped to letters and digits (5.3.1, DR-45). Its labels and `\eqref`s are prefixed with the slug at extraction time so that digests from different papers coexist in one bundle. Digest files are loose by construction: they are not reported `unreachable` (DR-51), and a reference to one of their nodes is never `loom:reference-to-loose` (DR-76).

## 5.11 Directives

### 5.11.1 Grammar

**[decided]** A directive is a line whose first non-whitespace characters are `% !LOOM` (or `%!LOOM`), followed by one of three forms:

```
bare:       % !LOOM ignore
region:     % !LOOM begin macros      ...      % !LOOM end macros
key-value:  % !LOOM tags: localization, residue
```

Rules:

1. One key per line. Values are trimmed. List values are comma-separated; items may contain hyphens and periods but not spaces or commas.
2. Keys are lowercase ASCII with hyphens. Unknown keys are `loom:unknown-directive` (warning), never ignored silently.
3. Directives are declarations. No directive causes loom to act, and no directive changes typeset output (P10).
4. `% !TEX root = ...` and `% !TEX program = ...` are read in their own `=` form. No other `% !TEX` key is read.

### 5.11.2 Scope

**[decided]**

- File-level: a directive in the first twenty lines of a file, before any node begins, applies to the file (`ignore`, `digest`, `source`, `method`, `requires`) or to every node the file defines (`author`, `created`, `tags`).
- Node-level: a directive inside a node's own text applies to that node, overriding a file-level value of the same key.
- Region: `begin X` ... `end X` pairs; only `macros` is defined.

### 5.11.3 Inventory

**[decided]** The directives that exist:

| directive | form | scope | meaning |
|---|---|---|---|
| `ignore` | bare | file | do not scan this file |
| `author: NAME[, NAME]` | key-value | file or node | author(s) of the node(s) |
| `created: YYYY-MM-DD` | key-value | file or node | creation date |
| `tags: a, b` | key-value | file or node | thematic labels |
| `see: ID, ID` | key-value | file or node | related nodes for the viewer; never a dependency |
| `environment: ENV = Name, style` | key-value | master file | declare a taxon the preamble does not (5.5.1) |
| `digest: CITEKEY` | key-value | digest file | this file is the digest of CITEKEY |
| `source: IDENT` | key-value | digest file | provenance, e.g. `arXiv:0805.2065v2` |
| `method: extract\|ingest\|manual` | key-value | digest file | how the digest was produced |
| `requires: pkg, pkg` | key-value | digest file | packages the digest's statements need |
| `numbering: emulated` | key-value | digest file | the results were numbered by counter emulation because the reference produced no `.aux` (8.5.2, DR-68) |
| `begin macros` / `end macros` | region | digest file | scoped macro block |

Any other key is unknown.

**[decided]** `see:` declares a relation, not a dependency. Each item resolves like a reference: an id, an alias, or a digest node id; an item that names nothing is `dangling-link`, and one that names the node it is written in, or repeats a relation already declared there, is `loom:see-redundant` (info). A relation enters no closure, no bundle, no acceptance row and no staleness computation, so a detailed version of a result may change freely without making the compact version stale. It is stored once, on the declaring node, and a viewer shows it on both. `\uses` remains the only way to declare a dependency the text does not name.

## 5.12 Macros

**[decided]** Three commands, provided by `loom.sty` (4.5). What the scanner does with each:

- `\uses{X, Y}`: an edge from the enclosing region to each item, resolved as a reference. Inside a digest node, records the reference paper's internal dependency.
- `\incomplete{TEXT}`: marks the enclosing key (statement or proof) as incomplete; `TEXT` is shown by `status`, the review panel, and the blockers page. A key with `\incomplete` displays as incomplete regardless of the ledger and can never display as proved or settled.
- `\nest{PATH}`: an inclusion with level shift one (5.9.1).

No other macro has meaning to the scanner. `\todo` from `todonotes` is ignored.

## 5.13 Text normalization and hashing

**[decided]** Where loom hashes text (acceptance rows, annotation target hashes, snapshots), it hashes the normalized own text of the region:

1. Inclusion lines (`\input`, `\nest`, `\include`) are kept as written; the included text is not part of the parent's own text. A child claimant in the same file (a nested environment, a proof, a subsection) is replaced by the line `% !LOOM child: <key>`, so that a structural change changes the parent's hash.
2. Comment lines that are not directives are removed; directives are kept. Comments are in any case invisible to every earlier stage, having been blanked when the file was read (5.1.1), so a commented-out environment defines no node and no label (DR-48).
3. Trailing whitespace is removed; runs of blank lines collapse to one; tabs become spaces.
4. Line endings are normalized to `\n`.
5. The hash is SHA-256 of the UTF-8 bytes, written as `sha256:<hex>`.

The preamble closure's hash is the hash of the concatenation of the normalized preamble text of the master followed by the included fragments in inclusion order, including `loom.sty`.

**[assumed]** Whitespace inside a line is not normalized, so a reflowed paragraph changes the hash. Reflow is an edit; the author re-accepts.

## 5.14 Lint

Lint is the set of checks performed on every scan, together with the checks that need the review records (Chapter 7): detached annotations, retired ledger keys, previous-key matches, and foreign annotation files are reported by `loom lint` and `loom check` alongside the scanner's codes, not only in the manifest (DR-61). Diagnostics are published in the manifest (Chapter 9) and printed by `loom lint`. The full code table is `specs/diagnostics.md`. Reserved codes (any publisher): `duplicate-id`, `dangling-link`, `missing-include`, `double-inclusion`, `inclusion-cycle`, `unreachable` (once per loose file, never for a digest; DR-51). Loom's own codes, with severity:

- error: `loom:environment-spans-files`, `loom:unattached-proof`, `loom:unknown-environment`, `loom:reference-to-loose`, `loom:macros-unloaded`, `loom:duplicate-label`, `loom:citekey-slug-collision`, `loom:line-anchoring` (a theorem-like `\begin` or `\end` not alone on its line, reported by `import` and `atomize` only; DR-40)
- warning: `loom:missing-proof`, `loom:multi-target-proof`, `loom:equation-in-proof-referenced`, `loom:unmatched-postnote`, `loom:taxon-conflict`, `loom:prefix-is-citekey`, `loom:macro-shadowed`, `loom:unknown-directive`, `loom:unknown-theoremstyle`, `loom:non-utf8-source`, `loom:main-not-found`, `loom:dependency-cycle`, `loom:version-mismatch`, `loom:missing-package`, `loom:digest-without-bib`, `loom:foreign-annotations`
- info: `loom:unlabelled-node`, `loom:positional-proof-key`, `loom:unexpected-proof`, `loom:uses-missing`, `loom:uses-unused`, `loom:documentclass-outside-drafts`, `loom:taxon-name-macro`, `loom:retired-ledger-key`, `loom:previous-key-match`, `loom:undigested-citekey`, `loom:detached-annotation`

`loom:non-utf8-source`, `loom:unknown-theoremstyle`, `loom:taxon-name-macro`, `loom:citekey-slug-collision`, and `loom:main-not-found` were added at implementation time, each for a condition the fixture papers produce (DR-52).

`[lint] disable` silences publisher codes; reserved codes cannot be silenced.

## 5.15 Worked examples

### 5.15.1 A single-file paper

An author who writes like the Stacks project has `drafts/main.tex` and nothing else:

```tex
\documentclass{amsart}
\usepackage{amsthm}
\usepackage{loom}
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\theoremstyle{definition}
\newtheorem{definition}[theorem]{Definition}
\begin{document}

\section{Setup}\label{ab-0010}

\begin{definition}[Widget]\label{ab-0001}
A \emph{widget} is a pair $(X, \sigma)$ with $\sigma^2 = \mathrm{id}$.
\end{definition}

\section{Results}\label{ab-0011}

\begin{lemma}\label{ab-0002}\label{lem:involution-fixed}
Every widget has a $\sigma$-fixed point.
\end{lemma}
\begin{proof}
Take the orbit decomposition; since $\sigma^2 = \mathrm{id}$, every orbit has one or two points, and ...
\end{proof}

\begin{theorem}[Main]\label{ab-0003}
The fixed locus of a widget is nonempty and closed.
\end{theorem}

Closedness is \cite[Theorem 4.1]{Man12} applied to the involution.

\begin{proof}[Proof of Theorem~\ref{ab-0003}]
\uses{ab-0001}
By Lemma~\ref{lem:involution-fixed} the locus is nonempty; ...
\end{proof}

\end{document}
```

What the scanner reads: two section nodes (`ab-0010` containing `ab-0001`; `ab-0011` containing `ab-0002`, `ab-0003`, and the deferred proof); three theorem-like nodes; `ab-0002/proof` attached by adjacency with no edges; `ab-0003/proof` attached by reference, with proof-edges to `ab-0001` (uses) and `ab-0002` (alias), and the infos `loom:uses-missing` and `loom:uses-unused`, because `\uses` omits `ab-0002`, which the text references, and lists `ab-0001`, which it does not; a prose-edge from the section `ab-0011`, whose own text holds the sentence, to `Man12-thm-4.1` if `refs/Man12.tex` exists, else `loom:undigested-citekey` (info). The paper compiles from the root unchanged.

### 5.15.2 A node file

`nodes/rl-0004.tex`, as written by `loom new lemma "Residue independent of embedding"` and then filled in:

```tex
% !LOOM author: Markas Hecht
% !LOOM created: 2026-09-15
% !LOOM tags: localization, residue

\begin{lemma}[Residue independent of embedding]\label{rl-0004}
Let $\iota$ be an embedding as in Definition~\ref{rl-0002}. Then $\mathrm{Res}=S\circ\sigma$ is independent of $\iota$.
\end{lemma}
\begin{proof}
\uses{Man12-thm-4.1}
Two embeddings are dominated by a third; by \cite[Theorem 4.1]{Man12} ...
\incomplete{The domination step needs the base to be quasi-compact.}
\end{proof}
```

Keys: `rl-0004` (draft or accepted per the ledger), `rl-0004/proof` (incomplete, whatever the ledger says).

### 5.15.3 A spine with `\nest`

`drafts/main.tex` after `loom atomize`:

```tex
\section{The residue map}\label{rl-0020}

We construct the residue as a specialization followed by a Segre class.

\input{nodes/rl-0011}
\input{nodes/rl-0012}

\nest{nodes/rl-0030}

\input{nodes/rl-0013}
```

`nodes/rl-0030.tex` begins with `\section{Independence}\label{rl-0030}` and contains its own lemmas; through `\nest` it appears as a subsection of `rl-0020`. The `.aux` records `rl-0030` as, say, 3.2, and arras shows it so.

### 5.15.4 Two proofs of one theorem

```tex
\begin{theorem}\label{rl-0040}
...
\end{theorem}
\begin{proof}[First proof]\label{rl-0041}
\uses{rl-0004, rl-0012}
...
\end{proof}
\begin{proof}[Second proof]\label{rl-0042}
\uses{rl-0012}
...
\end{proof}
```

Keys: `rl-0040`, `rl-0041`, `rl-0042`. The second proof follows a proof that attached by adjacency, so it attaches to the same theorem (5.6.1). The graph shows that `rl-0004` is used only by the first proof; if the author adopts the second, `rl-0004` may become unnecessary, which `loom unravel rl-0004` reports.

## Open questions

- Whether `\pageref` should create an edge (it references a location, not a result). **[assumed]** Yes, because omitting it would leave a dangling `\pageref` undetected.
- Nested theorem-like environments: settled by DR-41; a statement inside a proof is a node with a `nested` proof-edge from the enclosing proof, and no diagnostic is reported.
- The exact set of environments treated as labelled regions in 5.8.1. **[deferred]** Start with the amsmath display environments plus `figure`, `table`, and `enumerate` items; extend from fixtures.
- Whether `\declaretheorem` with a `sibling=` or `numberwithin=` key needs anything from the scanner. **[assumed]** No; numbering comes from the `.aux`.
- Whether `import` should also insert `\label`s on `\paragraph` and `\subparagraph` units. **[assumed]** No; sections through subsubsections only, by default; `--all-levels` to include them.

# 6. Bringing a paper in

This chapter specifies how an existing paper becomes a quilt and how a quilt is reshaped afterwards: `init --from`, `import`, `id`, `atomize`, `inline`, and the identity test that governs all of them. It ends with the two conversion fixtures as they ran at M4: Manolache's virtual pullbacks paper as the first walk-through and ACGS's decomposition paper as the stress test.

The governing rule is P7: loom never modifies an author file. Every operation here either writes copies, writes to a named destination, or prints a patch.

## 6.1 `loom init DIR --from FILE`

**[decided]** Creates the quilt as in 4.7, then performs `import FILE` into it. Everything the import prints before `Wrote N files` is a plan: the file list is headed "Plan, nothing written yet", and a refusal says that nothing was written, so no reader takes the arrows for work already done. `FILE` is the paper's main `.tex` file, anywhere on disk. The two are one command because it is the common case, and they are one transaction: an import that refuses removes the files `init` had written, leaving the directory as it was found, and nothing is announced as created until the import has finished. The instinct after the anchoring refusal is to re-run the same command with `--fix-anchoring`, and a surviving skeleton would refuse that as `already inside a quilt` (DR-106). In the in-place case only what `init` itself wrote is removed; the author's paper is not `init`'s to delete. `--prefix`, `--yes`, and `--fix-anchoring` (6.2) pass through to the import; `--git` additionally makes the quilt a repository, which loom otherwise does not do (4.7).

**[decided]** `loom import FILE`, run inside an existing quilt, is the same operation without creating the quilt. It may be run more than once, for a second master or a section file that was not reached.

## 6.2 What `import` does

Given `FILE`, whose directory is called the paper directory:

1. **[decided]** Resolve the closure: `FILE`; every file it reaches through `\input`, `\include`, and `\nest` (recursively, the path as written and then with `.tex`, resolved against the paper directory, the braceless `\input name` form included); every local `.sty` named by `\usepackage` or `\RequirePackage` (comma lists included) and every local `.cls` named by `\documentclass` or `\LoadClass`, followed recursively; the `.bib` files named by `\bibliography` or `\addbibresource`; the `.bst` named by `\bibliographystyle`; and every file named by `\includegraphics` (with the usual extension search). Files outside the paper directory are reported and not copied (`loom:import-outside-tree`, warning).
2. **[decided]** Copy the closure into the quilt preserving the relative layout of the paper directory, with one exception: `FILE` itself is placed in the masters directory. If `FILE` already lives in the quilt's masters directory (the in-place case of 4.7), nothing is moved.
3. **[decided]** In the copied master, insert `\usepackage{loom}` on the line after the first uncommented `\documentclass{...}` (after its optional argument, which may span lines) unless the master, or a file of the copied closure that its preamble loads, already loads it (M7). It must be the first uncommented one: a commented-out `\documentclass` above the real one would otherwise put the package before the class and break the copy (M4).
4. **[decided]** In every copied `.tex` file, for every theorem-like environment (5.5) and every sectioning command from `\part` to `\subsubsection` that has no id-shaped label, insert `\label{<prefix>-<local>}`: for an environment, on the `\begin` line immediately after the optional argument, before any existing `\label`; for a sectioning command, directly after the heading's arguments, before any existing `\label`, so that the id is the heading's first label under the same rule that governs environments (DR-64). Ids are allocated in document order, the master first, then the files it reaches in expansion order, then any other copied `.tex` file, under `[quilt] prefix` (or `--prefix`), starting after the current maximum (5.3.2). Existing labels are left untouched and become aliases.
5. **[decided]** Show the complete diff, as a unified diff per changed file, before writing anything, and require confirmation on a terminal; `--yes` skips the confirmation for scripts, and without a terminal or `--yes` the import stops with `import needs confirmation; pass --yes`.
6. **[decided]** Set `[quilt] main` to the copied master if `main` is unset or names a file that does not exist; otherwise leave `main` alone.
7. **[decided]** Rescan and report: counts of nodes by taxon and of sectioning units by level, proofs attached by adjacency, by reference, and by enclosure (DR-41) and unattached, dangling references, citations with locators but no digest, and unknown environments.
8. **[decided]** Run the identity test (6.6) and report its result. Failure is reported, not reverted; the quilt is left as written so the author can inspect, and the command exits 1. A skipped test (no `pdftotext`, or a document that did not compile) is reported and does not fail the command.

**[decided]** `import` never: splits files, moves proofs, renames labels, reorders anything, rewrites `\ref`s, inserts anything other than the `\label` lines, the one `\usepackage` line, and, with `--fix-anchoring`, the line breaks described below (DR-40), or writes metadata headers.

**[decided]** `import` refuses, before copying anything, on: an environment whose `\begin` or `\end` is not alone on its line (`loom:line-anchoring`, with the lines listed, numbered in the author's own file as it stands on disk rather than in the staged copy, which by then carries loom's `\usepackage` line) unless `--fix-anchoring` is given, in which case the copy is rewritten so that every theorem-like `\begin` and `\end` stands alone on its line, which typesets identically because a line break is a space in TeX and the environments start and end in vertical mode (DR-40); an environment spanning files; a master that does not compile from its own directory (checked by compiling it there first, so that a broken input paper is not mistaken for a loom problem). The scanner itself reads by character offset and tolerates unanchored environments; only `atomize`, which moves whole lines, and `id`, which places labels on the `\begin` lines, insist on anchoring (DR-40).

Example session, with the numbers of the relative localization paper at M4:

```
$ loom init relloc --from ~/papers/relloc/draft3.tex --prefix rl --fix-anchoring
Resolving closure of draft3.tex ... 5 files
Plan, nothing written yet:
  draft3.tex -> drafts/draft3.tex
  preamble.tex -> preamble.tex
  math-env.sty -> math-env.sty
  base-macros.sty -> base-macros.sty
  refs.bib -> refs.bib
Compiling original in /home/mh/papers/relloc ... ok
Proposed edits (53 lines in 1 file(s)):
--- drafts/draft3.tex
+++ drafts/draft3.tex
@@ -1,4 +1,5 @@
 \documentclass{amsart}
+\usepackage{loom}
 \input{preamble}
 ...
-\begin{defn}[Fixed stack]\label{def:fixed-stack}
+\begin{defn}[Fixed stack]\label{rl-0001}\label{def:fixed-stack}
 ...
Apply? [y/N]: y
Wrote 5 files. main = drafts/draft3.tex
Nodes: 12 Lemma, 9 Remark, 8 Definition, 6 Proposition, 4 Example, 2 Theorem; 5 sections, 6 subsections
Proofs: 14 adjacent, 1 by reference, 0 by enclosure, 2 unattached
References: 1 dangling; 10 citations with locators but no digest
Identity test: pass (pdftotext identical)
```

## 6.3 `loom id FILE [--to DEST]`

**[decided]** The tagging half of `import`, for files already in the quilt: computes the label insertions of 6.2.4 for `FILE` and prints them as a unified diff to stdout, or writes the resulting file to `DEST` with `--to` (refusing if `DEST` exists). It never modifies `FILE`. It refuses a file with line-anchoring violations, naming the lines, since it places labels on those lines (DR-40). A heading's id goes directly after the heading's arguments, ahead of any label the author already placed there (DR-64), and headings in a file no master reaches are labelled too, since such a file is sectioned on its own (DR-62). The single-file author who wrote human labels applies the patch with their editor or `git apply`.

Options: `--sections` and `--no-sections` (default: sections through subsubsection are labelled); `--all-levels` (also paragraphs and subparagraphs); `--prefix P`.

Example:

```
$ loom id drafts/main.tex
--- drafts/main.tex
+++ drafts/main.tex
@@ -8,9 +8,9 @@
 \begin{document}
 \maketitle
 
-\section{Setup}
+\section{Setup}\label{ab-0001}
 
-\begin{definition}[Widget]\label{def:widget}
+\begin{definition}[Widget]\label{ab-0002}\label{def:widget}
 A widget is a gadget with a hat.
 \end{definition}
```

## 6.4 `loom atomize SRC DEST`

### 6.4.1 What it does

**[decided]** Moves each node of `SRC` into its own file under `nodes/` and writes `DEST`, a copy of `SRC` in which each moved region is replaced by an inclusion line. `SRC` is not modified. `DEST` may not exist (`atomize never overwrites`, exit 2). Both positional `loom atomize SRC DEST` and `loom atomize SRC --to DEST` are accepted; `loom atomize SRC` alone exits with code 2 and `ERROR: specify a destination file after the source, or with --to`.

Precisely:

1. **[decided]** For every theorem-like node in `SRC` with an id, the region consisting of the node's environment, any `% !LOOM` directive lines immediately preceding it (its node-level directives), and the proofs attached to it by adjacency that follow it with nothing but whitespace between, widened to whole lines, is written to `nodes/<id>.tex`, and replaced in `DEST` by `\input{nodes/<id>}` on its own line; the blank lines around the region stay where they were, so that paragraphing is unchanged. A theorem-like environment nested inside another node, and a proof attached by enclosure, travel with the enclosing node (DR-41).
2. **[decided]** For every unlabelled proof in `SRC` attached by reference (5.6.1), or whose statement lives in another file, the proof environment is written to `nodes/<statement-id>.proof.tex` (or `.proof.2.tex`, ..., by ordinal), replaced by an `\input` line at its original position. No label is inserted.
3. **[decided]** A labelled proof (a proof node) is treated as a node: `nodes/<proof-id>.tex`.
4. **[decided]** With `--proofs separate`, adjacent proofs are also moved to their own files, so that `DEST` has an inclusion line per statement and per proof.
5. **[decided]** Sectioning units are not moved by default. With `--sections`, each section and subsection with an id in `SRC` is moved to `nodes/<section-id>.tex` containing the section's own text (its heading, prose, and the inclusion lines for its children; a subsection's file is included from its section's file), and replaced by `\input{nodes/<section-id>}`; headings are copied verbatim, so `\input` reproduces the document. **[decided]** `--sections` acts on sections and subsections, not deeper (settled at M4).
6. **[decided]** Nodes without ids are not moved; `atomize` lists them (`Not moved (no id): ...; run loom id first`) and lint reports them.
7. **[decided]** `--ignore-src` writes `% !LOOM ignore` above `SRC` once its nodes have moved, so the quilt keeps one definition of each node; without it the printed note says the quilt now holds two copies of everything moved and names the flag (DR-88). Files `SRC` includes are not touched; `atomize` acts on one file. `--all` acts on `SRC` and every file it reaches, writing each spine to the same relative path under a destination directory (`loom atomize --all drafts/draft3.tex --to-dir atomized/`).
8. **[decided]** Written node files end with one newline and no trailing blank line (M4); `DEST` places each inclusion line where the region's first line was. A `% !LOOM` file-level directive block at the top of `SRC` stays in `DEST`; node-level directives travel with their nodes.
9. **[decided]** Afterwards, the identity test compares `DEST` against `SRC`: directly when `SRC` is a master; otherwise through the first master that reaches `SRC`, compiled as it is and again in a scratch copy of the quilt where `DEST`'s text stands at `SRC`'s path; when no master reaches `SRC` the test is reported skipped (DR-65). `atomize` refuses to write anything if `SRC` has line-anchoring violations or spans, naming the lines (DR-40). It ends by noting that `SRC` still defines its ids inline.
10. **[decided]** `atomize` allocates no ids and inserts no labels.

### 6.4.2 Naming inside `nodes/`

**[decided]** `nodes/<id>.tex` for nodes; `nodes/<id>.proof.tex`, `nodes/<id>.proof.2.tex` for unlabelled proofs. If a target file exists, `atomize` refuses before writing anything (`loom:atomize-target-exists`, exit 1).

### 6.4.3 The typical use

The relative localization paper at M7 (step 2 of 13.6):

```
$ loom atomize drafts/draft3.tex drafts/draft4.tex --sections
Moved 52 nodes and 3 deferred proofs to nodes/
Wrote drafts/draft4.tex (spine, 104 lines, was 1030)
Identity test: pass (pdftotext identical)
Note: drafts/draft3.tex still defines its ids inline. Either delete it, move it out of the quilt, or add `% !LOOM ignore` to its first line.
```

The author then sets `main = "drafts/draft4.tex"` (or `loom init` did so), deletes `draft3.tex`, and edits the spine: reordering inclusion lines, deleting some, rewriting prose. Whatever the new master stops reaching becomes loose and stays visible.

## 6.5 `loom inline SRC DEST [--all]`

**[decided]** The reverse: writes `DEST`, a copy of `SRC` in which every `\input{...}` or `\nest{...}` line standing alone on its line, whose target is a `.tex` file containing exactly one node and its attached proofs (a node file written by `atomize`, or any file so shaped), is replaced by the file's contents. With `--all`, every `.tex` inclusion is inlined, recursively; a non-`.tex` inclusion is opaque and stays (DR-44). `DEST` may not exist. `SRC` and the node files are not modified; the author deletes the node files afterwards if they want. The identity test applies, through the reaching master when `SRC` is not one (DR-65).

`\nest` lines are inlined with sectioning shifted (`\section` becomes `\subsection`, and so on, composing across nested files), so that the result compiles identically, as the identity test checks; there is no separate diagnostic for it (M4).

**[decided]** The round trip `inline --all` of an atomized spine reproduces the original up to blank lines between the moved regions, since moved text is trimmed to whole lines and written with one trailing newline (settled at M4).

## 6.6 The identity test

**[decided]** For `import`, `atomize`, and `inline`: the compiled text of the master before and after must be identical modulo whitespace, and no label's number may change. Procedure:

1. Compile the "before" document with `latexmk` into a scratch output directory, using the master's engine (`% !TEX program`, else `[quilt] engine`): the original paper in its own directory for `import`; `SRC` itself when it is a master, or the first master that reaches it otherwise (DR-65), for `atomize` and `inline`.
2. Compile the "after" document the same way: from the quilt root for `import` and for a master `SRC`; for a non-master `SRC`, the same master from a scratch copy of the quilt in which `DEST`'s text stands at `SRC`'s path (DR-65).
3. Compare `pdftotext -layout` outputs after collapsing runs of whitespace within each line and dropping empty lines. Equal: pass. Unequal: report the first differing line pair.
4. Additionally compare the `.aux` label tables for the labels present in both; any label whose number changed is reported, and the test fails.

**[decided]** Failure never reverts. The author sees what differs, and the command exits 1.

**[decided]** `pdftotext` is from poppler; `loom doctor` lists it as an optional tool. Without it the identity test is reported skipped (`Identity test: skipped (pdftotext is not installed)`), as it is when either document fails to compile; a skipped test does not fail the command. Every tool's output is decoded with replacement, since TeX writes non-UTF-8 bytes to its terminal (settled at M4).

Known ways the test can fail legitimately, to be documented: `\input` of a file ending in a paragraph break where the original had none (loom writes node files without trailing blank lines to avoid this); `\include` in the original (loom keeps it; `\include` inside an `\input` is illegal, so `atomize` refuses to move a node that contains one).

## 6.7 The single-file author

**[decided]** Nothing in this chapter is required. An author who never atomizes writes ids by hand or applies `loom id` patches, keeps everything in `drafts/main.tex`, and has a complete quilt (5.15.1). `loom new --print` prints a skeleton for pasting. Every other command works identically.

## 6.8 Walk-through: Manolache, virtual pullbacks

This is the first conversion fixture (Chapter 14). Source: the arXiv e-print of `0805.2065`, version 2, kept locally under `tests/fixtures/0805.2065/` and never committed; the main file is `virtual6.tex`, one file of 1246 lines, with amsart-style `\newtheorem` declarations in the preamble. The version is recorded in `tests/fixtures/VERSIONS`.

**[decided]** What the fixture did (settled at M4, the digest at M5):

1. `loom init man12 --from tests/fixtures/0805.2065/virtual6.tex --prefix man` is refused: `51 line-anchoring violation(s) (loom:line-anchoring)`, listed by line. With `--fix-anchoring` the copy is rewritten and the import completes: 96 environments (30 Remark, 16 Definition, 12 Proposition, 11 Example, 7 Lemma, 6 Theorem, 6 Corollary, 3 Convention, 3 Construction, 1 Condition, 1 Setting) and 21 sectioning units (5 sections, 9 subsections, 2 subsubsections, 5 paragraphs); 25 proofs adjacent, 0 by reference, 5 by enclosure (proofs inside `example` environments, DR-41), 0 unattached; 0 dangling references. Identity test: pass.
2. `loom atomize drafts/virtual6.tex drafts/virtual6-atomized.tex --sections`: 110 files under `nodes/` (96 environments and 14 sections and subsections, the subsections included from their section files), a 79-line spine for the 1246-line master; identity test: pass. `loom inline --all` on the spine rebuilds a 1229-line master that passes the identity test and differs from the imported file only in blank lines between nodes.
3. `loom digest extract manolache_VirtualPullbacks2012 tests/fixtures/0805.2065/virtual6.tex` in the relloc quilt: `refs/manolache_VirtualPullbacks2012.tex` with 96 results; every Manolache postnote in the paper resolves to a digest node, `\cite[Theorem 4.3]{manolache_VirtualPullbacks2012}` among them, and a bundle of a relloc proof compiles with the theorem stated inside it (M5).

What the fixture tests: import on a real paper, line-anchoring in the wild and its repair, proofs by enclosure, `\newtheorem` discovery, atomize with sections, the inline round trip, identity, and mechanical digest extraction of the same source. The paper-tier tests (`tests/papers`, run with `LOOM_PAPER_FIXTURES` pointing at the fixtures) pin the 51 violations, the 96 environment and 16 heading ids, the 5 proofs by enclosure, and identity on import and on `atomize --sections`.

## 6.9 Stress test: ACGS, decomposition of degenerate Gromov–Witten invariants

Source: arXiv `1709.09864`, version 4, local only under `tests/fixtures/1709.09864/`; the main file is `decomposition-formula.tex`, one file of 4567 lines, with 11 `.pspdftex` figure inputs and their PDFs, 23 files in the closure.

**[decided]** What was found (settled at M4): no hand edits were needed. The source has 5 line-anchoring violations, all repaired by `--fix-anchoring`; the figure inputs are opaque inclusions (DR-44). Import: 71 environments (18 Definition, 16 Proposition, 10 Lemma, 9 Theorem, 9 Remark, 3 Example, 3 Corollary, 1 Examples, 1 Construction, 1 Notation) and 74 sectioning units (5 sections, 19 subsections, 42 subsubsections, 8 paragraphs); 31 proofs adjacent, 1 unattached; 0 dangling references; 27 citations with locators but no digest; identity test: pass. The one unattached proof (line 3596) follows its proposition after a prose paragraph, which the adjacency rule does not bridge; it is the author's to attach with `\begin{proof}[Proof of Proposition~\ref{...}]`. `atomize` moves 67 node files (four environments nested inside others travel with their parents), writes a 2838-line spine, identity pass; `inline --all` rebuilds a 4567-line master with zero non-blank line differences from the imported file, identity pass. A full scan of the imported quilt takes about one second and well under 100 MB. Of the failures the fixture was written to find (environments not alone on their lines in dense passages; `\begin{proof}` with optional arguments the reference rule does not match ("Proof of the theorem" without a `\ref`); `\label`s inside titles; equation labels reused across sections), the anchoring violations occurred and one proof was separated from its statement by prose; neither needed a hand edit.

Pass criterion, met at M4: import completes with an empty hand-edit list; identity test passes; `atomize` and `inline` pass; the scanner handles the file in about a second (the paper-tier test allows ten seconds and 300 MB for the source map, 5.9.2).

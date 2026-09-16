# 6. Bringing a paper in

This chapter specifies how an existing paper becomes a quilt and how a quilt is reshaped afterwards: `init --from`, `import`, `id`, `atomize`, `inline`, and the identity test that governs all of them. It ends with the two conversion fixtures as narrative: Manolache's virtual pullbacks paper as the first walk-through and ACGS's decomposition paper as the stress test.

The governing rule is P7: loom never modifies an author file. Every operation here either writes copies, writes to a named destination, or prints a patch.

## 6.1 `loom init DIR --from FILE`

**[decided]** Creates the quilt as in 4.7, then performs `import FILE` into it. `FILE` is the paper's main `.tex` file, anywhere on disk. The two are one command because it is the common case.

**[decided]** `loom import FILE`, run inside an existing quilt, is the same operation without creating the quilt. It may be run more than once, for a second master or a section file that was not reached.

## 6.2 What `import` does

Given `FILE`, whose directory is called the paper directory:

1. **[decided]** Resolve the closure: `FILE`; every file it reaches through `\input`, `\include`, and `\nest` (recursively, root-relative to the paper directory); every local `.sty`, `.cls`, and `.tex` fragment its preamble loads; the `.bib` files named by `\bibliography` or `\addbibresource`; every file named by `\includegraphics` (with the usual extension search); and any `.bst` or other local file the preamble names. Files outside the paper directory are reported and not copied (`loom:import-outside-tree`, warning).
2. **[decided]** Copy the closure into the quilt preserving the relative layout of the paper directory, with one exception: `FILE` itself is placed in the masters directory. If `FILE` already lives in the quilt's masters directory (the in-place case of 4.7), nothing is moved.
3. **[decided]** In the copied master, insert `\usepackage{loom}` on the line after `\documentclass{...}` (after its optional argument if multi-line) unless the preamble closure already loads it.
4. **[decided]** In every copied `.tex` file, for every theorem-like environment (5.5) and every sectioning command from `\part` to `\subsubsection` that has no id-shaped label, insert `\label{<prefix>-<local>}`: for an environment, on the `\begin` line immediately after the optional argument, before any existing `\label`; for a sectioning command, at the end of its line. Ids are allocated in document order of the master, under `[quilt] prefix`, starting after the current maximum (5.3.2). Existing labels are left untouched and become aliases.
5. **[decided]** Show the complete diff (every inserted line, with file and line number) before writing anything, and require confirmation on a terminal; `--yes` skips the confirmation for scripts.
6. **[decided]** Set `[quilt] main` to the copied master if `main` is unset or the quilt has no other master; otherwise report and leave `main` alone.
7. **[decided]** Run lint and report: counts of nodes by taxon, proofs attached by adjacency and by reference, unattached proofs, dangling references, files with line-anchoring violations, and unknown environments.
8. **[decided]** Run the identity test (6.6) and report its result. Failure is reported, not reverted; the quilt is left as written so the author can inspect.

**[decided]** `import` never: splits files, moves proofs, renames labels, reorders anything, rewrites `\ref`s, inserts anything other than the `\label` lines and the one `\usepackage` line, or writes metadata headers.

**[decided]** `import` refuses, before copying anything, on: an environment whose `\begin` or `\end` is not alone on its line (`loom:line-anchoring`, with the lines listed); an environment spanning files; a master that does not compile from its own directory (checked by compiling it there first, so that a broken input paper is not mistaken for a loom problem).

Example session:

```
$ loom init relloc --from ~/papers/relloc/draft3.tex
Resolving closure of draft3.tex ... 7 files
  draft3.tex -> drafts/draft3.tex
  preamble.tex, base-macros.sty, math-thms.sty, refs.bib -> ./
  figures/fixedlocus.pdf -> figures/
Compiling original in ~/papers/relloc ... ok
Proposed edits (41 lines in 1 file):
  drafts/draft3.tex:3   + \usepackage{loom}
  drafts/draft3.tex:88  \begin{defn}[Fixed stack]\label{rl-0001}\label{def:fixed-stack}
  drafts/draft3.tex:104 \begin{lem}\label{rl-0002}\label{lem:decomp}
  ...
Apply? [y/N] y
Wrote 7 files. main = drafts/draft3.tex
Nodes: 9 Definition, 14 Lemma, 6 Proposition, 3 Theorem, 4 Remark, 2 Example; 6 sections, 11 subsections
Proofs: 22 adjacent, 3 by reference, 0 unattached
References: 0 dangling; 4 postnotes unmatched (no digests yet)
Identity test: pass (pdftotext identical)
```

## 6.3 `loom id FILE [--to DEST]`

**[decided]** The tagging half of `import`, for files already in the quilt: computes the label insertions of 6.2.4 for `FILE` and prints them as a unified diff to stdout, or writes the resulting file to `DEST` with `--to`. It never modifies `FILE`. The single-file author who wrote human labels applies the patch with their editor or `git apply`.

Options: `--sections` and `--no-sections` (default: sections through subsubsection are labelled); `--all-levels` (also paragraphs); `--prefix P`.

Example:

```
$ loom id drafts/main.tex | head
--- drafts/main.tex
+++ drafts/main.tex
@@ -11,1 +11,1 @@
-\section{Setup}
+\section{Setup}\label{ab-0010}
@@ -13,1 +13,1 @@
-\begin{definition}[Widget]\label{def:widget}
+\begin{definition}[Widget]\label{ab-0001}\label{def:widget}
```

## 6.4 `loom atomize SRC DEST`

### 6.4.1 What it does

**[decided]** Moves each node of `SRC` into its own file under `nodes/` and writes `DEST`, a copy of `SRC` in which each moved region is replaced by an inclusion line. `SRC` is not modified. `DEST` may not exist. Both positional `loom atomize SRC DEST` and `loom atomize SRC --to DEST` are accepted; `loom atomize SRC` alone exits with code 2 and `ERROR: specify a destination file after the source, or with --to`.

Precisely:

1. **[decided]** For every theorem-like node in `SRC` with an id, the region consisting of the node's environment, any directives immediately preceding it (its node-level directives), and the proofs attached to it by adjacency, is written verbatim to `nodes/<id>.tex`, and replaced in `DEST` by `\input{nodes/<id>}` on its own line, preserving the blank lines that surrounded the region so that paragraphing is unchanged.
2. **[decided]** For every deferred proof in `SRC` (attached by reference, 5.6.1), the proof environment is written verbatim to `nodes/<statement-id>.proof.tex` (or `.proof.2.tex`, ...), replaced by an `\input` line at its original position. No label is inserted.
3. **[decided]** A labelled proof (a proof node) is treated as a node: `nodes/<proof-id>.tex`.
4. **[decided]** With `--proofs separate`, adjacent proofs are also moved to their own files, so that `DEST` has an inclusion line per statement and per proof.
5. **[decided]** Sectioning units are not moved by default. With `--sections`, each section node with an id in `SRC` is moved to `nodes/<section-id>.tex` containing the section's own text (its sectioning command, prose, and the inclusion lines for its children), and replaced by `\input{nodes/<section-id>}`; the section file's sectioning commands are copied verbatim, so `\input` reproduces the document. **[assumed]** `--sections` acts on sections and subsections, not deeper.
6. **[decided]** Nodes without ids are not moved; lint reports them; the author runs `loom id` first.
7. **[decided]** Files `SRC` includes are not touched; `atomize` acts on one file. `--all` acts on `SRC` and every file it reaches, writing each spine to the same relative path under a destination directory (`loom atomize --all drafts/draft3.tex --to-dir atomized/`).
8. **[decided]** Written node files end without a trailing blank line; `DEST` places each inclusion line where the region's first line was. A `% !LOOM` file-level directive block at the top of `SRC` is copied to `DEST`; node-level directives travel with their nodes.
9. **[decided]** Afterwards, the identity test compares `DEST` against `SRC`. `atomize` refuses to write anything if `SRC` has line-anchoring violations or spans, naming the lines.
10. **[decided]** `atomize` allocates no ids and inserts no labels.

**[deferred]** `--relative`: additionally rewrite the moved section files' sectioning commands to top level and emit `\nest` at the site, so section files read as standalone sections. Identity-preserving. Not in the MVP.

### 6.4.2 Naming inside `nodes/`

**[decided]** `nodes/<id>.tex` for nodes; `nodes/<id>.proof.tex`, `nodes/<id>.proof.2.tex` for unlabelled proofs. If a target file exists, `atomize` refuses before writing anything (`loom:atomize-target-exists`).

### 6.4.3 The typical use

```
$ loom atomize drafts/draft3.tex drafts/draft4.tex
Moved 38 nodes and 3 deferred proofs to nodes/
Wrote drafts/draft4.tex (spine, 412 lines, was 2,180)
Identity test: pass
Note: drafts/draft3.tex still defines 38 ids inline. Either delete it,
move it out of the quilt, or add `% !LOOM ignore` to its first line.
```

The author then sets `main = "drafts/draft4.tex"` (or `loom init` did so), deletes `draft3.tex`, and edits the spine: reordering inclusion lines, deleting some, rewriting prose. Whatever the new master stops reaching becomes loose and stays visible.

## 6.5 `loom inline SRC DEST [--all]`

**[decided]** The reverse: writes `DEST`, a copy of `SRC` in which every `\input{nodes/<id>}` line whose target is a node file written by `atomize` (or any file containing exactly one node and its adjacent proofs) is replaced by the file's contents. `--all` inlines recursively. `SRC` and the node files are not modified; the author deletes the node files afterwards if they want. The identity test applies.

`\nest` lines are inlined with sectioning shifted, so that the result compiles identically; lint notes it.

## 6.6 The identity test

**[decided]** For `import`, `atomize`, and `inline`: the compiled output of the master before and after must be identical modulo whitespace. Procedure:

1. Compile the "before" document (the original paper in its own directory for `import`; `SRC`'s master for `atomize` and `inline`) with `latexmk` into a scratch output directory.
2. Compile the "after" document from the quilt root the same way.
3. Compare `pdftotext -layout` outputs after collapsing whitespace. Equal: pass. Unequal: report the first differing line pair with page numbers.
4. Additionally compare the `.aux` label tables for the ids present in both; any id whose number changed is reported.

**[decided]** Failure never reverts. The author sees what differs.

**[assumed]** `pdftotext` is from poppler; `loom doctor` reports its absence as a warning (the identity test is then skipped with a notice).

Known ways the test can fail legitimately, to be documented: `\input` of a file ending in a paragraph break where the original had none (loom writes node files without trailing blank lines to avoid this); `\include` in the original (loom keeps it; `\include` inside an `\input` is illegal, so `atomize` refuses to move a node that contains one).

## 6.7 The single-file author

**[decided]** Nothing in this chapter is required. An author who never atomizes writes ids by hand or applies `loom id` patches, keeps everything in `drafts/main.tex`, and has a complete quilt (5.15.1). `loom new --print` prints a skeleton for pasting. Every other command works identically.

## 6.8 Walk-through: Manolache, virtual pullbacks

This is the first conversion fixture (Chapter 14). Source: the arXiv e-print of `0805.2065` (version pinned at implementation time), kept locally under `tests/fixtures/`, never committed.

**[deferred]** The specifics below are expectations to be verified when the fixture is first run; the numbers are illustrative.

1. `loom init man12 --from fixtures/0805.2065/main.tex`. Expected: one master, a handful of files, amsart-style `\newtheorem` declarations in the preamble, theorem-like environments line-anchored (the paper is written in a conventional style). Expect a few `\begin{proof}` environments attached by reference (proofs deferred to later sections) and possibly one or two environments not alone on their line, to be fixed by hand and re-run. Identity test: pass.
2. `loom status`: every key `draft`; no ledger.
3. `loom atomize drafts/main.tex drafts/atomized.tex --sections`: nodes to `nodes/`, spine written; identity test pass.
4. `loom bundle Man12-thm-4.1` (once the same paper is also present as a digest, Chapter 8) or `loom bundle <id>` of the main theorem: compiles standalone; its closure lists the definitions of relative obstruction theory and the earlier propositions.
5. `loom digest extract Man12 fixtures/0805.2065/main.tex` in a second quilt (the relloc quilt or a library quilt): produces `refs/Man12.tex`; `\cite[Theorem 4.1]{Man12}` in relloc now resolves.
6. Arras: master view shows sections and results with ids; node pages link through `\ref`s; the graph has no isolated nodes.

What the fixture tests: import on a real paper, deferred proofs, line-anchoring in the wild, `\newtheorem` discovery, atomize with sections, identity, and mechanical digest extraction of the same source.

## 6.9 Stress test: ACGS, decomposition of degenerate Gromov–Witten invariants

Source: arXiv `1709.09864` (version pinned), local only.

**[deferred]** Expectations to verify: a long paper with many sections, a large preamble with custom macros and possibly custom theorem environments defined through packages the scanner does not read (`loom:unknown-environment`, resolved by `% !LOOM environment:` lines); many `\eqref`s across sections; lists and cases inside proofs; figures. Likely failures the fixture exists to find: environments not alone on their lines in dense passages; `\begin{proof}` with optional arguments the reference rule does not match ("Proof of the theorem" without a `\ref`); `\label`s placed inside titles; equation labels reused across sections (which LaTeX tolerates as a warning and loom reports as `loom:duplicate-label`).

Pass criterion: import completes after at most a documented set of hand edits to the copied source; identity test passes; `atomize --all` passes; the scanner handles the file in under a few seconds; the source map (5.9.2) stays within memory bounds.

## Open questions

- Whether `import` should also copy files reached only by `\includeonly` or `\includegraphics` with unusual extensions. **[assumed]** Reported, not copied.
- Whether `atomize --sections` should default on. **[assumed]** Off; one-file-per-statement is the common wish, and section files can be made later.
- Whether the identity test should also compare bookmarks/hyperref anchors. **[assumed]** No; text and label numbers suffice.
- The two fixtures' arXiv versions. **[deferred]** Pin at first run and record in `tests/fixtures/VERSIONS`.

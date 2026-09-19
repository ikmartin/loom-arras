# 6. Bringing a paper in

This chapter specifies how an existing paper becomes a quilt and how a quilt is reshaped afterwards: `init --from`, `import`, `draft`, `id`, `atomize`, `inline`, and the identity test that governs all of them. It ends with the two conversion fixtures: Manolache's virtual pullbacks paper as the first walk-through and ACGS's decomposition paper as the stress test.

The governing rule is P7: loom never modifies an author file. Every operation here either writes copies, writes to a named destination, or prints a patch.

The path a paper takes has three steps, and each does one thing:

1. **`import`** copies the paper into the quilt as one flat canon document — a landmark, exactly as the paper arrived, with nothing inserted.
2. **`draft`** copies that landmark into the drafting directory as a working document, and *there* inserts `\usepackage{loom}` and an id on every node.
3. **`atomize`** moves each node of the working document into its own file and writes a spine.

The reason for the separation is that a landmark must be the paper as it was, and a working document must be loom's own file. Both are true only if they are two files.

## 6.1 `loom import PAPER` and `loom init DIR --from PAPER`

**[decided]** `loom init DIR --from PAPER` creates the quilt as in 4.7, then performs `import PAPER` into it. Everything the import prints before `Wrote N files` is a plan: the file list is headed "Plan, nothing written yet", and a refusal says that nothing was written, so no reader takes the arrows for work already done. `PAPER` is the paper's main `.tex` file, anywhere on disk. The two are one command because it is the common case, and they are one transaction: an import that refuses removes the files `init` had written, leaving the directory as it was found, and nothing is announced as created until the import has finished (DR-106). In the in-place case only what `init` itself wrote is removed; the author's paper is not `init`'s to delete. `--yes` passes through to the import; `--git` additionally makes the quilt a repository, which loom otherwise does not do (4.7).

**[decided]** `loom import PAPER`, run inside an existing quilt, is the same operation without creating the quilt. It may be run more than once, for a second paper or a later version of the same one; it refuses to overwrite a canon document that already exists.

## 6.2 What `import` does

Given `PAPER`, whose directory is called the paper directory:

1. **[decided]** Resolve the closure: `PAPER`; every file it reaches through `\input`, `\include`, and `\nest` (recursively, the path as written and then with `.tex`, resolved against the paper directory, the braceless `\input name` form included); every local `.sty` named by `\usepackage` or `\RequirePackage` (comma lists included) and every local `.cls` named by `\documentclass` or `\LoadClass`, followed recursively; the `.bib` files named by `\bibliography` or `\addbibresource`; the `.bst` named by `\bibliographystyle`; and every file named by `\includegraphics` (with the usual extension search). Files outside the paper directory are reported and not copied (`loom:import-outside-tree`, warning).
2. **[decided]** Write the master, flattened, to `<canon>/<name>.tex`: every `\input`, `\include` and `\nest` of a `.tex` file expanded in place, `\nest`'s level shift applied, comments and directives kept (17.13). An inclusion of anything that is not a `.tex` file — a figure's `.pspdftex`, a system file — stays as written, which is why the rest of the closure is still copied. A `\bibliography{…}` naming no `.bib` that exists is replaced by the paper's own `<stem>.bbl` when one sits beside it, which is how arXiv ships a bibliography: LaTeX finds a `.bbl` only by the master's stem, so the canon copy and every draft under another name would otherwise cite `[?]`.
3. **[decided]** Copy the rest of the closure — the styles, the class, the bibliography, the style file, the figures — into the quilt at their paper-relative paths, so that the flat document compiles from the quilt root exactly as the original compiled from the paper directory. The `.tex` files that were inlined are not copied: their text is in the canon document.
4. **[decided]** Insert nothing. No `\usepackage{loom}`, no ids, no directives. A landmark is the paper as it arrived.
5. **[decided]** Print the plan and require confirmation on a terminal; `--yes` skips it for scripts, and without a terminal or `--yes` the import stops with `import needs confirmation; pass --yes`.
6. **[decided]** Run the identity test (6.7) between the original, compiled from a clean copy of the paper directory, and the flat copy, compiled from the quilt root. A failure removes the copy and refuses, because a landmark that does not typeset as the paper is worse than no landmark; `--no-check` keeps it anyway. A skipped test (no `pdftotext`) is reported and does not fail the command.
7. **[decided]** Record step `0001-<name>`: the ledger line names the paper and its hash, the canon path and its hash, and the files that were inlined; the step's directory holds the canon document as written (17.6).

**[decided]** `import` never: splits files, moves proofs, renames labels, reorders anything, rewrites `\ref`s, inserts anything at all, or writes metadata headers. It refuses only on a paper that does not compile from its own directory — checked first, in a copy of that directory without its build products (DR-186), so that a broken input paper is not mistaken for a loom problem — and on a canon document of that name already existing. Line anchoring is not its business: nothing is inserted, so nothing needs a line to itself. That check belongs to `draft`.

Example session, with the relative localization paper:

```
$ loom init relloc --from ~/papers/relloc/draft3.tex --prefix rl
Resolving closure of draft3.tex ... 5 files
Plan, nothing written yet:
  draft3.tex -> canon/draft3.tex (linearized, 1 files inlined)
  math-env.sty -> math-env.sty
  base-macros.sty -> base-macros.sty
  refs.bib -> refs.bib
Compiling original from a clean copy of /home/mh/papers/relloc ... ok
Apply? [y/N]: y
Wrote 4 files.
Identity test: pass (pdftotext identical)
Recorded: import as step 0001 (0001-draft3)
next: loom draft canon/draft3.tex
```

## 6.3 `loom draft CANON [--to FILE]`

**[decided]** `loom draft` copies a canon document into the drafting directory and makes it a working document. The canon file is not touched. The destination must sit directly in the drafting directory and must not exist.

1. **[decided]** Replace the canon document's macro block with `\usepackage{loom}`, or insert that line after the first uncommented `\documentclass{...}` when there is no block (17.13). It must be the first uncommented one: a commented-out `\documentclass` above the real one would otherwise put the package before the class and break the copy.
2. **[decided]** For every theorem-like environment (5.5) and every sectioning command from `\part` to `\subsubsection` that has no id-shaped label, insert `\label{<prefix>-<local>}`: for an environment, on the `\begin` line immediately after the optional argument, before any existing `\label`; for a sectioning command, directly after the heading's arguments, before any existing `\label`, so that the id is the heading's first label under the same rule that governs environments (DR-64). Ids are allocated in document order under `[quilt] prefix` (or `--prefix`), starting after the current maximum (5.3.2). Existing labels are left untouched and become aliases. `--no-ids` skips this.
3. **[decided]** Show the diff before writing and require confirmation on a terminal; `--yes` skips it.
4. **[decided]** Refuse, before writing, on an environment whose `\begin` or `\end` is not alone on its line (`loom:line-anchoring`, with the lines listed, numbered in the canon document as it stands) unless `--fix-anchoring` is given, in which case the copy is rewritten so that every theorem-like `\begin` and `\end` stands alone on its line, which typesets identically because a line break is a space in TeX and the environments start and end in vertical mode (DR-40). Also refuse on an environment spanning files. The scanner itself reads by character offset and tolerates unanchored environments; only `atomize`, which moves whole lines, and the label insertion here, which places labels on the `\begin` lines, insist on anchoring.
5. **[decided]** Set `[quilt] main` to the copy if `main` is unset or names a file that does not exist; otherwise leave it alone.
6. **[decided]** Run the identity test (6.7) between the canon document and the copy. A failure removes the copy and refuses; `--no-check` keeps it.
7. **[decided]** Rescan and report: counts of nodes by taxon and of sectioning units by level, proofs attached by adjacency, by reference, and by enclosure (DR-41) and unattached, dangling references, citations with locators but no digest, and unknown environments.
8. **[decided]** Append a `draft` ledger line naming the canon document, its hash, the step that wrote it, the copy, and how many ids were inserted. When the canon file's hash is not the one its step recorded, say so (`loom:canon-edited`) and draft from the file as it is.

```
$ loom draft canon/draft3.tex --to drafting/main.tex --fix-anchoring --yes
Plan, nothing written yet:
  canon/draft3.tex -> drafting/main.tex (53 ids)
--- drafting/main.tex
+++ drafting/main.tex
@@ -1,4 +1,5 @@
 \documentclass{amsart}
+\usepackage{loom}
 ...
-\begin{defn}[Fixed stack]\label{def:fixed-stack}
+\begin{defn}[Fixed stack]\label{rl-0001}\label{def:fixed-stack}
Wrote drafting/main.tex
Identity test: pass (pdftotext identical)
main = drafting/main.tex
Nodes: 12 Lemma, 9 Remark, 8 Definition, 6 Proposition, 4 Example, 2 Theorem; 5 sections, 6 subsections
Proofs: 14 adjacent, 1 by reference, 0 by enclosure, 2 unattached
References: 1 dangling; 10 citations with locators but no digest
Recorded: draft (ledger line 2)
```

## 6.4 `loom id FILE [--to DEST]`

**[decided]** The tagging half of `import`, for files already in the quilt: computes the label insertions of 6.2.4 for `FILE` and prints them as a unified diff to stdout, or writes the resulting file to `DEST` with `--to` (refusing if `DEST` exists). It never modifies `FILE`. It refuses a file with line-anchoring violations, naming the lines, since it places labels on those lines (DR-40). A heading's id goes directly after the heading's arguments, ahead of any label the author already placed there (DR-64), and headings in a file no master reaches are labelled too, since such a file is sectioned on its own (DR-62). The single-file author who wrote human labels applies the patch with their editor or `git apply`.

Options: `--sections` and `--no-sections` (default: sections through subsubsection are labelled); `--all-levels` (also paragraphs and subparagraphs); `--prefix P`.

Example:

```
$ loom id drafting/main.tex
--- drafting/main.tex
+++ drafting/main.tex
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

## 6.5 `loom atomize SRC DEST`

### 6.5.1 What it does

**[decided]** Moves each node of `SRC` into its own file under `nodes/` and writes `DEST`, a copy of `SRC` in which each moved region is replaced by an inclusion line. `SRC` is not modified. `DEST` may not exist (`atomize never overwrites`, exit 2). Both positional `loom atomize SRC DEST` and `loom atomize SRC --to DEST` are accepted; `loom atomize SRC` alone exits with code 2 and `ERROR: specify a destination file after the source, or with --to`.

Precisely:

1. **[decided]** For every theorem-like node in `SRC` with an id, the region consisting of the node's environment, any `% !LOOM` directive lines immediately preceding it (its node-level directives), and the proofs attached to it by adjacency that follow it with nothing but whitespace between, widened to whole lines, is written to `nodes/<id>.tex`, and replaced in `DEST` by `\input{nodes/<id>}` on its own line; the blank lines around the region stay where they were, so that paragraphing is unchanged. A theorem-like environment nested inside another node, and a proof attached by enclosure, travel with the enclosing node (DR-41).
2. **[decided]** For every unlabelled proof in `SRC` attached by reference (5.6.1), or whose statement lives in another file, the proof environment is written to `nodes/<statement-id>.proof.tex` (or `.proof.2.tex`, ..., by ordinal), replaced by an `\input` line at its original position. No label is inserted.
3. **[decided]** A labelled proof (a proof node) is treated as a node: `nodes/<proof-id>.tex`.
4. **[decided]** With `--proofs separate`, adjacent proofs are also moved to their own files, so that `DEST` has an inclusion line per statement and per proof.
5. **[decided]** Sectioning units are not moved by default. With `--sections`, each section and subsection with an id in `SRC` is moved to `nodes/<section-id>.tex` containing the section's own text (its heading, prose, and the inclusion lines for its children; a subsection's file is included from its section's file), and replaced by `\input{nodes/<section-id>}`; headings are copied verbatim, so `\input` reproduces the document. **[decided]** `--sections` acts on sections and subsections, not deeper (settled at M4).
6. **[decided]** Nodes without ids are not moved; `atomize` lists them (`Not moved (no id): ...; run loom id first`) and lint reports them.
7. **[decided]** The history records that `DEST` superseded `SRC`, so `SRC` defines nothing from that moment and the quilt keeps one definition of each node without anything being written into the author's file (17.12, DR-138). `loom live SRC` reverses it; `--retire` moves `SRC` into `retired/` instead, which is the same inertness with the file out of the way. Files `SRC` includes are not touched; `atomize` acts on one file. `--all` acts on `SRC` and every file it reaches, writing each spine to the same relative path under a destination directory (`loom atomize --all drafting/main.tex --to-dir atomized/`).
8. **[decided]** Written node files end with one newline and no trailing blank line (M4); `DEST` places each inclusion line where the region's first line was. A `% !LOOM` file-level directive block at the top of `SRC` stays in `DEST`; node-level directives travel with their nodes.
9. **[decided]** Afterwards, the identity test compares `DEST` against `SRC`: directly when `SRC` is a master; otherwise through the first master that reaches `SRC`, compiled as it is and again in a scratch copy of the quilt where `DEST`'s text stands at `SRC`'s path; when no master reaches `SRC` the test is reported skipped (DR-65). `atomize` refuses to write anything if `SRC` has line-anchoring violations or spans, naming the lines (DR-40). It ends by naming what is now superseded and how to reverse it.
10. **[decided]** `atomize` allocates no ids and inserts no labels.

### 6.5.2 One node, planned rather than applied

**[decided]** `loom atomize --key KEY [--key KEY2]` moves only the nodes named, wherever they live, and never edits the source: it writes `nodes/<id>.tex` and prints the patch for the file, which the author applies, or `--json` prints the plan and writes nothing at all. The plan is what an editor applies as one workspace edit, creating the node file and replacing the region in the same step, so the author's file is changed by the author's editor, its undo reverses that change, and an unsaved buffer is included (16.1). Until the patch is applied the quilt holds two definitions of the node, so the node is conflicted and lint says so (5.3.5).

1. **[decided]** The region, the directives that travel with it, the proof a statement carries, and the naming inside `nodes/` are those of 6.5.1: a key names one node, and a proof key names the statement that carries it.
2. **[decided]** It refuses, with nothing written: a key the quilt does not have; a key in another file than the one being atomized; a node with no id, naming `loom id --next`; a section, which moves with `--sections` in the whole-file form; a node already in its own file; and a node inside another node being moved.
3. **[decided]** The plan is checked without LaTeX: putting the moved text back where the inclusion line stands must reproduce the file byte for byte, else it is refused (`loom:atomize-plan-unsound`). The compiled identity test of 6.7 governs the whole-file form; a single region moved verbatim needs no compile.
4. **[decided]** `loom id --next` prints the next free id and inserts nothing, so an editor can label a node itself before atomizing it. It allocates from the same visible set as `loom id` (5.3.2).

### 6.5.3 Naming inside `nodes/`

**[decided]** `nodes/<id>.tex` for nodes; `nodes/<id>.proof.tex`, `nodes/<id>.proof.2.tex` for unlabelled proofs. If a target file exists, `atomize` refuses before writing anything (`loom:atomize-target-exists`, exit 1).

### 6.5.4 The typical use

The relative localization paper at M7 (step 2 of 13.6):

```
$ loom atomize drafting/draft3.tex drafting/main.tex --sections
Moved 52 nodes and 3 deferred proofs to nodes/
Wrote drafting/main.tex (spine, 104 lines, was 1030)
Identity test: pass (pdftotext identical)
drafting/draft3.tex is now superseded: it defines nothing until `loom live drafting/draft3.tex` says otherwise
main = drafting/main.tex
Recorded: atomize (ledger line 3)
```

The author then edits the spine: reordering inclusion lines, deleting some, rewriting prose. Whatever the new master stops reaching becomes loose and stays visible. `draft3.tex` can stay where it is, inert, or be deleted, or be moved out; none of the three changes what the quilt defines.

## 6.6 `loom inline SRC DEST [--all]`

**[decided]** The reverse of `atomize`, for one file's own inclusions: writes `DEST`, a copy of `SRC` in which every `\input{...}` or `\nest{...}` line standing alone on its line, whose target is a `.tex` file containing exactly one node and its attached proofs (a node file written by `atomize`, or any file so shaped), is replaced by the file's contents. For a whole document, including the files a second document also includes, the command is `loom linearize` (17.13), which knows the identity rule and says what it cannot flatten. With `--all`, every `.tex` inclusion is inlined, recursively; a non-`.tex` inclusion is opaque and stays (DR-44). `DEST` may not exist. `SRC` and the node files are not modified; the author deletes the node files afterwards if they want. The identity test applies, through the reaching master when `SRC` is not one (DR-65).

`\nest` lines are inlined with sectioning shifted (`\section` becomes `\subsection`, and so on, composing across nested files), so that the result compiles identically, as the identity test checks; there is no separate diagnostic for it (M4).

**[decided]** The round trip `inline --all` of an atomized spine reproduces the original up to blank lines between the moved regions, since moved text is trimmed to whole lines and written with one trailing newline (settled at M4).

## 6.7 The identity test

**[decided]** For `import`, `draft`, `atomize`, `inline`, `linearize`, and `canonize`: the compiled text of the document before and after must be identical modulo whitespace, and no label's number may change. It is what makes every one of these operations safe to run on a paper that is about to be submitted. Which documents are compared:

| command | before | after |
|---|---|---|
| `import` | the paper, from a clean copy of its directory | the flat canon document, from the quilt root |
| `draft` | the canon document | the working copy |
| `atomize`, `inline` | `SRC`, or the first master reaching it | `DEST` in its place |
| `linearize` | the spine | the flat document |
| `canonize` | the live document | the canon document |

Procedure:

1. Compile the "before" document with `latexmk` into a scratch output directory, using the document's engine (`% !TEX program`, else `[quilt] engine`): for `import`, the original paper in a scratch copy of its directory that leaves out the build products (`.aux`, `.bbl`, `.fdb_latexmk` and the like; a `.bbl` stays when the directory has no `.bib`) and hidden directories, with any file the paper reaches outside its directory at the same relative position (DR-186); `SRC` itself when it is a master, or the first master that reaches it otherwise (DR-65), for `atomize` and `inline`.
2. Compile the "after" document the same way: from the quilt root for `import`, `draft`, `linearize`, `canonize`, and for a master `SRC`; for a non-master `SRC`, the same master from a scratch copy of the quilt in which `DEST`'s text stands at `SRC`'s path (DR-65).
3. Compare `pdftotext -layout` outputs after collapsing runs of whitespace within each line and dropping empty lines. Equal: pass. Unequal: report the first differing line pair.
4. Additionally compare the `.aux` label tables for the labels present in both; any label whose number changed is reported, and the test fails.

**[decided]** For `atomize` and `inline`, failure never reverts: the author sees what differs, the files stay, and the command exits 1. For `import`, `draft`, `linearize`, and `canonize`, which write one new file, failure removes that file and refuses, because the file is loom's own and a copy that does not typeset as its source is not worth keeping; `--no-check` skips the test and keeps whatever was written.

**[decided]** `pdftotext` is from poppler; `loom doctor` lists it as an optional tool. Without it the identity test is reported skipped (`Identity test: skipped (pdftotext is not installed)`), as it is when either document fails to compile; a skipped test does not fail the command. Every tool's output is decoded with replacement, since TeX writes non-UTF-8 bytes to its terminal (settled at M4).

Known ways the test can fail legitimately, to be documented: `\input` of a file ending in a paragraph break where the original had none (loom writes node files without trailing blank lines to avoid this); `\include` in the original (loom keeps it; `\include` inside an `\input` is illegal, so `atomize` refuses to move a node that contains one).

## 6.8 The single-file author

**[decided]** Nothing in this chapter is required. An author who never atomizes writes ids by hand or applies `loom id` patches, keeps everything in `drafting/main.tex`, and has a complete quilt (5.15.1). `loom new --print` prints a skeleton for pasting. Every other command works identically.

## 6.9 Walk-through: Manolache, virtual pullbacks

This is the first conversion fixture (Chapter 14). Source: the arXiv e-print of `0805.2065`, version 2, kept locally under `tests/fixtures/0805.2065/` and never committed; the main file is `virtual6.tex`, one file of 1246 lines, with amsart-style `\newtheorem` declarations in the preamble. The version is recorded in `tests/fixtures/VERSIONS`.

**[decided]** What the fixture did (settled at M4, the digest at M5):

1. `loom init man12 --from tests/fixtures/0805.2065/virtual6.tex --prefix man` writes `canon/virtual6.tex`, byte for byte the paper (it is one file, so flattening changes nothing), and records step 0001; identity test: pass. `loom draft canon/virtual6.tex --to drafting/main.tex` is then refused: `51 line-anchoring violation(s) (loom:line-anchoring)`, listed by line, and nothing is written. With `--fix-anchoring` the working copy is rewritten and the draft completes: 96 environments (30 Remark, 16 Definition, 12 Proposition, 11 Example, 7 Lemma, 6 Theorem, 6 Corollary, 3 Convention, 3 Construction, 1 Condition, 1 Setting) and 21 sectioning units (5 sections, 9 subsections, 2 subsubsections, 5 paragraphs); 25 proofs adjacent, 0 by reference, 5 by enclosure (proofs inside `example` environments, DR-41), 0 unattached; 0 dangling references. Identity test: pass.
2. `loom atomize drafting/main.tex drafting/main-atomic.tex --sections`: 110 files under `nodes/` (96 environments and 14 sections and subsections, the subsections included from their section files), a 79-line spine for the 1246-line master; identity test: pass; the history records that the spine superseded `drafting/main.tex`, so the quilt defines each of the 110 nodes exactly once although two files hold their text, and `main` moves to the spine. `loom inline --all` on the spine rebuilds a 1229-line master that passes the identity test and differs from the drafted file only in blank lines between nodes.
3. `loom canonize drafting/main-atomic.tex --to canon/virtual6-v1.tex -m "Atomized"`: a flat 1246-line landmark, identity test pass, a step holding a version of each of the 96 statements and their proofs. The landmark compiles in a directory holding nothing but itself and the paper's styles — the paper-tier test does exactly that, with `loom.sty` and `nodes/` absent.
4. `loom digest extract manolache_VirtualPullbacks2012 tests/fixtures/0805.2065/virtual6.tex` in the relloc quilt: `refs/manolache_VirtualPullbacks2012.tex` with 96 results; every Manolache postnote in the paper resolves to a digest node, `\cite[Theorem 4.3]{manolache_VirtualPullbacks2012}` among them, and a bundle of a relloc proof compiles with the theorem stated inside it (M5).

What the fixture tests: import on a real paper, line-anchoring in the wild and its repair, proofs by enclosure, `\newtheorem` discovery, atomize with sections, the inline round trip, identity at every step, supersession on a real paper, a self-contained landmark, and mechanical digest extraction of the same source. The paper-tier tests (`tests/papers`, run with `LOOM_PAPER_FIXTURES` pointing at the fixtures) pin the verbatim landmark and its step, the 51 violations, the 96 environment and 16 heading ids, the 5 proofs by enclosure, the one superseded file with no duplicate id, and identity on import, draft, atomize and canonize.

## 6.10 Stress test: ACGS, decomposition of degenerate Gromov–Witten invariants

Source: arXiv `1709.09864`, version 4, local only under `tests/fixtures/1709.09864/`; the main file is `decomposition-formula.tex`, one file of 4567 lines, with 11 `.pspdftex` figure inputs and their PDFs, 23 files in the closure.

**[decided]** What was found (settled at M4, re-run on the new path): no hand edits were needed. `import` writes `canon/decomposition-formula.tex`, flattening nothing (the paper is one file) and copying the 11 `.pspdftex` figures and their PDFs at their own paths, since a non-`.tex` inclusion is opaque and stays as written (DR-44); identity test: pass. The source has 5 line-anchoring violations, all repaired by `loom draft --fix-anchoring`. The drafted copy: 71 environments (18 Definition, 16 Proposition, 10 Lemma, 9 Theorem, 9 Remark, 3 Example, 3 Corollary, 1 Examples, 1 Construction, 1 Notation) and 74 sectioning units (5 sections, 19 subsections, 42 subsubsections, 8 paragraphs); 31 proofs adjacent, 1 unattached; 0 dangling references; 27 citations with locators but no digest; identity test: pass. The one unattached proof (line 3596) follows its proposition after a prose paragraph, which the adjacency rule does not bridge; it is the author's to attach with `\begin{proof}[Proof of Proposition~\ref{...}]`. `atomize` moves 67 node files (four environments nested inside others travel with their parents), writes a 2838-line spine, identity pass; `inline --all` rebuilds a 4567-line master with zero non-blank line differences from the imported file, identity pass. A full scan of the imported quilt takes about one second and well under 100 MB. Of the failures the fixture was written to find (environments not alone on their lines in dense passages; `\begin{proof}` with optional arguments the reference rule does not match ("Proof of the theorem" without a `\ref`); `\label`s inside titles; equation labels reused across sections), the anchoring violations occurred and one proof was separated from its statement by prose; neither needed a hand edit.

Pass criterion, met at M4: import completes with an empty hand-edit list; identity test passes; `atomize` and `inline` pass; the scanner handles the file in about a second (the paper-tier test allows ten seconds and 300 MB for the source map, 5.9.2).

## 6.11 Two more arXiv papers: Manolescu–Marengon–Piccirillo and Kenig–Pavlović–Staffilani–Velasco

Sources: arXiv `2012.12270` v2 (`slice4D.tex`, relative genus bounds in indefinite four-manifolds, quilt `demos/mmp`, prefix `mmp`) and arXiv `2605.29265` v1 (`mZK_paper.tex`, the complex-valued modified Zakharov–Kuznetsov equation, quilt `demos/kpsv`, prefix `kpsv`), local only under `tests/fixtures/`. Both are built by `python demos/build.py --papers mmp kpsv` with the commands of 6.9 and need no hand edits.

What they found. `slice4D.tex` cites through `\bibliography{topology}` with no `topology.bib` in the upload, only `slice4D.bbl`; import now inlines the `.bbl` (6.2). `mZK_paper.tex` begins one appendix heading with a space, ` \section{…}`, and `atomize --sections` used to pull that heading into the section before it, overlapping the two moves and losing everything after them from the spine; an end preceded only by indentation now counts as a line start. With both fixed, every identity test passes: mmp drafts to 51 environments and 17 sectioning units, atomizes 68 nodes and cites by its compiled numbers; kpsv drafts to 19 environments and 10 sectioning units and atomizes 29 nodes and one deferred proof. mmp keeps five unattached proofs, the paper's own idiom: a theorem from the introduction is restated inside a `{\renewcommand{\thethm}{\ref{…}} … \addtocounter{thm}{-1}}` group and its proof follows the closing brace, which the adjacency rule does not bridge.

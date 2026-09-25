# 2. Objectives

## 2.1 What loom is

**[decided]** Loom turns a LaTeX paper into a quilt: a directory in which every theorem-like environment and every section carries a permanent identifier, dependencies between statements are read from the `\ref`, `\cite`, and `\uses` the author writes, review decisions are recorded beside the source and checked against it, and the whole is published to a viewer. The paper compiles exactly as it did before, from the same files, with plain `pdflatex`.

**[decided]** Arras is a viewer for any corpus of interlinked nodes that publishes to the interface in `specs/`. Loom is its first publisher. The author's org-mode note site is intended as its second. Arras displays; it never edits.

**[decided]** The quilt is the contract: a directory shape, a handful of rules about labels and environments, and a short list of portability constraints. A quilt is also an ordinary LaTeX project that Overleaf can compile.

## 2.2 What loom achieves

For an author:

- A permanent address for every result, so that references survive renumbering, reordering, and moving text between files.
- A dependency graph that is never out of date, because it is read from the text on every scan.
- A record of what has been accepted, and an honest report of what has become stale since, with the diff that caused it.
- Bundles: a standalone document for any statement or proof containing exactly the statements it depends on, which is both the test of self-containedness and the right context to hand a reviewer.
- A viewer that shows the paper as a document (the master view), as a graph, as a review panel, and as pages per result, updating on save.
- Digests of cited papers, so that a citation with a locator becomes a checkable edge and a cited paper need not be reread.

For an author working with an assistant:

- A single orientation document that tells the assistant what a quilt is and how to work in it.
- One command for the assistant to leave a comment anchored to a sentence, and one place for its drafts, so that nothing the assistant produces enters the paper without a human copying it.
- An audit trail: every unit of assistant work is a directory.

For a colleague or coauthor:

- The same quilt, cloned. Comments from the terminal or, later, the browser. Acceptances by name.

## 2.3 Criteria for success

**[decided]** The minimum viable product is done when all of the following hold for the relative localization paper (the author's own draft, `draft3.tex`, with `preamble.tex`, `base-macros.sty`, and `math-thms.sty`):

1. `loom init relloc --from draft3.tex` produces a quilt whose master compiles from the root and whose `pdftotext` output equals the original's.
2. Every theorem-like environment and section in the paper carries an id, and every existing label survives as an alias.
3. `loom atomize` of the master to a new spine, and `loom inline` back, both pass the identity test.
4. `loom status` reports every key; the graph has no dangling references; every proof is attached.
5. The whole paper has been through the cycle: for every key, at least one review record exists (from `loom annotate`, by a person or an agent), and every key is accepted or explicitly incomplete.
6. At least one upstream edit has produced stale acceptances that `loom status --explain` attributes correctly with a diff, and those keys have been re-accepted.
7. Digests exist for the paper's principal references, including one extracted mechanically from LaTeX source and one produced by ingest from a PDF, and at least one `\cite[postnote]` resolves to a digest node.
8. Arras, served by `loom serve`, shows the master view, node pages, the review panel, the problems page, the graph, tags, and search for this quilt, and re-renders on save.
9. The quilt, uploaded to Overleaf with `drafting/main.tex` as the main document, compiles and matches the local PDF.
10. A second person, a graduate student in a different field with their own paper, has run `loom init --from` on it and reached step 4 without help beyond the README.

**[decided]** Whole-paper migration is required; a single section is not enough.

## 2.4 What loom is not

**[decided]** The following are out of scope for the MVP and, for most, permanently:

- Not a LaTeX editor. Authors keep their editor.
- Not a build system beyond `latexmk` wrappers.
- Not a hosted service. Nothing runs anywhere but the author's machine.
- Not a model client. No SDK, no API key, no hosted model. Local interfaces only.
- Not a chat application. The viewer shows threads; it does not conduct them in the MVP.
- Not a corpus. No cross-quilt references; each quilt is one paper (or one library of digests).
- Not a proof checker. Nothing is verified; acceptance is a human decision.
- Not a replacement for git. Git is recommended and never required.
- Not a converter from LaTeX to anything for publication. The `.tex` the author submits is the `.tex` they wrote.
- Not source-language-agnostic. Loom reads LaTeX. Arras reads the interface.

## 2.5 The deferred corpus

**[decided]** The long-term vision is a network-hosted library of mathematical statements and proofs, interconnected as one directed graph, to which people contribute results rather than papers. It is explicitly not what is being built now. Its unresolved problems (statements with many interconnected versions under slightly different hypotheses, identity across papers, licensing of redistributed statements) are noted and not solved.

**[decided]** Nothing built now may foreclose it. The concrete guarantees: ids are globally shaped (`<prefix>-<local>`) so a namespace can be added; digests are self-contained files with prefixed ids and can be collected in a library quilt today; the interface is publisher-agnostic; and the review model records decisions against content hashes, which is what any future federation would need. The library quilt (Chapter 8) is the seed of the corpus, and it needs no new tool.

## 2.6 Who this is for

**[decided]** The primary user is a mathematician with basic computer competency and LaTeX fluency, and nothing more. They can install a Python tool with one command, run commands in a terminal, and compile LaTeX. They do not know git well and may not use it. They use whatever editor they use.

**[decided]** The first user is the author, on the relative localization paper. The first external user is a graduate student in a different field. The tool is to be shared with a department.

**[decided]** Secondary users: an assistant (Claude Code or Codex) pointed at a quilt; a coauthor with a cloned quilt; a reader of a published arras site.

## 2.7 What "easy" means here

**[decided]** Install: `pipx install loomtex`, a TeX distribution, `loom doctor`. First use: `loom init --demo` and `loom serve` in under five minutes. First real use: `loom init mypaper --from draft.tex` and a compiling quilt in under ten. Comprehension: the contract page of the README, one page, is all an author needs to keep a quilt valid. Everything beyond that is optional depth.

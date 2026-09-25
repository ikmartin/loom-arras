# 1. Design philosophy

This chapter states the principles that decide what loom and arras are, the signs that a proposed feature violates them, and the procedure for deciding whether to add a feature. Everything in later chapters is a consequence of this one; when a later chapter and this one disagree, this one is wrong or the later chapter is, and the disagreement is a decision-record event.

## 1.1 The one idea

**[decided]** Loom is a tool for atomized mathematical development. Atomicity married to as-close-to-pure-LaTeX-as-possible is the whole design. A paper is a graph of statements and proofs; each statement is addressable by a permanent identifier; dependencies are read from the text the author already writes; the LaTeX compiles with or without loom.

**[decided]** Loom is not about AI a priori. It is a tool for atomicity. In practice it is designed to work with an AI assistant, and every choice that makes it good for an assistant (bundles, an orientation document, one command to leave a comment) also makes it good for a human collaborator. The AI layer is an optional client of loom, never its reason.

## 1.2 Principles

Each principle is stated, followed by one sentence of reason and one concrete consequence. All are **[decided]**.

### P1. Source is LaTeX, and nothing an author writes lives elsewhere.

Mathematicians already know LaTeX; every construct the tool needs is expressed as a label, an environment, a citation, or one of three macros that print nothing. Consequence: there is no node file format, no frontmatter language, no markup beside LaTeX. The identity of a node is a `\label`; its kind is its environment; its dependencies are its `\ref`s.

### P2. Author data in the source, decisions in the ledger, derived data never durable.

Three kinds of information have three homes, and nothing fits in more than one. Consequence: `config.toml` has a handful of keys; the ledger records acceptances only; `build/` can be deleted at any moment and regenerated.

### P3. States are computed, never stored.

A stored state can disagree with the source; a computed one cannot. Consequence: "stale", "draft", "reviewed", "proved", and "settled" are all computed from records and the current text on every query. Nothing writes the word "stale" anywhere.

### P4. One mechanism per concept, one write path per kind of record.

Two ways to say the same thing drift apart. Consequence: `\input` is transclusion, `\ref` is dependency, `\newtheorem` is taxon, `loom accept` is the only writer of the ledger, `loom annotate` is the only writer of annotation records.

### P5. The graph is defined by labels and environments, never by paths.

Where a file lives carries no meaning. Consequence: one file per node and twelve lemmas in one section file are the same specification at two granularities. `nodes/` is a convention `loom new` follows, not a rule the scanner enforces. No directory exists to hold a property loom can compute (there is no `loose/` directory; loose is computed).

### P6. Config only for what the preamble cannot say.

The preamble is the author's declaration of their conventions; the tool reads it. Consequence: taxa come from `\newtheorem`, style classes from `\theoremstyle`, macros from the preamble closure, the engine from `% !TEX program`. `config.toml` names the default master, the masters directory, the id prefix, and a default engine, and almost nothing else.

### P7. Loom never modifies an author file.

An author's file is theirs; a tool that edits it in place is a tool that destroys work. Consequence: every operation that would change a file either writes to a destination the user names (`atomize SRC DEST`), writes a new file (`new`, `import` into copies), or prints a patch (`id`). `loom delete` exists only to say that loom will not delete. The in-place writers are the ledger and loom's own record files.

### P8. No editor, server, model, or credential is required by any command.

Every command runs from a terminal against files. Consequence: Emacs, VS Code, Overleaf, Claude Code, and Codex are all clients; none is assumed. Loom holds no API key and imports no model SDK. A language server and two editor plugins exist (Chapter 16); they are clients like the rest, and no loom command requires one.

### P9. Local models only.

Any model is reached through a local interface: a model running on the machine, or an agent CLI operated locally. Consequence: the runner contract names a local command; there is no hosted-API path.

### P10. Comments declare; they never command; they never change typeset output.

A `% !LOOM` directive is a fact the scanner reads, never an action loom performs, and never something that alters the PDF. Consequence: `% !LOOM ignore` and `% !LOOM tags:` exist; `% !LOOM accept` and `% !LOOM nest` do not. Anything that changes the typeset document is a macro (`\nest`), because LaTeX must see it.

### P11. The build interface and the write API are the product boundaries.

Loom and arras share no code; they share two documents. Consequence: loom publishes a build directory conforming to the specification; arras reads it and nothing else. Arras knows only that a directory changed, never what kind of change or why.

### P12. The paper compiles from the quilt root, on any TeX, on Overleaf.

Portability is a property of the source, not of the tool. Consequence: all paths are root-relative, local style files sit at the root, no `TEXINPUTS`, no shell escape, no absolute paths.

### P13. Loom verifies what it can, reports what diverges, repairs nothing, and never blocks work.

The head is always the files on disk, and the history is a log of what loom was told, never a claim about the filesystem; a divergence between the two is a fact to report, not a fault to mend. Consequence: an edited canon document, a hand-edited record, a retired id written under again, and two live definitions of one id are each reported with the exact commands that would resolve them, the rest of the quilt builds normally, and no command creates a step, moves a file, or rewrites a record of its own accord to make the report go away.

## 1.3 Signs that a feature is bad

**[decided]** A proposed feature is antithetical to the design if it exhibits any of the following. The list is a filter, not a guideline; one hit is enough to reject or redesign.

1. It needs new syntax beyond `\uses`, `\incomplete`, and `\nest`.
2. It needs configuration where the preamble already says the answer.
3. It writes to an author's source file.
4. It introduces a second source of truth for anything.
5. It stores a state rather than computing it.
6. It requires a running process for something a command could do.
7. It only makes sense with a model in the loop.
8. It needs an API key.
9. It couples arras to a source language, to loom, or to a kind of event.
10. It names a directory for a property loom can compute.
11. It writes a record format that loom does not own (an annotation file written by hand, a ledger row written by an agent).
12. It makes a comment change what the PDF says.
13. It requires an editor, a server, or a particular agent.
14. It reinvents something LaTeX already has (`\input` for transclusion, multiple `\label`s for aliases, `\newtheorem` for taxa, TeX groups for scoped macros).

## 1.4 The test for a proposed feature

**[decided]** Before adding a feature, answer in writing:

1. Which principle motivates it? If none, stop.
2. Which sign in 1.3 does it come closest to? Explain why it does not cross the line.
3. What is the one mechanism it uses? If it introduces a second mechanism for an existing concept, redesign.
4. Where does its data live: source, ledger, or derived? If it needs a fourth place, redesign.
5. Does the paper still compile with plain `pdflatex` from the root, and on Overleaf, with the feature in use? If not, stop.
6. Does arras need to learn anything to display it? If arras needs to know what the feature means (rather than render a label, a link, a diff, or a diagnostic), redesign.
7. Can it be described in the README's contract page in two lines with an example? If not, it is too big or too clever.

Record the answers as a decision record (Appendix A) whether the feature is accepted or not.

## 1.5 How the philosophy evolves

**[decided]** The philosophy changes only through decision records. A record states the principle affected, the change, the reason, and the date. Implementation may reveal that a principle is wrong; when it does, the record says so and the principle is amended here, not silently bypassed in code.

**[decided]** The decision-record format is the one in Appendix A. It is deliberately small so that records get written.

## 1.6 Things the philosophy does not decide

The philosophy does not decide names, directory conventions, or command vocabulary; those are in later chapters and may change more freely. It does not decide what a "good" proof is, how review should be conducted, or how much an author should atomize; those are the author's. It does not decide the future corpus (Chapter 2); it only ensures that nothing built now forecloses it.

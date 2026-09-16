# The quilt contract

This directory is a quilt: an ordinary LaTeX project that `loom` can read. Everything loom needs is a label, an environment, a citation, or one of three macros that print nothing. The paper compiles with plain `pdflatex` from this directory, and on Overleaf with `drafts/main.tex` as the main document.

- **Masters** are the files in `drafts/` with `\documentclass`. Compile them from the quilt root: `pdflatex drafts/main.tex` or `loom compile`. Every path inside them (`\input`, `\includegraphics`, `\bibliography`) is relative to the root, and local `.sty` and `.cls` files sit at the root.
- **Nodes** are theorem-like environments and sections. A node's id is its first label when it has the form `prefix-XXXX`, for example `\label{rl-0004}`; any other labels on the same environment are aliases and keep working. `loom new lemma "Title"` writes a node file with a fresh id into `nodes/`.
- **Proofs** attach to the statement they follow immediately, or to the statement named in their optional argument, as in `\begin{proof}[Proof of Theorem~\ref{rl-0003}]`.
- **Dependencies** are read from `\ref`, `\eqref`, `\cref`, `\autoref`, from `\cite[Theorem 4.1]{Key}` when `refs/Key.tex` holds a digest of that paper, and from `\uses{rl-0001, rl-0002}` for anything the text does not name.
- **Three macros** come from `loom.sty` at the root, loaded by `\usepackage{loom}`: `\uses{...}` and `\incomplete{...}` print nothing; `\nest{file}` inputs a file with its sections shifted one level down.
- **Directives** are comments loom reads and LaTeX ignores: `% !LOOM tags: a, b`, `% !LOOM author: Name`, `% !LOOM ignore` at the top of a file that must not be scanned. `% !LOOM see: rl-0071` links two nodes in the viewer and prints nothing; it is never a dependency.
- **loom never edits your files.** Its own data lives in `.loom/` (the acceptance ledger), `comments/` and `ai/runs/` (review records), and `build/` (everything derived; delete it whenever you like).

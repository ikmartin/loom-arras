# This quilt

A quilt is an ordinary LaTeX project laid out so that `loom` can read it. Four directories carry the work; everything else here is either yours to place where you like or loom's own.

- **`drafting/`** — what you are writing. Every document in it is live: scanned, compiled, rendered, reviewed. `drafting/main.tex` is the default master, and a talk or an outline beside it is a second view of the same nodes. Masters compile from the quilt root — `pdflatex drafting/main.tex`, or `loom compile` — so every path inside them is relative to the root, and local `.sty` and `.cls` files sit at the root.
- **`canon/`** — landmarks. Each is one flat, self-contained copy of a document as it stood at a moment you named: every `\input` expanded in place, loom's macros carried inline, nothing left to resolve, so it compiles alone in an empty directory. `loom canonize` writes them and nothing else does. They are never scanned, so a landmark can never collide with the working text it was copied from.
- **`nodes/`** — one statement or proof per file, pulled in with `\input` by a document in `drafting/`. `loom new lemma "Title"` writes one with a fresh id; `loom atomize` cuts an existing document into them. The directory is a convention and nothing is inferred from it: a node written inline in a master is a node just the same.
- **`refs/`** — at the quilt root, your seed space for other people's work: the reference PDFs and `.bib` files you drop in for loom to read. Created empty, and yours alone — loom reads it and never writes it. Nothing under it is ever scanned, so a file here can neither define an id nor collide with yours.

**A file in `canon/` is never touched.** Loom does not edit it, annotate it, re-id it, reformat it or delete it, and neither should you. It is only ever read and copied somewhere else. That is the whole value of it: it is what you can still compile, still quote and still point a coauthor at in a year.

## The loop

You write in `drafting/`. When a document reaches a state worth being able to return to — submitted, sent to a coauthor, the version a referee read — `loom canonize` writes it flat into `canon/` and records, at that moment, the text of every key in the quilt. To work from a landmark again — a revision, a second version, a paper that has just been imported — `loom draft` copies it back into `drafting/` as a working document, putting `\usepackage{loom}` in place of the inline macros and an id on every node that has none. A quilt that started empty has no landmark yet, so its first turn of the loop is the second command alone.

```
$ loom draft canon/paper.tex --to drafting/main.tex
   ... prints the diff and asks; -y skips the question
Wrote drafting/main.tex
Identity test: pass (pdftotext identical)
Nodes: 1 Lemma; 1 sections
Recorded: draft (ledger line 2)

   ... you work in drafting/main.tex; canon/paper.tex is not touched

$ loom canonize drafting/main.tex --to canon/paper-v2.tex -m "Referee revisions"
Identity test: pass (pdftotext identical)
Wrote canon/paper-v2.tex (flat, 35 lines)
step 0002 froze 2 keys (2 reached by drafting/main.tex, 0 elsewhere), 0 unchanged, parent 0001 (declared)
Recorded: canonize as step 0002 (0002-paper-v2)
```

`--to` defaults to the same stem in the other directory, and `-m` is required: a landmark nobody named is a landmark nobody can ask for. Both commands compile before and after and compare the text of the two PDFs; a failure refuses and writes nothing. `loom history` then lists the landmarks, `loom history butt-0001` the versions that key has had, and `loom revert butt-0001@2` prints the patch that puts a recorded text back.

## The contract

Everything loom reads is a label, an environment, a citation, a comment, or one of three macros that print nothing. The paper compiles with plain `pdflatex` from this directory, and on Overleaf with `drafting/main.tex` chosen as the main document from Overleaf's menu.

- **Nodes** are theorem-like environments and sections. A node's id is its first label when that label has the form `prefix-XXXX`, for example `\label{butt-0004}`; any other labels on the same environment are aliases and keep working.
- **Proofs** attach to the statement they follow immediately, or to the statement named in their optional argument, as in `\begin{proof}[Proof of Theorem~\ref{butt-0003}]`.
- **Dependencies** are read from `\ref`, `\eqref`, `\cref`, `\autoref`, from `\cite[Theorem 4.1]{Key}` when `digests/Key.tex` holds a digest of that paper, and from `\uses{butt-0001, butt-0002}` for anything the text does not name.
- **Three macros** come from `loom.sty` at the root, loaded by `\usepackage{loom}`: `\uses{...}` and `\incomplete{...}` print nothing; `\nest{file}` inputs a file with its sections shifted one level down.
- **Directives** are comments loom reads and LaTeX ignores: `% !LOOM tags: a, b`, `% !LOOM author: Name`, and `% !LOOM ignore` at the top of a file that must not be scanned.
- **Loom edits a file you wrote only when you explicitly click Incorporate pull in a locally served Incoming review.** That action applies the exact displayed collaborator patch and creates local commits; it neither pushes nor accepts mathematics. Its own data lives in `.loom/` (the acceptance ledger and the history of every key), `annotations/log.jsonl` (every comment, reply and finding, appended and never rewritten), `.loom/sessions/` (one directory per session: its notes, command log and inbox), and `build/` (everything derived; delete it whenever you like).

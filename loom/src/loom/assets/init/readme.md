# This quilt

A quilt is a project of yours that `loom` reads: lay it out as you like. Loom put three things here, this file, `config.toml` and `.loom/`, and everything else is yours to make. This file teaches loom and is safe to delete.

- **A document** is any `.tex` file with `\documentclass`, in any directory you make, and every one is live: scanned, compiled, rendered, reviewed. With one document it is the default; with several, `main` in `config.toml` names the default. A document compiles from its own directory, as on Overleaf — `cd paper && pdflatex main.tex`, or `loom compile paper/main.tex` — so every path inside it is relative to that directory, and its local `.sty` and `.cls` files, figures and bibliography sit there too. `..` is never followed.
- **Nodes** are the statements and proofs loom tracks. `loom new lemma "Title"` writes one with a fresh id in `nodes/`, beside the default document, and says the `\input{nodes/...}` line that pulls it in; `--to` puts it elsewhere. `loom atomize` cuts an existing document into node files the same way. A node written inline in a document is a node just the same.
- **Papers you cite** go in loom's library: `loom library add FILE` files a PDF or a LaTeX source from anywhere, under the work it shows it is, and `loom library update` gathers the bibliography from wherever your documents' `\bibliography` names it.
- **The research state**, `research-state.md`, is written here when an agent first keeps one (`research_state` in `config.toml` puts it elsewhere). It is yours to edit.
- **The viewer** (`loom serve`) shows this quilt as a tree of its files: documents, Markdown, HTML, notebooks, PDFs and images, each drawn as itself, with loom's `.loom/`, dot-directories and what `.gitignore` ignores left out. It opens on this file until you remember a place in it, or name another with `home` in `config.toml`.
- **Agents** you attach (`loom ai init`) may write any file here except what loom keeps for itself (`.loom/`, `config.toml`, the research state) and what you name under `[agents] deny` in `config.toml`, gitignore-style: `deny = ["paper/"]` keeps them out of a paper, and they then work on a copy of it, which `loom adopt` lets you take back change by change. Run `loom upgrade` after editing the list, so Claude Code holds them to it too.
- **`.loom/`** holds everything loom writes: the acceptance ledger and the history of every key, annotations (every comment, reply and finding, appended and never rewritten), sessions (one directory per session: its notes, command log and inbox), digests of the papers you cite and loom's store of them, what agents are given in `.loom/ai/`, agents' copies of your documents in `.loom/copies/`, and `.loom/build/` (everything derived; delete it whenever you like). `.loom/.gitignore` says which of these stay on one machine; the rest is meant to be committed.

## The loop

You write in your documents. When one reaches a state worth being able to return to — submitted, sent to a coauthor, the version a referee read — `loom stamp` records, at that moment, the text of every key the document reaches and the whole document as it stands: a landmark. The landmark lives in loom's history, where nothing edits it. `loom history show NAME` prints it, `--plain` without loom, as a journal wants it, and `loom history restore NAME --to paper/FILE.tex` starts a new working document from it. A paper brought in with `loom import` or `loom init --from` arrives both ways at once: the paper as received is the first landmark, and the working document is drafted from it.

```
$ loom stamp paper/main.tex -m "referee revisions"
step 0002 records a new version of 2 results; landmark referee-revisions keeps paper/main.tex as
  it stands

$ loom history show referee-revisions --plain > paper-v2.tex
```

`-m` is required, and given a document it names the landmark: a landmark nobody named is a landmark nobody can ask for. `loom history` then lists the steps, `loom history q-0001` the versions that key has had, and `loom revert q-0001@2` prints the patch that puts a recorded text back.

Coauthors who work in Overleaf edit a **document workspace**: the paper's sources alone, in a Git repository of its own. Clone it yourself, into a directory inside this quilt or anywhere else (`git clone URL DIR`, with the project's Git URL), and pair with `loom sync init DIR`. Loom runs Git only there, never changes that directory's files or checked-out branch, and skips it when it reads the quilt; this quilt need not be a repository, and its own is never touched. The main document's directory is the workspace's root, as Overleaf compiles a project from its top, so the documents you publish together sit under it. The main document is selected automatically; `loom sync documents add paper/talk.tex` adds another live document. `loom sync publish` compiles every selected document from the files as they are, prepares their sources as one workspace revision, and stamps each document so what was published is a landmark; `--push` sends it. `loom sync fetch` brings coauthors' changes into Incoming, where you review them and incorporate them, or run `loom sync incorporate`; each document they reach is stamped first. Acceptance remains a separate mathematical act.

## The contract

Everything loom reads is a label, an environment, a citation, a comment, or one of three macros that print nothing. A document compiles with plain `pdflatex` from its own directory, and on Overleaf with that directory as the project.

- **Nodes** are theorem-like environments and sections. A node's id is its first label when that label has the form `prefix-XXXX`, for example `\label{q-0004}`; any other labels on the same environment are aliases and keep working.
- **Proofs** attach to the statement they follow immediately, or to the statement named in their optional argument, as in `\begin{proof}[Proof of Theorem~\ref{q-0003}]`.
- **Dependencies** are read from `\ref`, `\eqref`, `\cref`, `\autoref`, from `\cite[Theorem 4.1]{Key}` when the library holds a digest of that paper, and from `\uses{q-0001, q-0002}` for anything the text does not name.
- **Three macros** come from loom's macro block, the lines between `% !LOOM begin loom-macros` and `% !LOOM end loom-macros` in a document's preamble, or from a `loom.sty` you keep beside the document: `\uses{...}` and `\incomplete{...}` print nothing; `\nest{file}` inputs a file with its sections shifted one level down.
- **Directives** are comments loom reads and LaTeX ignores: `% !LOOM tags: a, b`, `% !LOOM author: Name`, and `% !LOOM ignore` at the top of a file that must not be scanned.
- **Loom edits a file you wrote only when you incorporate a contribution**, a collaborator's pull or an agent document, from a locally served Incoming review or the command line. It stamps each document the contribution reaches first, so what it replaced is kept as a landmark, and it neither commits, pushes nor accepts mathematics.

## Reviewer identity

Set your name in local Arras Settings, or `[author] name` in `~/.config/loom/config.toml` (respecting `XDG_CONFIG_HOME`). Git's user name is the fallback; tracked quilt attribution does not identify its reader. Use distinct, consistent names: changing a name selects another acceptance history. Pulling a collaborator's records never accepts mathematics for you. Review uses your history, while Context's Accepted by details expose other authors' current or stale acceptances.

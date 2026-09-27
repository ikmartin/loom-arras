# This quilt

A quilt is an ordinary LaTeX project laid out so that `loom` can read it. Four directories carry the work; everything else here is either yours to place where you like or loom's own.

- **`drafting/`** — what you are writing. Every document in it is live: scanned, compiled, rendered, reviewed. `drafting/main.tex` is the default master, and a talk or an outline beside it is a second view of the same nodes. Masters compile from the quilt root — `pdflatex drafting/main.tex`, or `loom compile` — so every path inside them is relative to the root, and local `.sty` and `.cls` files sit at the root.
- **`drafting-ai/`** — the documents you and an agent both edit. `loom draft drafting/main.tex --ai NAME` copies a document here, flat, every id in it suffixed `-ai`, for an agent to work in while you keep writing in `drafting/`. Its documents are live, and never reviewed, accepted or published.
- **`nodes/`** — one statement or proof per file, pulled in with `\input` by a document in `drafting/`. `loom new lemma "Title"` writes one with a fresh id; `loom atomize` cuts an existing document into them. The directory is a convention and nothing is inferred from it: a node written inline in a master is a node just the same.
- **`refs/`** — at the quilt root, your seed space for other people's work: the reference PDFs and `.bib` files you drop in for loom to read. Created empty, and yours alone — loom reads it and never writes it. Nothing under it is ever scanned, so a file here can neither define an id nor collide with yours.

## The loop

You write in `drafting/`. When a document reaches a state worth being able to return to — submitted, sent to a coauthor, the version a referee read — `loom stamp` records, at that moment, the text of every key the document reaches and the whole document as it stands: a landmark. The landmark lives in loom's history, where nothing edits it. `loom history show NAME` prints it, `--plain` without loom's package line as a journal wants it, and `loom history restore NAME --to drafting/FILE.tex` starts a new working document from it. A paper brought in with `loom import` or `loom init --from` arrives both ways at once: the paper as received is the first landmark, and the working document is drafted from it.

```
$ loom stamp drafting/main.tex -m "referee revisions"
step 0002 froze 2 keys; landmark referee-revisions, drafting/main.tex as it stands
Recorded: stamp as step 0002 (0002-referee-revisions)

$ loom history show referee-revisions --plain > paper-v2.tex
```

`-m` is required, and given a document it names the landmark: a landmark nobody named is a landmark nobody can ask for. `loom history` then lists the steps, `loom history q-0001` the versions that key has had, and `loom revert q-0001@2` prints the patch that puts a recorded text back.

The complete quilt uses ordinary Git. Loom manages a separate source-only **document workspace**, such as an Overleaf Git project. Configure it with `loom sync init --remote overleaf --branch master` after fetching that remote. The main document is selected automatically; `loom sync documents add drafting/toy.tex` persistently adds another live document without staging, committing or publishing. Commit source edits normally, then use `loom sync publish` to compile every selected document and prepare their committed inputs at `refs/loom/publication`. The output names the local ref and producing quilt commit; the remote remains unchanged. Use `loom sync publish --push` to perform the same checks and push the prepared revision to the configured document workspace. Neither mode stages or commits quilt bookkeeping. `loom sync fetch` recognizes the exact prepared revision without Incoming review; collaborator changes appear in Incoming for an explicit local Incorporate pull. Acceptance remains a separate mathematical act.

## The contract

Everything loom reads is a label, an environment, a citation, a comment, or one of three macros that print nothing. The paper compiles with plain `pdflatex` from this directory, and on Overleaf with `drafting/main.tex` chosen as the main document from Overleaf's menu.

- **Nodes** are theorem-like environments and sections. A node's id is its first label when that label has the form `prefix-XXXX`, for example `\label{q-0004}`; any other labels on the same environment are aliases and keep working.
- **Proofs** attach to the statement they follow immediately, or to the statement named in their optional argument, as in `\begin{proof}[Proof of Theorem~\ref{q-0003}]`.
- **Dependencies** are read from `\ref`, `\eqref`, `\cref`, `\autoref`, from `\cite[Theorem 4.1]{Key}` when `digests/Key.tex` holds a digest of that paper, and from `\uses{q-0001, q-0002}` for anything the text does not name.
- **Three macros** come from `loom.sty` at the root, loaded by `\usepackage{loom}`: `\uses{...}` and `\incomplete{...}` print nothing; `\nest{file}` inputs a file with its sections shifted one level down.
- **Directives** are comments loom reads and LaTeX ignores: `% !LOOM tags: a, b`, `% !LOOM author: Name`, and `% !LOOM ignore` at the top of a file that must not be scanned.
- **Loom edits a file you wrote only when you explicitly click Incorporate pull in a locally served Incoming review.** That action applies the exact displayed collaborator patch and creates local commits; it neither pushes nor accepts mathematics. Its own data lives in `.loom/` (the acceptance ledger and the history of every key), `annotations/log.jsonl` (every comment, reply and finding, appended and never rewritten), `.loom/sessions/` (one directory per session: its notes, command log and inbox), and `build/` (everything derived; delete it whenever you like).


## Reviewer identity

Set your name in local Arras Settings, or `[author] name` in `~/.config/loom/config.toml` (respecting `XDG_CONFIG_HOME`). Git's user name is the fallback; tracked quilt attribution does not identify its reader. Use distinct, consistent names: changing a name selects another acceptance history. Pulling a collaborator's records never accepts mathematics for you. Review uses your history, while Context's Accepted by details expose other authors' current or stale acceptances.

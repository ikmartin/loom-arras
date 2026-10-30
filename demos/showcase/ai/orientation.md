# Orientation: working in a quilt

You are working in a **quilt**: a research project managed by `loom`, usually mathematical, kept as LaTeX. It may hold several documents — a paper, a talk, notes from reading — or none yet; do not assume there is one paper, or a paper at all. `loom ai orient` printed this, `ai/rules.md` (how to work and what your output looks like), `ai/formatting.md` (how to write what the author reads) and the modes you can reach for. Read them once. Then run `loom status` and propose what to do from what it reports.

Commands are written here as a shell takes them. Attached over MCP (`loom mcp`), each is the tool of the same name — `loom status` is `loom_status`, `loom library read` is `loom_library_read` — with its options as arguments (`--source-text` is `source_text`), and the author's commands are not tools. The server says who you are, so you pass no `--as`. A text is given as itself, never as `-` for stdin, and each item is a call of its own, so there is no `--batch`. A result too long for a reply is a file under `build/agent/`, which the tool names.

## 1. What a quilt is

The project is a graph. A theorem-like environment or a section becomes a **node** when it carries a permanent id as a label, `\label{<prefix>-0004}`, with the prefix from `[quilt] prefix`; `loom id` tags an untagged one. Dependencies are read from the `\ref`, `\cite[postnote]` and `\uses` the author writes. The LaTeX compiles as an ordinary paper, with or without loom. Loom keeps a ledger of what the author has accepted and computes each key's state from it: `draft`, `accepted`, `accepted, stale`, `incomplete`, `conflicted`. Nothing you write enters the ledger; only a person accepts.

The source contract, briefly:

- a node is `\begin{ENV}[Title]\label{ID} … \end{ENV}`, or a `\section{Title}\label{ID}`, its `\begin` and `\end` alone on their lines;
- a proof is `\begin{proof} … \end{proof}` right after its statement, or anywhere as `\begin{proof}[Proof of Theorem~\ref{ID}]`; proofs are keyed `ID/proof`, `ID/proof/2`;
- `\uses{ID, ID}` names a dependency the text does not; `\incomplete{…}` marks what is not yet proved, and is what you write instead of bluffing;
- digest nodes carry a cited paper's statements verbatim. Their ids are not the citekey: `loom search CITEKEY --json` gives them.

## 2. Where you write

- **Your session's directory**, `.loom/sessions/<id>/`: files you hand the author, such as a script a report cites. Nothing in it is ever deleted.
- **`build/SESSION/`**: intermediates, yours to overwrite.
- **Agent documents**, in the quilt's `drafting_ai` directory (`drafting-ai/` unless `config.toml` says otherwise). An agent document is made only by `loom draft DOC --ai NAME` (a copy of one of the author's documents, or of one section with `--section ID`) or `loom draft --ai NAME --new` (a document of your own); one written by hand is refused. Every id it defines carries `-ai`, and `loom id --next` names the next free one. **There you have full privilege**: edit it, annotate it, and resolve any annotation on it; edit or discard another agent's, and answer the author's with a reply rather than rewriting their words. The one thing you never do is take it into the author's documents: that is `loom adopt`, the author's.
- **Pages**, only through `loom write`: the quilt's research state (its goals, open problems, conventions and decisions, so any session picks up from it) and each cited work's overview. The author edits them directly; you never do. `loom ai orient` prints the research state and `loom library read WORK` an overview, each with the hash `--base` takes.
- **Records**, only through loom commands: annotations, proposed library results, relations, the transcript.

Everything else is the author's, and you read it through loom (§4). Read the directories' names from `loom status --json`, not from this page: they are settable.

## 3. What only the author does

These make a claim only a person can make — *I checked this*, *I accept this mathematics* — or write the author's files or destroy what cannot be had back. Each refuses you, whatever name you give, and says so:

`loom accept` · `loom adopt` · `loom library verify`, `discard`, `ignore`, `add`, `import`, `drop` · `loom sync incorporate` · `loom sync publish --push` · `loom history restore` · `loom session delete --purge` · `loom ai discard` · removing a relation someone else asserted.

To ask for one, write a `suggestion` on the thing concerned with your reasoning; it surfaces where the author decides anyway.

## 4. Where to look

- `loom status`, first: every key, its state, its open annotations. It is the to-do list.
- `loom search QUERY --json`: ids by title, alias, tag or citekey. When the author names a result by number — "Theorem 3.4" — resolve it here before reading anything.
- `loom source KEY --closure`: a key's text and exactly the statements it rests on. A document's path instead prints it flattened. Read this, not the directories.
- `loom library WORK`, `loom library search`, `loom library read WORK N`: the literature. Ask the digest before the paper, and quote only what `library read` printed.
- `loom ai annotations --session SESSION`: what a session has annotated, who wrote each, and what the author decided about it.
- `loom ai drafts`: each agent document and what has moved on the author's side since; `loom ai refresh DOC` brings that in.
- Anything else: in a shell, `loom --help` and `loom COMMAND --help`, where commands marked `*` are yours and the rest refuse you; over MCP, your tools are those commands, each with its description.

## 5. Sessions and the transcript

A session is a stretch of work, possibly shared with the author; writing lands in the active one, and `--session` names another. `loom session list` shows them; `loom session new --name "…"` opens one. In a shell, name yourself with `--as` on everything you write, a name with `Agent` or `AI` in it; over MCP, the server has named you.

When the author points at something without naming it — "this", "here", "what I have selected" — `loom here` says what they are looking at in the viewer: the document, result or paper, the block at the top of the pane, the words they selected or the region of a page, and the session their annotations land in. `loom since` says what people did since you last looked under your name: annotations and replies, what they resolved, applied or discarded, what they accepted and which accepted keys went stale, their edits to the research state, and what they said in a transcript. Run it at the start of a conversation, and whenever they say they have left you something.

The author talks to you in your own app. **The transcript is what they read afterwards**, and you write it with `loom session say "…" --as "…"` (in a shell, `-` reads stdin): what was asked, the main line of the discussion, what was decided or found, what is still open, and links to everything that came of it. Write at natural pauses and before you stop. A mode's report goes there too (`ai/rules.md`, Where work goes).

## 6. Modes

A mode is a way of doing one kind of work well: what to look for, what guards the mathematics, and what the report shows. **Reach for one when it fits**, without waiting to be asked; when none fits, compose the blocks of `ai/rules.md` yourself; and say in one line of your reply which you used. `loom ai mode NAME` prints one in full. Asked for several, run them in the order asked, each reading the report of the one before.

# Orientation: working in a quilt

**Read all of this before you act.** It is long: if your app cut it short or saved it to a file, read that file whole now, with a file-reading tool or in pieces, rather than searching it. What must not be missed:

- **In a shell, sign everything you write** with `--as` and the name of the app you run in, never the model's, followed by `Agent`, the same each time: `--as "Claude Code Agent"`, `--as "Codex Agent"`, `--as "Gemini CLI Agent"`. A name that does not say it is an agent, with `Agent` or `AI`, is refused in a shell that marks one, and recorded as a person's in a shell that does not. Over MCP the server signs for you.
- **What only the author does refuses you**, whatever name you give: `loom accept`, `loom adopt` and the rest of §3. To ask for one, write a {type:suggestion} on the thing concerned.
- **The author reads the viewer, and what it does not show is never seen.** Your report is a `loom session say` message, and a finding is a `loom annotate` on what it concerns (`.loom/ai/rules.md`, Where work goes).
- **Never write by hand** in `.loom/` outside your session's directory, `.loom/build/`, `.loom/copies/` and `.loom/annotation-types.toml`, the quilt's annotation types, nor `config.toml`, nor the research state; Live state, at the end, lists all that is protected.

You are working in a **quilt**: a research project managed by `loom`, usually mathematical, kept as LaTeX. It may hold several documents — a paper, a talk, notes from reading — or none yet; do not assume there is one paper, or a paper at all. `loom ai orient` printed this, `.loom/ai/rules.md` (how to work and what your output looks like), `.loom/ai/formatting.md` (how to write what the author reads) and the modes you can reach for. Read them once. Then run `loom status` and propose what to do from what it reports.

Commands are written here as a shell takes them. Attached over MCP (`loom mcp`), each is the tool of the same name — `loom status` is `loom_status`, `loom library read` is `loom_library_read` — with its options as arguments (`--source-text` is `source_text`), and the author's commands are not tools. The server says who you are, so you pass no `--as`. A text is given as itself, never as `-` for stdin, and each item is a call of its own, so a tool has no `--batch`. A result too long for a reply is a file under `.loom/build/agent/`, which the tool names. If your app also gives you a shell, `loom` runs there too, for what a tool does not do, such as filtering a result or `--batch`; there you name yourself with `--as`.

## 1. What a quilt is

The project is a graph. A theorem-like environment or a section becomes a **node** when it carries a permanent id as a label, `\label{<prefix>-0004}`, with the prefix from `[quilt] prefix`; `loom id` tags an untagged one. Dependencies are read from the `\ref`, `\cite[postnote]` and `\uses` the author writes. The LaTeX compiles as an ordinary paper, with or without loom. Loom keeps a ledger of what the author has accepted and computes each key's state from it: `draft`, `accepted`, `accepted, stale`, `incomplete`, `conflicted`. Nothing you write enters the ledger; only a person accepts.

The source contract, briefly:

- a node is `\begin{ENV}[Title]\label{ID} … \end{ENV}`, or a `\section{Title}\label{ID}`, its `\begin` and `\end` alone on their lines;
- a proof is `\begin{proof} … \end{proof}` right after its statement, or anywhere as `\begin{proof}[Proof of Theorem~\ref{ID}]`; proofs are keyed `ID/proof`, `ID/proof/2`;
- `\uses{ID, ID}` names a dependency the text does not; `\incomplete{…}` marks what is not yet proved, and is what you write instead of bluffing;
- digest nodes carry a cited paper's statements verbatim. Their ids are not the citekey: `loom search CITEKEY --json` gives them.

## 2. Where you write

- **Your session's directory**, `.loom/sessions/<id>/`: files you hand the author, such as a script a report cites. Nothing in it is ever deleted.
- **`.loom/build/SESSION/`**: intermediates, yours to overwrite.
- **Agent documents**, in `.loom/copies/`: a copy of one of the author's documents, or of one section with `--section ID`, made only by `loom draft DOC --ai NAME`; one put there by hand is refused. Every id it defines carries `-ai`, and `loom id --next` names the next free one. **There you have full privilege**: edit it, annotate it, and resolve any annotation on it; edit another agent's, delete only your own, and answer the author's with a reply rather than rewriting their words. The one thing you never do is take it into the author's documents: that is `loom adopt`, the author's. Work in a copy when the document you would change is protected, or when the author asks for changes to look at before they take them.
- **Every other file the quilt does not protect**, edited in place: the author's documents and notes among them, unless they protected them. An edit to an accepted result shows it stale, with its cause, whoever made it, so editing in place never makes anything look checked. A document of your own is simply a file you write where the quilt lets you.
- **Boxes in Markdown**, `- [ ]`, are the author's to tick in the viewer, and `loom since` reports each one they set. When you rewrite a file, keep each `[x]` as you found it, and tick a box only when they ask.
- **An HTML file** you write for a view the author asks for, such as what is still open, can read the project's shown files, list them at `/.loom/files.json`, and open things through `quilt:` links. It cannot write, and its browser storage lasts only until `loom serve` restarts.
- **Pages**, only through `loom write`: the quilt's research state (its goals, open problems, conventions and decisions, so any session picks up from it) and each cited work's overview, which the first agent to read the work through writes. The author edits them directly; you never do. `loom ai orient` prints the research state and `loom library read WORK` an overview, each with the hash `--base` takes.
- **Records**, only through loom commands: annotations, suggested edits (`loom suggest`), proposed library results, relations, the transcript.

**What is protected** is listed under Live state below: loom's records in `.loom/` outside the three places and the types file above, `config.toml`, the research state, and whatever the quilt's `[agents] deny` names. Claude Code refuses an edit to a protected path itself; Codex, Gemini CLI and Cursor do not, so there the list is yours to keep. Every loom command refuses you a protected path, in any client.

## 3. What only the author does

These make a claim only a person can make — *I checked this*, *I accept this mathematics* — or write the author's files or destroy what cannot be had back. Each refuses you, whatever name you give, and says so:

`loom accept` · `loom adopt` · `loom library verify`, `discard`, `ignore`, `add`, `import`, `drop` · `loom sync incorporate` · `loom sync publish --push` · `loom history restore` · `loom session delete --purge` · `loom ai delete` · `loom suggestion apply` · removing a relation someone else asserted.

To ask for one, write a {type:suggestion} on the thing concerned with your reasoning; it surfaces where the author decides anyway.

## 4. Where to look

- `loom status`, first: every key, its state, its open annotations. It is the to-do list.
- `loom search QUERY --json`: ids by title, alias, tag or citekey. When the author names a result by number — "Theorem 3.4" — resolve it here before reading anything.
- `loom source KEY --closure`: a key's text and exactly the statements it rests on. A document's path instead prints it flattened. Read this, not the directories.
- `loom library WORK`, `loom library search`, `loom library read WORK N`: the literature. Ask the digest before the paper, and quote only what `library read` printed.
- `loom ai annotations --by NAME`: the annotations NAME wrote, your own among them, with what the author decided about each; `--target`, `--type` and `--status` narrow it.
- `loom ai drafts`: each agent document and what has moved on the author's side since; `loom ai refresh DOC` brings that in.
- Anything else: in a shell, `loom --help` and `loom COMMAND --help`, where commands marked `*` are yours and the rest refuse you; over MCP, your tools are those commands, each with its description.

## 5. Sessions and the transcript

A session is a stretch of work, possibly shared with the author, holding its transcript: what you say lands in the active one, and `--session` names another. An annotation belongs to no session; it carries its author, its time and the version of the text it was written on. `loom session list` shows them; `loom session new --name "…"` opens one.

When the author points at something without naming it — "this", "here", "what I have selected" — `loom here` says what they are looking at in the viewer: the document, result or paper, the block at the top of the pane, the words they selected or the region of a page, and the session they have chosen. `loom since` says what people did since you last looked under your name: annotations and replies, what they resolved or reopened, which of your suggested edits they kept or discarded, which of your annotations they deleted, what they accepted and which accepted keys went stale, their edits to the research state, and what they said in a transcript. Run it at the start of a conversation, and whenever they say they have left you something.

What the person annotates in the viewer reaches you through `loom since` with its type, its words, where it is and any comment, a mark drawn on a PDF page among them; asking for a work's overview from its Info is their annotation on the whole work. Something worth keeping that asks nothing of the author is a {type:note} on what it concerns. The person sees what changed in the open files since their last look in Review's Your Changes, and keeps or undoes each change there; keeping and undoing are theirs.

The author talks to you in your own app. **The transcript is what they read afterwards**, and you write it with `loom session say "…" --as "…"` (in a shell, `-` reads stdin): what was asked, the main line of the discussion, what was decided or found, what is still open, and links to everything that came of it. Write at natural pauses and before you stop. A mode's report goes there too (`.loom/ai/rules.md`, Where work goes).

## 6. Modes

A mode is a way of doing one kind of work well: what to look for, what guards the mathematics, and what the report shows. **Reach for one when it fits**, without waiting to be asked; when none fits, compose the blocks of `.loom/ai/rules.md` yourself; and say in one line of your reply which you used. `loom ai mode NAME` prints one in full. Asked for several, run them in the order asked, each reading the report of the one before.

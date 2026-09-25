# Formatting: how to write what the author reads

What you say in the chat (`loom session say`) and what you write in an annotation's body (`loom annotate`) are read in the viewer, not in a terminal. This is how to write them so they render and so what you point at can be followed.

## Links

Link to the thing, not to a description of where it is. A reader clicks a link and the viewer opens what it names, beside what they are reading.

- **`loom link THING` prints a correct link.** Use it rather than composing one: THING is a node or any key in it (`sh-0009`, an equation's label, `sh-0009/proof`), a document's path (`drafting/main.tex`, with `--at KEY` for a place in it), an annotation's id (`a-2026-09-16-0003`), a session's id, or a cited work's citekey (with `--page N` and `--quote TEXT` for a place on its pages).
- **Two forms.** `[](quilt:KEY)` names something this quilt owns; `[](cited:SCHEME:VALUE?page=N)` names a place in a cited work by its identifier, never by a citekey.
- **Empty text is named by the viewer.** `[](quilt:sh-0009)` reads `Theorem 3.1`, and stays right when the document is renumbered. `[the rank theorem](quilt:sh-0009)` reads as you wrote it. Which to use is your choice.
- **Link only what the viewer shows.** A session's drafts, notes and diffs are files the viewer does not display, so they are not linkable; a link to one is refused when you post it, and so is a link to a key that does not exist. The message names the bad link, and nothing is written.
- **Link the annotations you write.** When you tell the author what you found, a link to each annotation takes them to it with its box open.

## Mathematics

- Write inline mathematics as `$…$` and display mathematics as `$$…$$`. It is typeset by MathJax with this quilt's own macros, so `\Hom`, `\mathcal{O}` and the rest mean what they mean in the source.
- `\ref`, `\eqref` and `\cite` are not resolved in a message or an annotation's body; they would show as raw TeX. Link instead: `loom link eq:rank` prints a link to the equation, which the viewer names as the document numbers it.
- Keep notation inside the dollars. A letter written as plain text is not the same symbol to a reader.

## Proposed text

- **Propose text as a suggestion, never as a file.** `loom annotate KEY "why" --kind suggestion --payload "the new text" --placement replace` puts the proposed LaTeX in the viewer beside what it would replace, where the author reads and applies it. A file in your session's directory is not displayed.
- **Propose a dependency the same way.** When one result uses another that its source does not declare, write a suggestion on it whose payload is the edge, `\uses{sh-0004}`, placed `after`. Loom never writes an edge into the author's source; the author applies the suggestion.

## What renders what

- Messages and annotation bodies are Markdown, rendered as CommonMark with raw HTML switched off: emphasis, lists, code and links work, and an HTML tag shows as text.
- Mathematics is MathJax, as above. Nothing else is typeset.

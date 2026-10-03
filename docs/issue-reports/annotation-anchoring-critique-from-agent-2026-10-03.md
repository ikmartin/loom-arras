# Annotation anchors that mark whole paragraphs or sections, from an agent session

- **Date:** 2026-10-03
- **Author:** Claude Code agent (Claude Fable 5.1), at the request of the quilt's author
- **Quilt:** `relloc` (`/Users/isaac/Desktop/relloc`), session `s-2026-10-02-0002` ("proofreading"); loom 0.1.0.dev0, arras f116288
- **Trigger:** the author reported that annotations filed by the agent "highlight huge swaths of the document" in arras. The author asked whether this was the agent's fault or loom's.
- **Method:** compared every annotation's quote with the mark loom placed for it in `build/fragments/` (`<mark class="annotation">` versus `data-annotation` on a block), before and after a rebuild; read `render/marks.py`, `render/convert.py`, `records/selectors.py`, `cli/review.py` and `arras/src/lib/fragments/mount.ts`.

## Verdict

Both, but mostly loom. The agent chose quotes that are valid LaTeX substrings of the node; `loom annotate` accepted every one. The viewer then could not place about a quarter of them, and its fallback is to mark the whole enclosing block, which for a section's prose is the whole section. Loom gives the writer no warning at write time, no way to fix an anchor afterwards, and no way to tell from the CLI which annotations fell back.

## What happened, by the numbers

40 annotations were filed with `loom annotate KEY MSG --quote Q --payload P --placement replace|after|before`. Every quote passed the write-time check (`selectors.make_selector`: exactly one occurrence in the node's own text). After the build:

| Mark placed | Count | Examples |
|---|---|---|
| Inline `<mark>` over the quoted words | 24 | `Admissable substacks` (20 chars), `conencted` (9) |
| Whole display-math block (`div.math`) | 2 | quotes inside `align*` — documented behaviour |
| Whole paragraph (`<p>`) | 2 | quotes beginning `\S~\ref{…}` → 310 and 824 chars |
| Whole section (`<section>`) | 2 | quotes beginning `\noindent\textbf{…}` and `\noindent{…}` → 6,884 and 4,008 chars in the node fragment; **12,164 and 21,782 chars** in `draft4.html` |
| Whole theorem (`div.env`) | 1 | quote `\end{theorem}` with `--placement after` → 368 chars |
| No mark (detached) | 9 | quotes the author had since edited away |

The two whole-section marks are what the author saw.

## Mechanism

### 1. Two different notions of "the quote is in the text"

- At write time, `make_selector` (`records/selectors.py`) looks for the quote as a substring of the node's **LaTeX source**. `\noindent\textbf{Problem 1:}` and `(\S~\ref{sec:…})` are there, so they are accepted.
- At render time, `marks._locate` (`render/marks.py:253`) looks for `project_tex(quote)` in the **rendered HTML** of the enclosing block, through a projection that knows: `\(`→`$`, `\[`→`$$`, the eight text macros in `_TEXT_MACRO` (`\emph`, `\textbf`, …), references and citations via `data-tex`, and whitespace collapsing. Nothing else.

Anything outside that projection fails silently:

| In the quote | In the rendered block | Result |
|---|---|---|
| `~` | `&nbsp;` → U+00A0; `_norm` treats it as a space, but the quote still has a literal `~` | not found |
| `\S` | `§` | not found |
| `\noindent`, `\bigskip` | dropped (`convert.IGNORED_CMDS`) | not found |
| `\red{…}` (a user macro) | expanded or dropped | not found |
| `\end{theorem}` | nothing | not found |
| `--`, `---`, ``` `` ``` and `''` | `–`, `—`, `“`, `”` | not found (not hit here, but the same class) |

### 2. The fallback escalates to the wrong unit

`place_marks` (`marks.py:78-120`) chooses the smallest block **whose `data-src` span covers the selector's source span**. When `_locate` fails inside that block, the whole block gets `data-annotation` and `class="annotation-block"`.

For a quote beginning with `\noindent`, the selector's span starts at the `\noindent`, but `convert._walk` starts the paragraph's `data-src` span after the ignored command (`pstart[0]` is advanced past ignored tokens, `convert.py:580-593`). No `<p>` covers the span, the first candidate list is empty, and the second list (`marks.py:106-110`) admits `section`. So a quote that begins with a layout command marks the entire section's prose, and in the master's fragment the entire section including every subsection and theorem.

### 3. Nothing tells the writer

- `loom annotate` prints the id and nothing about placement.
- `loom ai annotations --json` reports `detached` (the quote is gone from the source) but not "placed at block level" or "placed at section level".
- `loom lint` has `loom:detached-annotation` but no diagnostic for a mark that fell back.
- The agent's orientation says a quote must be "a substring of the key's own text, copied exactly from the source" (`rules.md` §Findings 2). Following that rule exactly is what produced the failures: copying `\S~\ref{…}` exactly from the source is correct by the rule and wrong for the viewer.

### 4. An anchor cannot be corrected

- `loom annotate --edit ID` supersedes body, severity or payload (`cli/review.py:642`, `check_edit`); it does not accept `--quote`.
- `--batch` lists `quote` among its keys, but only for a new annotation; with `edit` the quote is ignored.
- So re-anchoring means filing a new annotation and withdrawing the old one with `--discard`, whose documented meaning is "withdraw a finding you should not have raised". The log now says four findings were withdrawn when in fact they were re-anchored, and the viewer shows the originals as settled with a text note pointing at the copy.

### 5. Marks for settled annotations are still placed

After a rebuild, the four discarded and one resolved whole-section/whole-paragraph annotations still carry `data-annotation` in the fragments (`a-2026-10-02-0024`, resolved, still marks 12,176 chars of `draft4.html`). Arras hides settled marks at rest (`mount.ts:63`, `settled()`), so this is invisible unless the "show settled" control is on, but the fragment still carries the fallback and it reappears the moment the control is used.

### 6. The `replace` payload ties highlight length to replacement length

`--placement replace` says the payload replaces the anchor. A suggestion that replaces a sentence therefore has to quote the sentence (198 and 208 characters in this session), and a suggestion that replaces a paragraph has to quote the paragraph. There is no way to say "replace the paragraph containing this short anchor".

### 7. Agent-side faults, for completeness

- Anchoring an "after the theorem" suggestion on `\end{theorem}` was a poor choice; the last sentence of the statement works and the message can say "after the environment".
- Quoting a `\red{…}` note in full rather than a few words of it.
- Nothing in the orientation warned against either, but an agent that had looked at the viewer once would have learned.

## Recommendations

1. **Check placement at write time.** `loom annotate` already has the node's fragment or can produce it; run `_locate` on the quote and refuse, or warn, when it would fall back: *"quote will mark the whole paragraph; it begins with `\noindent`, which the viewer does not show — quote from `Problem 1:` instead"*. The fix the agent would make is mechanical, so loom could offer it.
2. **Widen the projection** to the TeX the converter itself understands: `~`, `\S`, `\P`, `\,`, `--`/`---`, TeX quotes, ignored layout commands (strip them from the quote), and user macros through the same macro table `convert` uses. The quote should be projected by the converter, not by a second, smaller projection in `marks.py`.
3. **Never fall back past the paragraph.** If no block covers the selector span, trim the span to the first covering `<p>`, or mark the block that contains the span's *end*. A section-level mark is never what a quote meant.
4. **Add a re-anchor verb.** `loom annotate --edit ID --quote NEW` should record an `edited` event with a new selector, the way `--edit` records a new body. The event log keeps the old anchor; the viewer draws the new one.
5. **Report placement in the CLI.** `loom ai annotations --json` should carry `placed: inline | block | section | none` for each annotation, and `loom lint` should raise `loom:annotation-fell-back` for `block`/`section`, so an agent's re-check (or a `loom ai finish`) can catch what the author otherwise discovers in the viewer.
6. **Drop marks for settled annotations** from the fragments, or at least never place a fallback mark for one.
7. **Decouple the replaced range from the highlight.** Allow `--placement replace-paragraph` (or `--replaces START..END` offsets taken from a short anchor) so a short, unique quote can carry a long replacement without lighting up the whole passage.
8. **Tell the agent.** One line in `rules.md` §Findings 2: *"Quote words the reader sees. Do not begin a quote with `\noindent`, `\bigskip`, `~`, `\S` or an `\end{…}`; a quote inside a display marks the whole display."* Better still, make 1 happen and let the refusal teach it.

## Not checked

- Whether the "show settled" control in arras actually draws the stale section-level marks; inferred from `mount.ts` and the fragment contents.
- The exact `pstart` arithmetic for `\noindent` in `convert._walk`; the mechanism in §2 is inferred from `IGNORED_CMDS` and the observed `section`-level fallback, with the paragraph's `data-src` starting after the quote's offset.
- Whether the Codex permission rules differ.

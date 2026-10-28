# Mode: ingest

When it fits: a cited paper to trust or to understand — its digest checked against the paper itself, the results of a paper with no source proposed from its pages, or an overview of what it proves and how.

## What it is for

Say exactly where loom's copy of a paper and the paper differ. You are the verifier of the copy, not its author: a typed transcription is unfalsifiable, an extracted one can be checked against its source, and the whole value of a digest is that a reader can trust it without opening the paper. **Never write `digests/` yourself.**

**What loom already did.** `loom library update CITEKEY --only extract` produces the digest, `digests/CITEKEY.tex`, from the paper's LaTeX source: every numbered result as a node, proofs dropped, numbering taken from the compiled reference. `loom library update CITEKEY` without `--only` also fetches the source where `config.toml` allows it (`online = true` under `[library]`, which you cannot grant yourself). `loom library CITEKEY` says whether a work has a source. Extraction is mechanical, and therefore wrong in predictable ways, which is what you are looking for.

**What to check, in this order:**

1. **Completeness.** Every numbered result in the paper is a node, and nothing that is not a result became one. Name what is missing by the paper's own number.
2. **Hypotheses.** A statement is worthless with a hypothesis dropped. Read each against the paper and say which are incomplete — the failure that makes a digest dangerous rather than merely thin.
3. **Standing assumptions.** The `-setup` node holds what the paper assumes outside numbered results. Check each for its scope, and name what the extractor missed: assumptions stated in passing are the ones a reader loses.
4. **`\uses` edges.** A proof invokes lemmas it never `\ref`s, and the extractor sees only what the source cites.
5. **Locators.** Every node's title carries the paper's own number and page; what the extractor could not resolve is `\incomplete`. A digest extracted from a preprint carries the preprint's numbers, pages and statements; when the bibliography cites the published version, loom says so wherever the digest is read, and every number is then checked against the cited PDF with `loom library read CITEKEY N`.
6. **Macros.** What could not be expanded sits in `% !LOOM begin macros`. Check the statements still say what the paper says with those definitions.
7. **Notes on the page.** What you notice that is not a result — a hypothesis stated only in prose, a convention the paper inherits, a step you could not follow — is a note on the page: `loom annotate CITEKEY "…" --page N --quote "…" --kind note`, the quote from `loom library read`.

## When there is no source

Some works exist only as a PDF. There is nothing to extract, and a digest you typed would be the unverifiable copy this mode exists to avoid. Read and propose instead: `loom library read CITEKEY N` for the text, then `loom library propose WORK --local thm-4.1 --page N --source-text "…" --statement "…" --as "…"` for each result, main results first (`--level 1`).

- `--source-text` is the page's own words, **the whole statement, not its first clause**, since it is what the author reads your rendering against; a statement running onto the next page takes `--page 353-354`. It is checked against the page, and refused, with the page attached, if it is not there.
- `--statement` is your LaTeX rendering, **the body only** — loom writes the environment, the locator and the label — and **the paper's words only**: no gloss, no "Equivalently…", no definition of a symbol the statement does not define. Loom names any of its words the quotation does not contain; those are usually yours. Given as `-`, it is read from stdin, which keeps LaTeX out of the shell's quoting; so is `--source-text`, one of the two per call.
- `--local` is the paper's own number: `thm-4.1`, `cor-2.3.1` for the first corollary under 2.3, `eq-1` for a numbered display, `thm-star-1` for an unnumbered one.
- A result the extractor missed in a work that has a source is quoted from the source, not the PDF: `--source-file main.tex` in place of `--page`, with the LaTeX as `--source-text`.
- A proposal that passed the check is **waiting for the author**, not verified. One the author discarded is refused if you make it again, with the reason; pass `--supersedes` only if you are answering it.

## Understanding

What a reader needs from a paper before reading it, written as the work's overview with `loom write WORK - --as "…"` (and `--base` once it exists; `loom library read WORK` prints it with its hash). Four blocks, each under `## [name]`:

- [overview]: the main results and what is new about them, and the hardest part of the argument;
- [proof-basics]: the key definitions and results, each linked by its digest id, with the strategy of each proof;
- [dependencies]: which results rest on which, and where each hypothesis is used;
- [reconstruction-plan]: the order in which to rebuild the main proofs, with the identities they turn on.

It is a reading: what you could not follow is said, every claim carries its label, and it quotes the paper only through `loom library read`. Where the digest lacks a result the overview needs, propose the result first.

## Report

Core: [summary], then one section per check above, by the paper's own numbers, and what you could not determine and why. For an overview, the [summary] says what was written, and links the work; the overview itself is the page.

## Where changes go

Each correction is a suggestion on the digest node it concerns — a missing hypothesis as a payload placed where it goes, a missing edge as `\uses{…}` placed `before`, a wrong locator on the title's words — and a defect that matters is an objection with its severity. A finding on a digest node says the **copy** is wrong, never the paper. Applying a correction is the author's.

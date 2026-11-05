# Digests

A digest is loom's copy of one cited work's results, each a digest node with a permanent id, in a LaTeX file that obeys the source contract. This spec defines that file and the records beside it, and how a cited work's results get their ids, states and edges.

## 1. Files

All under `.loom/digests/` in the quilt:

| Path | Holds |
|---|---|
| `bibliography.bib` | the quilt's bibliography (§10) |
| `<citekey>.tex` | the digest: extracted and verified results |
| `<citekey>.proposed.tex` | proposals, not yet verified |
| `<citekey>.results.json` | one record per result: both texts, anchor, level, class, state, origin |
| `<citekey>.proposals.jsonl` | the event log, with each discard's reason |
| `links.jsonl`, `links-removed.jsonl` | relations (§9) |
| `storage/` | the cited works' documents (§10) |

A viewer receives these as the manifest's `references`, whose shapes [manifest.md §13](manifest.md#13-references) defines under the rules in [README.md](README.md).

## 2. The digest file

The header is `% !LOOM` directives in the first twenty lines:

- `digest: CITEKEY` (required) names the citekey verbatim; one missing from the bibliography is `loom:digest-without-bib` (warning).
- `prefix: NAME` is the id prefix (§3), by default the citekey's slug. Extraction always writes it, so ids survive a citekey rename.
- `extracted-from:` and `published-as:`, see §6.
- `method:` is `extract` (from LaTeX), `pdf` (from pages), `mixed` (more than one; each result's `class` says which) or `manual` (by hand).
- `numbering:` is `emulated` when no compile gave an `.aux`, and `mixed` when some numbers were counted instead of read. Without it, every number came from a compile.
- `requires:` lists packages beyond amsmath, amsthm and loom; one the default master lacks is `loom:missing-package` (warning).

Extraction then writes an optional macro block (§4), `\section*{Overview}`, a `<prefix>-setup` node holding the work's standing assumptions, and the work's sections with its results in order:

```tex
\section{Virtual pullback}\label{Man12-sec-4}

\begin{theorem}[{\cite[Theorem 4.1, p.~12]{Man12}}]\label{Man12-thm-4.1}
\uses{Man12-prop-3.2, Man12-setup}
\label{Man12-main}
Let $f\colon X\to Y$ be ...
\end{theorem}
```

A result's environment needs no document to declare it: the optional argument `[{\cite[LOCATOR]{key}}]` marks it as a result, so the scan treats the environment as theorem-like in this file, named from the locator's first word when that names a kind of result and otherwise after the environment, and a document's own declaration wins. A quilt of digests alone therefore has their results as nodes.

A result's title is its locator, with the page wherever loom found the result in the filed copy, and its body is the statement, verbatim. Proofs are never copied; a `\ref` to another result inside a dropped proof becomes a `\uses` entry.

## 3. Ids

An id is `<prefix>-<local>`, where `local` is letters, digits and dots in hyphen-separated parts (`loom/src/loom/scan/labels.py`):

- `<prefix>-<abbrev>-<number>` for a numbered result: `Man12-thm-4.1`, `Man12-cor-2.3.1`, `Man12-thm-A`. `abbrev` is `thm`, `lem`, `prop`, `cor`, `def`, `rem`, `ex`, `constr`, `conj`, or `eq` for a numbered display; other environments use their own name.
- `<prefix>-<abbrev>-star-<n>` for the n-th unnumbered result of that kind.
- `<prefix>-sec-<n>` for a section or subsection holding results, `n` its number as the paper prints it, a `\setcounter{section}` or `{subsection}` followed (a paper whose introduction is section 0 sets it to -1). Two headings the paper numbers alike are both written, and only the first is labelled.
- `<prefix>-setup` for the standing assumptions: the first three paragraphs under a heading that names conventions, notation, terminology or standing assumptions, up to the next heading of any level, `\part` included; a paragraph whose braces do not balance is left out, since a heading set inside a group leaves its opening brace behind.

A node's first label is its id when it has this shape; further labels are aliases. Every `\label` in an extracted statement gets the prefix, as does every `\eqref` to one, so the work's `\label{main}` becomes the alias `Man12-main` and two works' `eq:main` coexist. A label may hold one level of braces, as TeX reads it (`Def: Q_{tau}^vee`); it is read whole, and written with its braces dropped (`Man12-Def: Q_tau^vee`), so every reader of the digest reads it whole too. The slug is the citekey with everything but ASCII letters and digits removed; two citekeys with one slug are `loom:citekey-slug-collision` (error).

## 4. Macros

Extraction expands the work's simple macros in place. Macros the statements use but it cannot expand go into a block, each definition after `\let\NAME\undefined`:

```tex
% !LOOM begin macros
\let\Hom\undefined
\newcommand{\Hom}{\operatorname{Hom}}
% !LOOM end macros
```

Wherever a digest statement is compiled, loom writes `\begingroup`, the block, the statement, `\endgroup`. The work's meaning holds inside the group even when the quilt defines the same name, and the quilt's returns after it.

For rendering, each block becomes a macro set named by the citekey (`macros.sets`, [manifest.md §14](manifest.md#14-macros)), which each digest fragment names in `data-macros`; the viewer defines it before typesetting the fragment.

## 5. Citing a result

`\cite[POSTNOTE]{citekey}` creates an edge (`via: postnote`) to every node of that work whose locator the postnote names. `\cite{citekey}` alone cites the work, not a result, and makes no edge.

Both sides are normalised first, by the word lists in `loom/src/loom/scan/postnote.py`. A node answers to its locator, each part of it, and `<taxon> <number>` read off its id and each prefixed alias, so an alias `ro-thm-1.2.1` beside the id `ro-thm-1.0.1` answers both numberings. `-setup` answers `Standing assumptions`. A postnote is split on `,`, `;`, `and` and `&`, a bare number taking the taxon before it, so `Theorems 4.1 and 4.3` makes two edges.

1. Citations inside a work's own digest, whose titles all cite it, are never matched and raise nothing.
2. A postnote the work's digest does not answer is tried against its other versions' digests (§10); `loom:postnote-from-another-version` (info) names the one that answered.
3. No match while a digest exists is `loom:unmatched-postnote` (warning). A citekey cited with a postnote and no digest, its own or a version's, is `loom:undigested-citekey` (info).
4. Proposals are matched, but a match makes no edge: `loom:cites-proposed-node` (warning) says the result is unverified, and verifying it makes the citation a dependency. The same holds for a `\ref` or `\uses` naming a proposal from outside its own file.

## 6. Which version the numbers belong to

`extracted-from:` names the artifact the statements and numbers came from, such as `arXiv:0805.2065v2`. `published-as:` names the work the bibliography cites, when it differs. They are two facts, not two spellings of one. When the digest came from a preprint and the bibliography cites the published version, its numbers and pages are unverified against the copy a reader opens; `loom:unverified-locators` (warning) and the commands that read the digest say so.

## 7. Result states

A result's state is computed from its record (`state_of` in `loom/src/loom/refs/proposals.py`), never stored as a judgment:

- `proposed`: recorded by `library propose`, vouched for by nobody.
- `extracted`: read by loom from the work's LaTeX (`class: mechanical`), compared with the paper by no person.
- `verified`: a person compared the rendering with the source text and accepted it. A mechanical result is verified only once its origin holds a `verified` or `edited` act, which only `loom library verify` writes.
- `discarded`: rejected, its reason in the event log.

There is no `checked` state. A proposal that passed its page check has been checked, never verified: it stays `proposed` until the author verifies it. Verifying claims the copy is faithful, nothing about the mathematics, and records an acceptance, so a later change shows as `transcription-changed`. The author may correct the statement or local name while verifying; `source_text` never changes, so the anchor stays re-checkable.

Nothing `\input`s `<citekey>.proposed.tex`, and no edge leads to a proposal from outside it (§5, item 4), so a proposal is in no compile, no closure and no closure document.

## 8. How results arrive

**Extraction.** `loom library update` extracts a digest for every work with LaTeX source in the store and no digest; `--redo` extracts again, keeping what the author verified or edited. The algorithm is in `loom/src/loom/digest/`.

**Proposals.** For a work with only a PDF, or a result extraction missed, an agent reads pages with `loom library read` and records each result with `loom library propose`. The quotation must be on the named page (or in the LaTeX, with `--source-file`), folding only whitespace, line-end hyphens and ligatures (`loom/src/loom/refs/search.py`); otherwise nothing is stored. The rendering is the body only, in the work's words, and loom names each prose word the quotation lacks.

**Ingest.** Ingest is an agent mode (`loom ai mode ingest`), not a command. It checks extraction's output against the paper and never replaces it, handing the author its corrections as suggestions on the digest's nodes, with its report in the transcript. Nothing is typed from a PDF; a work without source is read and proposed.

## 9. Relations

`loom library relate FROM TO --kind KIND --why "…"` records that FROM relates to TO as `same-notion`, `generalises`, `specialises`, `depends-on` or `contradicts`. A relation is an assertion with a reason, attributed to whoever made it. It is never checked, never citable, and enters no closure and no digest.

## 10. The bibliography and the store

Every library step reads `bibliography.bib`. Gathering, the first step of `loom library update`, adds entries from the bibliographies the person's documents name, read from each document's own directory, then from the landmarks, and for stored documents no entry names. Loom only appends: an entry is never rewritten, so a hand correction survives, and it leaves only when the person deletes the work.

`storage/<scheme>/<id>/` holds a work's `paper.pdf` and `src/` (not committed) and page text (committed, so anyone can re-check an anchor). Beside the page text, `overview.md` is the work's **overview**: a reading of the paper an agent writes with `loom write WORK` and the author may edit, committed, and never part of the digest. It is not the digest's `\section*{Overview}`, which is the paper's opening paragraphs copied at extraction; `loom library read WORK` prints the overview where there is one and the opening otherwise. A PDF given to `loom library add`, or dropped in the viewer, is copied into the store whatever is known about it. It is filed against an entry on a strong match: an identifier on its first pages equal to the entry's, or the entry's whole title with its first author, where it names one, leading the byline or the file name, as a reference manager writes it (`loom/src/loom/refs/ingest.py`). Anything weaker is never filed against that entry without the person naming it. Such a PDF becomes a work of its own, added by hand: its entry takes what the file gives (a reference manager's file name, the PDF's document information, the first line of page one that could be a title, at the least the file name), and an identifier on its first pages, looked up where the network is allowed, adds to it only when the record's title is on the PDF's first page (`loom/src/loom/refs/add.py`). With no identifier it lives at `storage/file/<hash>/`, its entry saying so in `loom-file`, so correcting the title by hand does not move it. With `--for`, or from the work's own upload, the person's word files it, and what the PDF shows to the contrary is reported and recorded in `storage/copied.json`; only a LaTeX source is refused for showing it is another's, unless `--force`. A PDF with no text layer is filed the same way, without page text. A file that does not open as a PDF is the one thing refused. Saying what a PDF is reads its first two pages and its document information and never the rest; its page text is read whole only once, in runs of pages side by side, at once by `loom library add` and as a library run in the viewer, which says how far through the pages it is.

Copying is once per content hash (`storage/copied.json`, which names where each copy went relative to the store): a document renamed or given again is not copied again while the work holding it stands, unless the person names another work for it, and nothing leaves the store when the original is deleted. Deleting a work from the library takes its entry, its directory in the store and its digest files with it, and the ledger's record of its document, so the same PDF given again is a new document; a directory another entry also names stays, and a work a document cites or carries is refused, since gathering would bring it back. A second document for a work is a copy, recorded and not filed, or another version, filed beside the first under a sibling entry (`<key>A`), never over it: the document an anchor was checked against must never change.

## 11. Who runs what

An agent may run `loom library`, `update`, `read`, `search`, `review`, `why`, `check`, `locate`, `propose` and `relate`. `verify`, `discard`, `ignore`, `add`, `import` and `drop` are the author's, and refuse when an agent marker is set or `--as` names an agent. Flags are in `loom library --help`.

Loom uses the network only under `online = true` in `[library]` of `config.toml`, or `--online` for one run. An agent cannot give itself `--online`; only the author's config grants it the network.

## 12. What the draft decides

Today the library is organised around what the author's documents cite. Loom must also serve a reader with no draft, for whom a work read but not cited is first-class.

- Gathering seeds the bibliography from the documents' bibliographies and the landmarks, and otherwise only from what the author files with `library add`; seeding it from a reader's reading is ([not built yet](../design/README.md#decided-not-yet-built)).
- `update` fetches bibliography entries only, never a cited work's own references; following a reader's reading is ([not built yet](../design/README.md#decided-not-yet-built)).
- Ingest starts from works cited with a locator and no digest, as `loom status --undigested`, `loom ai orient` and `loom:undigested-citekey` list them; a trigger for works read but not cited is ([not built yet](../design/README.md#decided-not-yet-built)).
- Uncited works are demoted: `loom library` folds them into one line and never says they need an agent; `update` takes cited works first; lint counts their diagnostics in one line; `library search` ranks a result higher per citation in the author's documents. Treating a read work as a cited one is ([not built yet](../design/README.md#decided-not-yet-built)).

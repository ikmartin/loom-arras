# The source contract

This spec says exactly what loom reads from an author's LaTeX and what each construct means. Anything it does not name is ordinary LaTeX that loom passes over.

The old chapter 5 is frozen at [docs/book/05-source-contract.md](../book/05-source-contract.md) for history.

## 1. What is read

Loom scans every `.tex` file under the quilt root outside `build/`, `.loom/`, `ai/`, `refs/`, `digests/storage/`, `notes/`, `retired/`, the history and tool directories, unless its first twenty lines include the line `% !LOOM ignore`. A master is a file with `\documentclass` directly in a drafting directory; files it reaches by `\input`, `\include` or `\nest` (an `\input` one heading level down) are read in its context. Files no master reaches are scanned too.

Comments are blanked first: each, from an unescaped `%` to the end of the line, becomes spaces, except in `verbatim`, `lstlisting`, `comment` and `filecontents` environments and `\verb`. A commented-out environment defines nothing, and a commented-out `\ref` is no dependency. Directives (section 8) are read before blanking.

The scanner is not TeX: it reads surface forms and never expands the author's macros, so a `\lemref{X}` defined to wrap `\ref` is no dependency on X.

## 2. Nodes

Theorem-like environments, headings and proofs are nodes. "With an id" means the first label is id-shaped (sections 3 and 4).

| In the source | Key |
|---|---|
| theorem-like environment with an id | the id |
| theorem-like environment without | `FILE#ENV:N`, the Nth `ENV` in FILE |
| heading, `\part` to `\subparagraph`, with an id | the id |
| heading without | `FILE#LABEL`, else `FILE#COMMAND:N` |
| attached proof (section 5) | its id, else `S/proof`, `S/proof/2`, … |
| unattached proof | `FILE#proof:OFFSET`; `loom:unattached-proof` (error) |
| other environment: `equation`, `figure`, undeclared | none; its labels name regions, `KEY#LABEL` |
| a file | none; it owns the text no node claims |

An environment is theorem-like when a master declares it: by `\newtheorem` or `\declaretheorem` in its preamble or the local files the preamble loads, or by `% !LOOM environment: ENV = Name, style` in the master. The declared name is the taxon. An undeclared environment is prose, and `loom:unknown-environment` (error) if it has a common theorem-like name.

### 2.1 Basis

Each theorem-like node has a basis, inferred from its environment name or taxon, or from a `[basis]` table in `config.toml`:

| Basis | Names |
|---|---|
| `local-proof` | theorem thm lemma lem proposition prop corollary cor claim fact |
| `expository` | definition defn def notation construction convention remark rmk rem comment example examples exmp caveat warning note recall terminology |
| `assumption` | assumption axiom postulate hypothesis |
| `open-claim` | conjecture conj question problem |
| `cited-result` | a block whose title holds, or whose body opens with, `\cite[LOCATOR]{KEY}`; every digest node |

A block is **unclassified** when its names give no basis or two, when it cites without a locator, or when it has a proof but another basis. A line `% !LOOM basis: CATEGORY` inside the block settles it. An unclassified block a master reaches is `loom:needs-classification` (warning), and `loom accept --all-live` and `--master` refuse while one is in scope.

A `local-proof` block needs a proof unless it holds `\incomplete{TEXT}`, which marks a statement or proof incomplete whatever the ledger says; `loom accept` refuses an incomplete key.

## 3. Ids

### 3.1 Grammar

```
id         := prefix "-" local
prefix     := [A-Za-z0-9]+
local      := loomlocal | paperlocal
loomlocal  := [0-9A-Z]{4}                          base 36: 0001, 00ZZ
paperlocal := [A-Za-z0-9.]+ ("-" [A-Za-z0-9.]+)*   a paper's number: thm-4.1
derived    := prefix "-" loomlocal "-ai"           an agent document's copy
```

A prefix that is a citekey slug takes `paperlocal`; others take `loomlocal` or `derived`. A slug is a citekey stripped to ASCII letters and digits (`Fulton-Int:1998` gives `FultonInt1998`); loom knows the slugs of the citekeys in `digests/bibliography.bib` and the prefixes digests declare. So `sec-intro` is an id only if `sec` is a slug, while `\label{fig-0001}` on a lemma is its id whatever the quilt's prefix.

### 3.2 Never reused

`loom new` and `loom id` allocate one past the largest loom-local id visible under the prefix, recomputed on each call from:

- every `PREFIX-XXXX` in any scanned file, comments and dangling references included;
- the acceptance and history ledgers, the history's step file names, and the annotation log;
- with git, every tracked file in the newest 500 commits on any ref (`git rev-list --all`, then `git grep`).

A number is free only if nothing ever wrote it down; renaming an id deletes one node and creates another. Redefining an id the history recorded as removed, with a text it never recorded, is `loom:id-reused` (error).

### 3.3 Defined once

A node is defined once and included many times. When two scanned files define one id, it is **conflicted**: `duplicate-id` (error) names each file, offering `loom fork ID --in FILE` for each. References to it resolve, but it has no text and no winner, so it cannot be accepted, annotated, compiled or reverted. Choosing a definition by walk order would fail silently:

1. the viewer would publish one copy, chosen by filename, and hide the other;
2. a closure document would follow one copy while the paper compiles the other;
3. hashes, staleness and acceptance would rest on a text nobody chose;
4. an agent could edit one copy while the other quietly disagrees.

Two definitions in one file are `duplicate-id` but not conflicted: the later one holds the id.

## 4. Labels

The first `\label` in a theorem-like environment's own text, outside environments nested in it, is its id if id-shaped; the rest are aliases, resolving to the node. A heading's labels are those after its arguments on its line, else those on the next non-blank line, unless that line opens an environment or a heading. Comment-only lines are blank.

```tex
\section{Results}
\label{rl-0002}\label{sec:results}   % the heading's id and an alias
```

Any other label (an equation's, an `\item`'s, one in prose) names a region of the node whose own text holds it, and a reference to it is a reference to that node. Every label is unique across the quilt (`duplicate-id` for an id, else `loom:duplicate-label`): stricter than LaTeX, since closure documents combine text from many files.

## 5. Proofs

A `proof` attaches by the first rule that applies:

1. **Reference.** Its optional argument names a node by `\ref`, `\cref`, `\Cref`, `\autoref` or `\eqref`, as in `\begin{proof}[Proof of Theorem~\ref{rl-0003}]`; it may be anywhere. The first name that resolves wins; if none does, rules 2 and 3 apply.
2. **Adjacency.** It follows a theorem-like sibling with only whitespace and comments between, skipping a `remark`, `rmk`, `rem` or `comment` environment, or follows a proof attached this way, joining its statement. Any prose between breaks adjacency.
3. **Enclosure.** It sits directly in a theorem-like environment with no theorem-like sibling before it.

A statement may have several proofs, keyed by their ids or else `S/proof`, `S/proof/2`, … in the default master's order; `loom:positional-proof-key` (info) warns that deleting one renumbers the rest.

## 6. Edges and the closure

An edge runs from a key's own text (section 7) to a node: a statement-, proof- or prose-edge as that text is a statement's, a proof's, or a section's or file's. Sources:

1. `\ref`, `\eqref`, `\autoref`, `\pageref`, `\vref`, `\Vref` (one label) and `\cref`, `\Cref` (a list), starred or not;
2. `\uses{X, Y}`, for a dependency the text does not name;
3. `\cite[POSTNOTE]{CITEKEY}` and `\citep`, `\citet`, `\parencite`, `\textcite`, `\autocite`, `\footcite`, `\cites`, `\Cite`, `\Parencite`, `\Textcite`, when the postnote (the second of two optional arguments) matches nodes of CITEKEY's digest (section 9);
4. a theorem-like environment directly inside a proof.

A label resolves to the node with that id or alias, or owning that region, else is `dangling-link` (error). No node depends on itself, nor a proof on its statement.

A master's text before `\begin{document}` gives no edges, since macro bodies there hold `\ref{#1}`. Only that text is exempt: a `.tex` file the preamble `\input`s is scanned like any other, so a `\ref{#1}` in it dangles.

The **closure** of a statement is every node reachable from it by statement-edges, dependencies first; a proof's closure adds the targets of its own edges and their closures. Dependencies' proof-edges are never followed: a lemma's proof is not in the closure of a theorem citing the lemma. A closure document compiles exactly this.

## 7. Ownership and hashing

Ownership partitions each file among the file, each section's span in it, each theorem-like environment and each proof: every character belongs to the innermost claimant containing it, and a node's own text is its region minus its children's. A section's span ends at the next heading of equal or higher level in the same file, or at the file's end (`\end{document}` in a master), so ownership never depends on which master reached a file.

A key's hash is over its own text as written, with each child replaced by a line `% !LOOM child: KEY`, and an `\input`, `\include` or `\nest` line of a file with nodes by one marker per outermost node there; a parent hashes the same with a child inline or in its own file. Comment-only lines other than directives are dropped (a trailing comment stays), trailing whitespace and repeated blank lines go, and tabs become four spaces. Whitespace inside a line counts, so reflowing a paragraph changes the hash. The hash is `sha256:` and the hex SHA-256 of the UTF-8 bytes.

## 8. Directives

A directive is a line whose first non-blank characters are `% !LOOM` (the space optional), followed by a bare word or `key: value`; an unknown key is `loom:unknown-directive` (warning). Directives declare and never act: as comments they never change the PDF, and none makes loom write, compile or fetch anything. One in a file's first twenty lines, before its first node, applies to the file or every node in it; one in a node's own text applies to that node and overrides the file's.

- `ignore` (file): do not scan this file;
- `author: NAME, NAME`, `created: YYYY-MM-DD`, `tags: a, b` (file or node): who wrote it, when, and thematic labels;
- `see: ID, ID` (file or node): related nodes, for the viewer;
- `name: SHORT NAME` (node): a display name, which never stales an acceptance;
- `basis: CATEGORY` (theorem-like node): section 2.1;
- `environment: ENV = Name, style` (master): declares a theorem-like environment.

`see:` declares a relation, never a dependency. Items resolve like references. A relation enters no closure, acceptance or staleness check, so a detailed version of a result can change without staling the short one.

## 9. Digest nodes

A digest is a file whose first twenty lines carry `% !LOOM digest: CITEKEY`, kept at `digests/CITEKEY.tex` and specified in [digests.md](digests.md). Its theorem-like environments, proofs and sections are digest nodes: a cited paper's results, with locators in their titles, never proved here.

```tex
\begin{theorem}[{\cite[Theorem 4.1]{Man12}}]\label{Man12-thm-4.1}
```

The id is `PREFIX-PAPERLOCAL`: PREFIX is the header's `% !LOOM prefix:`, else the citekey's slug. Loom writes the prefix into each digest it makes, so the citekey is not always the prefix; `loom search CITEKEY` gives the ids. Digests are loose, yet never `unreachable`, and references to them are never `loom:reference-to-loose`.

A postnote matches the nodes whose locator, or the taxon and number in whose id, it names once both are normalised ([digests.md §5](digests.md#5-citing-a-result)); `Lemmas 2.1 and 2.3` gives an edge to each. With no digest, or no match, there is no edge.

## 10. Diagnostics

Every code named here is defined in [diagnostics.md](diagnostics.md).

# Deviations from the book

Every place the implementation departs from a `[decided]` statement, or settles an `[assumed]` or `[deferred]` one in a way worth recording. Each row also has a decision record in `docs/book/A-decision-records.md` (DR-39 onward). The final book revision walks this table and marks each row `book updated: y`.

| date | section | book says | implemented | why | DR | book updated |
|---|---|---|---|---|---|---|
| 2026-09-15 | 10.8 | arras source never contains the words quilt, digest, proof, or any loom command | guard test forbids quilt, atomize, unravel, and "loom <command>" phrases; digest and proof are exempt as manifest field names and the spec's route | `specs/manifest.md` §3, §4, §13 and route `/digest/<citekey>` use them; `crypto.subtle.digest()` too | DR-39 | n |
| 2026-09-15 | 5.1.4, 5.2.3, 6.2 | import and atomize refuse non-anchored environments | scanner tolerant by character offset; atomize refuses; import --fix-anchoring (M4) | 43 % of Manolache's nodes; user decision | DR-40 | n |
| 2026-09-15 | 5.6.1, 5.7.1 | proof attaches by adjacency or \ref only | plus enclosure; nested statements are nodes with `nested` proof-edges | Manolache and ACGS nesting | DR-41 | n |
| 2026-09-15 | 5.5.2 | external node = \cite in the title | or \cite as the first body token | all real instances | DR-42 | n |
| 2026-09-15 | 5.4.2 | heading label on the same or next non-blank line | unless that line opens an environment or heading | label theft | DR-43 | n |
| 2026-09-15 | 5.9.1 | \input{path} with .tex appended if absent | exact path, then .tex; braceless form; kpsewhich names ignored; non-.tex opaque | pspdftex figures, \input xy | DR-44 | n |
| 2026-09-15 | 5.3.1, 5.4 | digest prefix is the citekey | citekey slug with collision error; labels whitespace-normalised | punctuated citekeys, wrapped labels | DR-45 | n |
| 2026-09-15 | 5.5.1, 5.5.3 | closure = preamble plus local \usepackage files | transitive through .sty, comma lists; macro names expanded; unknown styles plain with warning | relloc's math-env.sty two hops away | DR-46 | n |
| 2026-09-15 | 5.1 | scan .tex files | decode Mac Roman then Latin-1 with a warning | Mac Roman arXiv source | DR-47 | n |
| 2026-09-15 | 5.13 | comments removed for hashing | comments blanked before every stage | commented duplicate label | DR-48 | n |
| 2026-09-15 | 5.9.2, 5.9.3 | sectioning on the expanded text; own text per node | hierarchy per master, ownership per file | hashes independent of the reaching master | DR-49 | n |
| 2026-09-15 | 5.7.1, 5.8 | edges from every own-text region | none from a master's preamble; none to oneself; single-label commands not split | macro bodies, labels with commas | DR-50 | n |
| 2026-09-15 | diagnostics.md, 8.1.2 | unreachable for a node or file | once per loose file, never for digests | noise | DR-51 | n |
| 2026-09-15 | diagnostics.md | fixed code table | five codes added | new conditions | DR-52 | n |
| 2026-09-15 | 5.5.1 | unknown-environment when a node uses an undeclared ENV | detected only for common theorem-like names | needs a heuristic | DR-53 | n |
| 2026-09-15 | 10.1.1, 10.7 | prerender every route to static files so a site is crawlable | shell prerender: one index.html per route plus the build directory; content loads client-side | needs a second data path; deferred | DR-54 | n |
| 2026-09-15 | 9.4.3, 10.1 (assumed) | MathJax 3 | MathJax 3 tex-svg, bundled | no font assets offline | DR-55 | n |
| 2026-09-15 | 8.3.5, 10.1 | arras takes one macro set per page | per-fragment set applied via \renewcommand inside the fragment's math | MathJax macros are global | DR-56 | n |
| 2026-09-15 | 10.1.2 | hash routing under file:// | path routing; SPA fallback in loom serve; file:// unsupported | router type is build-time | DR-57 | n |
| 2026-09-15 | specs/fixture.md §1 | missing \input and beamer talk redeclaring lemma | \iffalse-guarded missing include; talk declares proposition | both masters must compile | DR-58 | n |
| 2026-09-15 | 7.6.3 | proved needs an accepted proof | nodes that owe no proof are proved by acceptance | definitions could never be settled | DR-59 | n |
| 2026-09-15 | 7.4.2 | id counter per file | counter over every record | quilt-wide uniqueness | DR-60 | n |
| 2026-09-15 | 5.14 | lint = scanner checks | lint and check also report record-derived codes | codes need the records | DR-61 | n |
| 2026-09-15 | 5.9.2.3, 8.3.1 | loose files sectioned per file (stated, unimplemented) | files reached by no master get their own section units; digest headings become `<citekey>-sec-<n>` nodes | `loom id` on loose files; digests | DR-62 | n |
| 2026-09-15 | 5.6.1 | a `\ref` in the proof's optional argument decides attachment | when every named label is unknown, position decides and the label is a dangling link | deferred proofs with a typo'd label were unattached | DR-63 | n |
| 2026-09-15 | 6.2.4 | id label inserted after the heading | inserted directly after the heading's arguments, before existing labels | the id must be the first label | DR-64 | n |
| 2026-09-15 | 6.3, 6.4, 6.6 | identity test on the master | for a non-master SRC, the first reaching master is compiled with DEST in SRC's place in a scratch copy | section files have no PDF of their own | DR-65 | n |
| 2026-09-16 | 8.7 | `\cite[postnote]` in any region creates an edge | not when the citing node is in the digest of that citekey (its own locator title) | a digest node would depend on itself or its section | DR-66 | n |
| 2026-09-16 | 8.5.3 | ids `<citekey>-<abbrev>-<number>` | unnumbered results get `-star-<n>` and the locator `(unnumbered)` | `\newtheorem*` results have no number | DR-67 | n |
| 2026-09-16 | 8.5.2 | emulate counters only when compilation fails | emulate always, resynchronised at each `.aux` number; `numbering: emulated` only without an `.aux` | the `.aux` numbers only labelled results | DR-68 | n |
| 2026-09-16 | 8.1.7 | map environments by display name | prefer the numbered environment when a display name is declared twice | starred twins such as `thm*` | DR-69 | n |
| 2026-09-16 | 5.1 | scan every `.tex` under the root except `build/` | `ai/`, `refs/src/`, `refs/pdf/`, and `.claude/` are skipped too | run outputs and fetched sources are not the quilt's text | DR-70 | n |
| 2026-09-16 | 11.12 | skill stubs and slash commands | both are generated; skills carry the target as `$ARGUMENTS`, commands are one-line wrappers Claude Code now calls legacy | commands and skills were unified upstream | DR-71 | n |
| 2026-09-16 | 11.4.1 | the agent is launched with the orientation as its initial prompt | launched with a one-sentence pointer to `loom ai orient --run RUN`, `LOOM_RUN` set | the orientation is long and `orient` adds live state | DR-72 | n |
| 2026-09-16 | 5.5.1, 8.3.1 | macros are read from `\newcommand`, `\def`, `\DeclareMathOperator`, `\let` | also through aliases such as `\nc` declared by `\newcommand{\nc}{\newcommand}` or `\let`, resolved transitively | real preambles define hundreds of macros through one-letter aliases | DR-73 | n |
| 2026-09-16 | 8.3.2, 8.5.6 | the macro block holds unexpandable macros; `requires:` lists the reference's `\usepackage` lines | the block also carries `\newenvironment` and enumitem `\newlist`/`\setlist` definitions the statements use; page, font, and bibliography packages are left out of `requires:`; `\xspace` is dropped from expansions | bundles of the fetched papers would not compile otherwise | DR-74 | n |
| 2026-09-16 | 8.7 | a postnote matches a locator or `<taxon> <number>` from the id | also from any id-shaped alias of the node, so a digest can carry a result's number in another version of the paper | citations followed an earlier arXiv version | DR-75 | n |
| 2026-09-16 | 5.11 | `loom:reference-to-loose` for a statement referring to a node no master reaches | not when the target is in a digest file (digest sections included) | digests are loose by construction (8.1.2) | DR-76 | n |
| 2026-09-16 | 8.9 | `digest fetch` retrieves by the bib entry's arXiv identifier | only when `eprinttype`/`archiveprefix` is absent or arXiv; requests retry after a pause on 406 and 5xx; the PDF is fetched even when the source fails | JSTOR eprints and arXiv's burst refusals | DR-77 | n |
| 2026-09-16 | 10.1.2, 12.5 | `loom serve` falls back to index.html for paths without an extension | for every path that is not a bundle file or an asset, dots included; missing assets stay 404 | ids such as `ro-thm-1.0.1` have dots | DR-78 | n |
| 2026-09-16 | 9.4.2 | the fallback block compiles with the master's preamble closure | with the master's own preamble text compiled from the quilt root (`TEXINPUTS`), `@` made a letter, geometry and microtype neutralised, in a 16 cm minipage; a digest statement adds its macro block and required packages; three attempts before giving up | the closure's text defined every macro twice and lists cannot sit in LR mode | DR-79 | n |
| 2026-09-16 | 8.3.2 | the macro block is emitted at every extraction site | and never rendered as text: the digest document starts after `% !LOOM end macros` | the block's definitions were compiled a second time as a fallback figure | DR-80 | n |

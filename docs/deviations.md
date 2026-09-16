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

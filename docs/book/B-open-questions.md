# Appendix B. Open questions

Everything the design could not settle, collected from the chapters and specifications, with the marker each carries there. Each is closed by a decision record.

## From Chapter 2 (objectives)

- Whether criterion 10 (the external user) gates a release or only the claim "MVP done". [assumed: gates the claim]
- How many digests the MVP library must hold. [assumed: two]

## From Chapter 3 (vocabulary)

- Whether "thread" is too close to its withdrawn meaning. [assumed: kept]

## From Chapter 4 (the quilt)

- Interactive prefix prompt in `init` versus a required flag. [assumed: ask on a terminal]
- User-config keys beyond `[author]`. [not in MVP]
- Whether the minimal master's `\newtheorem` block should be configurable. [assumed: no]
- Merge tooling for the ledger. [assumed: none]

## From Chapter 5 (source contract)

- `\pageref` as an edge. [assumed: yes]
- A diagnostic for nested theorem-like environments. [assumed: none]
- The set of labelled-region environments. [deferred]
- `\declaretheorem` numbering keys. [assumed: irrelevant; `.aux` numbers]
- Labelling `\paragraph` units on import. [assumed: no by default]
- The id-shape rule for hyphenated human labels. [assumed: prefix-is-citekey decides]
- The git history check's implementation and cost. [deferred]
- The source map representation and cost. [deferred]

## From Chapter 6 (bringing a paper in)

- Files reached only by `\includeonly` or unusual `\includegraphics`. [assumed: reported, not copied]
- `atomize --sections` default. [assumed: off]
- Identity test comparing hyperref anchors. [assumed: no]
- The two fixtures' arXiv versions. [deferred: pin at first run]
- `--relative` atomize. [deferred]

## From Chapter 7 (review)

- Recording tool versions in the ledger. [assumed: schema only]
- `--kind ok` with a message. [assumed: allowed]
- Comment sessions per day versus per explicit session. [assumed: per day]
- Refusing acceptance when the master does not compile. [assumed: refuse; `--force`]
- Badge for accepted keys with many detached annotations. [deferred to arras: acceptance badge plus count]
- Dependency cycles and settledness. [assumed: warning; breaks settled]

## From Chapter 8 (digests)

- Library quilt as a config flag or as "no masters". [deferred]
- The extracted-id abbreviation map and overrides. [assumed: fixed map]
- Keeping proofs in a gitignored form for ingest. [assumed: no]
- Seeding the overview without an introduction. [assumed: empty with `\incomplete`]
- Locator normalization for letters and other languages. [deferred]
- Counter emulation fidelity. [deferred]

## From Chapter 9 (build and interface)

- `data-src` encoding. [deferred: characters plus byte offsets]
- PDF figures converted or embedded. [assumed: converted]
- `serve` port selection. [assumed: fixed default]
- Compiling on first build. [assumed: no]
- Id-beside-number in bundles. [deferred]
- The refresh endpoint fallback. [deferred; not built unless watching is too slow]

## From Chapter 10 (arras)

- Route scheme under `file://`. [assumed: hash fallback]
- Client-side graph layout at scale. [deferred]
- Dark theme in MVP. [assumed: yes]
- Closure list on node pages. [assumed: yes]
- Layout library (ELK versus dagre). [deferred]

## From Chapter 11 (the AI layer)

- Refusing to launch a missing agent command. [assumed: refuse]
- Nested runs. [assumed: no]
- Per-user mode templates. [assumed: per-quilt in MVP]
- Permission settings file formats. [deferred]
- Skill and slash-command stub formats and locations. [deferred]
- Structure of `thread.md`. [assumed: dated headings]
- `loom ai check` as a command name. [assumed]
- Import-by-reference in vendor files. [deferred]
- Agent launch flags. [deferred]

## From Chapter 12 (CLI)

- `check` compiling bundles by default. [assumed: stale only]
- `search --kind`. [assumed: yes]
- `loom open`. [not in MVP]

## From Chapter 13 (plan)

- M4 before M3. [assumed: M3 first]
- ACGS gating M4. [assumed: gates with documented edits]
- Alpha releases to PyPI from M2. [assumed: yes]

## From Chapter 14 (tests)

- Paper tier in a private CI. [assumed: no]
- Playwright against a live `serve`. [assumed: one integration test]

## From the specifications

- Footnote placement in the dialect. [assumed: inline]
- `nav.toc` in master fragments. [assumed: no]
- Diffs inlined or by path in the manifest. [assumed: by path]
- Full-text search index. [assumed: no]
- Manifest size limits. [deferred]
- `accept` exposed in the write API. [assumed: behind confirmation]
- CSRF for a localhost API. [deferred]
- Runner prompt as file versus stdin. [assumed: both]
- Streaming runner responses. [deferred]
- Fixture timestamps by variable or post-processing. [assumed: variable]
- Beamer talk in the fixture. [assumed: yes]
- `manifest.schema.json`. [deferred to M2 if time allows]

## Known unknowns that no chapter owns

- How often real papers violate line anchoring, and whether `import` should offer to fix it (an edit to a copy, so permitted) rather than refuse. [deferred; decide after Manolache and ACGS]
- Whether the converter's contract (9.4.1) covers enough of master prose to make the master view readable on a typical paper, or whether fallbacks dominate. [deferred; measure on the fixtures]
- Whether text-quote anchors survive the kinds of edits mathematicians actually make (renaming a variable throughout a proof detaches every quote containing it). [deferred; observe on relloc]
- Whether Overleaf resolves `\input` paths relative to the project root when the main document is in a subfolder. [deferred; the manual test settles it]
- Whether `latexmk` with `-outdir` handles `\include` and `bibtex` from the root for every author's setup. [deferred]

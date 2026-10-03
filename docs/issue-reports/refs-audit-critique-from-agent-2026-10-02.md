# Audit of the refs/digest system, from an agent session

- **Date:** 2026-10-02
- **Author:** Claude Code agent (Claude Fable 5.1), at the request of the quilt's author
- **Quilt audited:** `relloc` (`/Users/isaac/Desktop/relloc`), prefix `rl`, main `drafting/draft4.tex`, 64 author nodes
- **loom:** 0.1.0.dev0, interface 1; arras f116288
- **Method:** ran the system on this quilt (`refs ingest`, `refs coverage`, `refs match`, `refs find`, `refs grep`, `refs page`, `lint`, `status`, `deps`, `search`), read the files under `digests/`, and had a subagent read loom's refs/digest source and the design docs under `docs/`. Nothing in loom or the quilt was modified by the audit.

Stated goal of the library, from the author: make it easy to find and reference the literature in loom, and make the connections easy to see and view in the arras viewer.

## Verdict

The digest is over-weighted. A digest is the set of theorem statements extracted from a cited paper and loaded as external nodes; fetching LaTeX source is the mechanical route to it. The system extracts every statement from every paper up front, and almost none of it is used, while the two things the goal needs — a citation that always becomes a visible link, and good search — are the weak parts.

## State of the quilt when audited

- The author placed 39 PDFs loose in `refs/` and ran `loom refs ingest refs` and `loom refs build`.
- `digests/bibliography.bib` went from 35 entries (the quilt's `refs.bib`) to 76.
- `loom refs coverage`: 52 of 76 works digested; 67 have page text.
- Of the 26 works the draft cites: 19 have a digest, 4 have a PDF and page text but no digest (`atiyah-bott_…1984`, `garrel-siebert_…2026`, `graber-vakil_…2005`, `olsson_…2003`), and 3 have nothing (`stacks-project`, `SGA3-2`, `silverman_…1999`).
- 3,140 results across all `*.results.json`, every one `state: verified`, `level: 3`, `class: mechanical`.
- `loom status --json` reports `digests: reached 80, not_counted 3060`.

## Where it succeeds

- **Citation-to-result edges work when numbering lines up.** `\cite[Thm. 4.3]{manolache_VirtualPullbacks2012}` in `rl-001C` becomes a dependency edge to `manolacheVirtualPullbacks2012-thm-4.3` (`via postnote`).
- **Page text is the most useful layer.** `loom refs grep "virtual normal bundle"` returned 39 hits in 15 works with page and section; `loom refs page` is a checkable read, and quotations are verified against the page.
- **Ingest is conservative and shows its evidence.** It filed 23 PDFs and left 14 for the author, printing the signals for each.
- **`loom refs build` is one idempotent command**, and `loom refs coverage` reports honestly what each work has.
- **The viewer's Library** has a per-work item with Paper (pdf.js with result highlights), Digest and Info views; a work with only a PDF still opens and can be annotated.

## Where it fails

### 1. Almost nothing extracted is used, and all of it costs the author

- 3,140 results extracted; 80 reached from the draft (2.5%).
- `loom status` takes 31 s on a 64-node quilt; `loom deps KEY` takes about 4.5 s.
- `loom lint` reports 139 errors. Before the build it reported 10, all in `drafting/draft4.tex`. The other ~129 are inside machine-generated digest files the author cannot fix:
  - 88 `duplicate-id` (e.g. every label in `ranganathan_LogarithmicGromovWitten2022.tex` "defined twice" at the same line; `behrendfantechi…-sec-2` defined at two lines),
  - 19 `loom:duplicate-label` (e.g. `Abramovichetal2014Compar-notn:\arabic{notn`),
  - 15 `dangling-link` in digests,
  - 6 `loom:unknown-environment` (`condition`, `setting`, `assumption`, `problem`),
  - 1 `loom:environment-spans-files` (`\end{longtable}`).
- Also from digests: 43 `loom:missing-package` warnings and 17 `loom:dependency-cycle` warnings.

### 2. The author's own PDFs become duplicate works

- A PDF in `refs/` that matches an entry already holding a `paper.pdf` becomes a sibling entry (`<key>A`, `<key>B`), by design (DR-192; `refs/scan.py` `_free_key`, `copy_documents`).
- In practice the author's PDF is usually the same paper loom already fetched. Result here: 20+ sibling entries, many with a full second digest (`manolache_VirtualPullbacks2012A`, `kresch_CycleGroupsArtin1999A`, three copies of Punctured Logarithmic Maps).
- Every `refs find` and `refs grep` hit appears two or three times.
- There is no deduplication by title or by identifier across entries; the copy ledger only prevents re-copying byte-identical files.
- A PDF that matches nothing gets a key made from 24 characters of its filename (`Kato1989Logarithmicstruc`), with no bibliographic data.

### 3. A sibling without an identifier loses its PDF (bug)

- The sibling branch in `refs/scan.py` (around line 517) never writes `loom-file`.
- `olsson_LogarithmicGeometryAlgebraic2003A` and `…2003B` both resolve to `digests/storage/work/57e4b5ea`, which holds only `resolved.json`. Their PDFs are in `digests/storage/file/55558400e26abf74` and `file/5de76c1abbcfbbce`.
- Coverage shows both with no PDF, and `refs match` lists them as "no artifact".

### 4. Ingest attached a wrong PDF on two weak signals

- `Handbook of Moduli.pdf` ("Logarithmic Geometry and Moduli", Abramovich, Chen, Gillam, Huang, Olsson, Satriano, Sun) was filed as the PDF of `olsson_LogarithmicGeometryAlgebraic2003` on `first-author,title-on-page`. Olsson is the fifth author, and the title match is partial.
- The real Olsson 2003 PDF was then skipped because the slot was taken.
- `loom refs ingest --dry-run` and the real run print the same table, and a real run does not say which rows were skipped (`·`) or why.

### 5. "Verified" does not mean checked

- Mechanical results are written `state: verified, level 3` by construction (`refs/proposals.py` `record_extracted`).
- 16 of the 19 cited digests are marked `preprint`: extracted from arXiv while the bibliography cites the published DOI. Lint raises 27 `loom:unverified-locators` warnings, but the per-result state still says `verified`.
- Plan 0.12 §6 says level 1 (main results) is "derived where there is a source"; no mechanical result is level 1, so a paper's main theorems cannot be told from its remarks.
- A candidate-fetched preprint for an entry with no declared DOI is never flagged at all, because `published-as` is not written.

### 6. Version drift and locator shapes break matching

11 `loom:unmatched-postnote` warnings on the draft:

| Citation | Why it fails |
|---|---|
| `\cite[Def. 2.3]{romagny_GroupActionsStacks2005}` (×4), `[Prop. 1.5]` | Digest has only `def-2.1, def-3.1, def-3.3, prop-2.2, …`; extracted from an arXiv source, while the entry's filed PDF is 28 pages against 11 for the sibling copy |
| `\cite[Prop. 3.5.9]{kresch_CycleGroupsArtin1999}` | Digest has `lem-3.5.1, prop-3.5.2, cor-3.5.3` only |
| `\cite[Thm. 1.2]{halpern-leistner-preygel_…2023}` | Digest numbers are three-part (`def-1.1.1`, …); no `thm-1.2` |
| `\cite[Thm. 5.1.1.]{aranha-khan-latyntsev-etal_…2025}` | No `thm-5.1.1` in the digest (theorems are `0.1, 1.6, 2.1, …, A, C, D`) |
| `\cite[Eq. (4.4)]{…Punctured…}`, `[Appendix A]`, `[\S 3.1.1]` | Only theorem-like environments are extracted; equations and sections are not addressable |

There is no mechanical check of preprint numbering against the published version (WQ-39).

### 7. Extraction is thin on older papers

- `graber-pandharipande_LocalizationVirtualClasses1999`: 8 results (`lem-1…4, prop-1…3, setup`), no theorem.
- `kontsevich_EnumerationRationalCurves1995` and `LiandTian1998Virtualmodu`: the `setup` node only.
- These still count as "digested" in coverage.

### 8. No digest means no connection

- A located citation into a work without a digest creates no edge (`scan/postnote.py`); lint gives only an info-level `loom:undigested-citekey`.
- In this draft that covers six Stacks Project tags, `\cite[Thm. 3.2]{olsson_…2003}` and `\cite[Exp. IX, Rem. 7.4]{SGA3-2}`.
- In the viewer's graph such a work appears only in `papers` mode, not the default `reached` mode.
- A bare `\cite{key}` never creates an edge. 30+ of the draft's citations are bare.
- The works hardest to get source for (books, the Stacks Project, old papers) are exactly the ones that drop out of the picture.

### 9. Search is weak

- `loom refs find` is an unranked, case-insensitive substring match over statements, in file order (WQ-41).
- Its output truncates the id column, so the theorem number is cut off (`abramovichchengrossetalPuncturedLogarithmicMaps2025-thm-5.`, `aranhakhan…2025-co`), and it prints no statement snippet.
- `loom refs grep` is literal and case-sensitive.
- `loom search CITEKEY --json` returns `paragraph:1`, `paragraph:2` and `section:1` keys before any result.
- The viewer has no page-text search, and works are not in the command palette.

### 10. The viewer hides what loom knows

- Typed links between results (`links.jsonl`) are only listed under Info, not drawn.
- The preprint/published warning is not shown; only the arXiv `vN` mismatch is.
- Page links from digest locators require `ref.work == extracted_from`, so they do not appear for a DOI entry whose digest came from arXiv — most cited works here.
- For such an entry the PDF in the `doi/…` directory may itself be the arXiv preprint; only `src.json` records that.

### 11. Docs and code disagree

- The orientation (`loom/src/loom/assets/ai/orientation.md:25`) says `refs/` holds what was fetched. The code treats `refs/` as the author's seed space and stores under `digests/storage/`. The book (§8.4, 8.6, 8.9, 8.10) carries the same stale paths.
- The orientation says `refs build` refuses an agent, while the same document's permitted-command list includes it; the code does not refuse.
- Fetching is documented as using a "strong" candidate; `candidate_arxiv` accepts any recorded candidate (≥ 0.75).
- The arrival check is documented as title and first author; the code checks the title only.
- `loom status --undigested` listed three citekeys while seven cited works had no digest; the rule (cited with a locator) is not stated in the output.

## Recommendations

In priority order; 1 and 2 address both stated goals and remove most of the cost.

1. **Make the work and its pages the primary object.** Every located citation creates an edge to the work and opens the PDF at that place, with or without a digest. A Stacks Project tag resolves to its URL. A bare `\cite` creates a work-level edge.
2. **Make the digest lazy.** Keep the full extraction as a search index outside the node graph, and promote a result to a node only when it is cited or the author asks. This removes the lint, status and bundle cost of the 97% that is never reached.
3. **One work, several documents.** Attach the arXiv version, the published version and the author's own PDF to one entry as versions. Deduplicate by identifier and title at ingest. Match a citation against the version the bibliography cites. Fix the missing `loom-file` on siblings.
4. **Honest states.** Distinguish "extracted from preprint", "numbers checked against the published version" and "verified by the author". Either derive main results (level 1) or drop levels.
5. **One ranked search** over statements and page text, with full ids and snippets, case-insensitive, available in the viewer and the palette.
6. **Keep digest diagnostics out of the author's lint** unless a cited result is affected; report them under `refs` instead.
7. **Draw the links** between results in the viewer, and show version warnings there.
8. **Tighten ingest.** Do not attach on first-author when the matched author is not first; say in the output which files were skipped and why.
9. **Fix the docs**: `refs/` as the drop folder, `digests/storage/` as the store, and one consistent list of which commands an agent may run.

## Not checked

- The viewer was not opened; statements about arras come from reading its source.
- Digest statements were not compared against the published papers for faithfulness.
- Whether `loom refs add` overwrites an existing `paper.pdf` was not tested.
- Timings were taken once each, with no before-build baseline for `loom status`.

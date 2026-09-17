# WQ-02 · Recursive reference crawl: building a library

**Repo:** loom

## Trigger

The author decides to build a library. This is a decision, not an observation: the prerequisite, identifying a work from a bibliographic string, landed in [plan 0.7](../plans/0.7-three-queue-items.md) as `loom refs resolve`, and the design below was settled with the author on 2026-09-17.

## Why deferred

Only because it has not been started. It used to wait on identity resolution — nine citations in ten cannot be followed as written — and on where a confirmed identity is recorded (WQ-23). The first has landed. The second binds only the author's own bibliography entries, and the design follows lookup matches instead of waiting on it (see *Identification*).

## What it is

A breadth-first walk over cited works. Depth 1 is the quilt's own bibliography; depth 2 is what those works cite; and so on. The output is a **library**: the works, the citations between them, and the downloadable sources, filed under `refs/`. The same mechanism builds a sizable library for one project or, with the cap raised, an actual corpus. Connecting one quilt to another's library ([[WQ-03]]) is deferred until a library exists to connect to.

## Controls

The two controls are **depth** and **subject**, and a **hard cap** stops anything past a reviewed size.

```toml
[crawl]
depth = 2
subjects = ["14N", "14D", "14C"]   # MSC families; the arXiv categories they admit are derived
cap = 1000                          # works downloaded; raising it is a deliberate edit here
```

- **Subjects are MSC families** (`14N`, not `14N35`), and must be settled before a crawl runs. The default is the families of the depth-1 works' MSC codes, printed in the plan for the author to edit.
- **Depth-1 works always pass the filter**: the author cited them.
- **The arXiv fallback.** A work with no MSC codes (a preprint zbMATH has not indexed) is admitted by its arXiv category. Loom keeps a family-level table from MSC areas to arXiv math categories (`14` → `math.AG`, `55` → `math.AT`, `18` → `math.CT`, `81T` → `math-ph`, `hep-th`, …) and the plan prints the categories the chosen families admit. No published mapping was found online on 2026-09-17; the table can be checked against arXiv's own records, which carry the MSC codes authors give beside their categories. A work with neither MSC codes nor an arXiv category is excluded, and listed as excluded.
- **The cap counts downloads only**, and is overridden only in `config.toml`, never by a flag.
- **The order under the cap**: shallowest depth first, and within a depth the works cited by the most works already found. A paper that three of the corpus's works cite — `demos/relloc`, Aranha–Khan–Latyntsev–Park–Ravi and Romagny 2022 all cite Romagny's *Group actions on stacks and applications* — is reached before one cited once in passing.
- `[crawl] depth` is namespaced so it cannot be confused with the graph view's "depth around selection".

## Two phases: plan, then fetch

**Plan** walks the reference graph through metadata alone, applies depth and subjects, and reports before anything is downloaded (the numbers are illustrative):

```
depth 2 · subjects 14N 14D 14C (arXiv: math.AG) · cap 1000
  612 works: 431 downloadable (arXiv 402, open copies 29), 181 metadata only, 38 excluded by subject
  references not yet known for 57 works (preprints with no reference list in either index)
  ~1.4 GB · ~40 min at arXiv's pace · 1,900 lookups
  followed by lookup: 213 strong matches; 24 possible matches listed, not followed
```

**Fetch** runs only when the plan is under the cap, and records as it goes, so an interrupted crawl resumes.

The count is exact wherever an index lists a work's references. It is a floor where none does, because a preprint's references are known only once its source is downloaded and its `\bibitem`s read; the plan says how many works are in that state rather than pretending otherwise.

## Where reference lists come from

Measured on 2026-09-17, the two indexes complement each other:

| work | zbMATH Open | OpenAlex |
|---|---|---|
| Graber–Pandharipande, *Localization of virtual classes* (1999) | MSC 14N35, 14L30, 14N10; **no references** | **19 references**; no arXiv link |
| Aranha et al., *Virtual localization revisited* (published 2025) | MSC 14N35, 14A20, 14C17; **46 references, 30 resolved** | preprint record: **0 references** |
| Romagny, *Algebraicity and smoothness of fixed point stacks* (arXiv 2022) | listed, no MSC, no references | — |

So a work's references are the union of zbMATH's resolved list, OpenAlex's `referenced_works`, and, once downloaded, the `\bibitem`s of its own source, which is where a preprint's references usually are. MSC codes come from zbMATH only; OpenAlex's topics are not MSC and put the Aranha preprint under "Mathematical Physics", so they cannot drive the filter.

## Identification

Every work is identified before it is followed. Depth-1 works are identified by their bibliography entries where those state an identifier, and by lookup otherwise. Deeper works exist only as formatted text in someone's bibliography, so lookup is the only way they are ever identified — the core of `loom refs resolve` takes a free-text `Query` for this reason.

- A **strong** match (loom's own score of 0.9 or more, from title, first author and year) is followed at every depth, and the plan lists it as found by lookup, which is the author's chance to object before anything downloads.
- A **possible** match (0.75–0.9) is listed and not followed.
- An unmatched entry stays in the graph as text and is not followed.

The author judged confusion in lookup unlikely. The one consequence to know: when the crawl follows a lookup match for one of the author's own entries, the download is filed under the matched identifier, while the rest of loom still files that citekey under its synthetic `work:<hash>` until the entry states the identifier. The work's record says which citekey it was reached from, so the two can be joined.

## Where it is recorded

Per work, beside its downloads: `refs/<scheme>/<id>/work.json`, holding the work's metadata, its MSC codes and arXiv category, its resolved references, every identifier known for it, and how the crawl reached it (depth, from which works, by declaration or lookup). A metadata-only work gets a directory holding just that file. `refs/crawl/plan.json` holds the last plan and the parameters it ran with.

`<scheme>` is the kind of identifier the directory is named by — `doi`, `arxiv`, `mr`, `zbl`, or `work` for a work known by none — so `refs/doi/10.1353_ajm.1998.0020/`, `refs/arxiv/2207.01652/`, `refs/zbl/0911.14015/`. A work known by several identifiers is filed under the first in loom's resolution order (DOI, arXiv, MR, Zbl) and lists the others in its record.

Everything under `refs/` stays untracked. What makes a library reproducible is `[crawl]` in the tracked `config.toml`: a collaborator re-runs the plan, which needs no downloads, and fetches. A tracked export of the graph can be written later if sharing it through version control turns out to matter; it would carry zbMATH's CC-BY-SA data, and a published repository would take on its share-alike terms.

## Download options to assess

| option | what it gives | terms, as of 2026-09-17 |
|---|---|---|
| arXiv per-paper e-print | sources, the default | spaced requests; bulk use belongs elsewhere |
| arXiv bulk data on S3 | sources in bulk | requester pays |
| OpenAlex locations | `best_oa_location.pdf_url`: legal open copies of published papers | API key required for all requests; $1 of free use per day per key ($0.10 without one); a single work by id or DOI is free, list and filter $0.0001, search $0.001, a PDF through its content endpoint $0.01 (about 100 a day free); data CC0 |
| OpenAlex snapshot | the whole graph offline, ~750 GB as JSON Lines | free, quarterly, public S3 bucket `openalex` |
| Unpaywall | open copies of published papers by DOI | free with a contact address |
| Numdam, EuDML, Project Euclid | open archives of mathematics journals | per archive |

OpenAlex is the strongest candidate beside arXiv: its open-access locations are what reach a published paper with no preprint, and single lookups by DOI cost nothing. Unkeyed requests succeeded on 2026-09-17 under a $0.10 daily limit, but its announcement says a key is required, so a crawl should expect `[crawl] openalex_key` (or an environment variable, to keep the key out of a tracked file).

## Scale

Citation balls grow roughly 30 → 400 → 3,000 → 15,000 → 50–100,000 by depth 5; the subject filter is what keeps a deep crawl inside a subfield. A 50,000-work corpus is on the order of 150 GB of arXiv sources, which is where a byte cache outside the quilt ([[WQ-06]]) and the bulk options above take over. The crawl gives works and citations, never digests: extraction is mechanical and can follow, and verifying locators against published PDFs is not.

## Blast radius

A new subsystem in `loom/src/loom/refs/` (the plan, the fetchers, the MSC-to-arXiv table), `config.toml`'s `[crawl]` table, `refs/` layout (`work.json`, `refs/crawl/`), the network consent model (Chapter 4 §4.8), Chapter 8, and the terms of arXiv, zbMATH Open and OpenAlex.

## Related

Plan 0.7 (`loom refs resolve`, whose `Query` the crawl reuses); [[WQ-03]], deferred until a library exists; [[WQ-06]]; WQ-23 question 4, which binds only the author's own entries.

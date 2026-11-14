# The library: import, keys, matching, states, scale, Zotero

Investigator's raw report for the v0.1 study. Checkout: `v0.1-study` at `71621877`. Everything below was checked against the code or done on copies: `quant` (copied from the author's quilt), `showcase` (from `demos/showcase`), a showcase copy with 1,000 synthetic entries, and relloc's bibliography read in place. Scratch: `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/library` (abbreviated `$S` below; screenshots in `$S/shots/`, scripts in `$S/scripts/`). Online lookups used only Perelman's two Ricci-flow papers (arXiv math/0211159, math/0303109) and Hamilton 1982, on the showcase copy.

## Verdict in five lines

- Yesterday's wrong match is explained and reproduced: the Cox–Ross–Rubinstein PDF (J. Financial Economics, 1979) was matched to the work `Of`, which is Glosten–Milgrom (same journal, 1985), because `Of`'s entry had been made with the title "of Financial" (a fragment of the journal masthead) and no author, and loom's "title alone" rule calls any page showing that line a strong match (LIB-1).
- A second false-match route is reproduced: any arXiv id or DOI printed on a PDF's first two pages counts as the PDF's own identifier, so a paper that cites Perelman's arXiv id in its abstract is "Perelman's paper" (LIB-2).
- After a match, the default button files the PDF under the existing work; the CLI files it without asking; the per-work upload files on drop even when the PDF shows it is another work's; and no screen can take a wrongly filed PDF off a cited work (LIB-3, LIB-4, LIB-5). This is the one place in the library where loom can damage the person's records.
- Dropping a PDF can end in 7 different dialog states in the general dialog and 2 more in the per-work dialog, behind 5 entry points (LIB-10). Keys come from three generators and read `Of`, `Ric`, `Htt`, `Dep`, `Wor` (LIB-7).
- What to build: one intake flow with one question, a key scheme matching Better BibTeX's default, a dedicated Library page, an agent `library suggest` that the person accepts in one click, and, as the cheap Zotero step, reading the `file` field a Better BibTeX export already carries (sections 6–9).

## 1. Every way in

| Route | What the person does | What loom does | What it asks | Where it shows |
|---|---|---|---|---|
| Column shelf `+` | clicks `+` beside "Library" (`arras/src/lib/shell/Column.svelte:276`) | opens the Add a work dialog (`arras/src/lib/components/AddWork.svelte`) | see section 2 | dialog, then work Info |
| Review › Library "+ Add a work" | same dialog (`arras/src/routes/review/library/+page.svelte:187`) | same | same | same |
| Drop or choose a PDF in the dialog | drops on the dashed zone only; first file only (`AddWork.svelte:262-269`) | `library-upload`: base64 body, kept in `.loom/build/uploads/<sha>/`, identified (`loom/src/loom/render/api.py:223-240`); then `library-file`: `file_under` an existing work or `file_new` (`api.py:241-269`, `loom/src/loom/refs/add.py:250-409`) | match / metadata form / "may be this work" | Info of the work, with a run reading pages |
| Paste DOI, arXiv id, zbMATH, BibTeX | types in the dialog's textarea | `library-recognise` as you type, `library-lookup` on "Look up", `library-add` on Add (`api.py:174-222`) | network for the lookup (`AddWork.svelte:112-125`), network again for fetching (`:128-139`, three buttons) | Info of the new work |
| "Upload a PDF of K" | ledger row ⋯ (`arras/src/lib/review/LibraryRow.svelte:180`) or Info status (`arras/src/lib/components/WorkStatus.svelte:53`) | files the PDF under K at once, "on the person's word" (`AddWork.svelte:186`, `refs/add.py:348-409`) | nothing; a notice afterwards if the PDF shows it is another work | stays where opened |
| Fetch it / Digest / Fetch and digest everything | buttons on Info and the ledger (`WorkStatus.svelte:54,61`; `review/library/+page.svelte:188`) | `library-update` job: gather, look up, fetch, extract, map (`api.py:120-154`) | network, once per act where the quilt is offline | job card on Info |
| CLI `loom library add FILE...` | (types a command) | files each PDF under a strong match **without asking**, else makes a work of its own; folders recurse (`loom/src/loom/cli/library/add.py:69-232`, silent filing at `:136-141`) | nothing | report in the terminal |
| CLI `loom library update` | (types) or an agent runs it | gathers every entry of every `.bib` a document names, plus stored PDFs no entry names (`refs/scan.py:375`, `adopt_orphans` `:637-724`) | none | entries keep the person's own keys |
| CLI `loom library import PATH` | (types) | copies a digest from another quilt | none | — |
| Citations in a draft | writes `\cite{k}` with `k` in a `.bib` the draft names | gathered on the next run (`docs/specs/digests.md` §10) | none | the work appears; uncited entries are "cited nowhere, so not followed" (`cli/library/state.py:220-221`) |
| An agent | cannot add: `library add` is not an agent command (`loom/src/loom/ai/layout.py:32`), the CLI refuses under an agent marker (`cli/library/add.py:102`), `library-add/-upload/-file` refuse a declared agent (`api.py:188-191`) | may run `library update` (network only by config), may `library-lookup` without network, and is told to name a missing work in a Suggestion annotation (showcase `.loom/annotation-types.toml`, type `suggestion`) | — | an annotation in prose; the person re-types it into Add a work |

Five entry points reach a dialog, two of which are the same component in two modes; the CLI and the HTTP paths are two orchestrations over the same primitives (`cli/library/add.py:69` vs `api.py:157`), and they differ: the CLI files under a match silently, the viewer asks.

## 2. The tree after dropping a PDF

Done in a served showcase copy (`loom serve --port 48051 --no-compile`, headless Chromium, `$S/scripts/drops.cjs`). PDFs used: Perelman's two arXiv papers (born digital), the same file twice, a document-less entry `perelman_EntropyFormulaRicci2002` added to the copy's bibliography with the arXiv id (a paper "already in the library under another key"), a 3-page rasterised scan with no text layer, a 260 MB file built in the page and dropped as a real drop event, a seminar schedule (non-paper), a text file, two invented "journal masthead" papers, a note that cites Perelman's arXiv id, and a set of lecture notes titled like an existing work.

```
Drop a PDF  (only on the dialog's dashed zone; only the first file)
│
├─ > 256 MB (checked in the browser) ───────────── E1  error naming `loom library add FILE` on the command line          s10
├─ "Reading X…" ── POST library-upload (whole file as base64 JSON)
│   ├─ not %PDF- ───────────────────────────────── E2  "notes.txt is not a PDF"                                           s9
│   ├─ same bytes already held ─────────────────── D1  "This PDF is already in the library, as T (K)."  [Cancel] only     s2
│   ├─ strong match to an existing entry ───────── D2  "This is T (K), which the library has. Add files this PDF under it."
│   │      (identifier on p.1–2; whole title +        [It is a different work]  [Cancel]  [Add = file under K]           s3, s4*, s6*
│   │       first author leads byline; title alone
│   │       for an author-less entry; Zotero name)
│   │      ├─ Add ─► file_under ─► closes ─► Info of K (or N)                                                             s3-filed
│   │      └─ It is a different work ─► D3
│   ├─ nothing strong, nothing alike ───────────── D3  Metadata: Title / Author / Year (pre-filled, editable)  [Add]       s1, s5, s7, s8
│   └─ a tie, or an entry with the same title ──── D4  D3 + one line per candidate: "The library has T (K), which may be
│                                                        this work. [File it there instead]"                             s14
├─ Add (D3/D4) ─► file_new ─► dialog closes ─► work Info + run card ("Read the text"; scans: "It has no text to read")   s1-, s5-, s7-, s8-added
└─ N   notice + [Done]: "X: already in the library as K." | "Filed under K, on your word, though …" | "It has no page text (…)"

"Upload a PDF of K"  (ledger ⋯, Info status)
└─ drop ─► filed under K at once ─► P1 dialog closes   |   P2 notice "Filed under K, on your word, though it is J's: …"   s11
   (* = a false match)
```

Count: seven distinct states of the general dialog after a drop (E1, E2, D1, D2, D3, D4, N, with N carrying three different texts), two more in the per-work dialog (P1, P2), and the Info landing with a run card in two forms. The footer also changes under the person: "Fetch and digest it now" before a drop, "Look it up and digest it now" after one only when the network is on, nothing otherwise (`AddWork.svelte:296-298`). The paste path adds its own: kind chip, "Look up", two network questions, a found card, three not-found states, and "no service" notes for ISBN and MR numbers (`AddWork.svelte:233-252`). The author's requirement is one.

Screenshots (all in `$S/shots/`): `s1-born-digital-dropped.png`, `s1-born-digital-added.png`, `s2-same-bytes-again.png`, `s3-cited-entry-other-key.png`, `s3-filed-under-entry.png`, `s4-cites-an-arxiv-id.png`, `s4-said-different.png`, `s5-masthead-first.png`, `s5-masthead-first-added.png`, `s6-masthead-second.png`, `s7-scanned.png`, `s7-scanned-added.png`, `s8-non-paper.png`, `s8-non-paper-added.png`, `s9-not-a-pdf.png`, `s10-too-large.png`, `s11-upload-for-work-open.png`, `s11-upload-for-work-wrong-pdf.png`, `s12-paste-recognised.png`, `s12-paste-network-question.png`, `s13-paste-bibtex.png`, `s13-add-network-question.png`, `s14-same-title-maybe.png`, `showcase-add-empty.png`, `showcase-shelf.png`, `showcase-review-library.png`, `big-shelf.png`, `big-review-library.png`.

What each kind of PDF produced:

| PDF | Result | Key |
|---|---|---|
| Perelman, Ricci flow with surgery (arXiv, born digital), network off (the default, `loom/src/loom/cli/quilt.py:32`) | D3 with title only; no author, no year, though the PDF prints its arXiv id | `Ric` |
| same, with the network on (`$S/scripts/online.py`) | arXiv lookup fills author and year | `Per03` |
| same bytes again | D1 | — |
| Perelman, entropy formula, library holding a document-less entry for it under a Better BibTeX key | D2, correct; Add filed it under that entry | `perelman_EntropyFormulaRicci2002` |
| a note citing `arXiv:math/0211159` in its abstract | D2, **false**: "This is The entropy formula for the {Ricci} flow…" | — |
| first masthead paper ("Journal / of Imaginary Studies / … / TITLE / AUTHOR") | D3 titled "of Imaginary Studies" | `Of` |
| second masthead paper, different title and author | D2, **false**: "This is of Imaginary Studies (Of)" | — |
| scan, no text layer (ImageMagick-made) | D3 titled "scanned-surgery", author "https://imagemagick.org"; Info then says "It has no text to read" beside "✓ Text filed" | `Htt` |
| seminar schedule | D3 titled "Department of Mathematics"; accepted as a work | `Dep` |
| 260 MB | E1 telling the person to use the CLI | — |
| lecture notes titled like `Arden24` | D4 offering both `Arden24` and its own version `Arden24A` as separate targets | — |
| per-work upload of the seminar schedule onto `Cortez07` (cited, no paper) | filed at once; the same bytes now sit under `Dep` and under `Cortez07`; ledger record rewritten to `Cortez07` | — |

## 3. States

What the code computes and what the screens call it:

| Concept | CLI (`loom library`, `cli/library/state.py`) | Ledger (Review › Library, `arras/src/lib/library.ts`) | Work Info (`WorkStatus.svelte`) | Shelf |
|---|---|---|---|---|
| has its PDF | `pdf yes` | PAPER "filed" | "✓ Text filed" | nothing |
| has LaTeX source | `src` | DIGEST "(source)" | "Source LaTeX" / "none: results come from the pages" (said even for an arXiv paper whose source a run could fetch, `s1-born-digital-added.png`) | nothing |
| page text read | `pages 35 secs 9` | nothing | a run card while the page is open; nothing after | nothing |
| scanned, no text | "not read yet" | nothing (only the last run's report knows, `library.ts:229-230`, and `problemsOf` ignores it, `:248-266`); manifest has no field for it | "It has no text to read" while the run card stands | nothing |
| digested | "digested" / "digested from another version" / "digested through a version" | DIGEST count | "Digest n results · k verified" | nothing |
| results | `extracted`, `verified`, `waiting` | VERIFIED, "k to verify" | count | nothing |
| set aside | "set aside" | "declared unreadable" | — | "unreadable" |
| cited | "cited by N keys"; uncited works are one line, "cited nowhere, so not followed" | CITED / "not cited" | "Not cited yet. Cite it as \cite{K}" | nothing |
| what is expected | "needs you" (a `cause`), "waits for review", "in progress", "done", "needs an agent" (`state.py:310-327`) | "needs you" = open annotations or problems (`library.ts:281`) | buttons: Upload a PDF, Fetch it, Digest, Ask an agent | "N need you" link (`Column.svelte:290`) |
| suggested by an agent | does not exist | does not exist | does not exist | does not exist |
| added how | — | "added by hand" | "added by hand" | — |

Can a person tell? Partly. The ledger answers "is the PDF here, how much has been read off it", but "can I search it", "is this a scan", "what should I do next" and "who brought it" have no answer on screen. "Text" means the PDF on Info and the page text in the run card; "needs you" has three definitions (CLI cause, ledger filter, column link). On the quant copy `loom library` reports "0 works cited, 0 digested; 0 need you … cited nowhere, so not followed: 18 entries": a learner whose lessons link to books by `cited:` links has a library loom treats as idle (findings item 5, still true).

## 4. Reference keys

Generators today:

- `key_for` (`loom/src/loom/refs/lookup.py:68-80`): first three letters of the first author's surname plus a two-digit year (`Man08`); with no author, the title's first word that is not a/an/the (so "of"); with nothing, "Work"; a taken key gets `A`, `B`, … (`refs/scan.py:561-569`). Used by drop, paste and CLI add.
- `_derived_key` (`refs/scan.py:626-630`): the dropped file's name with non-alphanumerics removed, cut at 24 characters (`Halloway2026Notesonbalan`), or `pdf<sha8>`. Used for stored PDFs no entry names.
- Sibling entries for a second document of a work: `<key>A` (`refs/scan.py:616`), the same suffix as a collision.
- Entries gathered from the person's `.bib`: the person's own key, unchanged.

Thirty real keys:

| Key | Title (as stored) | Origin | Judgement |
|---|---|---|---|
| `Wor` | Stochastic Calculus for Finance II | quant, early failed add: no author, no title then, so "Work" | meaningless, actively misleading in search results (`library search` prints `Wor` for Shreve) |
| `WorAA` | Modeling Volatility in Prediction Markets | quant, a copy of a deleted `WorA` | meaningless, double suffix |
| `Hul22` | Options, futures, and other derivatives | quant, Zotero file name | readable but cryptic |
| `Han21` | Econometrics | quant, PDF info | cryptic |
| `Pra18` | Advances in Financial Machine Learning-Wiley (2018) | quant, file name | surname wrong ("de Prado" → Pra), title polluted |
| `Cas` | Statistical Inference | quant, PDF info, no year | cryptic, no year |
| `Sta` | Statistics For Quants : Revision Notes | quant, title word | meaningless |
| `Bec21` | An Introduction to Gaussian Process Models | quant, Zotero file name | cryptic |
| `Kee` | Prediction Market Derivatives Arbitrage, … | quant, Zotero file name without year | cryptic |
| `Opt` | Option market making under inventory risk | quant, title word (DOI printed, network off) | meaningless |
| `Alg` | Algorithmic market making: the case of equity derivatives∗ | quant, title word (arXiv printed, network off) | meaningless, stray `∗` in title |
| `Dal` | Toward Black Scholes for Prediction Markets… | quant, "Shaw Dalen" read as one person | wrong |
| `Hig` | High-frequency trading in a limit order book | quant, title word | meaningless |
| `Of` | of Financial | quant, journal masthead fragment | wrong title and key; caused LIB-1 |
| `Wol04` | Prediction Markets | quant, PDF info | fine for alpha style |
| `Har81` | Martingales and stochastic integrals… | quant, Zotero file name | fine for alpha style |
| `Bla73` | The Pricing of Options and Corporate Liabilities | quant, Zotero file name | fine for alpha style (amsalpha would say BS73) |
| `Cox79` | Option pricing: A simplified approach | quant; author typed "Cox, Ross, Rubinstein", which BibTeX reads as one person | key fine, entry wrong (LIB-12) |
| `Ric` | Ricci flow with surgery on three-manifolds | showcase drop, network off | meaningless |
| `Htt` | scanned-surgery | showcase drop of a scan | absurd (author "https://imagemagick.org") |
| `Dep` | Department of Mathematics | showcase drop of a non-paper | meaningless |
| `Halloway2026Notesonbalan` | Notes on balanced quivers | showcase, orphan adoption | truncated mid-word |
| `Arden24A` | Cycle spaces of finite quivers (v2) | showcase sibling | reads as a different 2024 Arden paper |
| `Cox11` | Toric varieties David A. Cox, John B. Little, Henry K. Schenck. | relloc, loom drop of a Zotero-named file | title polluted; the person's own `.bib` would key this work differently, so citing it later makes a second entry |
| `manolache_VirtualPullbacks2012` | — | relloc, the author's Better BibTeX export | the scheme he already uses |
| `olsson_LogarithmicGeometryAlgebraic2003` | Logarithmic Geometry and Algebraic Stacks | relloc, BBT | good |
| `abramovich-chen-gross-etal_DecompositionDegenerateGromov2020` | Decomposition of Degenerate Gromov–Witten Invariants | relloc, BBT | good, long |
| `gross-siebert_LogarithmicGromovWittenInvariants` | Logarithmic Gromov-Witten Invariants | relloc, BBT, no year | acceptable |
| `shun-ichi_FractionalIntersectionBivariant1992` | Fractional Intersection and Bivariant Theory | relloc, BBT, Zotero mis-parsed the name | Zotero's fault, but shows a key is only as good as the metadata |
| `stacks-project`, `SGA3-2` | Stacks Project; SGA 3 II | relloc, hand-made | good |

Proposed scheme (one generator, `refs/lookup.py:key_for`, used by every route):

- The person's key wins: a key from their own `.bib`, from a pasted BibTeX entry, or from Zotero (when integrated) is used as is.
- Otherwise Better BibTeX's default formula, `auth.lower + shorttitle(3,3) + year` (https://retorque.re/zotero-better-bibtex/citing/): first author's surname lowercased and ASCII-folded, the first three significant title words in TitleCase, the year: `coxOptionPricingSimplified1979`, `perelmanRicciFlowSurgery2003`, `shreveStochasticCalculusFinance` (no year known: omitted, never guessed), `casellaStatisticalInference`. A part that is unknown is left out; a work with no usable title or author is `untitled-<sha8>`, never `Work`/`Wor`.
- Collisions: suffix `a`, `b`, `c` (BBT's rule, same page). A second document of one work is not a collision and must not share the suffix: sibling keys become `<key>-v2`, `-v3` (change `_sibling`, `refs/scan.py:616`).
- The key is made once metadata is as good as it will get on that act (after a lookup where the network is allowed); while the work is new (no citation, digest, annotation), editing its details re-derives the key.

What renaming an existing key touches: the entry in `.loom/digests/bibliography.bib` and any `loom-copy-of = {KEY}` pointing at it; the digest files named by key (`<key>.tex`, `.results.json`, `.proposals.jsonl`, `.proposed.tex`) and the result labels inside, whose prefix is derived from the key (relloc: `\label{manolacheVirtualPullbacks2012-setup}`), hence every `\uses{…}` and `\cite[…]{key}` in the person's drafts; `unreadable.json` events keyed by citekey; tab titles; past transcripts (leave). Not touched: `cited:` links and annotations on a work, which store the work id (`cited:work:6d63c808`, annotation target `work:abd8ef6c` in quant; `loom/src/loom/refs/links.py:231`, `cli/review.py:593-607`). So: rename freely only works with no digest and no citation, which is every hand-added work in quant; never rewrite a person's drafts. The real hazard runs the other way (LIB-9): correcting a hand-added work's title or year changes its id and detaches its links and annotations.

## 5. The wrong match

The code. `identify` (`refs/add.py:163-209`) returns the held work for identical bytes, else `identify_document` (`refs/ingest.py:403-443`), whose `_strong` (`:367-400`) calls an entry a strong match when (a) any DOI or arXiv id read anywhere in the first two pages' text equals the entry's (`:373-380`, ids from `identifiers_in`, `:132-136`), or (b) the entry's whole title is set over one to three lines of page one and its first author leads the byline, or (c) **the entry names no author and its title, of more than one word, is set as lines of page one** (`_title_alone`, `:287-289`, used at `:387-388`), or (d) a reference-manager file name states title and first author. One best match becomes `seen.best`, and the dialog offers to file under it with Add as the primary button (`AddWork.svelte:279-283`, `151`); the CLI files under it with no question (`cli/library/add.py:136-141`).

The incident (quant, 2026-11-12, local evening). No record names it: the copy ledger and bibliography hold only the end state, which suggests the author caught it and pressed "It is a different work". Timeline from `.loom/build/uploads` mtimes and `copied.json`: Black–Scholes uploaded 22:54:26 and filed 22:54:27; Cox et al. uploaded 22:55:14 and filed 22:56:05, 51 seconds later, with authors typed by hand. Reproduced on the copy by calling `identify` with `Cox79` left out of the bibliography (`$S/scripts/ident.py`): `best: "Of"`, `how: "its title is the entry's, which names no author"`. Why: the Cox PDF's page one, as pdftotext reads it, begins `Journal` / `of Financial` / `Economics` / `OPTION` / `7 (1979) 229-263.` …; the earlier Glosten–Milgrom PDF (`1-s2.0-0304405X85900443-main.pdf`, the same journal) begins with the same three masthead lines. When it was added on 2026-11-11, `own_entry` took its title from "the first line on page one that could be a title" (`refs/add.py:77-89`), and `title_lines` skips "Journal" only because it is under 10 characters (`refs/ingest.py:102`), so the title became "of Financial", with no author. Every later paper from that journal then matches `Of` by rule (c). Two defects compound: a bad entry made from a masthead, and a rule that trusts a two-word author-less title.

Reproduced in the viewer on the showcase copy with invented PDFs (`s5`, `s6`): the first masthead paper became `Of` "of Imaginary Studies", and the second, a different paper by a different author, was announced as "This is of Imaginary Studies (Of)". Rule (a) is reproduced by `s4`: a note whose abstract mentions `arXiv:math/0211159` is "The entropy formula for the {Ricci} flow…". The code knows (a) is unsafe in another place: `_offer` drops a looked-up record unless the PDF carries its title, "an identifier on the first pages may be one the document cites" (`refs/add.py:139`), but `_strong` has no such guard. Errata, comments and replies print the original's DOI on page one and will match the original the same way.

The fix, consistent with one predictable interface:

1. Loom never files a document under an existing work without the person saying "same work" in the same place, beside both titles and bylines. A strong match only chooses the question; the CLI asks for `--for` instead of filing.
2. Rule (c) goes: an entry with no author is matched only by identifier or by an exact file hash. Rule (a) requires the identifier to be the document's own: on arXiv's margin stamp line, or a DOI in page one's header or footer and the entry's title also on page one (`carries_title`, already in `refs/fetch.py`).
3. `own_entry` never takes a title from a masthead: skip lines naming a journal (`Journal`, `of …`, `Vol.`, `(19xx)`, publisher names), prefer the largest-font line when the text layer offers it, and look the printed identifier up whenever the network is allowed.
4. An undo that takes a filed document off a work (section 9).

## 6. References an agent suggests

Smallest mechanism, built on what exists:

- Record: `.loom/digests/suggested.jsonl`, append-only events (the pattern of `refs/proposals.py`): `suggested` with an id (`sg-YYYY-MM-DD-NNNN`), who, session, when, the reference (DOI, arXiv id, zbMATH, BibTeX, or title + authors + year), `why` (required, one or two sentences), and optionally `for` (a key, document or result it bears on); then `added` (with the citekey) or `dismissed` (with who).
- Agent command: `loom library suggest REF --why TEXT [--for TARGET] [--title T --authors A --year Y]`, offline only. It runs `recognise` (`refs/identity.py:241`) and `duplicates` (`refs/lookup.py:83-103`) and refuses a work already in the library, naming its key. Adding `"library suggest"` to `AGENT_COMMANDS` and to `ACTS` as `write` (`ai/layout.py:21-58`) makes the MCP tool `loom_library_suggest` with no further code (`mcp/tools.py:97-101`). One call per work: twelve calls are cheap for an agent and keep each `why` attached.
- Manifest: `suggested_works` (open suggestions only), from `render/build.py`.
- Endpoint: `library-take {ids: [...], fetch: bool}`, the author's: for each, `look_up` with the network allowed by that click, `add_entry` (`refs/added.py:73`) under the key scheme of section 4, one `jobs.submit` for all of them (as `api.py:196-202`), and an `added` event; `library-dismiss {ids}`.
- Viewer: the Library page's first filter, "Suggested (12)": a row per suggestion with title, authors, year, identifier, the agent's why, who suggested it and when; [Add] and [Dismiss] per row, [Add all] at the top. The column shows a badge. When the quilt is offline, the button says so: "Add 12 and fetch them (uses the network)" or "Add without fetching".
- Feedback: `loom since` reports added and dismissed suggestions, so the agent knows what the person kept.
- Change the Suggestion type's instruction ("A work worth citing that the bibliography lacks is a suggestion too: name the work") to point at the command, and add one line to the orientation.

What exists: `recognise`, `look_up`, `duplicates`, `add_entry`, the job runner, the proposals record pattern, the agent-command-to-MCP derivation, `loom since`. What is missing: the record, the command and its tool, the manifest field, the two endpoints, the viewer section, the `since` event. Effort: two to three days. This answers findings item 21 (an agent cannot file even at the person's request) without giving agents the act of adding, and is preferable to INV-9's "admit `library add` for agents", since a person still decides what enters their library. An agent that has downloaded a PDF may name it with `--file PATH` (inside its session folder), which the person's Add files through the intake of section 9.

## 7. A large library

Today the library has three faces: the column shelf (folded by default, `Column.svelte:77`; one line per work, "authors, title", no year, sorted by author, a filter box, and "Manage the library", `:270-290`); Review › Library, a working table titled "Library" with search, seven filters (all, needs you, no paper, no overview, not cited, proposed, verified), columns PAPER, DIGEST, VERIFIED, OVERVIEW, CITED, a ⋯ menu per row and bulk acts (`routes/review/library/+page.svelte`, `LibraryRow.svelte`); and each work's Info. So a dedicated page exists, but it is a Review section reached by "Manage the library".

Measured (headless Chromium, `$S/scripts/pages.cjs`) on the showcase (10 works) and the same with 1,000 synthetic entries added: manifest 0.22 MB → 1.0 MB; first load 0.9 s → 1.3 s; shelf opens in 35 ms → 123 ms with 1,006 rows; the ledger draws 1,005 rows in 1.2 s (`big-review-library.png`). Nothing breaks at 200 or 1,000 in speed. What breaks is finding things: the shelf becomes a 1,000-line list; the ledger has a fixed order (needs-you first, then key, so `Alg`, `Bla73`, `Cas` sort by meaningless keys), no sort control, no year or venue or date-added column; "not cited" is most of a reading library and is filtered as a deficiency; there is no way for the person to search inside papers (agent-only `library search`, INV-15), no record of what the person has opened, and nothing says which works an agent proposed.

Library page (a top-level route `/library`, opened from the column's "Library" heading):

- Row: title (TeX rendered, braces gone), first authors' surnames with "et al.", year, venue or arXiv id chip, key (small, copyable), one state word (Suggested · No PDF · Reading pages · Ready · Ready, scanned · Digested n), my marks (notes, open comments, results to verify), cited in (draft names), added (date, and "by you" or "suggested by an agent").
- Sort: date added (default, newest first), year, first author, title, last opened.
- Filters: Suggested; Needs a PDF; Scanned (no text); Has results; Has my notes; Cited in ‹draft›; Opened / never opened; Added this week.
- Search: one box over key, title, authors, year, and an "inside papers" toggle that runs the page-text and results search the agent already has (`cli/library/read.py`, `refs/search.py`) through a new read endpoint.
- Grouping: none by default; "group by draft citing it" as an option.
- Organising structure: none new for v0.1. Filters on facts loom already knows, plus search, cover a reading library of a thousand; tags or collections are a second taxonomy to keep up. If Zotero integration lands, show the person's Zotero collections read-only as a filter rather than inventing loom's own.
- Bulk: select, then Add (suggested), Fetch and digest, Delete.
- The column keeps: a "Library" link with its count and a badge for what arrives or waits (suggested, questions from section 9), and the five most recently opened works for quick return. The full list leaves the column; Review loses its Library section (Review = changed mathematics + AI-proposed edits, as INV-7 recommends).
- "Last opened" needs a small per-person record (the existing `.loom/looked/` records file snapshots for `since`, not works opened).

## 8. Zotero, as a nice-to-have

Current documentation: Zotero's desktop app serves a local copy of its Web API at `http://localhost:23119/api/` once the person ticks "Allow other applications on this computer to communicate with Zotero" in Settings › Advanced; reads need no key, `users/0` is the local library, `/items/KEY/file/view/url` returns the attachment's `file://` path as text, and writes need Zotero 10 and a key the person approves (https://www.zotero.org/support/dev/web_api/v3/local_api). Better BibTeX's default key formula is `auth.lower + shorttitle(3,3) + year`, keys are stable and collisions take a letter (https://retorque.re/zotero-better-bibtex/citing/); its "Keep updated" export rewrites a `.bib` on every change to a library or collection (https://retorque.re/zotero-better-bibtex/exporting/auto/). Dragging items out of Zotero gives Quick Copy output, a formatted bibliography by default and BibTeX when Quick Copy is set to it (https://www.zotero.org/support/creating_bibliographies); dragging an attachment row copies the file, with reported bugs (https://forums.zotero.org/discussion/comment/424392/). Whether a browser page receives the PDF from such a drag on current macOS Zotero is untested here and must be tried by hand. The author's relloc `refs.bib` is a Better BibLaTeX export whose entries carry `file = {…}` with absolute paths into Zotero's storage (13 of 36 entries); loom reads no `file` field today (no match in `loom/src/loom/refs/`).

| Way | Person does once | Each import then costs | Effort | What breaks |
|---|---|---|---|---|
| 1. Read the `file` field of a Better BibTeX export loom already gathers, and let the person name one more export as "my library" in Settings | nothing for cited works (already exporting); one path in Settings for the rest | nothing: the next run copies each named PDF into the store, paired by the person's own Zotero record | a day: a gather/fetch step in `refs/scan.py` / `refs/build.py`, the setting in `config_edit.py` and Settings › Library | paths on another machine; linked files outside storage; several files in one `file` field; the export must be kept up to date (BBT does) |
| 2. Drag from Zotero onto loom's window | nothing | drag the PDF attachment row (not the parent) | free once section 9's window drop accepts files and BibTeX text | untested in a browser; parent-item drags give text, so BibTeX Quick Copy helps |
| 3. Local API picker ("Add from Zotero") on the Library page | tick one Zotero setting | search, tick, Add: many at once, PDF copied from the path the API returns, Zotero's key kept | two to four days | Zotero must be running; the setting; older Zotero versions; item types without PDFs |
| 4. "Send to loom" Zotero plugin | install a plugin | right-click, Send | a week plus distribution and upkeep across Zotero versions | Zotero plugin API changes; pairing a token with `loom serve` |

Recommendation for v0.1: 1 and 2, both cheap, both on the person's existing workflow (no more "Show in Finder"). 3 is the better long-term experience and should follow v0.1. Must be true first: LIB-1 to LIB-5 (no wrong match; nothing filed without a yes; undo), section 4's rule that the person's key wins (so a Zotero item keeps its Better BibTeX key and citing it later makes no duplicate), section 9's window-wide multi-file drop, and section 7's page to see what arrived.

## 9. The one flow

Inputs, all feeding one intake: drop any number of files, or text (BibTeX entries, DOIs, arXiv ids, one per line) anywhere on the viewer window; "+ Add" on the Library page (a file picker and a paste box, nothing else); a person's Add on agent suggestions; `loom library add` (same function, prints the same states).

States of one item, shown as a row in an "Arriving" tray at the top of the Library page and as a small tray visible from anywhere while something is in progress or waiting:

1. Reading: file received (streamed, not base64 JSON), hashed, page one and printed identifier read. Held in `.loom/incoming/<sha>/`, not under `.loom/build/`.
2. Looking up: only where the quilt allows the network, which is asked once per quilt at its first add ("Look up papers' details online? arXiv, Crossref, zbMATH"), never per item.
3. Exactly one of:
   - **Added**: "Title — Authors, year · key" with [Open] [Undo]. Entry and PDF written at once.
   - **Already here**: same bytes; [Open]; nothing written.
   - **One question**, for any candidate at all (an identifier, a title, a same-title entry, a tie, or a per-work upload whose PDF shows another work): "Is this ‹existing title — authors, year›?" beside the PDF's own page-one title and byline, [Same work] [A different work]. Nothing is filed until answered; unanswered items wait in the tray and in the column badge.
   - **Can't add**: not a PDF, unreadable; [Dismiss].
4. After Added or Same work: "Reading pages 12/35", then **Ready** (searchable) or **Ready, scanned** (opens; no text to search or quote; persisted on the work, not only in the run's report).

Undo: on the tray row and on the work's Info, for as long as the work has no digest results or citations: a new work is deleted (`delete_work`, `refs/added.py:139`); a document filed under an existing work is taken off it (a new `unfile` operation; today nothing can, and `library-delete` refuses a cited work, reproduced: `{"code": "from-document"}`). The person's original file is never touched.

Details are not edited in the flow. The work's Info gets one "Edit details" (title, authors as a list, year, identifier); while the work is new, its key follows.

Deleted: `AddWork.svelte` (535 lines: the metadata form, the "This is … Add files this PDF under it" default, the "File it there instead" list, the per-work mode that files on drop, the 256 MB message naming the CLI, the network questions on add, the footer checkbox variants), `NetworkAsk` on add, the "Upload a PDF…" entries in `LibraryRow.svelte:180` and `WorkStatus.svelte:53` (they open the tray with the pairing proposed), endpoints `library-upload`, `library-file`, `library-add` (replaced by `library-take`, `library-answer`, `library-undo`), and the CLI's silent filing (`cli/library/add.py:136-141`). The two orchestrations (CLI and HTTP) become one module, `refs/intake.py`.

Textbook check: a scanned 600-page book with no DOI (quant's C&B) goes: Reading → (lookup skipped: no identifier; ISBN lookup is still absent) → Added "Statistical Inference — Casella, Berger" from the PDF information → Ready, scanned. Key `casellaStatisticalInference` (no year in the file; Edit details adds it and the key follows). Its stable identity must not depend on the title (LIB-9). An arXiv paper goes: Reading → Looking up (if allowed) → Added `perelmanRicciFlowSurgery2003` → Ready → Digest fetches its LaTeX source.

## 10. Bugs hit, with reproductions

- B1 (LIB-1) Title-alone false match. Showcase copy, viewer: drop `$S/pdfs/masthead-1985.pdf`, Add; drop `$S/pdfs/masthead-1979.pdf`: "This is of Imaginary Studies (Of)". Quant copy: `python -I $S/scripts/ident.py $S/quant "<Cox upload>" Cox79` gives `best: Of`.
- B2 (LIB-2) Cited arXiv id counts as the PDF's own. Library holding `perelman_EntropyFormulaRicci2002` (eprint math/0211159); drop `$S/pdfs/cites-perelman.pdf`: "This is The entropy formula…".
- B3 (LIB-4) Per-work upload files another work's PDF and double-stores it. Drop `seminar-schedule.pdf` via Add (becomes `Dep`), then Review › Library › `Cortez07` ⋯ › Upload a PDF… › drop the same file: "Filed under Cortez07, on your word, though it is Dep's"; `storage/file/08c8e11b…/paper.pdf` and `storage/work/52fa6386/paper.pdf` hold the same bytes; `copied.json` now names only `work/52fa6386`.
- B4 (LIB-5) No undo for B3: `POST /_api/library-delete {"citekey":"Cortez07"}` → `from-document`; the viewer greys "Delete" for cited works and offers no "remove this PDF".
- B5 (LIB-6) Scan from ImageMagick becomes author "https://imagemagick.org", key `Htt`: drop `$S/pdfs/scanned-surgery.pdf`. `_NO_AUTHOR` filters e-mail addresses but not URLs (`refs/add.py:51`).
- B6 (LIB-12) Author field taken verbatim: typing "Cox, Ross, Rubinstein" (quant `Cox79`) stores one BibTeX person; surnames and the synthetic id see only "Cox".
- B7 (LIB-15) Scan state lost: after the run card is dismissed or the server restarts, the ledger shows `Htt` "filed" with no problem; the manifest has no page-text field (`artifacts: {pdf, source}` only).
- B8 (LIB-19) Pasting two BibTeX entries recognises only the first (`recognise("@book{x,…}\n@book{y,…}")` → `x`); a list of arXiv ids is "not recognised".
- B9 (LIB-20) Raw braces: the dialog shows "The entropy formula for the {Ricci} flow" (`AddWork.svelte:206, 211` use the raw field; the ledger strips them).
- B10 (LIB-11) Only `files[0]` of a drop is used and the input has no `multiple` (`AddWork.svelte:265, 269`): dropping twelve PDFs adds one, silently.
- B11 (LIB-21) `loom library read Cox79` on the quant copy exits with "Error: Cox79 has no overview yet…" (`cli/library/read.py:227`); findings item 34, still true.
- B12 (LIB-14) `.loom/build/uploads/` is never emptied after filing (cleared only when a work is deleted, `refs/added.py:240`): 57 MB of duplicates in quant beside 119 MB of store.
- B13 `library-ignore` on a work holding a PDF succeeds over HTTP ("Cortez07 set aside: wrong pdf") and records a `forget` of the stored document's hash, though the viewer hides the act for filed works (`LibraryRow.svelte:183`); harmless but a second, undocumented way to set a document aside. Undone in the copy.
- Not reproduced, still true by reading: section labels on pages are often wrong (`library search` on quant labels Hull's "Risk-neutral valuation" page "[7.27 OIS rates are 3.4% for all maturities]"; findings items 24, 33). Fixed since the findings: JBIG2 scans now draw (`arras/src/lib/pdf/document.ts:46` passes `wasmUrl`, `arras/scripts/pdfjs-assets.mjs:21` copies `wasm`); scanned pages still have no text (`loom library read Cas 80` prints an empty page).

## Findings

| Id | Finding | Evidence | Weight | Rec |
|---|---|---|---|---|
| LIB-1 | An author-less entry whose title is any phrase on page one is a strong match ("title alone"); with a masthead-fragment title it captured a different paper from the same journal (yesterday's incident). | `refs/ingest.py:287-289, 387-388`; B1; quant timeline in section 5 | blocks | fix |
| LIB-2 | Any DOI or arXiv id on the first two pages counts as the PDF's own identifier, so a paper citing another is filed as it; errata and replies too. | `refs/ingest.py:132-136, 373-380`; B2; contrast `refs/add.py:139` | blocks | fix |
| LIB-3 | A strong match makes "file under it" the default (Add); the CLI files under it without asking. | `AddWork.svelte:151, 279-283`; `cli/library/add.py:136-141` | blocks | fix: never file without "same work" |
| LIB-4 | "Upload a PDF of K" files on drop on the person's word, even when the PDF shows it is another work, or is the same bytes another work holds; the ledger record is overwritten. | `AddWork.svelte:6, 186`; `refs/add.py:348-409`; B3 | blocks | fix: same one question |
| LIB-5 | Nothing can take a filed document off a work; deleting is refused for a cited work. | `refs/added.py:139-179`; B4 | blocks | fix: undo / unfile |
| LIB-6 | The entry a PDF makes of itself takes mastheads, department names and file names as titles and tool URLs as authors. | `refs/add.py:51, 77-133`; `refs/ingest.py:94-105`; table in section 2; quant `Of`, `Pra18`, `Alg` | hurts | fix |
| LIB-7 | Keys come from three generators; title-word keys with no year (`Of`, `Ric`, `Hig`), `Wor` from the literal "Work", `A` meaning both collision and version, and no agreement with the person's Better BibTeX keys. | `refs/lookup.py:68-80`; `refs/scan.py:561-569, 616, 626-630`; section 4 | blocks (the author's words) | fix: one scheme, the person's key wins |
| LIB-8 | With the network off (the default) a drop never looks up the identifier the PDF prints, and the viewer never asks; metadata and keys suffer (`Ric` vs `Per03`). | `cli/quilt.py:32`; `scan/quilt.py:60`; `AddWork.svelte:4, 189-192`; `$S/scripts/online.py` | hurts | fix: ask once per quilt |
| LIB-9 | A work with no identifier is identified by a hash of surnames, title and year, so correcting its details breaks its `cited:` links and detaches annotations on it (they store the work id). | `refs/identity.py:124-170`; `refs/links.py:231`; quant annotation target `work:abd8ef6c`; findings item 22 | hurts | fix: stable id from the stored PDF's hash (`loom-file`) |
| LIB-10 | Seven dialog states after a drop in the general dialog, two more in the per-work one, five entry points, separate network questions for paste. | section 2 tree and screenshots | blocks (author's requirement) | fix: section 9 |
| LIB-11 | Drop works only inside the modal, one file per drop; no window drop. | `AddWork.svelte:262-269`; grep: no other `ondrop` but `PagesEditor.svelte:209`; B10 | hurts | fix |
| LIB-12 | The metadata form writes the author line verbatim; a comma list becomes one BibTeX person. | `AddWork.svelte:194`; `refs/add.py:305`; quant `Cox79`; B6 | hurts | remove the form; Edit details with an author list |
| LIB-13 | Files over 256 MB are refused with a CLI instruction; every upload travels as base64 inside JSON. | `AddWork.svelte:43, 171-179`; `api.py:88-89, 224-231`; `s10-too-large.png` | hurts | fix: streamed upload, no command text |
| LIB-14 | Dropped PDFs wait in, and stay forever in, `.loom/build/uploads`, a directory loom treats as deletable. | `api.py:194, 235`; `refs/added.py:240`; B12 | hurts | fix: `.loom/incoming/`, emptied on filing |
| LIB-15 | "No page text" (scans) is known only to the last run; Info says "✓ Text filed" beside "It has no text to read"; no OCR. | `library.ts:229-266`; manifest `artifacts`; `s7-scanned-added.png`; B7 | hurts | fix the state; defer OCR, say it plainly |
| LIB-16 | State words are scattered and partly wrong: three meanings of "needs you", "Text" for the PDF, "Source: none" for an arXiv paper, a reading library reported as "0 works cited … not followed". | section 3; `cli/library/state.py:220, 310-327`; `library.ts:281`; `WorkStatus.svelte:57` | hurts | fix: one state word per work (section 7) |
| LIB-17 | An agent cannot add or stage a work; its only channel is a Suggestion annotation in prose, re-typed by the person. | `ai/layout.py:32`; `api.py:188-191`; showcase `annotation-types.toml`; findings item 21; INV-9 | blocks (must-have) | fix: `library suggest` (section 6) |
| LIB-18 | The library is a folded column list plus a Review sub-page called "Manage the library"; no sort, year, date added, page-text search for the person, or record of what was opened. | `Column.svelte:77, 270-290`; `review/library/+page.svelte`; measurements in section 7 | hurts | fix: Library page |
| LIB-19 | Paste takes one entry; lists of identifiers and titles are not recognised; ISBN and MR are recognised but not looked up, which is every textbook. | `refs/identity.py:241`; `AddWork.svelte:238`; B8 | hurts | fix lists; defer ISBN |
| LIB-20 | Raw BibTeX braces in the Add dialog. | `AddWork.svelte:206, 211`; B9 | cosmetic | moot after section 9 |
| LIB-21 | Reading a work with no overview is an error. | `cli/library/read.py:227`; B11 | cosmetic (agents see it first) | fix |
| LIB-22 | Non-papers (a seminar schedule) become works with no signal. | `s8-non-paper-added.png` | cosmetic | keep; Undo covers it |
| LIB-23 | No Zotero integration; the author's Better BibTeX export already carries the PDF paths loom needs. | grep; relloc `drafting/refs.bib`; section 8 | nice-to-have | fix ways 1 and 2 for v0.1; 3 after |

## Work for parallel implementers

| Package | Owns | Depends on | Independent? |
|---|---|---|---|
| A. Matching (LIB-1, 2, 3 backend) | `loom/src/loom/refs/ingest.py`, `refs/add.py` (`identify`), `cli/library/add.py` (no silent filing) | none | yes |
| B. Entry from a PDF (LIB-6, 8) | `refs/add.py` (`own_entry`, `_first_page_title`, `_info_authors`), `refs/ingest.py` (`title_lines`), `cli/quilt.py` (setting wording) | coordinate `refs/add.py` with A (different functions) | mostly |
| C. Keys and stable identity (LIB-7, 9) | `refs/lookup.py` (`key_for`), `refs/scan.py` (`_free_key`, `_derived_key`, `_sibling`), `refs/identity.py` (`identify`/`synthetic`: prefer `loom-file`) | none; anyone else touching `refs/identity.py` must coordinate | yes |
| D. Intake backend (LIB-4, 5, 10, 13, 14) | new `refs/intake.py`; `render/api.py` library endpoints (`library-take`, `-answer`, `-undo`, `unfile`); `refs/added.py` | A's rule; agree the API contract with E first | after A, in parallel with E |
| E. Intake viewer (LIB-10, 11, 12, 20) | replaces `arras/src/lib/components/AddWork.svelte`; window drop overlay in `arras/src/routes/+layout.svelte`; tray component; upload items in `LibraryRow.svelte`, `WorkStatus.svelte` | D's contract | in parallel with D |
| F. Library page and states (LIB-15, 16, 18) | new `arras/src/routes/library/+page.svelte`; `arras/src/lib/library.ts`; `Column.svelte` shelf; `review/sections.ts`; manifest page-text field in `render/build.py` | shares `Column.svelte` with E (E only adds the drop target in the layout) | yes |
| G. Agent suggestions (LIB-17) | new `refs/suggested.py`, `cli/library/suggest.py`, `cli/library/__init__.py`, `ai/layout.py`, `render/api.py` (two endpoints), `render/build.py` (manifest), `since.py`, viewer section on F's page | F for the viewer half; `render/api.py` shared with D (separate functions) | backend yes |
| H. Zotero `file` field (LIB-23) | gather/fetch step in `refs/scan.py` or `refs/build.py`; Settings › Library (`config_edit.py`, `arras/src/lib/shell/settings/`) | A and C (pairing and keys) | after A, C |
| I. Small fixes (LIB-19, 21) | `refs/identity.py` (`recognise` lists), `cli/library/read.py:227` | C for `identity.py` | yes |

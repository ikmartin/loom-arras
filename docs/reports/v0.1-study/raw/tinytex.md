# v0.1 study: a private TinyTeX, installed and run

Done 2026-11-13 on an Apple M2 (arm64), macOS Darwin 25.5.0, with other agents sharing the machine (`vm.loadavg` 2.2 to 23 during the work; the value beside each timing is the one-minute load). Everything lives under the scratch directory `S=/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/tinytex`: the installation in `$S/tt/TinyTeX`, quilt copies in `$S/q`, every tool log and JSON report in `$S/logs`, scripts in `$S/scripts`, screenshots in `$S/shots`. loom ran as `/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin/loom` with `XDG_CONFIG_HOME` in scratch.

Three PATHs were used (`$S/scripts/env-*.sh`):

- **tt**: TinyTeX's `bin/universal-darwin` first, then the ordinary PATH with every `/usr/local/texlive*`, `/Library/TeX*` and TinyTeX entry removed (Homebrew's poppler and Ghostscript stay, `LIBGS=/opt/homebrew/lib/libgs.dylib` from the shell stays).
- **bare**: `$S/tt/TinyTeX/bin/universal-darwin:/usr/bin:/bin:/usr/sbin:/sbin` and `LIBGS` unset: a Mac with no Homebrew and no MacTeX, the Overleaf-only pilot.
- **tl**: the ordinary PATH (TeX Live 2024 from `/usr/local/texlive/2024`).

Proof of which binaries ran (`which`, `--version`): under tt and bare, `latexmk pdflatex make4ht dvisvgm biber kpsewhich` all resolve to `$S/tt/TinyTeX/bin/universal-darwin/`, and report pdfTeX 1.40.29 (TeX Live 2026), make4ht v0.4e, dvisvgm 3.6, latexmk 4.89; under tl they resolve to `/usr/local/texlive/2024/bin/universal-darwin/` and report pdfTeX 1.40.26 (TeX Live 2024), make4ht v0.4b, dvisvgm 3.2.2, latexmk 4.86a. Every timing run printed the `latexmk`/`make4ht` path it used.

The example quilts from the main checkout (`man12`, `acgs`, `relloc`, all present, relloc 2.8 MB so copied whole) are in an older layout: `loom.sty`, `nodes/`, styles, `refs.bib` and figures sit at the quilt root while the document is `drafting/main-atomic.tex`, so they fail identically under both TeX Lives (`File loom.sty not found`; doctor's "macro block" warning). In the scratch copies only, I moved those into `drafting/` before building. Nothing was written to the main checkout.

## Summary of findings

| id | finding | severity | rec |
|---|---|---|---|
| TTX-1 | TinyTeX-0 v2026.11 installs in under a second anywhere (1.6 MB, 7.5 MB on disk, TL 2026, arm64 native), but 12 days after its release it could install nothing until `tlmgr update --self` | — | keep, with self-update in the recipe |
| TTX-2 | loom's programs plus the showcase's packages: 5 rounds; with TinyTeX-1's list as a seed, 54 MiB, 328 MB, about 50 s; biber alone is 68 MiB, an 81 MB binary and a 218 MB unpack in `$TMPDIR` on first run, which doctor reports as "hung" | hurts | fix |
| TTX-3 | Real papers needed 4, 8 and 20 install rounds; relloc pulled cm-super (62 MiB); the finished installation is 407 MB and downloaded 166 MiB in all | hurts | fix (preflight + seed) |
| TTX-4 | A missing file is read reliably from TeX's log only in the common case; six failures name no file or never reach loom; offline, tlmgr hangs past 200 s | hurts | fix |
| TTX-5 | Pictures fail silently: xy diagrams need dvips's headers (a package) and Ghostscript (not in TeX Live for macOS); PDF figures need poppler or Ghostscript | blocks (no-Homebrew pilot) | fix |
| TTX-6 | TinyTeX's output is TL 2026's; after normalisation every word matches TL 2024 except two review fragments that repeat their last line (a loom bug on 2026 output, not shown by today's viewer) | cosmetic (latent) | fix |
| TTX-7 | TinyTeX is faster: showcase cold 19 s against 29-31 s, warm 10 s against 15 s, man12 HTML 12 s against 26 s | — | keep |
| TTX-8 | Pinning: a dated release does not pin; a frozen repository exists only after the year closes; loom's own archive pins (58 MB lean, 191 MB whole, relocatable) | blocks (as the fix for INST-4) | fix |
| TTX-9 | The person's first ten minutes, with measured waits | — | design |
| TTX-10 | Use loom's TeX by default; pass the person's TEXMFHOME explicitly, since TinyTeX ignores it | hurts | fix |
| TTX-11 | Verdict on INST-3/4/5: recommendation confirmed with changes; disk and round figures changed; "recompile once" and "TEXMFHOME still read" refuted | — | — |
| TTX-12 | What I installed, where, and the one command that removes it | — | — |

## TTX-1 · Install

Source confirmed from TinyTeX's own pages: https://yihui.org/tinytex/ (script `https://tinytex.yihui.org/install-bin-unix.sh`; "Installing or running TinyTeX does not require admin privileges"; bundles "released on the monthly basis to the GitHub repo https://github.com/rstudio/tinytex-releases"), https://yihui.org/tinytex/faq/ (FAQ 8 `TINYTEX_DIR`, FAQ 9 portable, FAQ 11 yearly reinstall) and the releases page (bundle names; `TINYTEX_VERSION`). I read the script (`$S/dl/install-bin-unix.sh`, 5340 bytes) and did not run it: it starts with `rm -rf $TEXDIR` (its `TINYTEX_DIR` plus `/TinyTeX`), and on macOS, without `--no-path`, runs `tlmgr path add` (symlinks into `/usr/local/bin`) when that directory is writable, else asks for sudo to write `/etc/paths.d/TinyTeX`. I did by hand what it does for a bundle: download, `tar xf` into scratch. It also runs `tlmgr postaction install script xetex`, which matters only once xetex is installed; I did not install xetex.

- Bundle: `https://github.com/rstudio/tinytex-releases/releases/download/v2026.11/TinyTeX-0-darwin-v2026.11.tar.xz`, 1,632,112 bytes, sha256 `5405651b…acd421`. Download 0.40 s, extract 0.19 s (load 23.5). `du -sh`: 7.5M. Same release: TinyTeX-1 67.2 MB, TinyTeX 210.5 MB (GitHub API).
- TeX Live year: 2026 (`release-texlive.txt`; `tlmgr --version`: "TeX Live (https://tug.org/texlive) version 2026").
- Architecture: binaries are Mach-O universal (x86_64 + arm64); `arch -arm64 …/pdftex --version` runs, so no Rosetta is involved.
- Defaults the bundle carries (`$S/tt/TinyTeX/texmf.cnf`): `TEXMFHOME = $TEXMFLOCAL` (the person's `~/Library/texmf` is not searched), `TEXMFVAR`/`TEXMFCONFIG` inside the tree (portable), `max_print_line = 10000` (logs are not wrapped at 79 columns, unlike TL 2024's, which loom's warning lines show truncated). Package repository: `https://tlnet.yihui.org` (a Cloudflare-served copy of tlnet).
- **The dated bundle could not install anything.** The first `tlmgr install` (12 days after the v2026.11 release) stopped with "tlmgr itself needs to be updated. Please do this via either tlmgr update --self …". `tlmgr update --self` took 3.99 s (texlive.infra 80683 → 80721, 466k). After that, packages come from the live repository of that day (latexmk installed is dated 8 November 2026, a week after the bundle), so a dated bundle fixes only the base. The first contact with the repository also cached the package database: `tlpkg/texlive.tlpdb.main.<hash>`, 21.0 MB on disk.

## TTX-2 · What loom needs beyond the base

TeX programs loom calls, from the code: `latexmk` (`src/loom/tex/runner.py:133-134,249-252`, engine flags `runner.py:21-26`), the engines through latexmk and make4ht (`src/loom/tex/tex4ht.py:27`), `make4ht` with tex4ht/luaxml (`tex4ht.py:358,462-465,525`), `extractbb` (`tex4ht.py:438-441`), `kpsewhich` (`tex4ht.py:650-653`, `src/loom/scan/expand.py:81`, `src/loom/scan/preamble.py:342`), `dvisvgm` (`src/loom/render/assets.py:51-59`, and inside make4ht for pictures), `bibtex`/`biber` through latexmk, and `tlmgr` only as doctor's remedy text (`src/loom/doctor.py:90`). Not TeX but used for figures: `pdftocairo` (`assets.py:44-50`, `src/loom/records/crops.py:167`) and, inside dvisvgm, Ghostscript (TTX-5).

Rounds on the showcase copy under tt, TinyTeX-0 to both HTML and PDF of every document (`$S/logs/tlmgr-*.txt`, `sc-*`):

| round | trigger | packages | download | time | `du -sh` after |
|---|---|---|---|---|---|
| 0 | `tlmgr install` refused | `tlmgr update --self` | 0.5 MiB | 4.0 s | 28M (tlpdb cache) |
| 1 | doctor: latexmk, pdflatex, dvisvgm failing | `latexmk latex-bin make4ht tex4ht luaxml dvisvgm extractbb bibtex biber` (51 containers with dependencies) | 94.6 MiB, of which biber 67.8 MiB | 30.2 s (load 10) | 298M |
| 2 | `File amsart.cls not found` | amscls | 32k | 0.7 + 1.7 + 2.8 s | |
| 3 | amsart: "Package `amsfonts' not installed" (latexmk); `File amssymb.sty not found` (make4ht's run) | amsfonts | 3.5 MiB | 1.1 + 2.2 + 3.6 s | |
| 4 | `File tikz-cd.sty not found` | tikz-cd | 7k | 1.0 + 2.2 + 2.5 s | |
| 5 | `File tikz.sty not found` | pgf | 0.7 MiB | 1.0 + 1.6 + 2.1 s | 312M |
| 6 | `File beamer.cls not found` (talk.tex) | beamer (29 containers) | 0.45 MiB | 0.7 + 2.2 + 4.2 s | 316M |

(Each time is compile + `tlmgr search` + `tlmgr install`.) After round 6 all five showcase documents compile to PDF and HTML and `loom build` reports only the quilt's own content error (`duplicate-id`). Doctor then shows 14 checks ok, `xelatex` not found (warn, remedy still `brew install --cask mactex-no-gui`), and **`biber` failing: "hung: --version did not answer in 10 s"**. biber is a packed Perl program that unpacks itself on first run: first `biber --version` 10.6 s, second 1.6 s; the unpack is `$TMPDIR/par-6973616163/cache-bcf1e1e0…`, 218 MB, outside the TeX tree, and macOS's periodic cleaning of `$TMPDIR` repeats it. doctor's probe deadline is `PROBE_TIMEOUT = 10.0` (`src/loom/doctor.py:31`).

Seed alternative, measured on a second fresh TinyTeX-0 (`$S/tt2`, bare PATH, load 8-17): download + extract 1 s, `tlmgr update --self` 7.1 s, then `tlmgr install` of TinyTeX-1's current 95-package list (`tools/pkgs-custom.txt`, unchanged since the audit read it) plus `make4ht tex4ht luaxml dvisvgm tikz-cd pgf xypic`: 41.4 s, 125 containers, 54.2 MiB, 328M on disk (bin 108M, texmf-dist 160M of which tex4ht 45M and fonts 68M, texmf-var 30M of formats, tlpkg 30M). TinyTeX-1's list already holds amscls, amsfonts, dvips, metafont, mfware, ec, xkeyval, l3packages and float, which the real papers otherwise fetched on demand.

Compared with the audit's list (`make4ht tex4ht luaxml dvisvgm` + `standalone preview tikz-cd xypic pgf enumitem float mathtools` + `biber biblatex logreq`): `standalone` and `preview` were needed by nothing I built (CI's comment ties them to tests, `.github/workflows/loom.yml:83`); `beamer` (any talk), `dvips` (xy pictures, TTX-5), `metafont`+`mfware` or `cm-super` (TTX-3) are missing from it.

## TTX-3 · On-demand packages on the real papers

Done by `$S/scripts/ondemand.py`: `loom compile DOC --html --json`, read the missing names from loom's JSON (latexmk's and make4ht's `! ` lines) and from latexmk's log, map each with `tlmgr search --global --file /NAME`, `tlmgr install`, retry. Where it stopped with no name, I diagnosed by hand and installed (marked "by hand"). Starting state for each paper is the installation the previous one left (order showcase, man12, acgs, relloc).

| paper | missing, in the order met | packages | install rounds | time | download | `du -sh` after |
|---|---|---|---|---|---|---|
| man12 (article, 49 pp, xy) | mathrsfs.sty, setspace.sty, xy.sty; then `tex.pro` (make4ht's stdout only, TTX-5) | jknapltx (+rsfs), setspace, xypic; dvips by hand | 3 + 1 | 58.0 s + 3.6 s, then 45 s to redraw pictures | 0.75 + 0.3 MiB | 318M |
| acgs (amsart, xy, pstricks) | paralist, stmaryrd, epic, pstricks, pst-xkey.tex, comment, tcrm1200.tfm; then `!pdfTeX error: … Font tcrm1200 at 600 not found` | paralist stmaryrd eepic pstricks xkeyval comment ec; metafont mfware by hand | 7 + 1 | 94.5 s + 2.5 s + 24.8 s | 0.53 + 0.7 MiB | 330M |
| relloc (amsart, biblatex/biber, quiver, microtype, mathalpha) | microtype, mathtools, scalerel, marvosym, lipsum, l3keys2e, cancel, colortbl, float, xpatch, enumitem, mathalpha, quiver, biblatex (seen only in make4ht's run), old-arrows, libertinust1-mathbb.tfm; tikz library `spath3`; tikz library `nfold`; grfext.sty; then `! pdfTeX error (font expansion): auto expansion is only possible with scalable fonts.` | the 16, then spath3 (by hand, pattern added), tikz-nfold, grfext, then cm-super by hand | 16 + 1 + 2 + 1 | 105.7 + 3.2 + 49.6 + 7.4 + 25.6 = 191.5 s | 2.0 + 0.01 + 61.6 MiB | 406M |

After all of them: 135 packages, `du -sh` 407M, 166 MiB downloaded in 128 containers (biber 67.8 and cm-super 61.6 of it). The final compiles succeed: man12 126/126 nodes stamped, 343/343 blocks placed; acgs 103/103 nodes, 504/540 exact (the 36 are author and bibliography lines, as under TL 2024 the paper's own structure); relloc 58/58 nodes with biber 2.22 producing a 31-entry `.bbl`. relloc's `loom build` then reports 31 `loom:snippet-failed` (digest environments undefined, `\xymatrix` under a preamble without xy): content, not TeX.

A typical round on these papers costs 4-7 s (search 1.3-2.5 s, install 1.5-3.5 s, a compile that stops in the preamble 1-3 s); latexmk runs with `-halt-on-error` (`runner.py:250-251`), so each missing file costs a round. Two measured ways to cut rounds: (1) **resolve names locally**: the tlpdb tlmgr already cached (21 MB) maps 240,705 file names to packages in 0.20 s with no network (checked: stmaryrd.sty, tikzlibraryspath3.code.tex → spath3, tex.pro → dvips, tcrm1200.tfm → ec, sfrm1200.pfb → cm-super); (2) **preflight from the preamble**: relloc's preamble names 26 packages directly (29 `\usepackage` names in `main-atomic.tex` and its two local styles, 3 of them its own), which covers 13 of its 20 install rounds in one `tlmgr install`; with the seed of TTX-2 about 6 rounds remain (colortbl, libertinust1math, spath3, tikz-nfold, grfext, and the cm-super font case). loom already computes a preamble closure (`src/loom/scan/preamble.py`) and the packages it loads (`loaded_packages`, `src/loom/scan/digests.py:99,122`).

## TTX-4 · Detecting a missing package, failures that look like something else, and offline

Reliability per tool:

- **The engine (latexmk's log)**: `! LaTeX Error: File 'x' not found.` named the file in 30 of the 37 install rounds after the programs round (showcase 5, man12 4, acgs 8, relloc 20); 4 more named a file in another form (a missing TFM metric twice, a TikZ library twice); 3 named nothing loom reads (dvips, metafont/mfware, cm-super). TinyTeX's unwrapped logs (`max_print_line = 10000`) keep long names on one line; under TL 2024 they wrap at 79 columns.
- **make4ht**: its TeX pass runs without halting, so it sometimes reaches a second missing file in the same round (showcase round 3, relloc round 14), but loom keeps only TeX's log when one exists (`tex4ht.py:407`, `tex4ht.py:540`) and drops make4ht's own output, which is where dvisvgm's and mkutils' errors are.
- **biber**: never missing in these runs; its failure would show in latexmk's "Collected error summary", which loom already reads (`runner.py:66-77`).

Failures that do not look like a missing package:

1. Class/package checks that use `\IfFileExists`: amsart's "Package `amsfonts' not installed, or version too old?" names a package, not a file; under `-halt-on-error` it is the only message.
2. TikZ libraries: "I did not find the tikz library 'spath3'. I looked for files named tikzlibraryspath3.code.tex …" (a pattern of its own; quiver depends on spath3 and tikz-nfold, and TeX Live's package metadata does not say so).
3. Missing bitmap font: `!pdfTeX error: pdflatex (file tcrm1200): Font tcrm1200 at 600 not found`. The file's package (ec) is installed; the cure is metafont+mfware (bitmap) or cm-super (Type 1). loom's error pattern `^! ` (`runner.py:284`, `tex4ht.py:408`, `src/loom/render/snippets.py:38`) misses this line because there is no space after `!`; loom reported only "latexmk exited 12: pdflatex: Command for 'pdflatex' gave return code 1".
4. microtype with a bitmap font: `! pdfTeX error (font expansion): auto expansion is only possible with scalable fonts.` names nothing; cure cm-super (62 MiB).
5. dvisvgm without dvips's headers: `WARNING: PostScript header file tex.pro not found` and `[ERROR] mkutils: File s0x.svg doesn't exist` in make4ht's stdout only; the pictures silently fail (TTX-5).
6. dvisvgm without Ghostscript: `processing of PostScript specials is disabled (Ghostscript not found)` / `17 PostScript specials ignored`: not a TeX package at all (TTX-5).

**Cached failures are not retried after an install.** Snippet results are cached under a key of loom's version, loom's code, preamble and text (`snippets.py:116-130`), not the TeX installation; a picture TeX4ht named but never drew is not cached as a refusal, and `_refused` drops an empty error, so no diagnostic is raised (`src/loom/render/fragments.py:232-249`). After installing dvips, `loom build` and `loom build --force` (2 s) still showed 55 failed diagrams; only deleting `.loom/build/cache/snippets` and then `--force` (45 s) drew them.

**Offline.** `tlmgr search` against a refused connection fails in 0.35 s ("could not get texlive.tlpdb … Maybe the repository setting should be changed"); against an unreachable address it was still waiting when killed at 200 s. loom should: give tlmgr its own deadline (about 30 s); resolve names from the cached tlpdb offline so it can still say which package is needed; show the document as source with "needs package X; loom will fetch it when online", and retry on the next compile.

**Where the retry would live** (new `src/loom/tex/missing.py` holding the name patterns, the tlpdb index and the install call):

- `compile_tex`, after the log is read (`src/loom/tex/runner.py:279-286`): collect names from the log and from latexmk's output, install, rerun, up to a bound; widen the error pattern to `^!`.
- `compile_html`, the pass loop and log read (`src/loom/tex/tex4ht.py:389-408`): scan both the log and make4ht's `said`; the same for `make_html` (`tex4ht.py:538-545`) and the snippet run (`src/loom/render/snippets.py:298-331`).
- The serve path that compiles in the background (`src/loom/render/serve.py:792-824`) is where progress belongs ("fetching stmaryrd, 163 KB"); `loom compile` (`src/loom/cli/build_cmds.py:150-158`) gets the same retry.
- A TeX-state stamp (TL year + a counter bumped on every install) into `snippet_key` (`snippets.py:128`), so earlier refusals and undrawn pictures are retried; and a diagnostic when a picture is missing (`fragments.py:247`).
- doctor (`src/loom/doctor.py:31,76-116`): loom's TeX as a row, remedies that name loom's own repair, and a longer first deadline for biber.

## TTX-5 · Pictures fail silently, and Ghostscript is outside TeX Live

- **xy diagrams need dvips's PostScript headers.** loom draws a diagram in TeX4ht's svg mode (`tex4ht.py:176-177`, `src/loom/render/fragments.py:219-242`); xy loads its dvips driver there and dvisvgm needs `tex.pro`, `texps.pro`, `special.pro`, `color.pro` from the `dvips` package. Without it, man12's 55 diagrams all rendered as `figure.diagram.failed` (raw `\xymatrix` source) with no diagnostic, against 100 SVGs under TL 2024 (reproduced alone with `$S/scripts/repro_picture2.py`). `tlmgr install dvips`: 0.3 MiB, then 99 SVGs. dvips is in TinyTeX-1's list.
- **The same diagrams need Ghostscript.** On the bare PATH (no Homebrew, `LIBGS` unset) dvisvgm said "processing of PostScript specials is disabled (Ghostscript not found) … 17 PostScript specials ignored" and drew the diagram with **no arrows** (`$S/shots/xy-gs-vs-nogs.png`: left with Ghostscript, right without). TeX Live does not ship Ghostscript for macOS (MacTeX installs it separately; it is what `/usr/local/bin/gs` is on this machine). acgs's pstricks pictures are in the same position.
- **PDF figures need poppler or Ghostscript.** On the bare PATH the showcase's `figures/quiver.pdf` is not converted (`assets.py:44-62` tries `pdftocairo`, then `dvisvgm --pdf`); four fragments name `figures/quiver-.png`, which does not exist; no diagnostic.

So TinyTeX makes the text of every paper render, but on a Mac without Homebrew loom's pictures are wrong or missing. Options for the lead: render pictures through the PDF loom already compiles (pdflatex with xy's own PDF driver) and convert with a bundled PDF library (INST-8's pypdfium2, to PNG); or ship a Ghostscript build (no brew-free official one for macOS); or require Homebrew's ghostscript and poppler for the pilots. Whatever is chosen, a missing picture must raise a diagnostic.

## TTX-6 · Sameness with TeX Live 2024

Same build (every document `loom compile DOC --html`, then `loom build`) on fresh copies under tl and tt; compared with `$S/scripts/htmlcmp.py` (tags with attributes and text, whitespace collapsed) and `$S/scripts/wordbag.py` (word multisets, inline math with spaces removed).

- **Which year TinyTeX matches: TL 2026.** Raw TeX4ht pages show exactly the 2026 forms `loom/tests/unit/render/test_normalise.py:82-139` records: displays as `<span class='mathjax-env …'>` inside the paragraph (2024: `<div>` after `</p>`), the title as `h1` (2024: `h2`), and the MathJax 4 script (2024: MathJax 3). loom's normaliser absorbs these.
- **Showcase** (101 published fragments): 49 byte-identical, 50 identical modulo whitespace, 2 differ in words. The 2 are `fragments/review/*-block.html` for sh-0008 and sh-000C/proof: under TinyTeX each repeats its last line after the closing `</details>` (for example "… has integral vertices by the saturation of Proposition 2.6. □" twice), already so in the cached snippet. Deterministic (three TinyTeX builds), absent in both TL 2024 builds (which are byte-identical to each other), and not reproduced by a one-text run, so it comes from the multi-text snippet run's paragraph closing on 2026 output (`snippets.py:332-343`). CI's TL 2026 would show it too. The shipped viewer does not read `review_fragment` (only declared in `arras/src/lib/manifest/types.ts:330`), so nobody sees it today. The talk (beamer) shows 3 blocks as source under both years.
- **man12** (731 fragments, after dvips): 381 byte-identical, 138 modulo whitespace, 191 differ only in markup, 21 differ in token text; the word multisets are identical in all 731. What differs: paragraph segmentation (the compile report's 274 blocks under 2024, 343 under 2026: 2026 splits paragraphs at displays), spacing inside inline math as written (`\(\alpha\in A_k(\mathfrak{F}^{\prime})\)` against `\(\alpha \in A_k(\mathfrak {F}^{\prime })\)`), and SVG file names (dvisvgm 3.6 against 3.2.2).
- **Diagnostics**: identical sets, showcase 9/9, man12 735/735. Compile warnings identical except TL 2024's are cut at 79 columns. PDFs: same page counts (3; 49), producers pdfTeX-1.40.26 against 1.40.29.
- **Screenshots** (headless Chromium through `arras/node_modules/playwright`, servers on ports 48401-48404, all stopped, `lsof` clean): showcase Theorem 3.1 and Theorem 3.4 differ in 0.15% and 0.28% of pixels, all in one strip: TL 2024 prints a wider gap in "Proposition  2.6" (its HTML keeps the tie as several spaces), TinyTeX the normal one (`$S/shots/crop-sc-0.png`). man12's master scrolled to its fourth diagram: 0.53% of pixels, 55/55 diagrams drawn under both, no visible difference (`$S/shots/side-m.png`). Before dvips was installed the same page showed 55 diagrams as source.

Nothing rendered wrongly in the viewer under TinyTeX once dvips was present; the one wrong output is the latent review fragment.

## TTX-7 · Speed

| run | TL 2024 | TinyTeX | load |
|---|---|---|---|
| showcase cold: 5 documents `compile --html`, then `build` | 30.9 s; 28.5 s | 19.2 s; 18.7 s | 5.3-6.0 |
| of which main-atomic `compile --html` | 6.1 s; 5.3 s | 3.4 s; 3.0 s | |
| of which `loom build` | 8.1 s; 9.2 s | 6.7 s; 7.3 s | |
| showcase warm (the same again, nothing changed) | 14.9 s | 10.2 s | 5.4-5.8 |
| man12 cold `compile --html` | 26.1 s | 11.6 s | 6.4-7.6 |
| man12 `loom build` with all diagrams drawn | 93.0 s (cold) | 45 s (`--force`, empty snippet cache) | 5.1-6.4 |
| trivial amsart + tikz-cd `pdflatex`, 3 runs | 0.49-0.51 s | 0.24-0.28 s | 4.9 |
| `kpsewhich amsart.cls` | 0.09 s | 0.00 s | 4.9 |
| showcase cold on the bare PATH | — | 15.0 s | 2.2 |

The two cold pairs ran in opposite orders with the same result. The difference is per process: a full TeX Live loads a larger `ls-R` and searches more trees (TL 2024's TEXMF list includes `~/Library/texmf`), and make4ht starts many TeX processes per page.

## TTX-8 · Pinning

| way | pins | evidence | verdict |
|---|---|---|---|
| a dated TinyTeX release (`TINYTEX_VERSION=2026.11`) | the bundle only | v2026.11 could not install from the live repository 12 days later until `tlmgr update --self`; every package fetched afterwards is that day's | not a pin |
| a frozen repository | everything, including on-demand | the historic archive keeps "the frozen state at the end of the cycle in tlnet-final/" (https://tug.org/texlive/acquire.html); 2024 and 2025 `tlnet-final` answer 200 at ftp.math.utah.edu, ftp.tu-chemnitz.de and mirrors.tuna.tsinghua.edu.cn; 2026's exists only once 2026 closes | use from March 2027 |
| loom's own archive of a finished installation | the base, byte for byte, for every pilot | `tar | xz -6` of the installation: 191 MB whole (with biber, cm-super, tlpdb cache), 58 MB without those three; 29 s to make, 13.4 s to extract; extracted to a different directory it ran (`pdflatex`, `kpsewhich`, `make4ht`) with no path change | recommend |

When the year changes: TeX Live 2027 is planned for 7 March 2027 (https://tug.org/texlive/, "Plan for TeX Live 2027"). From then a TL 2026 tlmgr refuses the live repository ("Remote repository is newer than local", TinyTeX FAQ 11, whose advice is to reinstall), so on-demand installs stop for every pilot on the same day unless loom has already pointed tlmgr at the 2026 `tlnet-final`. Moving to 2027 is then a deliberate loom release: a new archive and a revalidated normaliser.

**Recommendation.** loom builds one archive per platform on a chosen day: TinyTeX-0 vYYYY.MM, `tlmgr update --self`, then a seed (TinyTeX-1's list + loom's programs + the pilots' known packages, without biber and cm-super), published as a release asset with a checksum. The installer extracts it to `~/Library/Application Support/loom/tex` and sets tlmgr's repository to a named mirror (not a redirector, as CI's step learned, `.github/workflows/loom.yml:84-96`); loom switches that setting to the 2026 `tlnet-final` at the freeze. On-demand installs (and biber, cm-super) come from that repository. CI installs the same seed list on Linux the same day.

## TTX-9 · The person's experience (Overleaf-only, no TeX), under that design

1. Runs the install script. It fetches loom and loom's TeX: about 58 MB (measured archive), extracted in about 13 s; or, without an archive, TinyTeX-0 and the seed through tlmgr, about 56 MiB in about 50 s on this connection. Show: "Setting up TeX for reading papers (one time, about 60 MB)", with a byte count, and that nothing needs a password.
2. First launch, opens a quilt with their paper. loom scans the preamble and installs what it names in one batch (TTX-3: about 4-7 s plus download), then compiles. Show the document as source at once, with one line: "Typesetting: fetching 12 LaTeX packages (2.0 MB)".
3. First page. Small paper: about 3 s for PDF and HTML (showcase main-atomic, 3.0-3.4 s). A 49-page paper with diagrams: 12 s for the page, about 45 s more to draw its 55 diagrams. Show a per-document state ("typeset", "drawing diagrams 12/55").
4. If something is still missing: each further round 4-7 s; a paper like relloc about 5 more rounds plus cm-super (62 MiB, 7 s here) and biber (68 MiB, then 11 s on its first run). Show each package by name and size; if offline, say which package is needed and that loom will fetch it when online.
5. If loom cannot fix it (a font case, no Ghostscript for xy pictures): one diagnostic per kind with the remedy, never a silent source block or a missing arrow.

## TTX-10 · Their own TeX or always loom's

Use loom's own, always, with the person's own TeX behind a setting. For: one TeX year, the one CI tests (INST-4); measured 35-60% faster (TTX-7); no admin and no Homebrew; repairs loom can make itself. Against: about 0.35-0.4 GB again on a machine that already has TeX; the PDF loom compiles may differ from the one their own TeX or Overleaf makes (different package versions); and **their personal tree is invisible**, because TinyTeX's `TEXMFHOME = $TEXMFLOCAL` and loom asks the active `kpsewhich` for TEXMFHOME (`tex4ht.py:646-656`) only for make4ht, never for latexmk (`runner.py:260`). loom must pass `TEXMFHOME` (the person's `~/Library/texmf`) explicitly to both, or styles that live there (this author's `~/Library/texmf` links to style sheets) will be "not found" under loom's TeX, which the on-demand logic would then wrongly try to fetch.

## TTX-11 · Verdict on the earlier audit (INST-3, INST-4, INST-5)

| claim | verdict |
|---|---|
| INST-3: without TeX loom shows source; a local TeX is required in practice | confirmed |
| INST-4: TeX4ht's HTML differs 2024/2026; pin every pilot to TL 2026 | confirmed (TTX-6); a TL 2026-only defect exists (review fragments) |
| INST-5 recommendation: loom's own TinyTeX, per user, TL 2026, on-demand packages | confirmed, with changes: ship loom's own archive rather than install from a dated release (TTX-8), preflight from the preamble, and pictures need Ghostscript/poppler beyond TeX (TTX-5) |
| v2026.11 is TL 2026; darwin bundles 1.6 MB / 67 MB / 210 MB / 2.0 GB | confirmed (1,632,112 / 67,211,812 / 210,514,532 bytes; TinyTeX-2 daily only) |
| universal-darwin, Apple Silicon native | confirmed |
| per-user, no admin; sudo only for `/etc/paths.d`, skipped with `--no-path`; `TINYTEX_DIR`, `TINYTEX_VERSION` | confirmed; add: the script also symlinks into `/usr/local/bin` when writable, and `rm -rf`s its target first |
| what loom needs is not in TinyTeX-1 (no make4ht, tex4ht, luaxml, dvisvgm, tikz-cd) | confirmed; add beamer, dvips (in TinyTeX-1), and metafont/mfware or cm-super |
| TinyTeX-1 equivalent about 53 MB / 0.21 GB | not measured directly (TinyTeX-0 was installed); bundle is 67 MB |
| plus make4ht tex4ht luaxml dvisvgm: about 57 MB / 0.28 GB | changed: TinyTeX-1 list + those + tikz-cd pgf xypic measured 54.2 MiB (+1.6 MB bundle) and 0.33 GB (328M) |
| plus biber biblatex logreq: about 129 MB / 0.37 GB; biber 71 MB | download confirmed (biber container 69,429k); disk changed: biber's binary is 81 MB and its first run unpacks 218 MB more in `$TMPDIR` |
| "about 60 MB download, 0.3 GB on disk, a few minutes" for the whole | changed: base with the seed 56 MiB / 0.33 GB / about 50 s; after three real papers 166 MiB / 0.41 GB, driven by biber and cm-super |
| on demand: read `File x not found`, `tlmgr search --global --file`, install, "recompile once" | changed: that pattern caught 30 of 37 rounds (34 with two more patterns); a paper takes up to 20 rounds, not one; six failure kinds need other handling (TTX-4) |
| "the person's TEXMFHOME still read (`tex4ht.py:638-656`)" | refuted under TinyTeX (TTX-10) |
| frozen year installable from `tlnet-final`; TL 2026 live until about March 2027 | confirmed (7 March 2027 planned) |
| INST-5 effort "2-3 days" | changed: add the preflight, the tlpdb index, the snippet-cache stamp, make4ht stdout scanning and picture diagnostics (about a day more), and a decision on Ghostscript/poppler (TTX-5), which TinyTeX does not answer |

## TTX-12 · What I installed, where, and how to remove it

- `$S/tt/TinyTeX`: TinyTeX-0 v2026.11 plus 135 packages by tlmgr (list in `$S/logs/installed-final.txt`), 407M.
- `$S/tt2/TinyTeX`: a second TinyTeX-0 v2026.11 with TinyTeX-1's list and `make4ht tex4ht luaxml dvisvgm tikz-cd pgf xypic`, 328M.
- `$S/reloc/TinyTeX`: the archive of the first, extracted to test relocation, 405M; `$S/archive/*.tar.xz`, 237M.
- Side effect outside scratch: biber's unpack cache `/var/folders/xh/br51g1_j71sdmy2fqdss_blh0000gn/T/par-6973616163/cache-bcf1e1e0a2c546e2ccb004c42af5f8631c12c6fd` (218M, created 14:51 by TinyTeX's biber 2.22; the sibling `cache-4cd328e4…` predates this work and is not mine).
- Nothing in `~/Library/TinyTeX`, the shell profile, `/usr/local/bin`, `/etc/paths.d` or any PATH outside my commands; no sudo. Quilt copies, logs, scripts and screenshots are also under `$S` (1.5G in all).

One command removes all of it:

```
rm -rf /private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/tinytex /var/folders/xh/br51g1_j71sdmy2fqdss_blh0000gn/T/par-6973616163/cache-bcf1e1e0a2c546e2ccb004c42af5f8631c12c6fd
```

I did not run it.

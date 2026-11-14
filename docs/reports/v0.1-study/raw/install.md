# v0.1 study: install, TeX, Overleaf, platforms, launch

Auditor: install. Checkout studied: `.claude/worktrees/v01-study` at 71621877 (branch v0.1-study, equal to main). Paths below are relative to the checkout; `loom/src/loom/` is abbreviated `src/`. Web research was done with WebSearch/WebFetch using generic queries only; every outside claim carries a URL, and the few I could not confirm are marked unverified. Hand checks ran in `$SCRATCH/study/install` on a copy of `demos/showcase`, with `XDG_CONFIG_HOME` pointed at scratch, using the `loom` on PATH (0.1.0.dev0, Python 3.13.13). No server was left running; one ran for nine seconds on port 47951.

The lead's updates (Overleaf through git only, with no zip path, since a person without git copies text by hand; agent apps are Claude Code in the Claude desktop app's Code tab and Codex in the ChatGPT desktop app; effort to be given honestly with file ownership and the author's own tasks) are folded in throughout.

## Summary of findings

| id | finding | weight | effort | rec |
|---|---|---|---|---|
| INST-1 | No launcher: `loom serve` is one quilt per process, run from a terminal inside the quilt, port 8791 fixed; no home, recent quilts, open-folder or new-quilt | blocks | days (3-4) | fix |
| INST-2 | No installable release; both READMEs install from a clone or from a repository that does not exist | blocks | hours + a day | fix |
| INST-3 | Without TeX every LaTeX text is shown as raw source; doctor fails | blocks | (see INST-5) | fix |
| INST-4 | TeX4ht HTML differs by TeX Live year; only 2024 and 2026 are handled; CI's image floats | hurts | hours (pin) | fix |
| INST-5 | A private, per-user TinyTeX (TL 2026) is small, needs no admin, and can carry what loom needs | blocks (as the fix) | days (2-3) | fix |
| INST-6 | Every tool is found through PATH; apps started from Finder/Dock and agent-started `loom mcp` get launchd's bare PATH | hurts | hours | fix |
| INST-7 | git on a fresh Mac is the Command Line Tools shim; loom and `uv tool install git+…` invoke it | hurts | hours | fix |
| INST-8 | poppler has no brew-free route on a Mac; page text, word boxes, identity test and crops depend on it | hurts | days (2-4) | fix or defer |
| INST-9 | Overleaf sync is quilt-as-truth publishing, paired and fetched only from the CLI, never run against real Overleaf, with no credential handling | blocks (Overleaf pilot) | (see INST-10) | fix |
| INST-10 | A read-only Overleaf mirror flow on the existing sync, and what to hide | blocks (Overleaf pilot) | days (4-6) | fix |
| INST-11 | Annotations when text changes underneath them (any pull, a paste by hand): blocks without loom ids are keyed by position, so an annotation detaches or lands on the wrong block when a change both inserts and edits | hurts | days (2-3) | fix |
| INST-12 | No Overleaf path without git: a downloaded-zip import was considered and declined; copy and paste by hand needs nothing from loom | irrelevant | — | remove |
| INST-13 | Showing Overleaf's own PDF instead of local TeX: not automatable, and marks do not carry across downloads | irrelevant as a design | — | remove (as an option) |
| INST-14 | Windows: several hard blockers in process control, liveness, open, encoding, file replacement; tests cannot run there | blocks Windows | a week or more | defer |
| INST-15 | Linux is covered by CI; macOS, the pilots' platform, is not in CI at all | hurts | hours | fix |
| INST-16 | Dragging resources in: only a PDF into the library's Add dialog; no window-level drop, no .tex, source-archive or folder import over the API | hurts | days (2-3) | fix |
| INST-17 | Restart after update is detected but manual | hurts | (in INST-1) | fix |
| INST-18 | Viewer preferences live in localStorage per origin, so ports must be stable per quilt | cosmetic | hours | fix |
| INST-19 | Packaging options ranked | — | — | see table |
| INST-20 | An unsigned downloaded .app is blocked on Sequoia; a launcher .app written locally by the install script is not quarantined | hurts (if downloaded) | — | keep (local launcher), defer (signed app) |
| INST-21 | Homebrew tap: Rust-built dependencies, needs brew and CLT first | irrelevant | days | remove (as an option) |
| INST-22 | doctor's remedies assume Homebrew/apt and a 6.9 GB MacTeX, and `latexmk` missing is a hard fail | hurts | hours | fix |
| INST-23 | Agent hookup: per-quilt MCP files exist for both pilot apps, but are written by a CLI step, and "open this quilt in the app" does not exist | hurts | hours-a day | fix |

## 1. What loom needs to run

**Python and packages.** `requires-python = ">=3.11"` (`loom/pyproject.toml:7`); runtime dependencies `click`, `markdown-it-py`, `mcp>=2.3,<3` (`loom/pyproject.toml:18-22`), which close to 29 packages in `loom/uv.lock`, three with native wheels (`pydantic-core`, `rpds-py`, `pywin32`). All have wheels for macOS arm64, so `uv` installs without a compiler. CI tests 3.11-3.13 on Ubuntu (`.github/workflows/loom.yml:16-30`). The viewer ships as a committed 12 MB bundle (`src/assets/arras/`, 303 tracked files, stamped `4c4ba495-dirty` in `VERSION`), so no Node is needed.

**External programs, from the code** (doctor's table is `src/doctor.py:76-116`; it is accurate on presence but understates git):

| program | where called | what for | lost when missing |
|---|---|---|---|
| `latexmk` (+ the engine) | `src/tex/runner.py:134,227-299` | every compile: the PDF, the `.aux` numbers, the identity test, the arXiv digest's numbering (`src/digest/extract.py:449-462`) | no PDF, no `\ref` numbers; serve prints `compiled X: FAILED: latexmk is not installed` per document (hand check); doctor exits 2 |
| `pdflatex` / `latex` / `xelatex` / `lualatex` | through latexmk and make4ht (`src/tex/tex4ht.py:27`) | engines; `latex` (DVI) is what TeX4ht runs | the document's engine missing fails its compile (`src/doctor.py:464-480`) |
| `make4ht` + `tex4ht` + `luaxml` | `src/tex/tex4ht.py:358-360,454-480,525-527`; gated in `src/render/serve.py:811,922`; snippets `src/render/snippets.py:198` | the reading HTML of every document and every text no compile makes (digest results, previews) | everything shows as its LaTeX source (`src/render/sourceview.py:1-3`, `src/render/build.py:436`) |
| `dvisvgm` | `src/render/assets.py:44-60` | pictures TeX draws (TikZ, xy) and PDF figures | figures and diagrams missing; doctor fails (REQUIRED) |
| `extractbb` | `src/tex/tex4ht.py:438-441` | bounding boxes of PDF/PNG figures for TeX4ht | figure sizes wrong in the HTML |
| `kpsewhich` | `src/scan/expand.py:76-90`, `src/scan/preamble.py:342`, `src/tex/tex4ht.py:638-656` | finding TeX-tree files a source reads, TEXMFHOME for TeX4ht | the person's own styles not found in HTML runs |
| `bibtex` / `biber` | through latexmk | bibliographies | no bibliography; doctor checks biber against biblatex (`src/doctor.py:319-358`) |
| `pdftotext` | `src/refs/pages.py:118-125`, `src/tex/identity.py:40-65`, `src/records/marks.py:91-96,231-235,465-484` | page text of library PDFs (what agents read and search), `-bbox-layout` word boxes for highlights and marks, the import identity test | a PDF paper still displays (pdf.js in the bundle) but has no text for agents, no locate, no marks' words; import skips the identity test |
| `pdfinfo` | doctor only lists it as "page rotation" | rotation | rotated pages misplaced |
| `pdftocairo` | `src/records/crops.py:167`, `src/render/assets.py:44` | the crop image an agent gets beside a PDF mark; PDF figures | no crop; dvisvgm stands in for figures |
| `git` | `src/sync.py:120-166` (all of sync); `src/adopt.py:156` (`git merge-file`, required to merge an agent document's prose: it raises otherwise); `src/scan/quilt.py:214-229` (author name fallback, on the serve path); `src/scan/alloc.py:32-55` (ids seen in history); `src/ai/clients.py:161` (tracked client files); `src/cli/quilt.py:50-71` (`init --git`) | sync, adopt, identity | sync and adopt refuse; doctor says only "loom init --git and loom sync" (`src/doctor.py:114`) |
| `open` / `xdg-open` / `gtk-launch` | `src/files.py:465-504` | opening a file or an app from a link | Windows: refused as unsupported |

**With no TeX at all** (hand check: PATH reduced to `~/.local/bin:/usr/bin:/bin`, `loom build` on the showcase copy, then `loom serve` for nine seconds):

- A LaTeX draft: every node and every stretch of prose is a `<pre class="source">` of the raw LaTeX (`.loom/build/fragments/masters/drafting/main-atomic.html`, `fragments/nodes/sh-0001.html`). Nodes keep their identity, label and `data-src`, so they can be found, linked and annotated, but nothing is typeset: `$V(\quiv)$` is shown as those characters. No PDF.
- A library paper that came as a PDF: displayed by the viewer's bundled pdf.js. Without poppler there is no page text (`MapRefused`, `src/refs/pages.py:118-125`), so agents cannot read or search it through loom and marks have no words.
- A library paper that came as arXiv source: the digest is extracted without TeX (numbering "emulated", `src/digest/extract.py:458-464`), but its results are shown as LaTeX source like a draft (`fragments/digests/Arden24.html`, 13 `pre.source` blocks).
- `loom doctor` fails (exit 2) on `latexmk`, `pdflatex`, `dvisvgm` and the quilt's engine, each with the remedy `brew install --cask mactex-no-gui` (`src/doctor.py:34-41,76-79`).

## 2. Is a local TeX required, and how to make it painless

### INST-3 · Without TeX, loom is a source viewer · blocks · rec fix
Evidence above. Annotation, suggested edits and agents all work on source, so loom does not crash, but reading mathematics as raw LaTeX in a monospace block is not the product. For v0.1 a local TeX is required in practice; the question is only who installs it.

### INST-4 · TeX Live year changes what loom has to parse · hurts · hours to pin · rec fix
TeX4ht's HTML changed between TeX Live 2024 and 2026: displays inside paragraphs, paragraph opening and closing between snippets, bibliographies as lists (`loom/tests/unit/render/test_normalise.py:82-139`; commits `fe24330e`, `01b9d57c`, `6e1b1c70`, `b7fddcd6` "CI green again: TeX Live 2026's pages read as earlier ones"). The normaliser is tested on those two years only. The author's machine runs TL 2024 (`/usr/local/texlive/2024`), CI runs whatever `texlive/texlive:latest-medium` is (`.github/workflows/loom.yml:78`), which will become TL 2027 when that ships (planned 7 March, per the "Plan for TeX Live 2027" on https://tug.org/texlive/). A pilot with TL 2023, 2025 or MiKTeX is on an untested path. Pin: give every pilot the same TL 2026 (INST-5) and pin CI's container to a 2026 tag.

### INST-5 · A private TinyTeX per user · blocks (as the fix) · days · rec fix
Facts, checked today:

- TinyTeX v2026.11 (2026-11-01) is TeX Live 2026 (`depend release/2026` in the current `texlive.tlpdb`). Bundles for darwin: TinyTeX-0 1.6 MB, TinyTeX-1 67 MB, TinyTeX 210 MB, TinyTeX-2 2.0 GB, compressed (GitHub API on https://github.com/rstudio/tinytex-releases, release `v2026.11`). Linux x86_64/arm64/musl and Windows bundles exist at similar sizes. Licence GPL-2 (same page). macOS binaries are TeX Live's `universal-darwin` (the author's TL 2024 shows the same directory), so Apple Silicon is native.
- It installs per user (`~/Library/TinyTeX` on macOS, `~/.TinyTeX` on Linux, `%APPDATA%\TinyTeX` on Windows) with no admin rights; the macOS script only asks for sudo to write `/etc/paths.d`, skipped with `--no-path`; `TINYTEX_DIR` and `TINYTEX_VERSION` choose location and release (https://yihui.org/tinytex/, https://yihui.org/tinytex/faq/, https://github.com/rstudio/tinytex-releases). The profile is `portable 1` (`tools/tinytex.profile` in https://github.com/rstudio/tinytex).
- What loom needs is not in it. TinyTeX-1's list (`tools/pkgs-custom.txt`) has `latexmk`, `amsmath`, `hyperref`, `lm`; the larger bundle (`pkgs-yihui.txt`) adds `pgf`, `xypic`, `standalone`, `preview`, `biber`, `biblatex`. Neither has `make4ht`, `tex4ht`, `luaxml`, `dvisvgm` or `tikz-cd`. CI's own list of what the medium scheme lacks is the right seed (`.github/workflows/loom.yml:81-95`).
- Sizes, computed from the current `texlive.tlpdb` (my script summing `containersize` over dependency closures for `universal-darwin`; installed size assumes TeX Live's 4 KiB size unit, so treat it as an estimate): TinyTeX-1 equivalent about 53 MB download, about 0.21 GB installed; plus `make4ht tex4ht luaxml dvisvgm` about 57 MB / 0.28 GB; plus `standalone preview tikz-cd xypic pgf enumitem float mathtools` about 58 MB / 0.29 GB; plus `biber biblatex logreq` about 129 MB / 0.37 GB (biber's binary alone is 71 MB). Against: MacTeX.pkg 6.87 GB and BasicTeX.pkg 140 MB (Content-Length from https://mirror.ctan.org/systems/mac/mactex/), both system-wide `.pkg` installs that need an admin password, and BasicTeX's later `tlmgr install` needs sudo.
- Missing packages are not installed automatically outside R: the FAQ says to find them with `tlmgr search --global --file` and `tlmgr install` (https://yihui.org/tinytex/). Loom would do that itself: read `! LaTeX Error: File `x.sty' not found` from the log (loom already collects `^! ` lines, `src/tex/runner.py:283-286`), ask `tlmgr search --global --file /x.sty`, install, recompile once. MiKTeX does this natively, but MiKTeX is a different TeX4ht and a different path.
- The yearly freeze: after TL 2027 is released, a TL 2026 tlmgr refuses the live repository ("Remote repository is newer than local", https://yihui.org/tinytex/faq/ FAQ 11); the frozen year stays installable from the historic archive's `tlnet-final` (https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2025/web/acquire.html). For a pilot that starts now, TL 2026 is live until about March 2027; after that loom pins its tlmgr to the 2026 `tlnet-final` or moves everyone to 2027 together in a loom update.

**Recommendation for v0.1: loom's own TeX, always, in a per-user directory loom owns** (for example `~/Library/Application Support/loom/tex`), TL 2026, TinyTeX-1 plus loom's list (about 60 MB download, 0.3 GB on disk, a few minutes), missing packages fetched on demand, and the person's TEXMFHOME still read (loom already passes it, `src/tex/tex4ht.py:638-656`). Use the person's own TeX only behind a setting. This gives every pilot the TL year CI tests, needs no admin, no Homebrew and no 6.9 GB download, and works the same on Linux; on Windows it is the same bundle. Effort for agents: provisioning (in the install script) hours; `src/tex/private.py` that finds loom's TeX and puts its `bin/` first on `os.environ["PATH"]` at startup, hours; on-demand package install in the compile path with a test, a day; a "Repair TeX" action and doctor's view of it, hours. Independent of the rest: it owns a new `src/tex/private.py` and `src/tex/missing.py`, and touches `src/tex/runner.py` (retry) and `src/doctor.py`. The author must accept the policy and run it once on a clean Mac.

### INST-6 · Tools are found through PATH only · hurts · hours · rec fix
Every lookup is `shutil.which` (`src/doctor.py:366`, `src/tex/runner.py:134`, `src/tex/tex4ht.py:358,438,525`, `src/render/assets.py:44-51`, `src/records/crops.py:167`, `src/tex/identity.py:41,65`). Apps started from Finder, the Dock or Spotlight get launchd's environment, not the shell's, so `/Library/TeX/texbin` and `/opt/homebrew/bin` are absent (https://eclecticlight.co/2020/12/10/controlling-processes-and-environments/). The same holds for `loom mcp` started by the Claude or ChatGPT desktop app from the absolute command loom writes (`src/ai/clients.py:94-110`). The failure is silent: loom simply shows source. Fix with INST-5's `private.py`: at startup put loom's TeX, then known TeX and Homebrew locations, first on PATH.

### INST-7 · git on a fresh Mac is a shim that opens an installer · hurts · hours · rec fix
On a Mac without the Command Line Tools, `/usr/bin/git` exists and running it asks to install the tools (https://developer.apple.com/documentation/xcode/installing-the-command-line-tools). `shutil.which("git")` finds it, and loom runs it on the serve path when no author is configured (`src/scan/quilt.py:214-229`), when drawing ids (`src/scan/alloc.py:32-55`), in doctor's probe, and for adopt's merge (`src/adopt.py:156`). `uv tool install git+…` also needs a working git (uv's `GitNotFound` error, https://docs.rs/crate/uv-git/latest/source/src/git.rs). Fix: install loom from a release wheel (no git), and on macOS treat git as absent when `xcode-select -p` fails, so loom never triggers the dialog; ask for the tools only when a pilot reaches sync or adopt. The exact first-run behaviour needs the author's check on a clean Mac.

### INST-8 · poppler has no brew-free route on a Mac · hurts · days · rec fix or defer
Uses listed in section 1. The only remedy loom gives is `brew install poppler` (`src/doctor.py:39`), and a fresh Mac has no Homebrew. Option: replace the three programs with `pypdfium2` (5.15.2, 2026-11-09, BSD-3/Apache-2.0, wheels for macOS 13+ arm64/x86_64, Windows, Linux; text extraction, bounded text and rendering to bitmaps, https://pypi.org/project/pypdfium2/; per-character boxes through PDFium's raw API, unverified in pypdfium2's helpers). Effort 2-4 days, independent: owns `src/refs/pages.py`, `src/tex/identity.py`, `src/records/crops.py` and doctor's TOOLS rows; risk is matching `-bbox-layout` word geometry the marks rely on. If deferred, v0.1 states poppler as optional, and papers that arrive as arXiv source are unaffected.

## 3. Overleaf

### INST-9 · What exists today · blocks the Overleaf pilot · rec fix
- The model is the reverse of the pilot's: the quilt is the truth and the Overleaf project is a "document workspace" coauthors edit, which loom publishes to and fetches from (`src/sync.py:1-4`).
- Pairing is CLI only and takes a clone, not a link: `loom sync init DIR` refuses a URL and tells the person to `git clone` first (`src/sync.py:456`), and refuses many directory shapes (`src/sync.py:362-429`). The quilt must already hold the document as its default master (`src/sync.py:464-468`).
- Fetch is CLI only: the write API serves `sync-preview` and `sync-incorporate` but no fetch or pair (`src/render/api.py:23-71`, handler `:746-787`). Incorporate applies the fetched diff as a patch to the quilt's own copies, hunk by hunk (`src/sync.py:629-681`), stamping a landmark per reached document first (`src/sync.py:801-808`).
- Credentials are not handled: loom runs plain `git fetch` (`src/sync.py:493-505`); under a launcher there is no terminal for git's prompt.
- It has never run against real Overleaf: WQ-16 is "a manual procedure requiring an Overleaf account… blocked since M7" (`docs/work-queue/WQ-16-overleaf.md`).

Overleaf facts for the readme (checked today):
- Git integration, GitHub sync and Dropbox sync are premium; the free plan has none of them. "If the project is owned by a user with a premium subscription, all members of the project can git clone/push/pull to it" (https://docs.overleaf.com/getting-started/free-and-premium-plans/premium-features).
- Clone URL `https://git.overleaf.com/<project id>`; one branch (`main`), no tags, no LFS, symlinks become files, a rename is a delete and a create, and "pushes can result in the loss or displacement of track changes and comments"; automated polling can be rate limited (https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration).
- Authentication: username `git`, a token as the password; tokens are made in Account Settings or the project's Git dialog, one token serves all projects, at most 10, they expire after one year, and Overleaf recommends a credential helper (https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration/git-integration-authentication-tokens).
- Without git access the person copies and pastes text between Overleaf and their local files by hand, and loom does nothing special for that (the author's decision); see INST-12. Each project picks its TeX Live year; new projects default to the latest (2026) (https://docs.overleaf.com/getting-started/recompiling-your-project/selecting-a-tex-live-version-and-latex-compiler).

### INST-10 · The smallest Overleaf flow, built on the present sync · blocks the Overleaf pilot · days (4-6) · rec fix
A quilt whose document is a read-only mirror of one Overleaf project:

1. New quilt from an Overleaf link: the person pastes `https://www.overleaf.com/project/<id>`; loom derives `https://git.overleaf.com/<id>`, asks once for the token and stores it in the Keychain (feed it to git through `GIT_ASKPASS` or the `osxkeychain` helper, never on a command line), clones into a directory inside the quilt (allowed, and skipped by every walker, `src/sync.py:191-197`), copies the tree into the document directory, picks the main file (Overleaf's main-file setting is not in git: choose the file with `\documentclass` and `\begin{document}`, prefer `main.tex`, ask when ambiguous), writes `[quilt] main`, and calls the existing `configure` (`src/sync.py:432-490`). New code: an API endpoint and a small form.
2. Update: a "Update from Overleaf" button, and a fetch when the quilt opens, never a background poll (Overleaf rate limits polling). It runs the existing `fetch` then `incorporate` without the review token, which the API already allows (`src/render/api.py:766-783`). For a mirror the honest semantics is "take theirs": since nothing local is meant to change, replace files with the fetched tree rather than apply a patch, so a stray local edit cannot block every later pull. The stamp before the pull stays: it keeps the old text that annotations were written on.
3. Reading and AI feedback: unchanged from any quilt; agents annotate and suggest through MCP.
4. Edits by hand in Overleaf, then Update.

Hide for v0.1: `sync publish` and `--push`, `sync documents`, the publication ref and revisions list, and the incoming review's accept step (keep its "what changed since the last pull" diff, which is useful reading). Change on mirrored documents: Keep on a suggested edit must not write the file (`src/records/edits.py:460-477` applies it), because the local copy would then differ from Overleaf and, under patch semantics, the next pull fails at `git apply` (`src/sync.py:672`); offer "Copy new text" and "Done in Overleaf" instead. Loom already computes when a suggested edit's block "reads as it taken already" (`src/records/edits.py:5,477`), so after the person makes the edit in Overleaf and updates, the suggestion can close itself. Publishing must stay hidden for a second reason: an Overleaf push can lose that project's comments and tracked changes.

Effort: pairing from a link with Keychain token, a day; fetch endpoint and button, hours; mirror semantics and Keep change, a day; main-file detection, hours; UI, a day; tests with a local bare repo standing in for Overleaf, a day. Ownership: `src/sync.py`, `src/cli/sync.py`, new endpoints in `src/render/api.py` (shared with INST-16: one agent should own api.py's dispatch or they serialise), and the arras sync and suggested-edit components. The author must run it against a real premium Overleaf project with the pilot's kind of paper (this is WQ-16).

### INST-11 · Annotations when the text changes underneath them · hurts · days (2-3) · rec fix
This holds for any change loom did not make: a pull from Overleaf, text pasted in by hand, an agent editing in place. Only loom-shaped labels make a stable key (`src/scan/labels.py:33-40`); a mathematician's `\label{thm:main}` does not, so the theorem's key is `paper/main.tex#theorem:3` (`src/scan/nodes.py:362-371`) and a section's `file#name:ordinal` (`src/scan/nodes.py:426-428`). What happens to an annotation, by case:

- Its block keeps its key and its quoted words still stand: it stays where it was; the quote selector resolves inside the block.
- Its block moved (a block was put in before it) but its text is unchanged and unique in the file: the record follows it to the new position (`src/records/store.py:122-150`).
- Its quoted words are gone from its block: it is shown "gone", as an empty mark at the aligned point in the new text, beside the old words loom kept (`src/render/versions.py:118-172`). The old text is kept by every rebuild for each annotated key that moved (`src/records/lastseen.py:68-71`, called at `src/render/build.py:429`), so this works for hand edits too, not only after a pull's stamp (`src/sync.py:801-808`).
- Its block moved and was also edited (a pull that inserts a theorem earlier and changes the annotated one): the record stays on the old position, so it lands on the wrong theorem if its words happen to be there, and is otherwise shown gone against the wrong block's text.
- The file was renamed: the path is part of every position key, so every such annotation on that file is detached.

Fix: treat any `\label` on a block as a stable key, and on a miss look for the record's quote with its prefix and suffix across the whole file before calling it gone. Owns `src/scan/nodes.py`'s key rule and `src/records/store.py:written_on`; needs care because keys are referenced in every record.

### INST-12 · No Overleaf path without git · irrelevant · rec remove
Considered and declined: importing a downloaded Overleaf source zip, replaced on each update. The author's choice is that a person without git access copies and pastes text by hand, which loom already handles as ordinary edits to local files (INST-11 describes what happens to annotations), so nothing is built.

### INST-13 · Overleaf's PDF instead of local TeX · irrelevant as a design · rec remove
There is no documented way to fetch the compiled PDF: Overleaf's source download excludes it and the PDF download is a button in the editor (https://docs.overleaf.com/managing-projects-and-files/downloading-a-project); git carries the project's files only. A person could download the PDF and drop it in, and loom would show it with PDF marks, but a PDF anchor names the artifact by its hash (`src/anchors.py:3`), so marks on today's PDF do not carry to tomorrow's download; the text view, source-anchored annotations and suggested edits still need the source, which without TeX shows raw (INST-3). With a 60 MB private TeX (INST-5) there is no reason to design this path.

## 4. Platforms

### INST-14 · Windows · blocks Windows · a week or more · rec defer
Present: a Windows file lock (`src/locks.py:26-43`), `loom.exe` in the MCP command (`src/ai/clients.py:97`), the Windows Claude Desktop config path (`src/ai/clients.py:62`). Blockers:
- `os.killpg` is POSIX only (https://docs.python.org/3/library/os.html#os.killpg) and is how every compile and TeX4ht run is stopped on timeout or cancel (`src/tex/runner.py:303-314`, used by `src/tex/tex4ht.py:22,478`) and how doctor kills a hung probe (`src/doctor.py:276`); `start_new_session` does nothing there.
- `os.kill(pid, 0)` is the "is the server alive" probe (`src/render/serve.py:184-190`); on Windows any signal other than CTRL_C_EVENT/CTRL_BREAK_EVENT terminates the process, and 0 is CTRL_C_EVENT, which is sent to a console process group (https://docs.python.org/3/library/os.html#os.kill). Either way it is not a liveness check.
- Opening files and apps is refused on Windows (`src/files.py:465-479`); `os.startfile` would do.
- About 60 file and subprocess text calls without an explicit encoding (20 `read_text()`, 21 `write_text(` without `encoding=`, 18 `text=True` without encoding, counted by grep under `src/`) use the ANSI code page on Windows; a launcher setting `PYTHONUTF8=1` covers them.
- Replacing files and directories that the HTTP threads may hold open (`os.replace` in `src/render/publish.py:39`, `src/records/store.py:450`; directory renames in `src/tex/tex4ht.py:423-425`) raises `PermissionError` on Windows when a reader has the file open; needs retries, found only by running there.
- `latexmk` needs Perl; TeX Live/TinyTeX on Windows carry one, MiKTeX does not (from TeX Live's design; unverified for TinyTeX's Windows bundle).
- The unit tier cannot run on Windows: the fake TeX is extensionless scripts with a shebang (`loom/tests/conftest.py:18-35,55-60`), so a Windows CI job first needs a `.exe`/`.cmd` shim.
Effort: shim and a windows-latest job, a day; process control and liveness, hours; open, hours; encoding, hours with the launcher; file-replacement races and whatever the job then finds, days; PowerShell installer and TinyTeX on Windows, a day. Independent of the Mac work except the launcher. The author must test on a real Windows machine; distributing an unsigned `.exe` also meets SmartScreen, and signing costs about $9.99/month (Azure Artifact Signing, individuals in the USA and Canada only) or a $150-300/year certificate, neither of which gives immediate SmartScreen trust (https://learn.microsoft.com/windows/apps/package-and-deploy/code-signing-options). Recommendation: no Windows in v0.1 unless a pilot needs it; add the Windows CI job early anyway, since it is cheap and tells the truth.

### INST-15 · Linux is in CI, macOS is not · hurts · hours · rec fix
CI runs the unit tier on Ubuntu for 3.11-3.13, the TeX tier in a TeX Live container, and an install-from-clone job that starts `loom serve` (`.github/workflows/loom.yml:13-96`). Nothing runs on macOS, the pilots' platform, so the Mac paths (`open`, osascript, Keychain, universal-darwin TeX, launchd PATH) are tested only on the author's machine with TL 2024. Add a `macos-latest` job: unit tier, plus install from the built wheel and the install script with the private TeX and a smoke `loom serve`. Linux needs only the install script's Linux branch and a `.desktop` file for v0.1 (hours).

## 5. Launching and quilts

### INST-1 · No launcher · blocks · days (3-4) · rec fix
What `loom serve` assumes: it must find a quilt by walking up from the current directory or `--quilt` (`src/cli/serve_cmd.py:33`, `src/scan/quilt.py:169-191`); one server per quilt, refusing a second (`src/cli/serve_cmd.py:41-44`); port 8791 by default, failing if busy (`src/render/serve.py:32`, `src/cli/serve_cmd.py:16,49-54`); opens the browser only with `--open` (`src/cli/serve_cmd.py:17,54-55`); every handler is bound to that one quilt root (`src/render/serve.py:851-876`). Port 0 already works (the bound port is read back, `src/render/serve.py:872-873`). A terminal is needed to stop it.

What each wanted action needs:

| action | exists | missing |
|---|---|---|
| one launch with no quilt chosen | nothing | a `loom app` home server on a fixed port: a page with recent quilts, Open, New; it starts one `loom serve` child per quilt and redirects the tab to it |
| recent quilts, "open a folder" | nothing (no registry anywhere) | `~/.config/loom/quilts.json` (honouring `XDG_CONFIG_HOME`); a browser cannot give a folder's path, so the server asks the OS: `osascript -e 'POSIX path of (choose folder)'` on macOS, `zenity`/`kdialog` on Linux |
| new quilt, optionally with a paper or an Overleaf link | `loom init`, `loom init --from FILE`, `loom import` (CLI only, interactive prompts, `src/cli/quilt.py:87,105`) | an endpoint that runs init non-interactively (`--yes --ai` equivalents), writes the agent files, then imports a dropped paper (INST-16) or pairs Overleaf (INST-10) |
| drag further resources in | PDF into the library's Add dialog only (INST-16) | window-level drop |
| stay running, restart cleanly after an update | the server notices it is stale (`src/render/serve.py:209-228`) and the viewer says "restart" (`arras/src/lib/outOfStep.svelte.ts:1-35`) | the home server restarts its stale children itself; an Update button runs the updater and restarts |

Effort for agents: home server, registry, choose-folder, child supervision with stable ports, restart, about three days; the home page as plain server-rendered HTML avoids touching arras. Owns new `src/cli/app_cmd.py` and `src/app/`; touches `src/cli/serve_cmd.py` only to accept a no-browser, assigned-port mode it already nearly has. Independent of INST-10/16 except that "new quilt with X" calls their endpoints.

### INST-16 · Dragging resources in · hurts · days (2-3) · rec fix
Today: paste an identifier or drop a PDF inside the library's Add dialog (`arras/src/lib/components/AddWork.svelte:255-270`), served by `library-upload`/`library-file` (`src/render/api.py:223-276`); a paper's .tex or a project folder can only come in through `loom import` on the CLI. In a browser a drop gives file contents, never paths, so dropping is copying: a window-level drop zone that sends PDFs to the existing library flow, a `.tar.gz` or `.zip` source archive (as arXiv serves a paper) or a folder (read with `webkitGetAsEntry`) to a new endpoint that unpacks into the quilt and runs the import logic, and a lone `.tex` the same. Owns a new arras drop component and one endpoint in `src/render/api.py`; reuses `src/refs/add.py` and the import code.

### INST-17 · Restart after update is manual · hurts · in INST-1 · rec fix
See the table above; with a supervisor the "restart" message becomes an automatic restart and a reload.

### INST-18 · Ports must be stable per quilt · cosmetic · hours · rec fix
Viewer preferences and workspace layout are in localStorage (`arras/src/lib/prefs.svelte.ts:2,92-101`, `arras/src/lib/workspace/remember.ts:10`), which is per origin, port included. Random ports would reset them every launch; two quilts on the same port would share them. The registry should give each quilt its own remembered port.

### INST-23 · Opening the quilt in the agent app · hurts · hours to a day · rec fix
`loom ai init` writes per-quilt MCP files with loom's absolute path for both pilot apps' engines: `.mcp.json` for Claude Code and `.codex/config.toml` for Codex (`src/ai/clients.py:55-56,94-110`), and doctor warns when they are missing (`src/doctor.py:507-555`; the showcase copy warned). New-quilt should write them without asking. Opening the app on the quilt does not exist: `open -a APP` is allowed only without a file (`src/files.py:478-483`); `open -a "Claude" DIR` or the ChatGPT app's equivalent may or may not open the folder in the Code tab or in Codex (unverified; the author must try both apps). Minimum: a button that opens the app and copies the quilt's path, with one line saying where to paste it. The MCP server those apps start inherits launchd's PATH (INST-6).

## 6. Packaging

### INST-19 · Options ranked for v0.1

| rank | option | build effort (agents) | person installs | person updates | what breaks | author-only |
|---|---|---|---|---|---|---|
| 1 | (b) install script from a GitHub release: installs uv to `~/.local/bin` (https://docs.astral.sh/uv/getting-started/installation/), `uv tool install --managed-python --python 3.13 <release wheel URL>` (no git; `--managed-python` avoids the system Python shims, https://docs.astral.sh/uv/concepts/python-versions/), the private TeX (INST-5), and writes `~/Applications/Loom.app`, a script bundle that runs `loom app`, then opens it | a day for the script and a release workflow building the wheel; the `.app` is a dozen lines | pastes one line in Terminal once; then Loom is in Applications and the Dock | an Update button in loom home runs `uv tool install --force <latest wheel URL>` and restarts; TeX updates are loom's (`tlmgr` within the pinned year) | needs network; Terminal once; a person who refuses curl-pipe-sh can read the script | cut releases (publishing is the maintainer's, `loom/docs/RELEASE.md:3`); run it on a clean Mac (VM or a fresh user account; only a VM shows the Command Line Tools case) |
| 2 | (a) one line with uv: `uv tool install git+https://github.com/ikmartin/loom-arras#subdirectory=loom` (subdirectory syntax, https://docs.astral.sh/uv/concepts/projects/dependencies/) plus `loom app` | hours (it is the README) | installs uv, then this line; needs git, so the Command Line Tools on a fresh Mac (INST-7); TeX separately | `uv tool upgrade loomtex`, whose behaviour for a git source is not documented (https://docs.astral.sh/uv/concepts/tools/, unverified) | git prompt, TeX left to the person, several commands | none beyond a clean-machine check |
| 3 | (d) a Mac window around the server with pywebview (6.2.1, BSD-3, pure wheel; WKWebView through pyobjc on macOS, WebView2 on Windows, GTK or Qt on Linux; https://pypi.org/project/pywebview/, https://pywebview.flowrl.com/guide/installation.html), launched by the same local Loom.app | 1-2 days on top of INST-1 | as rank 1 | as rank 1 | a webview lacks browser tabs and find-in-page unless added; gains real paths on drop (`pywebviewFullPath`, https://sources.debian.org/src/python-pywebview/6.1%2Bdfsg-1/examples/drag_drop.py) and native dialogs | as rank 1 |
| 4 | (d') a downloadable, self-contained, signed and notarised Loom.app (bundled Python and deps via PyInstaller or Briefcase, TeX downloaded on first run) | 1-2 weeks: bundling 29 packages with Rust wheels, signing every Mach-O, notarisation in CI | downloads a .dmg, drags to Applications | Sparkle-style updater or re-download | unsigned: Sequoia blocks it; the person must try, then go to System Settings › Privacy & Security › Open Anyway (Control-click no longer works, https://appleinsider.com/articles/24/08/06/apple-removes-control-click-option-for-skipping-gatekeeper-in-macos-sequoia) | enrol in the Apple Developer Program ($99/year, https://developer.apple.com/programs/), create a Developer ID certificate, put notarisation credentials in CI |
| 5 | (e) Linux | hours: the script's Linux branch and a `.desktop` file | as rank 1 | as rank 1 | `zenity`/`kdialog` may be absent for the folder dialog | test on one distribution |
| 5 | (e) Windows | a week or more (INST-14) plus a PowerShell installer | `irm … \| iex` | as rank 1 | INST-14 | a Windows machine; signing for SmartScreen |
| 6 | (c) Homebrew tap | days | needs Homebrew, hence the Command Line Tools, first | `brew upgrade` | a tap formula vendors all 29 Python resources and, without bottles, builds `pydantic-core` and `rpds-py` from Rust on the person's machine | maintain the tap |

### INST-20 · Signing · hurts only for a downloaded app · rec keep the local launcher, defer signing
Gatekeeper checks quarantined files, and curl and other Unix tools do not set the quarantine attribute (Apple DTS, https://developer.apple.com/forums/thread/666452; https://eclecticlight.co/2020/10/29/quarantine-and-the-quarantine-flag/). A Loom.app that the install script writes on the person's machine is therefore never quarantined and needs no signature; it contains a shell script, not unsigned native code. This is the cheapest way to "an application you launch" on a Mac, and it costs no money and no Apple account. A signed, notarised download is rank 4 and can follow v0.1.

### INST-21 · Homebrew tap · irrelevant · rec remove (as an option)
See rank 6. It adds Homebrew and the Command Line Tools as prerequisites, which the install script avoids.

### INST-2 · No installable release; the install docs are wrong · blocks · hours + a day · rec fix
`loom/README.md:13-35` installs with `pipx install git+https://github.com/ikmartin/loom`, a repository that does not exist (GitHub answers "Could not resolve to a Repository"); `loom/pyproject.toml:27` names the same URL; it lists `brew install --cask mactex-no-gui` (5-7 GB) as the TeX route and describes `canon/`, `loom canonize` and `loom digest extract`, which are gone. The root `README.md:30-38` installs editable from a clone. There is no GitHub release, wheel or tag. Fix: a release workflow building `loomtex` with `uv build` and attaching the wheel and `install.sh` to a GitHub release; rewrite both READMEs' install sections to the one line. Owns `.github/workflows/release.yml`, `scripts/install.sh` (new), the README sections.

### INST-22 · doctor speaks to developers · hurts · hours · rec fix
Remedies are `brew install --cask mactex-no-gui`, `brew install poppler`, `brew install git` or apt lines (`src/doctor.py:34-41`), and a missing `latexmk` is a hard failure with exit 2 (`src/doctor.py:76-79,381-384`). With loom's own TeX the remedy becomes "Repair TeX" in the app, and doctor should report which TeX loom uses and its year. The `git` row should name adopt (`src/doctor.py:110-115`). Doctor also warns on the vendored bundle's `-dirty` stamp in a checkout (`src/doctor.py:455-460`; seen in the hand check), which a pilot never sees from a wheel.

## 7. The first ten minutes

### Today, a new Mac user with no TeX, following the READMEs
1. Open Terminal (decision: knows how).
2. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`; open a new terminal or source its env (2 commands).
3. `git clone https://github.com/ikmartin/loom-arras` → the Command Line Tools dialog (decision; a several-minute download); run the clone again (1-2 commands).
4. `cd loom-arras`, `uv tool install -e ./loom` (2); perhaps `uv tool update-shell` and a new terminal (1, decision).
5. `loom doctor` (1): fails on latexmk, pdflatex, dvisvgm; says `brew install --cask mactex-no-gui`. There is no Homebrew (decision: install Homebrew with its own one-line script and admin password, or download MacTeX.pkg, 6.87 GB, from CTAN and run the installer with an admin password). Then `brew install poppler` (2-3 commands, an admin password, 30-60 minutes of download).
6. `loom init mypaper --from ~/path/main.tex` (1), answering the id-prefix and AI questions (2 decisions).
7. `cd mypaper`, `loom serve --open` (2).
8. Set the reviewer name in the viewer's Settings (decision).
9. For agents: `loom ai init` (1), then open the folder in the Claude desktop app's Code tab or in Codex (decision).

About 13-16 typed commands, 7-8 decisions, 2 admin passwords, roughly an hour, most of it TeX. Skipping TeX gives the raw-source viewer.

### Under the recommended v0.1
1. Open Terminal and paste the one line from the README: it installs uv, loom from the release wheel, loom's TeX (about 60 MB, a few minutes, no password), writes Loom.app and opens it (1 command).
2. Loom's home page asks for the reviewer name once (decision).
3. New quilt: choose a folder in the native dialog, and either drop a paper (a .tex, a source archive or a PDF) or paste an Overleaf project link and the git token (2 decisions).
4. The quilt opens and compiles; its agent files are already written. "Open in Claude" or "Open in Codex" opens the app with the path to hand (decision).
5. Afterwards: Loom from the Dock; updates from a button.

One typed command, 4 decisions, no admin password, about five minutes.

## Recommended v0.1 path

In build order; items on the same line can run in parallel on separate files.

1. Release and install (INST-2, INST-19 rank 1, INST-7): release workflow and wheel; `scripts/install.sh` with uv, `--managed-python`, the wheel URL, the private TeX and Loom.app; README one-liner. A day. In parallel: macOS CI job (INST-15), hours.
2. Loom's own TeX (INST-5, INST-6, INST-22): `src/tex/private.py` (find and prepend), on-demand package install, doctor rows, pin CI's container to 2026. 2-3 days. Independent of 1 except that the script calls loom to provision.
3. `loom app` home and supervisor (INST-1, INST-17, INST-18, INST-23's file writing): 3-4 days. Owns `src/app/`, `src/cli/app_cmd.py`.
4. In parallel with 3: drop zone and import endpoint (INST-16), 2-3 days; and the Overleaf mirror over git (INST-10), 4-6 days. These two share `src/render/api.py`'s dispatch, so one agent owns that file's edits or they land in sequence.
5. Stable keys for mirrored documents (INST-11), 2-3 days, after 4.
6. Optional: pypdfium2 in place of poppler (INST-8), 2-4 days, independent; pywebview window (rank 3), 1-2 days, after 3.

Author-only: cut the release; run the install on a clean Mac (a VM, so the no-Command-Line-Tools case is real); test the Overleaf flow on a premium project (WQ-16) and record Overleaf's TL year; try "open this folder" in the Claude desktop app's Code tab and in ChatGPT's Codex; decide TL 2026 as the pilot's TeX.

State as prerequisites rather than solve: macOS 13 or later on Apple Silicon or Intel (pypdfium2's floor, if adopted; TeX and uv go lower); a Terminal paste once; network during install and for missing packages; Overleaf git access for live Overleaf updates (the project's owner on a premium plan; otherwise the person copies text by hand and loom does nothing special); poppler via Homebrew for PDF-only library papers if INST-8 is deferred.

Defer: Windows (INST-14) unless a pilot needs it, but add its CI job; a signed, notarised downloadable app (INST-19 rank 4); a Homebrew tap (remove); publishing to Overleaf from loom (hide); the multi-quilt server refactor (the supervisor makes it unnecessary).

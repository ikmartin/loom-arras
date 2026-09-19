# Example quilts

- `demo/`: exactly what `loom init --demo` writes in the current release. Committed.
- `synthetic/`: the quilt that exercises every construct of the source contract and generates the conformance fixture in `docs/specs/fixture/`. Committed.
- `showcase/`: the quilt to open when you want to see what loom does. An invented paper about balanced flows on finite quivers, two invented cited works with committed PDFs, a digest extracted from a source and a second built from verified proposals, annotations of every kind, severity and state, two runs and one discarded, a landmark history with a stamp, a fork and a revert, and the three faults a quilt can be left in. Committed, PDFs and all. Regenerate it after a feature lands: that is what keeps it a picture of loom today.
- `relloc/`, `man12/`, `acgs/`, `mmp/`, `kpsv/`: quilts built from real papers. Gitignored, because they contain the paper sources.

`build.py` rebuilds all of them. The three committed quilts come from `loom/scripts/gen_quilts.py`, which writes them by running loom's own commands on the source files under `loom/tests/quilts/sources/` — so they are what loom ships, and a test proves it (book 14.3). It then compiles and publishes the showcase, so that `demos/showcase/build/` is there to open, and refreshes the conformance fixture and vendors it into both tool repositories.

The showcase alone commits the PDFs in its store (DR-194). Every cited work in it is invented and compiled from LaTeX in this repository by `loom/tests/quilts/sources/showcase-works/build.sh`, so the bytes are ours to publish, and committing them is what lets a fresh clone open the viewer with every `cited:` locator resolving to the page it names. Its own `.gitignore` carries the negation that makes that possible; no other quilt should.

The paper quilts are rebuilt by running the commands an author runs:

```
loom init demos/man12 --from tests/fixtures/0805.2065/virtual6.tex --prefix man --yes
loom draft canon/virtual6.tex --to drafting/main.tex --fix-anchoring --yes --quilt demos/man12
loom atomize drafting/main.tex drafting/main-atomic.tex --sections --quilt demos/man12
loom canonize drafting/main-atomic.tex --to canon/virtual6-v1.tex -m "Atomized" --quilt demos/man12
loom compile --quilt demos/man12
```

Every one of them runs with an empty `HOME`, empty TeX trees, and a `PATH` holding only loom, TeX Live and poppler, so that a compile can read nothing but the quilt and the distribution: a macro defined somewhere else on the machine cannot make one of these work.

Each quilt holds **one definition of each node**. `nodes/` has the nodes, `drafting/main-atomic.tex` is the spine that includes them, and the history records that the spine superseded `drafting/main.tex`, so that file defines nothing until `loom live` says otherwise (book 17.12). Several documents in `drafting/` are welcome — they are different arrangements over the same nodes, as `synthetic/` shows with `main.tex` and `talk.tex` — but two live files defining one id leave that id conflicted, with no text, and `loom lint` says so.

`python demos/build.py --skip-papers` stops after the committed quilts and the fixture, which is what a machine without the paper sources can do. The showcase needs poppler, because `loom refs scan` reads the page text of the two PDFs it files; it does not need TeX, and without TeX it is published uncompiled, with citations showing their keys rather than `[Ard24]`.

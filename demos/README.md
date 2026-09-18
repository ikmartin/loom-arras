# Example quilts

- `demo/`: exactly what `loom init --demo` writes in the current release. Committed.
- `synthetic/`: the quilt that exercises every construct of the source contract and generates the conformance fixture in `docs/specs/fixture/`. Committed.
- `relloc/`, `man12/`, `acgs/`: quilts built from real papers. Gitignored, because they contain the paper sources.

`build.py` rebuilds all of them. The two committed quilts come from `loom/scripts/gen_quilts.py`, which writes them by running loom's own commands on the source files under `loom/tests/quilts/sources/` — so they are what loom ships, and a test proves it (book 14.3). It then refreshes the conformance fixture and vendors it into both tool repositories.

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

`python demos/build.py --skip-papers` stops after the committed quilts and the fixture, which is what a machine without the paper sources can do.

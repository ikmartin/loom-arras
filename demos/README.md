# Example quilts

- `demo/`: exactly what `loom init --demo` writes in the current release. Committed.
- `synthetic/`: the proof-of-concept quilt that exercises every construct of the source contract and generates the conformance fixture in `docs/specs/fixture/`. Committed.
- `relloc/`, `man12/`, `acgs/`, `scratch-*/`: quilts built from real papers. Gitignored because they contain the paper sources.

`refresh.sh` regenerates `demo/` and `synthetic/` from the loom checkout beside this directory so that these copies never drift from what loom ships. Run it after any milestone that changes loom's demo assets or the synthetic quilt.

`hermetic.sh` runs a loom command with an empty HOME and empty TEXMF trees, so a compile can read only the quilt, TeX Live, and poppler. The paper quilts are built with it:

```
demos/hermetic.sh loom init demos/man12 --from tests/fixtures/0805.2065/virtual6.tex --prefix man --no-git --yes --fix-anchoring
demos/hermetic.sh loom init demos/acgs --from tests/fixtures/1709.09864/decomposition-formula.tex --prefix acgs --no-git --yes --fix-anchoring
demos/hermetic.sh loom init demos/relloc --from tests/fixtures/relloc/draft3.tex --prefix rl --no-git --yes --fix-anchoring
```

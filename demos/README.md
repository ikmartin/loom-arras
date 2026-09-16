# Example quilts

- `demo/`: exactly what `loom init --demo` writes in the current release. Committed.
- `synthetic/`: the proof-of-concept quilt that exercises every construct of the source contract and generates the conformance fixture in `docs/specs/fixture/`. Committed.
- `relloc/`, `man12/`, `acgs/`, `scratch-*/`: quilts built from real papers. Gitignored because they contain the paper sources.

`refresh.sh` regenerates `demo/` and `synthetic/` from the loom checkout beside this directory so that these copies never drift from what loom ships. Run it after any milestone that changes loom's demo assets or the synthetic quilt.

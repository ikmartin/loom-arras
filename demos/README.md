# Example quilts

- `demo/`: exactly what `loom init --demo` writes in the current release. Committed.
- `synthetic/`: the proof-of-concept quilt that exercises every construct of the source contract and generates the conformance fixture in `docs/specs/fixture/`. Committed.
- `relloc/`, `man12/`, `acgs/`, `scratch-*/`: quilts built from real papers. Gitignored because they contain the paper sources.

`refresh.sh` regenerates `demo/` and `synthetic/` from the loom checkout beside this directory so that these copies never drift from what loom ships. Run it after any milestone that changes loom's demo assets or the synthetic quilt.

`hermetic.sh` runs a loom command with an empty HOME and empty TEXMF trees, so a compile can read only the quilt, TeX Live, and poppler. The paper quilts are built with it:

```
demos/hermetic.sh loom init demos/man12 --from tests/fixtures/0805.2065/virtual6.tex --prefix man --yes --fix-anchoring
demos/hermetic.sh loom init demos/acgs --from tests/fixtures/1709.09864/decomposition-formula.tex --prefix acgs --yes --fix-anchoring
demos/hermetic.sh loom init demos/relloc --from tests/fixtures/relloc/draft3.tex --prefix rl --yes --fix-anchoring
```

Each paper quilt holds **one definition of each node**: `nodes/` has the patches, `drafts/main.tex` is the spine that includes them, and the file the paper was imported as carries `% !LOOM ignore` so it stays for reference without defining anything a second time. Several masters are welcome — they are different arrangements over the same patches, as `synthetic/` shows with `drafts/main.tex` and `drafts/talk.tex` — but two files defining the same id are not, and produce a `duplicate-id` error per node. Round-trip artefacts (`loom inline` output, an atomized copy kept for comparison) belong in a scratch directory outside the quilt.

```
demos/hermetic.sh loom init demos/man12 --from tests/fixtures/0805.2065/virtual6.tex --prefix man --yes --fix-anchoring
demos/hermetic.sh loom atomize drafts/virtual6.tex drafts/main.tex --sections --ignore-src --quilt demos/man12
# then main = "drafts/main.tex" in config.toml, and loom compile so the numbering is known
```


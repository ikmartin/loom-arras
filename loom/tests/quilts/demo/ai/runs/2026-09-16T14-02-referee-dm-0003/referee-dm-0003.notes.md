## [summary]
Refereed `dm-0003` (Main). One objection on the proof: continuity of $(\mathrm{id},\sigma)$ into $X\times X$ is used but not stated (a-2026-09-16-0003). One suggestion on the statement: the finiteness hypothesis serves only the parity claim (a-2026-09-16-0002). The author decides whether to split the statement.

## [gaps-and-ambiguities]
- The map $(\mathrm{id},\sigma)\colon X\to X\times X$ is continuous because $\sigma$ is; the proof uses this without saying it. `file-verified` against the bundle. Annotation a-2026-09-16-0003.

## [worked-examples]
- $X=\{1,2,3\}$, $\sigma=(1\,2)$: orbits $\{1,2\}$ and $\{3\}$, so $\Fix(\sigma)=\{3\}$ and $|X|=3$ is odd. `proved-here`.
- $X=\{1,2\}$, $\sigma=(1\,2)$: no fixed point, $|X|=2$ even. `proved-here`.

## [counterexample]
None found. The parity argument is an orbit count and the closedness argument is the standard diagonal argument.

## [referee-review]
- Minor: the continuity of $(\mathrm{id},\sigma)$ (objection, proof, add one sentence, a-2026-09-16-0003).
- Clarity: the two claims have different hypotheses (suggestion, statement, split the theorem, a-2026-09-16-0002).

## [referee-revised]
Nothing rewritten; the fix is one sentence.

## [decision]
Minor Revision: the mathematics is correct; add the continuity sentence.

## Checklist
- [x] At least two worked examples with exact outputs.
- [x] Every objection is anchored and its id is in the notes.
- [x] [decision] cites the blocks above.
- [x] The diff, if any, compiles in a bundle. (no diff)
- [x] Nothing was written outside `$LOOM_RUN`.

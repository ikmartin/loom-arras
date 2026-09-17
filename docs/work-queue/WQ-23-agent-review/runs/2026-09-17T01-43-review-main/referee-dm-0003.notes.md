# Referee: dm-0003 (Theorem, Main)

[summary]
The parity statement is false as an equivalence: its "only if" fails already at $|X| = 2$. The proof's congruence is correct and proves a weaker, true claim; the error is in reading oddness as nonemptiness. The topological clause is true.

[gaps-and-ambiguities]
1. Statement, "is nonempty if and only if $|X|$ is odd": the only-if direction is false. Annotation a-2026-09-17-0001.
2. Proof, "which gives the parity statement": the congruence gives the parity of $|\Fix(\sigma)|$, not its nonemptiness. Annotation a-2026-09-17-0002.
3. Proof, the appeal to Proposition 3.2 of Man12: unclear whether a dependency or an analogy. Annotation a-2026-09-17-0003.

[worked-examples]
- $X=\{0,1,2\}$, $\sigma$ swapping 0 and 1: $\Fix(\sigma)=\{2\}$, $|X|=3$ odd, nonempty. Consistent with the statement.
- $X=\{0,1,2,3\}$, $\sigma=(0\,1)(2\,3)$: $\Fix(\sigma)=\emptyset$, $|X|=4$ even. Consistent with the statement.

[counterexample]
$X=\{0,1\}$, $\sigma=\mathrm{id}$. Then $\sigma^2=\mathrm{id}$, $\Fix(\sigma)=X$ is nonempty, and $|X|=2$ is even. The only-if direction fails. A brute force over every widget with $|X|\le 5$ finds 8 such cases; the congruence $|X|\equiv|\Fix(\sigma)|\pmod 2$ holds in all of them (referee-dm-0003.check.py, trial 1).

[referee-review]
- Major. Location: statement. The equivalence is false; only the forward implication holds. Fix: state the congruence and derive nonemptiness for odd $|X|$. (a-2026-09-17-0001)
- Major. Location: proof, first sentence. The step from congruence to the claim is unjustified. Fix: say what the congruence gives. (a-2026-09-17-0002)
- Minor. Location: proof, last clause. The citation's role is ambiguous and makes a postnote edge. Fix: decide whether it is a dependency. (a-2026-09-17-0003)

[referee-revised]
`proposal-dm-0003.diff` (since revised by simplify; this version is `.history/proposal-dm-0003.referee.diff`). Built with `loom bundle dm-0003 --with`.

[decision]
Major Revision. The statement as written is false, though the argument is sound and proves the corrected claim; the fix is local and does not disturb anything that depends on this theorem.

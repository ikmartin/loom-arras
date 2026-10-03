// What compare draws (book 15.2.6), computed from the two panes' nodes and nothing else: the pairs, which side holds the base, the marks, the wedges, and the differences stepped through. Pure, so its rules are tested without a browser; the drawing is CompareLayer's.
//
// **Two comparisons.** With a base — an agent document against its source, a landmark against today or another landmark — a pair that differs is drawn as git draws a diff: `−` on the side holding the base, `+` on the other, `~` in the stale amber when both changed since the base; a node only one side has is marked on every line with a wedge where the base places it in the other pane; a node moved unchanged between a copy and its source is `↕`. Without a base — two of the author's documents — a shared node is one node file and so the same text, and only presence (a dashed rule) and order (a dotted one) can differ.

/** One node a pane shows, in document order. */
export interface Found {
	/** The key with any derived id made plain: what pairs it. */
	pair: string;
	/** Its `data-hash`. */
	hash: string;
	/** Its key there, when the fragment carries one: a landmark's nodes carry none. */
	key: string | null;
	/** The number of the section it stands in, for "moved from §2". */
	section: string | null;
}

/** What compare knows of one pane's item. */
export interface Side {
	id: string;
	kind: 'document' | 'landmark' | 'node';
	/** How the tags name it: `talk.tex`, or a landmark's `widgets-v1 @1`. */
	name: string;
	/** A landmark's step. */
	step: number | null;
	/** An agent document's source document. */
	copyOf: string | null;
	/** Whether it is in the agent's drafting directory. */
	copy: boolean;
}

/** One side of a pair as the publisher answered it. */
export interface AnsweredSide {
	key: string;
	hash: string;
	/** Its rendering with the changed words marked, under the build directory; absent when no live node gives it context. */
	fragment?: string;
}

export interface AnsweredPair {
	pair: string;
	base: 'left' | 'right' | 'both' | null;
	left: AnsweredSide;
	right: AnsweredSide;
}

export interface Answer {
	left: { item: string; kind: string; macros: string | null };
	right: { item: string; kind: string; macros: string | null };
	pairs: AnsweredPair[];
}

export type MarkKind = 'del' | 'add' | 'both' | 'moved' | 'only' | 'order';

export interface Mark {
	kind: MarkKind;
	/** The quiet words after the node's label; '' for none. */
	tag: string;
	/** A second mark a changed node also carries: moved, or order differs. */
	also: 'moved' | 'order' | null;
	/** Marked on every line, rather than on the lines whose words changed. */
	whole: boolean;
}

/** A place in a pane where the other pane has a node this one lacks, or had one before a move. */
export interface Wedge {
	/** Stands after this pair's node; null at the document's head. */
	after: string | null;
	kind: 'del' | 'add' | 'moved';
	/** The pair it stands for. */
	pair: string;
}

export interface Difference {
	pair: string;
	/** Which panes draw the node itself; a pane that lacks it draws a wedge or nothing. */
	in: [boolean, boolean];
}

export interface Plan {
	based: boolean;
	marks: [Map<string, Mark>, Map<string, Mark>];
	wedges: [Wedge[], Wedge[]];
	differences: Difference[];
}

/** The pairs of `a` that a longest common subsequence with `b` keeps: the rest are the fewest nodes that explain the difference in order. */
export function lcs(a: string[], b: string[]): Set<string> {
	const n = a.length;
	const m = b.length;
	const t: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
	for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) t[i][j] = a[i] === b[j] ? t[i + 1][j + 1] + 1 : Math.max(t[i + 1][j], t[i][j + 1]);
	const keep = new Set<string>();
	let i = 0;
	let j = 0;
	while (i < n && j < m) {
		if (a[i] === b[j]) {
			keep.add(a[i]);
			i++;
			j++;
		} else if (t[i + 1][j] >= t[i][j + 1]) i++;
		else j++;
	}
	return keep;
}

/** Whether a key is an agent document's: its id carries the derived suffix. */
export function derived(key: string | null): boolean {
	return !!key && /-ai$/.test(key.split('/')[0]);
}

/**
 * What compare draws for two panes.
 *
 * Parameters
 * ----------
 * found : [Found[], Found[]]
 *     Each pane's nodes in document order.
 * sides : [Side, Side]
 *     The two items.
 * baseOf : (key: string) => string | null
 *     A derived node's base, as its `data-hash` would be: the manifest's `base.math`.
 * answer : Answer | null
 *     The publisher's answer, when one is serving; its directions win over those worked out here.
 *
 * Returns
 * -------
 * Plan
 *     The marks and wedges per pane, and the differences in the left pane's order.
 */
export function plan(found: [Found[], Found[]], sides: [Side, Side], baseOf: (key: string) => string | null, answer: Answer | null): Plan {
	const lists = found.map((f) => {
		const seen = new Set<string>();
		return f.filter((x) => (seen.has(x.pair) ? false : (seen.add(x.pair), true)));
	}) as [Found[], Found[]];
	const at = lists.map((l) => new Map(l.map((x) => [x.pair, x]))) as [Map<string, Found>, Map<string, Found>];
	const common = lists[0].filter((x) => at[1].has(x.pair)).map((x) => x.pair);
	const both = new Set(common);
	const copyRel = sides[0].copyOf === sides[1].id ? 1 : sides[1].copyOf === sides[0].id ? 0 : null; // the pane holding the source
	const landmarks = sides.map((s) => s.kind === 'landmark');
	const baseSide: 0 | 1 | null =
		copyRel !== null
			? copyRel
			: landmarks[0] && landmarks[1]
				? (sides[0].step ?? 0) <= (sides[1].step ?? 0)
					? 0
					: 1
				: landmarks[0]
					? 0
					: landmarks[1]
						? 1
						: sides[0].copy !== sides[1].copy
							? sides[0].copy
								? 1
								: 0
							: null;
	const based = baseSide !== null || lists.some((l) => l.some((x) => derived(x.key)));
	const answered = new Map((answer?.pairs ?? []).map((p) => [p.pair, p]));
	const marks: [Map<string, Mark>, Map<string, Mark>] = [new Map(), new Map()];
	const wedges: [Wedge[], Wedge[]] = [[], []];

	/** The pair of the nearest node before `pair` in pane `p` that the other pane also has, where the other pane's wedge stands after. */
	const anchor = (p: 0 | 1, pair: string, kept: Set<string>): string | null => {
		const l = lists[p];
		for (let i = l.findIndex((x) => x.pair === pair) - 1; i >= 0; i--) if (kept.has(l[i].pair)) return l[i].pair;
		return null;
	};

	// order: the shared nodes outside a longest common subsequence
	const inOrder = lcs(
		common,
		lists[1].filter((x) => both.has(x.pair)).map((x) => x.pair)
	);
	const outOfOrder = new Set(common.filter((p) => !inOrder.has(p)));

	for (const pair of common) {
		const l = at[0].get(pair)!;
		const r = at[1].get(pair)!;
		const moved = outOfOrder.has(pair);
		const also = moved ? (copyRel !== null ? 'moved' : 'order') : null;
		if (l.hash !== r.hash) {
			const a = answered.get(pair);
			let dir: 0 | 1 | 'both';
			if (a) dir = a.base === 'left' ? 0 : a.base === 'right' ? 1 : 'both';
			else {
				const key = derived(l.key) ? l.key : derived(r.key) ? r.key : null;
				const math = key ? baseOf(key) : null;
				dir = math ? (l.hash === math ? 0 : r.hash === math ? 1 : 'both') : (baseSide ?? 'both');
			}
			for (const p of [0, 1] as const) {
				const whole = !(p === 0 ? a?.left.fragment : a?.right.fragment);
				const kind: MarkKind = dir === 'both' || !based ? 'both' : dir === p ? 'del' : 'add';
				const tag = dir === 'both' && based ? `changed on both sides since the ${copyRel !== null || lists.some((x) => x.some((f) => derived(f.key))) ? 'copy' : 'base'}` : '';
				marks[p].set(pair, { kind, tag: joinTags(tag, movedTag(p, pair, also)), also, whole });
			}
		} else if (also) {
			for (const p of [0, 1] as const) marks[p].set(pair, { kind: also, tag: movedTag(p, pair, also), also: null, whole: true });
		}
		if (also === 'moved' && copyRel !== null) {
			// a grey wedge in the copy's pane where the node stood in the source
			const copyPane = (1 - copyRel) as 0 | 1;
			wedges[copyPane].push({ after: anchor(copyRel, pair, inOrder), kind: 'moved', pair });
		}
	}

	function movedTag(p: 0 | 1, pair: string, also: 'moved' | 'order' | null): string {
		if (also === 'order') return 'order differs';
		if (also !== 'moved' || copyRel === null) return '';
		if (p === copyRel) return `moved in ${sides[1 - copyRel].name}`;
		const section = at[copyRel].get(pair)?.section;
		return section ? `moved from §${section}` : 'moved';
	}

	for (const p of [0, 1] as const) {
		const other = (1 - p) as 0 | 1;
		for (const x of lists[p]) {
			if (both.has(x.pair)) continue;
			if (based && baseSide !== null) {
				const old = p === baseSide;
				marks[p].set(x.pair, { kind: old ? 'del' : 'add', tag: old ? `removed in ${sides[other].name}` : 'new', also: null, whole: true });
				wedges[other].push({ after: anchor(p, x.pair, both), kind: old ? 'del' : 'add', pair: x.pair });
			} else {
				marks[p].set(x.pair, { kind: 'only', tag: `not in ${sides[other].name}`, also: null, whole: true });
			}
		}
	}

	// the differences, in the left pane's order; a node only the right has stands where its wedge would
	const positions: { pair: string; pos: number; in: [boolean, boolean] }[] = [];
	lists[0].forEach((x, i) => {
		if (marks[0].has(x.pair)) positions.push({ pair: x.pair, pos: i, in: [true, at[1].has(x.pair)] });
	});
	const index = new Map(lists[0].map((x, i) => [x.pair, i]));
	lists[1].forEach((x, i) => {
		if (at[0].has(x.pair) || !marks[1].has(x.pair)) return;
		const after = anchor(1, x.pair, both);
		positions.push({ pair: x.pair, pos: (after === null ? -1 : (index.get(after) ?? -1)) + 0.5 + i / 1e6, in: [false, true] });
	});
	positions.sort((a, b) => a.pos - b.pos);
	return { based, marks, wedges, differences: positions.map(({ pair, in: inside }) => ({ pair, in: inside })) };
}

function joinTags(a: string, b: string): string {
	return [a, b].filter(Boolean).join(' · ');
}

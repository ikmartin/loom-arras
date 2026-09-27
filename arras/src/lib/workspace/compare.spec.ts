import { describe, expect, it } from 'vitest';
import { lcs, plan, type Found, type Side } from './compare';

const f = (pair: string, hash = pair, key: string | null = pair, section: string | null = null): Found => ({ pair, hash, key, section });
const ai = (pair: string, hash = pair, section: string | null = null): Found => f(pair, hash, pair.replace(/^([^/]+)/, '$1-ai'), section);
const doc = (id: string, extra: Partial<Side> = {}): Side => ({ id, kind: 'document', name: id.split('/').pop()!, step: null, copyOf: null, copy: false, ...extra });

describe('lcs', () => {
	it('keeps the longest run in common, so the rest are the fewest that moved', () => {
		expect([...lcs(['a', 'b', 'c', 'd'], ['a', 'c', 'd', 'b'])]).toEqual(['a', 'c', 'd']);
		expect(lcs([], ['a']).size).toBe(0);
	});
});

describe('with a base: a copy against its source', () => {
	const main = doc('drafting/main.tex');
	const copy = doc('drafting-ai/aidoc.tex', { copyOf: 'drafting/main.tex', copy: true });
	const left = [f('s1', 'h1'), f('s2', 'h2'), f('s3'), f('s4', 's4', 's4', '2'), f('gone')];
	const right = [ai('s1', 'h1*'), ai('s4', 's4', '1'), ai('s2', 'h2*'), ai('s3'), ai('new')];
	const bases: Record<string, string> = { 's1-ai': 'h0', 's2-ai': 'h2' };
	const p = plan([left, right], [main, copy], (k) => bases[k] ?? null, null);

	it('draws − on the side holding the base and + on the other', () => {
		expect(p.marks[0].get('s2')?.kind).toBe('del');
		expect(p.marks[1].get('s2')?.kind).toBe('add');
		expect(p.marks[1].get('s2')?.whole).toBe(true); // no answer yet: every line of the node
	});
	it('draws amber on both sides when both changed since the copy', () => {
		expect(p.marks[0].get('s1')).toMatchObject({ kind: 'both', tag: 'changed on both sides since the copy' });
		expect(p.marks[1].get('s1')?.kind).toBe('both');
	});
	it('marks a node only one side has, with a wedge where the base places it', () => {
		expect(p.marks[0].get('gone')).toMatchObject({ kind: 'del', tag: 'removed in aidoc.tex' });
		expect(p.marks[1].get('new')).toMatchObject({ kind: 'add', tag: 'new' });
		expect(p.wedges[1]).toContainEqual({ after: 's4', kind: 'del', pair: 'gone' });
		expect(p.wedges[0]).toContainEqual({ after: 's3', kind: 'add', pair: 'new' });
	});
	it('reports a move between a copy and its source, with a grey wedge where it came from', () => {
		expect(p.marks[0].get('s4')).toMatchObject({ kind: 'moved', tag: 'moved in aidoc.tex' });
		expect(p.marks[1].get('s4')).toMatchObject({ kind: 'moved', tag: 'moved from §2' });
		expect(p.wedges[1]).toContainEqual({ after: 's3', kind: 'moved', pair: 's4' });
	});
	it('counts each difference once, in the left pane’s order, the right’s own where its wedge stands', () => {
		expect(p.differences.map((d) => d.pair)).toEqual(['s1', 's2', 'new', 's4', 'gone']);
		expect(p.differences.find((d) => d.pair === 'new')?.in).toEqual([false, true]);
	});
	it('takes the direction the publisher answered, and narrows the marks it rendered', () => {
		const answer = {
			left: { item: main.id, kind: 'document', macros: null },
			right: { item: copy.id, kind: 'document', macros: null },
			pairs: [{ pair: 's2', base: 'left' as const, left: { key: 's2', hash: 'h2', fragment: 'compare/a.html' }, right: { key: 's2-ai', hash: 'h2*', fragment: 'compare/b.html' } }]
		};
		const q = plan([left, right], [main, copy], () => null, answer);
		expect(q.marks[0].get('s2')).toMatchObject({ kind: 'del', whole: false });
	});
});

describe('landmarks', () => {
	it('the earlier holds the base, and order is only "order differs"', () => {
		const v1 = doc('.loom/history/0001-v1/v1.tex', { kind: 'landmark', name: 'v1 @1', step: 1 });
		const now = doc('drafting/main.tex');
		const p = plan([[f('a', 'a0'), f('b'), f('c')], [f('a', 'a1'), f('c'), f('b')]], [now, v1], () => null, null);
		expect(p.marks[1].get('a')?.kind).toBe('del');
		expect(p.marks[0].get('a')?.kind).toBe('add');
		expect(p.marks[0].get('b')).toMatchObject({ kind: 'order', tag: 'order differs' });
	});
});

describe('without a base: two of the author’s documents', () => {
	const p = plan(
		[
			[f('d'), f('l'), f('r'), f('t')],
			[f('d'), f('t'), f('r'), f('x')]
		],
		[doc('drafting/main.tex'), doc('drafting/talk.tex')],
		() => null,
		null
	);
	it('marks presence with a dashed rule naming where it is missing', () => {
		expect(p.based).toBe(false);
		expect(p.marks[0].get('l')).toMatchObject({ kind: 'only', tag: 'not in talk.tex' });
		expect(p.marks[1].get('x')).toMatchObject({ kind: 'only', tag: 'not in main.tex' });
		expect(p.wedges).toEqual([[], []]);
	});
	it('marks order on the fewest nodes, on both sides', () => {
		const ordered = [...p.marks[0]].filter(([, m]) => m.kind === 'order').map(([k]) => k);
		expect(ordered).toHaveLength(1);
		expect(p.marks[1].get(ordered[0])?.kind).toBe('order');
	});
});

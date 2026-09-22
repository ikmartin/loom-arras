import { describe, expect, it } from 'vitest';
import { ambiguous, anyMoved, documentOf, findingsOf, isDocument, notationOf, runsOn, versionNote } from './run';
import type { Annotation, Manifest, Thread } from '$lib/manifest/types';

const ann = (id: string, over: Partial<Annotation> = {}): Annotation =>
	({
		id,
		author: { kind: 'agent', id: 'r' },
		created: '2026-09-16T14:31:00Z',
		target: { key: 'n-1', hash: 'h1' },
		kind: 'objection',
		body_html: '',
		status: 'open',
		in_reply_to: null,
		anchored: true,
		detached: false,
		run: 'r1',
		record: 'r1',
		discarded: false,
		...over
	}) as Annotation;

const m = {
	masters: [{ path: 'drafting/main.tex', title: 'Main', default: true, fragment: 'f' }],
	nodes: { 'n-1': { reached_by: ['drafting/main.tex'] }, 'n-2': { reached_by: [] } },
	keys: { 'n-1': { node: 'n-1', hash: 'h1' }, 'n-2': { node: 'n-2', hash: 'h9', version: { step: '0002', name: 'paper-v1' } } },
	annotations: {},
	threads: {}
} as unknown as Manifest;

const thread = (over: Partial<Thread> = {}): Thread => ({ id: 'r1', kind: 'session', title: 't', created: '2026-09-16T14:02:00Z', participants: [], targets: ['n-1'], messages: [], attachments: [], log: [], discarded: false, ...over });

describe('what a run says about a document', () => {
	it('knows a document from a node', () => {
		expect(isDocument(m, 'drafting/main.tex')).toBe(true);
		expect(isDocument(m, 'n-1')).toBe(false);
	});

	it('takes the document a run names, and otherwise the one reaching its nodes', () => {
		expect(documentOf(m, thread({ targets: ['n-1', 'drafting/main.tex'] }))).toBe('drafting/main.tex');
		expect(documentOf(m, thread({ targets: ['n-1'] }))).toBe('drafting/main.tex');
		expect(documentOf(m, thread({ targets: ['n-2'] }))).toBe(null); // in no document
	});

	it('separates findings about the document from findings about a node, worst first', () => {
		const mm = {
			...m,
			annotations: {
				a: ann('a', { severity: 'minor' }),
				b: ann('b', { severity: 'major' }),
				c: ann('c', { target: { key: 'drafting/main.tex', hash: '' } }),
				d: ann('d', { in_reply_to: 'b' }), // a reply is not a finding
				e: ann('e', { discarded: true }), // nor is a withdrawn one
				f: ann('f', { run: 'other' }) // nor another run's
			}
		} as unknown as Manifest;
		const got = findingsOf(mm, thread());
		expect(got.document.map((x) => x.id)).toEqual(['c']);
		expect(got.node.map((x) => x.id)).toEqual(['b', 'a']); // major before minor
	});

	it('says nothing while the anchor still matches, and names the version once it does not', () => {
		expect(versionNote(m, ann('a'))).toBe(null); // h1 === h1
		expect(versionNote(m, ann('a', { target: { key: 'n-1', hash: 'old' } }))).toBe('changed since this run');
		expect(versionNote(m, ann('a', { target: { key: 'n-2', hash: 'old' } }))).toBe('changed since this run, now @paper-v1');
		expect(anyMoved({ ...m, annotations: { a: ann('a') } } as unknown as Manifest, thread())).toBe(false);
	});

	it('collects declared notation and catches a symbol given two meanings', () => {
		const t2 = thread({
			pipeline: [
				{
					mode: 'referee',
					target: 'sy-0003',
					report: 'r.md',
					blocks: [
						{
							name: 'notation',
							title: 'notation',
							symbols: [
								{ tex: '\\Fix(\\sigma)', means: 'the fixed locus' },
								{ tex: 'k', means: 'the number of orbits' },
								{ tex: '\\Fix(\\sigma)', means: 'the fixed locus on orbits' }
							]
						}
					]
				}
			]
		});
		expect(notationOf(t2).map((d) => d.tex)).toEqual(['\\Fix(\\sigma)', 'k']); // sorted, and the repeat merged
		expect(ambiguous(t2).map((d) => d.tex)).toEqual(['\\Fix(\\sigma)']);
		expect(ambiguous(t2)[0].means).toHaveLength(2);
		expect(notationOf(thread())).toEqual([]); // a run with no pipeline declares nothing
	});

	it('finds the runs that touched a document, newest first', () => {
		const mm = {
			...m,
			annotations: { a: ann('a', { run: 'r1' }), b: ann('b', { run: 'r2', target: { key: 'drafting/main.tex', hash: '' } }) },
			threads: {
				r1: thread({ id: 'r1', created: '2026-09-16T14:02:00Z' }),
				r2: thread({ id: 'r2', created: '2026-09-17T09:00:00Z' }),
				r3: thread({ id: 'r3', created: '2026-09-18T09:00:00Z' }) // touched nothing here
			}
		} as unknown as Manifest;
		expect(runsOn(mm, 'drafting/main.tex').map((t) => t.id)).toEqual(['r2', 'r1']);
		expect(runsOn(mm, null)).toEqual([]);
	});
});

describe('what a result rests on', () => {
	const mm = {
		keys: {
			a: { node: 'a', uses: [] },
			'a/proof': { node: 'a', uses: ['b', 'c'] },
			b: { node: 'b', uses: ['d'] },
			c: { node: 'c', uses: [] },
			d: { node: 'd', uses: [] },
			e: { node: 'e', uses: [] }
		},
		nodes: {
			a: { proofs: ['a/proof'] },
			b: { proofs: [] },
			c: { proofs: [] },
			d: { proofs: [] },
			e: { proofs: [] }
		}
	} as unknown as Manifest;

	it('rests on what its proof rests on, deepest first, the result last', async () => {
		const { stack } = await import('./closure');
		// the statement's own `uses` is empty -- every dependency is inside the argument, which is the ordinary case
		expect(stack(mm, 'a', 1)).toEqual(['b', 'c', 'a']);
		expect(stack(mm, 'a', 2)).toEqual(['d', 'b', 'c', 'a']); // what b uses comes before b
		expect(stack(mm, 'e', 2)).toEqual(['e']); // rests on nothing
		expect(stack(mm, 'missing', 1)).toEqual([]);
	});
});

describe('the stack agrees with the publisher', () => {
	it('reaches exactly the closure loom wrote, given enough depth', async () => {
		// Viewer obligation 2 (plan 0.9.5 §1): a back end never re-derives what the front end knew. Depth is genuinely
		// not in the manifest -- `uses` is one step and `closure` is all of them -- so walking `uses` is allowed, but
		// walking it far enough must land on the publisher's own answer or one of us is wrong.
		const { stack } = await import('./closure');
		const mm = {
			keys: {
				a: { node: 'a', uses: ['b'], closure: ['b', 'c'] },
				b: { node: 'b', uses: ['c'], closure: ['c'] },
				c: { node: 'c', uses: [], closure: [] }
			},
			nodes: { a: { proofs: [] }, b: { proofs: [] }, c: { proofs: [] } }
		} as unknown as Manifest;
		const deep = stack(mm, 'a', 99).filter((k) => k !== 'a');
		expect(deep.sort()).toEqual([...mm.keys['a'].closure].sort());
	});
});

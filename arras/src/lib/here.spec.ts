import { describe, expect, it } from 'vitest';
import { placeOf, type PlaceInput } from './here.svelte';

const reading = (over: Partial<PlaceInput>): PlaceInput => ({
	route: 'reading',
	current: null,
	beside: null,
	selection: null,
	region: null,
	review: null,
	session: null,
	...over
});

describe('placeOf', () => {
	it('reports the focused item, the block at its top, the other pane and the session, each item bare', () => {
		const got = placeOf(
			reading({
				current: { kind: 'document', id: 'drafting/main.tex', anchor: 'sec-2', view: 'text' },
				beside: { kind: 'work', id: 'Bellamy19', place: { page: 3 } },
				block: { src: 'nodes/sy-0003.tex:1:4', key: 'sy-0003' },
				session: 's-2026-10-30-0001'
			})
		);
		expect(got).toEqual({
			route: 'reading',
			item: { kind: 'document', id: 'drafting/main.tex' },
			block: { src: 'nodes/sy-0003.tex:1:4', key: 'sy-0003' },
			beside: { kind: 'work', id: 'Bellamy19', place: { page: 3 } },
			session: 's-2026-10-30-0001'
		});
	});

	it("carries a selection only when it is in the current item, words before a region", () => {
		const current = { kind: 'node' as const, id: 'sy-0003' };
		const words = { item: 'node:sy-0003', key: 'sy-0003', text: 'a finite widget' };
		expect(placeOf(reading({ current, selection: words })).selection).toEqual({ key: 'sy-0003', text: 'a finite widget' });
		expect(placeOf(reading({ current, selection: { ...words, item: 'node:sy-0004' } })).selection).toBeUndefined();
		const box = { item: 'node:sy-0003', page: 2, rects: [[1, 2, 3, 4]] };
		expect(placeOf(reading({ current, region: box })).selection).toEqual({ page: 2, rects: [[1, 2, 3, 4]] });
		expect(placeOf(reading({ current, selection: words, region: box })).selection).toEqual({ key: 'sy-0003', text: 'a finite widget' });
	});

	it("reports a paper's page, its box as the selection", () => {
		const got = placeOf(
			reading({ current: { kind: 'work', id: 'Bellamy19' }, page: 4, region: { item: 'work:Bellamy19', page: 4, rects: [[72, 100, 300, 140]] } })
		);
		expect(got).toEqual({ route: 'reading', item: { kind: 'work', id: 'Bellamy19' }, page: 4, selection: { page: 4, rects: [[72, 100, 300, 140]] } });
	});

	it('in Review reports the block under review in place of the workspace, and elsewhere only the path', () => {
		const panes = { current: { kind: 'document' as const, id: 'drafting/main.tex' }, session: 's-1' };
		expect(placeOf({ ...reading(panes), route: 'review', review: { key: 'sy-0003', cause: 'edited' } })).toEqual({
			route: 'review',
			review: { key: 'sy-0003', cause: 'edited' },
			session: 's-1'
		});
		expect(placeOf({ ...reading(panes), route: 'elsewhere', path: '/graph' })).toEqual({ route: 'elsewhere', path: '/graph', session: 's-1' });
	});
});

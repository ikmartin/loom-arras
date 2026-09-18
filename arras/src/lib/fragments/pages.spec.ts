import { describe, expect, it } from 'vitest';
import { pagesOf } from './pages';
import type { Manifest } from '$lib/manifest/types';

const MASTER = 'drafting/main.tex';

const m = {
	keys: {
		'sy-0001': { node: 'sy-0001' },
		'sy-0002': { node: 'sy-0002' },
		'sy-0003': { node: 'sy-0003' },
		'sy-0004': { node: 'sy-0004' }
	},
	nodes: {
		'sy-0001': { numbers: { [MASTER]: { number: '1', page: 4 } } },
		'sy-0002': { numbers: { [MASTER]: { number: '2', page: 4 } } },
		'sy-0003': { numbers: { [MASTER]: { number: '2.1', page: 6 } } },
		// never compiled, or not reached by this master: no number, so no page
		'sy-0004': { numbers: {} }
	}
} as unknown as Manifest;

/** A stand-in for a fragment: the keyed elements in document order, which is all `pagesOf` reads. */
function fragment(keys: string[]): HTMLElement {
	const root = { querySelectorAll: () => keys.map((key) => ({ dataset: { key } })) };
	return root as unknown as HTMLElement;
}

describe('the compiled page a node fell on', () => {
	it('reads the publisher’s own numbers, in document order', () => {
		expect(pagesOf(m, MASTER, fragment(['sy-0001', 'sy-0002', 'sy-0003']))).toEqual([4, 4, 6]);
	});

	it('gives nothing for a node the publisher never numbered', () => {
		// An inclusion, a loose node, a master that was never compiled: the boundary is unknown and is not invented.
		expect(pagesOf(m, MASTER, fragment(['sy-0004', 'nodes/sy-0001.tex']))).toEqual([null, null]);
	});

	it('gives nothing for another master, or for none', () => {
		expect(pagesOf(m, 'drafting/talk.tex', fragment(['sy-0001']))).toEqual([null]);
		expect(pagesOf(m, null, fragment(['sy-0001']))).toEqual([null]);
		expect(pagesOf(null, MASTER, fragment(['sy-0001']))).toEqual([null]);
	});
});

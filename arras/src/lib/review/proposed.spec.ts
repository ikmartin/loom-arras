import { describe, expect, it } from 'vitest';
import fixture from '../../../tests/fixture/manifest.json';
import type { Manifest } from '$lib/manifest/types';
import { adoptionsOf, cardsOf, copySays, proposedCount, pullLabel, resultsOf } from './proposed';

const m = fixture as unknown as Manifest;
// the fixture's two open suggested edits: one on sy-0002, the newer, and one on sy-0004 answering an annotation
const TEXT = 'e-2026-09-17-zwvx4m';
const ANSWERING = 'e-2026-09-16-r2hw0m';
const COPY = '.loom/copies/aidoc.tex';

/** The fixture with `over` applied to a deep copy. */
function changed(over: (x: Manifest) => void): Manifest {
	const x = structuredClone(m);
	over(x);
	return x;
}

describe('what is proposed to the person', () => {
	it('lists a copy, then the open suggested edits, newest first, one card each', () => {
		expect(cardsOf(m).map((c) => c.kind)).toEqual(['copy', 'edit', 'edit']);
		expect(cardsOf(m).filter((c) => c.kind === 'edit').map((c) => c.id)).toEqual([TEXT, ANSWERING]);
		expect(proposedCount(m)).toBe(3);
		expect(adoptionsOf(m).map((a) => a.copy)).toEqual([COPY]);
	});

	it('puts a pull first, by its own name', () => {
		const x = changed((y) => {
			y.incoming = { workspace: 'https://git.overleaf.com/0123', changes: [], files: [] } as unknown as Manifest['incoming'];
		});
		expect(cardsOf(x)[0].kind).toBe('pull');
		expect(pullLabel(x)).toBe('Pull from https://git.overleaf.com/0123');
	});

	it('holds a suggested edit on a copy on that copy, and counts it no longer', () => {
		const x = changed((y) => {
			y.nodes['sy-0002'].reached_by = [COPY];
		});
		const cards = cardsOf(x);
		expect(cards.some((c) => c.id === TEXT)).toBe(false);
		const copy = cards[0];
		expect(copy.kind === 'copy' && copy.edits.map((e) => e.id)).toEqual([TEXT]);
		expect(proposedCount(x)).toBe(2);
	});

	it('gives a suggested edit on a copy with no card one of its own', () => {
		const x = changed((y) => {
			y.nodes['sy-0002'].reached_by = [COPY];
			y.contributions = [];
		});
		expect(cardsOf(x).some((c) => c.id === TEXT)).toBe(true);
	});

	it('leaves out an edit once it is kept or discarded', () => {
		const x = changed((y) => {
			y.suggested_edits![TEXT].status = 'kept';
			y.suggested_edits![ANSWERING].status = 'discarded';
		});
		expect(cardsOf(x).map((c) => c.kind)).toEqual(['copy']);
	});

	it('counts each work with results proposed once, however many it has', () => {
		const x = changed((y) => {
			y.references.Kre99.results = {
				a: { state: 'proposed' },
				b: { state: 'proposed' },
				c: { state: 'verified' }
			} as unknown as Manifest['references'][string]['results'];
		});
		expect(resultsOf(x)).toEqual([{ citekey: 'Kre99', count: 2 }]);
		expect(cardsOf(x).at(-1)).toMatchObject({ kind: 'results', id: 'Kre99', count: 2 });
		expect(proposedCount(x)).toBe(4);
	});
});

describe("what a copy's card says", () => {
	it('asks to take or leave until something is decided', () => {
		expect(copySays({ taken: 0, left: 0, undecided: 6, clash: 1 })).toBe("6 to take or leave, 1 that can't be taken");
		expect(copySays({ taken: 2, left: 1, undecided: 3, clash: 0 })).toBe('2 taken, 1 left out, 3 to decide');
	});
});

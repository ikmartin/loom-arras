import { describe, expect, it } from 'vitest';
import { taxonLegend, taxonTone } from './taxonomy';
import type { Manifest } from '$lib/manifest/types';

const m = {
	taxa: {
		Lemma: { style: 'plain', slug: 'lemma', count: 3 },
		Definition: { style: 'definition', slug: 'definition', count: 2 },
		Remark: { style: 'remark', slug: 'remark', count: 1 },
		Widget: { style: 'plain', slug: 'widget', count: 9 }
	}
} as unknown as Manifest;

describe('the taxon palette', () => {
	it('gives every taxon a colour, whatever it is called', () => {
		// Definition, Lemma, Widget sorted; Remark is out of the ordering because its style decides it.
		expect(taxonTone(m, 'Definition')).toBe('var(--taxon-1)');
		expect(taxonTone(m, 'Lemma')).toBe('var(--taxon-2)');
		expect(taxonTone(m, 'Widget')).toBe('var(--taxon-3)'); // a taxon no publisher of ours ever named
		expect(taxonTone(m, 'Remark')).toBe('var(--taxon-remark)'); // by meaning, not by position
	});

	it('keeps a colour as the corpus grows', () => {
		const grown = { taxa: { ...m.taxa, Zorn: { style: 'plain', slug: 'zorn', count: 1 } } } as unknown as Manifest;
		expect(taxonTone(grown, 'Lemma')).toBe(taxonTone(m, 'Lemma')); // adding a later taxon repaints nothing
	});

	it('says nothing about a taxon the corpus does not have', () => {
		expect(taxonTone(m, 'Nonesuch')).toBe('var(--rule-strong)');
		expect(taxonTone(null, 'Lemma')).toBe('var(--rule-strong)');
		expect(taxonTone(m, undefined)).toBe('var(--rule-strong)');
	});

	it('offers a legend in a stable order', () => {
		expect(taxonLegend(m).map((x) => x.taxon)).toEqual(['Definition', 'Lemma', 'Remark', 'Widget']);
		expect(taxonLegend(null)).toEqual([]);
	});
});

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
	it('gives a taxon the colour of its style, whatever it is called', () => {
		// Three, by style, so a finding has a register no taxon can wear (DR-175).
		expect(taxonTone(m, 'Lemma')).toBe('var(--taxon-result)');
		expect(taxonTone(m, 'Widget')).toBe('var(--taxon-result)'); // a taxon no publisher of ours ever named
		expect(taxonTone(m, 'Definition')).toBe('var(--taxon-definition)');
		expect(taxonTone(m, 'Remark')).toBe('var(--taxon-aside)');
	});

	it('draws a style it has never heard of as a result rather than as nothing', () => {
		const odd = { taxa: { Gadget: { style: 'conjecture', slug: 'gadget', count: 1 } } } as unknown as Manifest;
		expect(taxonTone(odd, 'Gadget')).toBe('var(--taxon-result)');
	});

	it('keeps a colour as the corpus grows', () => {
		const grown = { taxa: { ...m.taxa, Zorn: { style: 'plain', slug: 'zorn', count: 1 } } } as unknown as Manifest;
		expect(taxonTone(grown, 'Lemma')).toBe(taxonTone(m, 'Lemma')); // nothing here counts or orders taxa
		expect(taxonTone(grown, 'Zorn')).toBe(taxonTone(m, 'Lemma')); // and two of a style share one colour
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

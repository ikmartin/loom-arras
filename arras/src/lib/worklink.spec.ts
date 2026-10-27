import { describe, expect, it } from 'vitest';
import { externalUrl, locate, normalId, pageOf, parseWorkLink, resultPlace } from './worklink';
import { keyUrl } from './nav';
import type { Manifest, Reference } from './manifest/types';

const ref = (over: Partial<Reference>): Reference => ({ citekey: 'X', bib: {}, digest: null, version_mismatch: false, cited_by: [], ...over });
const manifest = (refs: Reference[]) => ({ references: Object.fromEntries(refs.map((r) => [r.citekey, r])) }) as unknown as Manifest;

describe('a work link', () => {
	it('names an identifier and a page or a quote', () => {
		expect(parseWorkLink('cited:arxiv:0805.2065v2#page=9')).toEqual({ id: 'arxiv:0805.2065v2', page: 9 });
		expect(parseWorkLink('cited:arXiv:math/9810166v2#quote=fixed%20locus')).toEqual({ id: 'arxiv:math/9810166v2', quote: 'fixed locus' });
		expect(parseWorkLink('cited:DOI:10.1090/S1056-3911-2011-00606-1')).toEqual({ id: 'doi:10.1090/s1056-3911-2011-00606-1' });
		expect(parseWorkLink('https://arxiv.org/abs/0805.2065')).toBeNull();
		expect(parseWorkLink('cited:arxiv:')).toBeNull();
		expect(parseWorkLink('cited:arxiv:1#page=0')).toEqual({ id: 'arxiv:1' });
	});

	it('spells an identifier one way', () => {
		expect(normalId('arXiv:2207.01652')).toBe('arxiv:2207.01652');
		expect(normalId('doi:10.1353/AJM.1998.0020')).toBe('doi:10.1353/ajm.1998.0020');
	});

	it('opens the copy on file only when it is the artifact the link names', () => {
		const m = manifest([ref({ citekey: 'Man12', work: 'arXiv:0805.2065v2', works: ['arXiv:0805.2065v2', 'doi:10.1090/X'], artifacts: { dir: 'refs/arxiv/0805.2065v2', pdf: true, source: true } })]);
		expect(locate(m, { id: 'arxiv:0805.2065v2', page: 9 })).toMatchObject({ local: '/refs/arxiv/0805.2065v2/paper.pdf#page=9', external: 'https://arxiv.org/pdf/0805.2065v2#page=9' });
		const published = locate(m, { id: 'doi:10.1090/x', page: 9 });
		expect(published.local).toBeUndefined();
		expect(published.otherCopy).toEqual({ id: 'arXiv:0805.2065v2', url: '/refs/arxiv/0805.2065v2/paper.pdf' });
		expect(published.external).toBe('https://doi.org/10.1090/x');
	});

	it('has nowhere local to go when nothing is fetched, or the work is not cited', () => {
		const m = manifest([ref({ citekey: 'Man12', work: 'arXiv:0805.2065v2', works: ['arXiv:0805.2065v2'], artifacts: { dir: 'refs/arxiv/0805.2065v2', pdf: false, source: false } })]);
		expect(locate(m, { id: 'arxiv:0805.2065v2', page: 3 }).local).toBeUndefined();
		expect(locate(m, { id: 'arxiv:9999.99999' }).ref).toBeUndefined();
		expect(externalUrl({ id: 'work:abcd' })).toBeUndefined();
	});
});

describe('a digest locator', () => {
	it('carries the page extraction wrote', () => {
		expect(pageOf('Construction 1.7, p.~13')).toBe(13);
		expect(pageOf('Proposition 3.1, p. 18')).toBe(18);
		expect(pageOf('Theorem A, pp. 4–6')).toBe(4);
		expect(pageOf('Theorem 2.1')).toBeUndefined();
	});
});

describe("a cited result's place", () => {
	const digest = { file: '', fragment: '', source: 'arXiv:2207.01652', extracted_from: 'arXiv:2207.01652', method: 'extract', nodes: ['Z22-c1.7'] };
	const filed = { dir: 'refs/arxiv/2207.01652', pdf: true, source: true };
	const at = (over: Partial<Reference> = {}, locator = 'Construction 1.7, p.~13', page = 0) =>
		({
			nodes: { 'Z22-c1.7': { digest: 'Z22', locator } },
			references: { Z22: ref({ citekey: 'Z22', work: 'arXiv:2207.01652', artifacts: filed, digest, results: { 'Z22-c1.7': { state: 'extracted', page } as never }, ...over }) }
		}) as unknown as Manifest;

	it('is its paper at the page its anchor was read from, else the page its locator names', () => {
		expect(resultPlace(at({}, 'Construction 1.7, p.~13', 14), 'Z22-c1.7')).toEqual({ citekey: 'Z22', page: 14, result: 'Z22-c1.7' });
		expect(resultPlace(at(), 'Z22-c1.7')).toEqual({ citekey: 'Z22', page: 13, result: 'Z22-c1.7' });
		expect(keyUrl(at(), 'Z22-c1.7')).toBe('/library/Z22?page=13&result=Z22-c1.7');
	});

	it("is its digest node's page where no paper is filed, no page is known, or the locator's page is another version's", () => {
		expect(resultPlace(at({ artifacts: { ...filed, pdf: false } }), 'Z22-c1.7')).toBeNull();
		expect(keyUrl(at({ artifacts: { ...filed, pdf: false } }), 'Z22-c1.7')).toBe('/node/Z22-c1.7');
		expect(resultPlace(at({}, 'Construction 1.7'), 'Z22-c1.7')).toBeNull();
		expect(resultPlace(at({ work: 'doi:10.1/x' }), 'Z22-c1.7')).toBeNull();
		expect(resultPlace(at({ version_mismatch: true }), 'Z22-c1.7')).toBeNull();
		const other = at();
		other.references.Z22.results!['Z22-c1.7'].version = { extracted_from: 'arXiv:2207.01652v1', cited: 'doi:10.1/x' };
		expect(resultPlace(other, 'Z22-c1.7')).toBeNull();
		// a page read off the copy filed is that copy's, whatever version the digest was extracted from
		expect(resultPlace(at({ work: 'doi:10.1/x' }, 'p. 13', 2), 'Z22-c1.7')?.page).toBe(2);
	});

	it('is nothing for a key that is not a cited result', () => {
		expect(resultPlace(at(), 'sy-0001')).toBeNull();
	});
});

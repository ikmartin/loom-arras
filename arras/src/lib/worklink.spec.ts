import { describe, expect, it } from 'vitest';
import { digestPageLink, externalUrl, locate, normalId, pageOf, parseWorkLink } from './worklink';
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

	it('links to that page only in the artifact the digest was extracted from', () => {
		const onFile = ref({ work: 'arXiv:2207.01652', artifacts: { dir: 'refs/arxiv/2207.01652', pdf: true, source: true }, digest: { file: '', fragment: '', source: 'arXiv:2207.01652', extracted_from: 'arXiv:2207.01652', method: 'extract', nodes: [] } });
		expect(digestPageLink(onFile, 'Construction 1.7, p.~13')).toEqual({ id: 'arxiv:2207.01652', page: 13 });
		const published = { ...onFile, work: 'doi:10.1/x' };
		expect(digestPageLink(published, 'Construction 1.7, p.~13')).toBeNull();
		expect(digestPageLink({ ...onFile, artifacts: { dir: '', pdf: false, source: false } }, 'p. 13')).toBeNull();
	});
});

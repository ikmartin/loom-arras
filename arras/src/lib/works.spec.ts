import { describe, expect, it } from 'vitest';
import { bibText, resolve, workLinks } from './works';
import type { Reference } from './manifest/types';

const ref = (over: Partial<Reference>): Reference => ({ citekey: 'X', bib: {}, digest: null, version_mismatch: false, cited_by: [], ...over });

describe('a work links out through its identifiers', () => {
	it('resolves each scheme, whatever its case', () => {
		expect(resolve('doi:10.1090/S1056-3911-2011-00606-1')?.href).toBe('https://doi.org/10.1090/S1056-3911-2011-00606-1');
		expect(resolve('arXiv:2207.01652')).toMatchObject({ label: 'arXiv', href: 'https://arxiv.org/abs/2207.01652' });
		expect(resolve('mr:MR1234567')?.href).toBe('https://mathscinet.ams.org/mathscinet-getitem?mr=1234567');
		expect(resolve('zbl:0909.14006')?.href).toBe('https://zbmath.org/?q=an:0909.14006');
	});

	it('links nothing for a synthetic id', () => {
		expect(resolve('work:2c270585')).toBeNull();
		expect(workLinks(ref({ work: 'work:2c270585', works: ['work:2c270585'] }))).toEqual([]);
	});

	it('adds the bibliography url and a fetched PDF, and no PDF that was never fetched', () => {
		const links = workLinks(ref({ works: ['arxiv:0805.2065'], bib: { url: 'https://example.org/paper' }, artifacts: { dir: 'refs/arxiv/0805.2065', pdf: true, source: true } }));
		expect(links.map((l) => l.label)).toEqual(['arXiv', 'link', 'PDF']);
		expect(links[2].href).toBe('/refs/arxiv/0805.2065/paper.pdf');
		expect(workLinks(ref({ works: ['arxiv:0805.2065'], artifacts: { dir: 'refs/arxiv/0805.2065', pdf: false, source: true } })).map((l) => l.label)).toEqual(['arXiv']);
	});

	it('falls back to the bibliography fields when the manifest predates works', () => {
		expect(workLinks(ref({ bib: { doi: 'https://doi.org/10.1/abc', eprint: '0805.2065' } })).map((l) => l.href)).toEqual(['https://doi.org/10.1/abc', 'https://arxiv.org/abs/0805.2065']);
	});
});

describe('a bibliography field reads as text', () => {
	it('drops protective braces', () => {
		expect(bibText('Decomposition of Degenerate {{Gromov}}--{{Witten}} Invariants')).toBe('Decomposition of Degenerate Gromov–Witten Invariants');
	});

	it('turns accent commands into accented letters', () => {
		expect(bibText("Sch\\'emas en groupes {II}: g\\'en\\'eraux")).toBe('Schémas en groupes II: généraux');
		expect(bibText('Kiem, Young-Hoon and G{\\"o}ttsche and Erd\\H{o}s and \\o{}ksendal and Stra\\ss e')).toBe('Kiem, Young-Hoon and Göttsche and Erdős and øksendal and Straße');
	});

	it('keeps what a font command sets and drops the command', () => {
		expect(bibText('The \\textit{Stacks Project}')).toBe('The Stacks Project');
		expect(bibText('\\emph{On} the {{Gromov}} witten')).toBe('On the Gromov witten');
	});

	it('leaves mathematics for the typesetter', () => {
		expect(bibText('The $\\mathbb{G}_m$-action')).toBe('The $\\mathbb{G}_m$-action');
	});
});

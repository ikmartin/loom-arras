import { describe, expect, it } from 'vitest';
import { documentLabel, shortLocator } from './names';

describe('shortLocator', () => {
	it('drops the page and abbreviates the taxon', () => {
		expect(shortLocator('Proposition 2.1, p.~1')).toBe('Prop 2.1');
		expect(shortLocator('Theorem 3.1, p.~2')).toBe('Thm 3.1');
		expect(shortLocator('Lemma (unnumbered) (Support), pp. 3-4')).toBe('Lem (unnumbered) (Support)');
	});
	it('keeps a locator that names no taxon', () => {
		expect(shortLocator('Standing assumptions')).toBe('Standing assumptions');
		expect(shortLocator('Section~5')).toBe('Section 5');
	});
});

describe('documentLabel', () => {
	const masters = [{ path: 'drafting/main.tex' }, { path: 'drafting/outline.tex' }, { path: 'paper/main.tex' }];
	it('is the file name while no other document has it', () => {
		expect(documentLabel(masters, 'drafting/outline.tex')).toBe('outline.tex');
	});
	it('is the path where two documents share a file name', () => {
		expect(documentLabel(masters, 'drafting/main.tex')).toBe('drafting/main.tex');
		expect(documentLabel(masters, 'paper/main.tex')).toBe('paper/main.tex');
	});
});

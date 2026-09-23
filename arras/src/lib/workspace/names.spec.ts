import { describe, expect, it } from 'vitest';
import { shortLocator } from './names';

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

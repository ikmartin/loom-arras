import { describe, expect, it } from 'vitest';
import { delimit, hasMath } from './delimit';

describe('delimit', () => {
	it('turns a display into a display, not two inline halves', () => {
		// Graber and Pandharipande's formula arrived on the verification surface as raw `$$…$$` source
		expect(delimit('then: $$[X]^{vir} = \\iota_* \\sum$$ in $A_*(X)$.')).toBe('then: \\[[X]^{vir} = \\iota_* \\sum\\] in \\(A_*(X)\\).');
	});
	it('leaves an escaped dollar alone', () => {
		expect(delimit('costs \\$5 and $x$')).toBe('costs \\$5 and \\(x\\)');
	});
	it('keeps line breaks and text without math', () => {
		expect(delimit('(i) one\n(ii) two')).toBe('(i) one\n(ii) two');
	});
});

describe('hasMath', () => {
	it('finds a formula in either delimiter a title is written with', () => {
		// a section titled `Examples on \(\mathbb P^2\)` was shown untypeset in the contents, which only looked for dollars
		expect(hasMath('Examples on \\(\\mathbb P^2\\)')).toBe(true);
		expect(hasMath('Structure of $\\Sigma$')).toBe(true);
		expect(hasMath('then \\[x^2\\]')).toBe(true);
		expect(hasMath('costs \\$5')).toBe(false);
		expect(hasMath('Toric targets')).toBe(false);
	});
});

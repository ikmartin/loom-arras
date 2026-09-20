import { describe, expect, it } from 'vitest';
import { delimit } from './delimit';

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

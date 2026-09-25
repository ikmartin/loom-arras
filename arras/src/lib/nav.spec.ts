import { describe, expect, it } from 'vitest';
import { canonUrl, docUrl } from './nav';

const m = {
	masters: [{ path: 'drafting/main.tex' }],
	canon: [{ path: 'canon/widgets-v1.tex' }]
};

describe('routing', () => {
	it('sends a landmark to its own page and a draft to the read view', () => {
		expect(canonUrl('canon/widgets-v1.tex')).toBe('/canon/widgets-v1');
		expect(docUrl(m, 'canon/widgets-v1.tex')).toBe('/canon/widgets-v1');
		expect(docUrl(m, 'drafting/main.tex')).toBe('/master/main');
		expect(docUrl(null, 'drafting/main.tex')).toBe('/master/main');
	});
});

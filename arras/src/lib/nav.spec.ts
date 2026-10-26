import { describe, expect, it } from 'vitest';
import { canonUrl } from './nav';

describe('routing', () => {
	it('sends a landmark to its own page', () => {
		expect(canonUrl('canon/widgets-v1.tex')).toBe('/canon/widgets-v1');
	});
});

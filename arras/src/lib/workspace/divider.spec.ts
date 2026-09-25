import { describe, expect, it } from 'vitest';
import { settle } from './divider';

describe('the divider', () => {
	it('snaps at the middle and nowhere else', () => {
		expect(settle(0.49)).toBe(0.5);
		expect(settle(0.52)).toBe(0.5);
		expect(settle(0.45)).toBe(0.45);
		expect(settle(0.34)).toBe(0.34);
		// a key names an exact step, which the snap must not pull back
		expect(settle(0.52, false)).toBe(0.52);
	});

	it('keeps both panes usable however far the pointer goes', () => {
		expect(settle(1.4)).toBe(0.8);
		expect(settle(-0.3)).toBe(0.2);
	});
});

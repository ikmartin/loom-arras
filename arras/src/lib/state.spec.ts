import { describe, expect, it } from 'vitest';
import { toneClass, toneOf } from './state';

describe('state tones', () => {
	it('maps every colour class the interface declares', () => {
		expect(toneOf('positive')).toBe('accepted');
		expect(toneOf('positive-strong')).toBe('accepted');
		expect(toneOf('warning')).toBe('stale');
		expect(toneOf('neutral')).toBe('draft');
		expect(toneOf('negative')).toBe('incomplete');
		expect(toneOf('info')).toBe('loose');
	});

	it('falls back for a class it has never seen', () => {
		expect(toneOf('chartreuse')).toBe('loose');
		expect(toneOf(undefined)).toBe('loose');
		expect(toneClass('chartreuse')).toBe('tone-loose');
	});
});

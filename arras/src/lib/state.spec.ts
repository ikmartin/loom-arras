import { describe, expect, it } from 'vitest';
import { stateClass, stateTone, toneClass, toneOf } from './state';

describe('state tones', () => {
	const labels = { incomplete: { color: 'negative' as const }, conflicted: { color: 'negative' as const } };

	it('maps every colour class the interface declares', () => {
		expect(toneOf('positive')).toBe('accepted');
		expect(toneOf('positive-strong')).toBe('accepted');
		expect(toneOf('warning')).toBe('stale');
		expect(toneOf('neutral')).toBe('draft');
		expect(toneOf('negative')).toBe('incomplete');
		expect(toneOf('info')).toBe('loose');
	});

	it('tells conflicted from incomplete although the interface colours them alike', () => {
		expect(stateTone(labels, 'conflicted')).toBe('conflicted');
		expect(stateTone(labels, 'incomplete')).toBe('incomplete');
		expect(stateClass(labels, 'conflicted')).toBe('tone-conflicted');
	});

	it('falls back for a class or a state it has never seen', () => {
		expect(toneOf('chartreuse')).toBe('loose');
		expect(toneOf(undefined)).toBe('loose');
		expect(toneClass('chartreuse')).toBe('tone-loose');
		expect(stateTone(labels, 'invented')).toBe('loose');
	});
});

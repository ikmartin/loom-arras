import { describe, expect, it } from 'vitest';
import { coerce, DEFAULTS } from '$lib/prefs.svelte';

/** What `Split.svelte` does to a dragged position before it becomes the ratio. Kept beside the component it describes. */
function settle(next: number, snap = 0.5, near = 0.03): number {
	const snapped = Math.abs(next - snap) < near ? snap : next;
	return Math.min(0.8, Math.max(0.2, snapped));
}

describe('the divider', () => {
	it('snaps at the middle and nowhere else', () => {
		// one snap, because a snap at a third is a guess about a screen this code cannot see
		expect(settle(0.49)).toBe(0.5);
		expect(settle(0.52)).toBe(0.5);
		expect(settle(0.45)).toBe(0.45);
		expect(settle(0.34)).toBe(0.34);
	});

	it('keeps both panes usable however far the pointer goes', () => {
		// a drag past the edge of the frame must not leave a pane a reader cannot use, and a pointer leaving the window
		// mid-drag reports coordinates well outside it
		expect(settle(1.4)).toBe(0.8);
		expect(settle(-0.3)).toBe(0.2);
	});

	it('is one ratio for the whole app, remembered between visits', () => {
		// the preference is where it lives, so every split is the same width: a reader sets the shape of their screen
		// once rather than once per route
		expect(DEFAULTS.divider).toBeGreaterThan(0.2);
		expect(DEFAULTS.divider).toBeLessThan(0.8);
		expect(coerce({ divider: 0.42 }).divider).toBe(0.42);
	});
});

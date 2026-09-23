import { describe, expect, it, vi, afterEach } from 'vitest';
import { attributes, coerce, DEFAULTS, read, write } from './prefs.svelte';

function stub(initial: Record<string, string> = {}) {
	const map = new Map(Object.entries(initial));
	const ls = {
		getItem: (k: string) => map.get(k) ?? null,
		setItem: (k: string, v: string) => void map.set(k, v),
		removeItem: (k: string) => void map.delete(k)
	};
	vi.stubGlobal('localStorage', ls);
	return map;
}

afterEach(() => vi.unstubAllGlobals());

describe('the display preferences', () => {
	it('defaults to serif, medium, mid, system, the compiled page, a floating comment box, and no ids', () => {
		expect(DEFAULTS).toEqual({
			divider: 0.5,
			panel: true,
			ids: false,
			zoom: { pdf: 1.4 },
			face: 'serif',
			size: 'm',
			width: 'mid',
			theme: 'system',
			format: 'p1',
			comments: 'floating'
		});
	});

	it('keeps the divider inside the range a pane is usable in, and reads a stored hover placement as the default', () => {
		// a ratio outside it leaves one pane too narrow to read, which a stored value from a dragged-off-screen divider
		// or a hand-edited blob could otherwise do
		expect(coerce({ divider: 0.95 }).divider).toBe(0.8);
		expect(coerce({ divider: 0.01 }).divider).toBe(0.2);
		expect(coerce({ divider: 'wide' }).divider).toBe(DEFAULTS.divider);
		expect(coerce({ comments: 'hover' }).comments).toBe('floating');
		// zoom is per renderer kind and remembered, and is clamped for the same reason the divider is
		expect(coerce({ zoom: 9 }).zoom).toEqual({ pdf: 3 }); // a number is what this stored before it was per kind
	expect(coerce({ zoom: { pdf: 0.1, other: 2 } }).zoom).toEqual({ pdf: 0.5, other: 2 });
		expect(coerce({ zoom: 0.1 }).zoom).toEqual({ pdf: 0.5 });
	});

	it('ignores a stored shell, now that there is only one arrangement', () => {
		expect('shell' in coerce({ shell: 'b' })).toBe(false);
	});

	it('round-trips through storage', () => {
		stub();
		const p = { ...DEFAULTS, theme: 'dark' as const, size: 'l' as const };
		write(p);
		expect(read()).toEqual(p);
	});

	it('narrows a stored blob field by field', () => {
		expect(coerce({ shell: 'z', face: 'serif', size: 42 })).toEqual({ ...DEFAULTS, face: 'serif' });
		expect(coerce(null)).toEqual(DEFAULTS);
	});

	it('survives storage that throws and storage that holds nonsense', () => {
		vi.stubGlobal('localStorage', {
			getItem: () => {
				throw new Error('denied');
			},
			setItem: () => {
				throw new Error('denied');
			}
		});
		expect(read()).toEqual(DEFAULTS);
		expect(() => write(DEFAULTS)).not.toThrow();

		stub({ 'arras.prefs': 'not json' });
		expect(read()).toEqual(DEFAULTS);
	});

	it('sets no theme attribute when the theme follows the system', () => {
		expect(attributes({ ...DEFAULTS, theme: 'system' })['data-theme']).toBeNull();
		expect(attributes({ ...DEFAULTS, theme: 'dark' })['data-theme']).toBe('dark');
	});
});

describe('the format rename', () => {
	it('sends a stored `paper` or `blog` back to the default', () => {
		// The names moved: what was `paper` is `b1` and what was `blog` is `b2`, and the compiled page took the name.
		// Nothing migrates a stored value, so a browser holding either gets p1 — which is what it would now choose.
		expect(coerce({ format: 'paper' }).format).toBe('p1');
		expect(coerce({ format: 'blog' }).format).toBe('p1');
		for (const f of ['p1', 'p2', 'b1', 'b2']) expect(coerce({ format: f }).format).toBe(f);
	});
});

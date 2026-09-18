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
	it('defaults to shell C, serif, medium, mid, system, the compiled page, comments in the margin', () => {
		expect(DEFAULTS).toEqual({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'system', format: 'p1', comments: 'margin' });
	});

	it('reads a stored tabs shell, which is retired, as the default', () => {
		expect(coerce({ shell: 'b' }).shell).toBe('c');
	});

	it('round-trips through storage', () => {
		stub();
		const p = { ...DEFAULTS, shell: 'a' as const, theme: 'dark' as const, size: 'l' as const };
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

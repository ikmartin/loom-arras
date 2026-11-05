import { beforeEach, describe, expect, it, vi } from 'vitest';
import { keepPlace, keptPlace } from './position';

const FILE = { id: 'abc', pages: 12 };

function memoryStorage(): Storage {
	const held = new Map<string, string>();
	return {
		getItem: (k: string) => held.get(k) ?? null,
		setItem: (k: string, v: string) => void held.set(k, v),
		removeItem: (k: string) => void held.delete(k),
		clear: () => held.clear(),
		key: () => null,
		get length() {
			return held.size;
		}
	};
}

describe('a reader’s place in a work', () => {
	beforeEach(() => {
		vi.stubGlobal('localStorage', memoryStorage());
	});

	it('comes back as it was kept, once per work and per corpus', () => {
		keepPlace('q', 'A', FILE, { page: 3, share: 0.25 });
		keepPlace('q', 'B', FILE, { page: 7, share: 0.5 });
		keepPlace('r', 'A', FILE, { page: 9, share: 0.75 });
		expect(keptPlace('q', 'A', FILE)).toEqual({ page: 3, share: 0.25 });
		expect(keptPlace('q', 'B', FILE)).toEqual({ page: 7, share: 0.5 });
		expect(keptPlace('r', 'A', FILE)).toEqual({ page: 9, share: 0.75 });
	});

	it('is nothing for a work never read', () => {
		expect(keptPlace('q', 'A', FILE)).toBeNull();
	});

	it('is forgotten at the top of the first page, where a work opens anyway', () => {
		keepPlace('q', 'A', FILE, { page: 3, share: 0.25 });
		keepPlace('q', 'A', FILE, { page: 1, share: 0 });
		expect(keptPlace('q', 'A', FILE)).toBeNull();
		expect(localStorage.getItem('arras.positions')).toBe('{"q":{}}');
	});

	it('does not carry over to another file behind the work, or a file of another length', () => {
		keepPlace('q', 'A', FILE, { page: 3, share: 0.25 });
		expect(keptPlace('q', 'A', { id: 'other', pages: 12 })).toBeNull();
		expect(keptPlace('q', 'A', { id: 'abc', pages: 2 })).toBeNull();
	});

	it.each([
		['a page past the end', { page: 13, share: 0, file: 'abc', pages: 12 }],
		['a page below the first', { page: 0, share: 0, file: 'abc', pages: 12 }],
		['a page that is no number', { page: '3', share: 0, file: 'abc', pages: 12 }],
		['a share past the page', { page: 3, share: 1.5, file: 'abc', pages: 12 }],
		['a share that is no number', { page: 3, share: null, file: 'abc', pages: 12 }]
	])('ignores %s', (_why, kept) => {
		localStorage.setItem('arras.positions', JSON.stringify({ q: { A: kept } }));
		expect(keptPlace('q', 'A', FILE)).toBeNull();
	});

	it('survives a store that holds nonsense, and writes over it', () => {
		localStorage.setItem('arras.positions', 'not json');
		expect(keptPlace('q', 'A', FILE)).toBeNull();
		keepPlace('q', 'A', FILE, { page: 2, share: 0.5 });
		expect(keptPlace('q', 'A', FILE)).toEqual({ page: 2, share: 0.5 });
	});

	it('fails quietly in a browser that refuses to store', () => {
		vi.stubGlobal('localStorage', {
			getItem() {
				throw new Error('denied');
			},
			setItem() {
				throw new Error('denied');
			}
		});
		expect(() => keepPlace('q', 'A', FILE, { page: 2, share: 0.5 })).not.toThrow();
		expect(keptPlace('q', 'A', FILE)).toBeNull();
	});
});

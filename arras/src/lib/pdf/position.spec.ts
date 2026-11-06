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

describe('a reader’s place in a file', () => {
	beforeEach(() => {
		vi.stubGlobal('localStorage', memoryStorage());
	});

	it('comes back as it was kept, one for each file', () => {
		const other = { id: 'def', pages: 12 };
		keepPlace(FILE, { page: 3, share: 0.25 });
		keepPlace(other, { page: 7, share: 0.5 });
		expect(keptPlace(FILE)).toEqual({ page: 3, share: 0.25 });
		expect(keptPlace(other)).toEqual({ page: 7, share: 0.5 });
	});

	it('is nothing for a file never read', () => {
		expect(keptPlace(FILE)).toBeNull();
	});

	it('is forgotten at the top of the first page, where a file opens anyway', () => {
		keepPlace(FILE, { page: 3, share: 0.25 });
		keepPlace(FILE, { page: 1, share: 0 });
		expect(keptPlace(FILE)).toBeNull();
		expect(localStorage.getItem('arras.places')).toBe('{}');
	});

	it('is not found under another file, or the same identifier at another length, and is still there for the file it was in', () => {
		keepPlace(FILE, { page: 3, share: 0.25 });
		expect(keptPlace({ id: 'other', pages: 12 })).toBeNull();
		expect(keptPlace({ id: 'abc', pages: 2 })).toBeNull();
		expect(keptPlace(FILE)).toEqual({ page: 3, share: 0.25 });
	});

	it.each([
		['a page past the end', { page: 13, share: 0 }],
		['a page below the first', { page: 0, share: 0 }],
		['a page that is no number', { page: '3', share: 0 }],
		['a share past the page', { page: 3, share: 1.5 }],
		['a share that is no number', { page: 3, share: null }]
	])('ignores %s', (_why, kept) => {
		localStorage.setItem('arras.places', JSON.stringify({ 'abc:12': kept }));
		expect(keptPlace(FILE)).toBeNull();
	});

	it('survives a store that holds nonsense, and writes over it', () => {
		localStorage.setItem('arras.places', 'not json');
		expect(keptPlace(FILE)).toBeNull();
		keepPlace(FILE, { page: 2, share: 0.5 });
		expect(keptPlace(FILE)).toEqual({ page: 2, share: 0.5 });
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
		expect(() => keepPlace(FILE, { page: 2, share: 0.5 })).not.toThrow();
		expect(keptPlace(FILE)).toBeNull();
	});
});

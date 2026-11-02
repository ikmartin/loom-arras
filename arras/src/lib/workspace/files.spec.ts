import { describe, expect, it, vi } from 'vitest';
import type { Manifest } from '$lib/manifest/types';
import { readingAddress } from '$lib/shell/views';
import { itemForFile, itemFromPath, pathFor } from './item';
import { itemForQuilt } from './links';
import { linkName } from './names';

vi.mock('$app/navigation', () => ({ goto: vi.fn(async () => {}) }));

// The least of a manifest that the project's files are read from (plan 0.22.7): a document with a part it reads, a Markdown file, a PDF, a deck, and a front door.
const m = {
	corpus: { name: 'q', root_label: 'q', home: 'notes/day 1.md' },
	masters: [{ path: 'paper/main.tex', default: true }],
	canon: [],
	nodes: {
		'q-0002': { kind: 'environment', taxon: 'lemma', numbers: {}, file: 'paper/parts/a.tex', src: [40, 90], reached_by: ['paper/main.tex'] },
		'q-0001': { kind: 'environment', taxon: 'lemma', numbers: {}, file: 'paper/parts/a.tex', src: [10, 30], reached_by: ['paper/main.tex'] }
	},
	keys: {},
	regions: {},
	references: {},
	annotations: {},
	sessions: [],
	threads: {},
	files: [
		{ path: 'paper/main.tex', kind: 'document', bytes: 1 },
		{ path: 'paper/parts/a.tex', kind: 'tex', bytes: 1 },
		{ path: 'paper/parts/empty.tex', kind: 'tex', bytes: 1 },
		{ path: 'notes/day 1.md', kind: 'markdown', bytes: 1, body: 'files/notes/day 1.md.html' },
		{ path: 'books/hull.pdf', kind: 'pdf', bytes: 1 },
		{ path: 'deck.apkg', kind: 'other', bytes: 1 }
	]
} as unknown as Manifest;

describe('a project file', () => {
	it('is addressed at /file/ by its path, each segment encoded, and read back', () => {
		const item = { kind: 'file' as const, id: 'notes/day 1.md', anchor: 'setup' };
		const at = pathFor(m, item);
		expect(at).toBe('/file/notes/day%201.md#setup');
		expect(itemFromPath(m, at)).toEqual(item);
	});

	it('is linked by its path with its suffix, at a heading or a page, and named by its file name', () => {
		expect(itemForQuilt(m, 'notes/day%201.md#setup')).toEqual({ kind: 'file', id: 'notes/day 1.md', anchor: 'setup' });
		expect(itemForQuilt(m, 'books/hull.pdf#page=12')).toEqual({ kind: 'file', id: 'books/hull.pdf', anchor: 'page=12' });
		expect(linkName(m, 'quilt:books/hull.pdf#page=12')).toBe('hull.pdf p. 12');
		expect(linkName(m, 'quilt:deck.apkg')).toBe('deck.apkg');
	});

	it('opens from the tree as a document, as the document that reads it at its first key, or as itself', () => {
		expect(itemForFile(m, 'paper/main.tex')).toEqual({ kind: 'document', id: 'paper/main.tex' });
		expect(itemForFile(m, 'paper/parts/a.tex')).toEqual({ kind: 'document', id: 'paper/main.tex', anchor: 'q-0001' });
		expect(itemForFile(m, 'paper/parts/empty.tex')).toEqual({ kind: 'file', id: 'paper/parts/empty.tex' });
		expect(itemForFile(m, 'deck.apkg')).toEqual({ kind: 'file', id: 'deck.apkg' });
	});
});

describe('the front door', () => {
	it('is where a quilt opens when nothing is remembered: a file, the research state, or a document', () => {
		expect(readingAddress(m)).toBe('/file/notes/day%201.md');
		expect(readingAddress(m, '/node/q-0001')).toBe('/node/q-0001');
		const state = { ...m, corpus: { ...m.corpus, home: 'research-state.md' }, research_state: { path: 'research-state.md' } } as unknown as Manifest;
		expect(readingAddress(state)).toBe('/page/state');
		const paper = { ...m, corpus: { ...m.corpus, home: 'paper/main.tex' } } as unknown as Manifest;
		expect(readingAddress(paper)).toBe('/master/paper/main');
		const none = { ...m, corpus: { ...m.corpus, home: null } } as unknown as Manifest;
		expect(readingAddress(none)).toBe('/master/paper/main');
	});
});

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls: [string, Record<string, unknown>][] = [];
vi.mock('$lib/write', () => ({
	can: async () => true,
	write: async (endpoint: string, body: Record<string, unknown>) => {
		calls.push([endpoint, body]);
		return { ok: true, result: 'a-2026-11-12-new000  Bellamy19  p. 2' };
	}
}));
const types = [
	{ id: 'question', name: 'Question', look: { color: 'blue', style: 'highlight', weight: 2, opacity: 60 }, open: true, notes: false, instructions: '' },
	{ id: 'note', name: 'Note', look: { color: 'grey', style: 'highlight', weight: 2, opacity: 60 }, open: false, notes: true, instructions: '' }
];
vi.mock('$lib/manifest/client.svelte', () => ({ store: { manifest: { annotations: {}, annotation_types: types, reviewer: { name: 'me', source: '' } }, refresh: async () => {} } }));

const { MarkDesk } = await import('./desk.svelte');
const { hand } = await import('$lib/review/annotating.svelte');

const settle = () => new Promise((r) => setTimeout(r, 0));
const desk = () => new MarkDesk(() => ({ on: 'Bellamy19', owns: () => true, url: '', name: 'Bellamy19.pdf' }));

beforeEach(() => {
	calls.length = 0;
});

describe('what the desk writes', () => {
	it('marks words with the type in hand, which draws them, and its style', async () => {
		hand.set({ type: 'note', over: {}, plain: {} });
		desk().markWords({ page: 2, text: 'incidence matrix', rects: [[10, 20, 60, 30]] });
		await settle();
		expect(calls).toEqual([['annotate', { target: 'Bellamy19', page: 2, rects: [[10, 20, 60, 30]], quote: 'incidence matrix', type: 'note' }]]);
	});

	it('writes a drawing with the type in hand and the look set over it, its tool drawing it', async () => {
		hand.set({ type: 'note', over: { color: 'green', style: 'underline', weight: 4 }, plain: {} });
		desk().draw({ kind: 'box', page: 1, rects: [[1, 2, 30, 40]] });
		await settle();
		expect(calls[0][1]).toEqual({ target: 'Bellamy19', page: 1, mark: 'box', rects: [[1, 2, 30, 40]], type: 'note', look: { color: 'green', weight: 4 } });
	});

	it('with Plain in hand writes only what is set over the plain look, words in its style', async () => {
		hand.set({ type: null, over: {}, plain: { style: 'strike' } });
		desk().markRegion({ page: 3, rects: [[5, 5, 50, 20]] });
		await settle();
		expect(calls[0][1]).toEqual({ target: 'Bellamy19', page: 3, rects: [[5, 5, 50, 20]], look: { style: 'strike' } });
	});
});

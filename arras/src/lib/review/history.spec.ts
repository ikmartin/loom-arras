import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls: [string, Record<string, unknown>][] = [];
vi.mock('$lib/write', () => ({
	write: async (endpoint: string, body: Record<string, unknown>) => {
		calls.push([endpoint, body]);
		if (endpoint === 'annotate' || endpoint === 'reply') return { ok: true, result: 'a-new  key  untyped' };
		if (endpoint === 'delete') return { ok: true, result: 'deleted', removed: [{ event: 'created', id: body.annotation }] };
		return { ok: true, result: 'done' };
	}
}));
vi.mock('$lib/manifest/client.svelte', () => ({ store: { manifest: null, refresh: async () => {} } }));

const { annotate, edit, forget, history, redo, remove, resolve, undo, undoDelete } = await import('./history.svelte');

beforeEach(() => {
	calls.length = 0;
	history.done = [];
	history.undone = [];
	history.deletions = [];
});

describe('the history of annotation writes', () => {
	it('undoes a new annotation by deleting it, and does it again by restoring what the delete took out, as often as asked', async () => {
		await annotate({ target: 'k', quote: 'q' });
		expect(await undo()).toBe('');
		expect(calls.at(-1)).toEqual(['delete', { annotation: 'a-new' }]);
		expect(await redo()).toBe('');
		expect(calls.at(-1)).toEqual(['restore', { events: [{ event: 'created', id: 'a-new' }] }]);
		expect(history.done).toHaveLength(1);
		expect(history.undone).toHaveLength(0);
		await undo();
		expect(calls.at(-1)).toEqual(['delete', { annotation: 'a-new' }]);
	});

	it('undoes a resolve by reopening, and a reopen by resolving', async () => {
		await resolve('a1');
		await undo();
		expect(calls.at(-1)).toEqual(['resolve', { annotation: 'a1', undo: true }]);
		await resolve('a2', true);
		await undo();
		expect(calls.at(-1)).toEqual(['resolve', { annotation: 'a2' }]);
	});

	it('undoes an edit by an edit back to the words, type and look it had', async () => {
		const a = { id: 'a1', type: 'gone', look: { color: 'red', style: 'highlight', weight: 2, opacity: 65 }, body_html: '<p>Before.</p>' } as never;
		await edit(a, { message: 'After.', type: null, look: { color: 'blue' } });
		await undo();
		expect(calls.at(-1)).toEqual(['edit', { annotation: 'a1', message: 'Before.', type: 'gone', look: { color: 'red', style: 'highlight', weight: 2, opacity: 65 } }]);
	});

	it('holds a delete at the foot of the window while it stands, whose Undo is the same step', async () => {
		await remove('a1', 'Revision on Theorem 2.1');
		expect(history.deletions).toEqual([{ id: 'a1', said: 'Revision on Theorem 2.1' }]);
		await undoDelete('a1');
		expect(calls.at(-1)).toEqual(['restore', { events: [{ event: 'created', id: 'a1' }] }]);
		expect(history.deletions).toEqual([]);
		await redo();
		expect(history.deletions).toHaveLength(1);
		forget('a1');
		expect(history.deletions).toEqual([]);
		expect(history.done).toHaveLength(1);
	});
});

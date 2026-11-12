import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Manifest, PendingChange } from '$lib/manifest/types';

const calls: [string, Record<string, unknown>][] = [];
let answer: Record<string, unknown> = { ok: true, result: 'done' };
vi.mock('$lib/write', () => ({
	can: async () => true,
	write: async (endpoint: string, body: Record<string, unknown>) => {
		calls.push([endpoint, body]);
		return answer;
	}
}));
const MAIN = 'drafting/main.tex';
const change = (over: Partial<PendingChange>): PendingChange => ({ id: 'c-0001', kind: 'edit', path: 'drafting/nodes/sy-0001.tex', key: 'sy-0001', documents: [MAIN], old: 'a widget', new: 'a gadget', state: 'ready', ...over });
const live = { annotations: {}, annotation_types: [], reviewer: { name: 'me', source: '' }, masters: [], changes: [] as PendingChange[] };
vi.mock('$lib/manifest/client.svelte', () => ({ store: { manifest: live, refresh: async () => {} } }));

const { actSays, allSays, authorOf, byDocument, changeById, changesIn, IN_THE_FILE, kindName, pending, refusal, summary, whoMade } = await import('./changes');
const { acted, mark, prune } = await import('./acted.svelte');
const { Annotating, entries } = await import('./annotating.svelte');
const { discardChanges, history, keepChanges, undo, redo } = await import('./history.svelte');

const suggestion = change({ id: 'e-1', kind: 'suggested', author: { kind: 'agent', id: 'agent', label: 'Claude' }, created: '2026-11-12T10:00:00Z', comment_html: '<p>plural</p>' });

beforeEach(() => {
	calls.length = 0;
	answer = { ok: true, result: 'done' };
	acted.map = {};
	history.done = [];
	history.undone = [];
	live.changes = [];
});

describe('the pending changes the manifest lists', () => {
	it('reads only entries that are pending changes, in order, and finds one by id or by document', () => {
		const m = { changes: [change({}), { path: 'notes/intro.md', kind: 'changed', hunks: 1 } as unknown as PendingChange, change({ id: 'c-0002', documents: ['drafting/talk.tex'] })] };
		expect(pending(m).map((c) => c.id)).toEqual(['c-0001', 'c-0002']);
		expect(changeById(m, 'c-0002')?.documents).toEqual(['drafting/talk.tex']);
		expect(changeById(m, 'nope')).toBeUndefined();
		expect(changesIn(m, MAIN).map((c) => c.id)).toEqual(['c-0001']);
		expect(pending(null)).toEqual([]);
	});

	it('names an edit in the file and a suggestion, and who made each', () => {
		expect(kindName(change({}))).toBe('Edit in the file');
		expect(kindName(suggestion)).toBe('Suggestion');
		expect(authorOf(change({}))).toEqual({ id: IN_THE_FILE, name: IN_THE_FILE });
		expect(authorOf(suggestion)).toEqual({ id: 'agent', name: 'Claude' });
		expect(whoMade({ reviewer: { name: 'agent', source: '' } }, suggestion)).toBe('you');
		expect(whoMade(null, suggestion)).toBe('Claude');
		expect(whoMade(null, change({}))).toBe('');
		// the manifest names a change's author by name
		expect(authorOf(change({ author: 'agent' }))).toEqual({ id: 'agent', name: 'agent' });
		expect(whoMade({ reviewer: { name: 'agent', source: '' } }, change({ author: 'agent' }))).toBe('you');
	});

	it('says what one does in a line', () => {
		expect(summary(change({}))).toBe('“a widget” → “a gadget”');
		expect(summary(change({ old: '' }))).toBe('add “a gadget”');
		expect(summary(change({ new: '' }))).toBe('remove “a widget”');
		expect(summary(change({ old: 'x'.repeat(80) })).length).toBeLessThan(80);
	});

	it('says why one that is not ready cannot be kept, in loom\'s words where it gives them', () => {
		expect(refusal(change({}))).toBe('');
		expect(refusal(change({ state: 'unplaced', why: 'an earlier suggestion overlaps it' }))).toBe('an earlier suggestion overlaps it');
		expect(refusal(change({ state: 'on-a-copy' }))).toMatch(/agent's copy/);
		expect(refusal(change({ state: 'taken' }))).toMatch(/already reads/);
	});

	it('says what Keep and Discard do, one and all', () => {
		expect(actSays(change({})).line).toBe('Already in the file. Discard writes your words back.');
		expect(actSays(suggestion).line).toBe('Not in the file yet. Keep writes it in.');
		expect(allSays([suggestion, change({}), change({ id: 'c-2' })])).toEqual({
			keep: 'Writes the 1 suggestion into the file and keeps the 2 edits already in it.',
			discard: 'Deletes the 1 suggestion and writes your old words back over the 2 edits.'
		});
		expect(allSays([])).toEqual({ keep: '', discard: '' });
	});

	it('groups them by the document that lists them, the person\'s own first, a change in no document under its file', () => {
		const masters = [
			{ path: '.loom/copies/aidoc.tex', agent: { name: 'Claude' }, copy_of: MAIN },
			{ path: MAIN, default: true },
			{ path: 'drafting/old.tex', closed: true }
		] as unknown as Manifest['masters'];
		const changes = [change({ id: 'c-1', documents: ['.loom/copies/aidoc.tex', MAIN] }), change({ id: 'c-2', documents: ['drafting/old.tex'], path: 'drafting/old.tex' }), change({ id: 'c-3', documents: ['.loom/copies/aidoc.tex'] }), change({ id: 'c-4', documents: [], path: 'notes/a.md', key: null })];
		const groups = byDocument({ masters, changes });
		expect(groups.map((g) => [g.path, g.document, g.changes.map((c) => c.id)])).toEqual([
			[MAIN, true, ['c-1']],
			['.loom/copies/aidoc.tex', true, ['c-3']],
			['drafting/old.tex', false, ['c-2']],
			['notes/a.md', false, ['c-4']]
		]);
	});
});

describe('changes in the stepper and the list', () => {
	const m = { annotations: { a1: { id: 'a1', status: 'open', type: null, author: { id: 'agent' }, in_reply_to: null } }, annotation_types: [], reviewer: { name: 'me', source: '' }, changes: [change({}), suggestion] } as unknown as Manifest;
	const state = (over: Partial<InstanceType<typeof Annotating>> = {}) => Object.assign(new Annotating(), { order: ['c-0001', 'a1', 'e-1', 'gone'] }, over);

	it('goes through annotations and changes in reading order, as the layer chosen lists them', () => {
		expect(entries(m, state(), false).map((e) => e.id)).toEqual(['c-0001', 'a1', 'e-1']);
		expect(entries(m, state({ layer: 'annotations' }), false).map((e) => e.id)).toEqual(['a1']);
		expect(entries(m, state({ layer: 'changes' }), false).map((e) => e.id)).toEqual(['c-0001', 'e-1']);
	});

	it('keeps every change in To do, leaves out an author the filter leaves out, and one just kept or discarded', () => {
		expect(entries(m, state({ todo: true }), false).map((e) => e.id)).toEqual(['c-0001', 'e-1']);
		expect(entries(m, state({ hidden: [IN_THE_FILE] }), false).map((e) => e.id)).toEqual(['a1', 'e-1']);
		mark(['e-1'], 'kept');
		expect(entries(m, state(), false).map((e) => e.id)).toEqual(['c-0001', 'a1']);
		prune({ changes: [change({})] });
		expect(acted.map).toEqual({});
	});
});

describe('Keep and Discard', () => {
	it('keeps changes by id, shown kept at once, and puts nothing on the undo history', async () => {
		live.changes = [change({}), suggestion];
		const going = keepChanges({ changes: ['c-0001'] });
		expect(acted.map).toEqual({ 'c-0001': 'kept' });
		answer = { ok: true, result: 'kept 1', done: ['c-0001'], refused: [] };
		await going;
		expect(calls).toEqual([['change-keep', { changes: ['c-0001'] }]]);
		expect(history.done).toHaveLength(0);
	});

	it('discards every ready change of a document; the suggestion among them is undone by change-discard with undo and done again, the edit in the file is not', async () => {
		live.changes = [change({}), suggestion, change({ id: 'c-x', state: 'unplaced' }), change({ id: 'c-t', documents: ['drafting/talk.tex'] })];
		answer = { ok: true, result: 'discarded 2', done: ['c-0001', 'e-1'], refused: [] };
		await discardChanges({ all: true, document: MAIN }, 'not wanted');
		expect(calls).toEqual([['change-discard', { all: true, document: MAIN, why: 'not wanted' }]]);
		expect(acted.map).toEqual({ 'c-0001': 'discarded', 'e-1': 'discarded' });
		expect(history.done).toHaveLength(1);
		expect(await undo()).toBe('');
		expect(calls.at(-1)).toEqual(['change-discard', { changes: ['e-1'], undo: true }]);
		expect(acted.map).toEqual({ 'c-0001': 'discarded' });
		expect(await redo()).toBe('');
		expect(calls.at(-1)).toEqual(['change-discard', { changes: ['e-1'] }]);
	});

	it('puts a discarded edit in the file on no history, its words being back in the file', async () => {
		live.changes = [change({})];
		answer = { ok: true, result: 'discarded 1', done: ['c-0001'], refused: [] };
		await discardChanges({ changes: ['c-0001'] });
		expect(history.done).toHaveLength(0);
	});

	it('shows a change refused, or an act refused whole, pending again', async () => {
		live.changes = [change({}), suggestion];
		answer = { ok: true, result: 'kept 1', done: ['c-0001'], refused: [{ id: 'e-1', why: 'author-only' }] };
		await keepChanges({ changes: ['c-0001', 'e-1'] });
		expect(acted.map).toEqual({ 'c-0001': 'kept' });
		answer = { ok: false, error: { code: 'no-such-change', message: 'gone' } };
		const res = await discardChanges({ changes: ['e-1'] });
		expect(res.ok).toBe(false);
		expect(acted.map).toEqual({ 'c-0001': 'kept' });
		expect(history.done).toHaveLength(0);
	});
});

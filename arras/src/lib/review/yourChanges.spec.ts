import { describe, expect, it } from 'vitest';
import fixture from '../../../tests/fixture/manifest.json';
import type { Manifest, PendingChange } from '$lib/manifest/types';
import { acceptanceOf, todoOf, waitingIn, yourChangesCount } from './yourChanges';

const m = fixture as unknown as Manifest;
const MAIN = 'drafting/main.tex';
const change = (over: Partial<PendingChange>): PendingChange => ({ id: 'c-0001', kind: 'edit', path: 'drafting/nodes/sy-0001.tex', key: 'sy-0001', documents: [MAIN], old: 'a', new: 'b', state: 'ready', ...over });
const withChanges = (...changes: PendingChange[]): Manifest => ({ ...m, changes });
const waits = m.unresolved!.filter((r) => r.cause !== 'never-accepted').length;

describe("one document's blocks waiting to be accepted", () => {
	it('lists a block changed since accepted once, with why it waits', () => {
		const a = acceptanceOf(m, MAIN);
		const rows = a.changed.filter((b) => b.key === 'sy-0001');
		expect(rows).toHaveLength(1);
		expect(rows[0].row?.cause).toBe('earlier-change');
	});

	it('keeps a block taken in with its source, apart from the changed', () => {
		const x = structuredClone(m);
		x.unresolved = x.unresolved!.map((r) => (r.key === 'sy-0001' ? { ...r, cause: 'adopted' as const, source_label: 'From the copy' } : r));
		const a = acceptanceOf(x, MAIN);
		expect(a.changed.some((b) => b.key === 'sy-0001')).toBe(false);
		expect(a.taken).toEqual([{ label: 'From the copy', rows: [expect.objectContaining({ key: 'sy-0001' })] }]);
	});

	it('folds the never accepted apart and counts only what waits', () => {
		const a = acceptanceOf(m, MAIN);
		expect(a.never.length).toBeGreaterThan(0);
		expect(a.never.every((b) => b.row?.cause === 'never-accepted')).toBe(true);
		expect(waitingIn(a)).toBe(a.changed.length + a.taken.reduce((n, t) => n + t.rows.length, 0));
	});

	it('says nothing of the pending changes, which are listed above it', () => {
		expect(acceptanceOf(withChanges(change({})), MAIN)).toEqual(acceptanceOf(m, MAIN));
	});
});

describe("the quilt's To do", () => {
	it('lists the open annotations from others, by where they are read, and not the reader\'s own', () => {
		const todo = todoOf(m);
		const ids = todo.flatMap((g) => g.annotations.map((a) => a.id));
		// open, of a type that stays open, by the agent: not the resolved ones, and not the reader's
		expect(ids).toContain('a-2026-09-16-ecnav2');
		expect(ids).not.toContain('a-2026-09-16-hwtkaw');
		expect(ids).not.toContain('a-2026-09-16-bns3an');
		expect(todo.every((g) => g.label && g.annotations.length)).toBe(true);
	});
});

describe('what Review counts', () => {
	it('counts each pending change, and each block waiting once', () => {
		expect(yourChangesCount(withChanges())).toBe(waits);
		expect(yourChangesCount(withChanges(change({}), change({ id: 'c-0002', key: null, documents: [] })))).toBe(waits + 2);
	});

	it('counts no entry that is not a pending change', () => {
		const x = { ...m, changes: [{ path: 'notes/intro.md', kind: 'changed' }] as unknown as PendingChange[] };
		expect(yourChangesCount(x)).toBe(waits);
	});
});

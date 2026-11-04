import { describe, expect, it } from 'vitest';
import fixture from '../../../tests/fixture/manifest.json';
import type { FileChange, Manifest } from '$lib/manifest/types';
import { otherFiles, waitingIn, yourChangesCount, yourChangesOf } from './yourChanges';

const m = fixture as unknown as Manifest;
const MAIN = 'drafting/main.tex';
const change = (over: Partial<FileChange>): FileChange => ({ path: 'drafting/nodes/sy-0001.tex', kind: 'changed', hash: 'h', hunks: 1, diff: 'd', blocks: [['sy-0001']], documents: [MAIN], ...over });
const withChanges = (...changes: FileChange[]): Manifest => ({ ...m, changes });

describe('one document as Your Changes lists it', () => {
	it('lists a block edited and changed once, with its edit', () => {
		const y = yourChangesOf(withChanges(change({})), MAIN);
		const rows = y.changed.filter((b) => b.key === 'sy-0001');
		expect(rows).toHaveLength(1);
		expect(rows[0].row?.cause).toBe('earlier-change');
		expect(rows[0].edit?.hunks).toEqual([0]);
	});

	it('gathers a block\'s changes, and leaves those touching none outside', () => {
		const y = yourChangesOf(withChanges(change({ hunks: 3, blocks: [['sy-0001'], [], ['sy-0001']] })), MAIN);
		expect(y.changed.find((b) => b.key === 'sy-0001')?.edit?.hunks).toEqual([0, 2]);
		expect(y.outside.map((e) => e.hunks)).toEqual([[1]]);
	});

	it('draws an edit across two blocks under the first, and the second says so', () => {
		const y = yourChangesOf(withChanges(change({ blocks: [['sy-0001', 'sy-0002']] })), MAIN);
		expect(y.changed.find((b) => b.key === 'sy-0002')).toMatchObject({ edit: undefined, editedWith: 'sy-0001' });
	});

	it('lifts an edited block out of Never accepted and out of Accepted', () => {
		const accepted = yourChangesOf(withChanges(), MAIN).accepted[0].key;
		const y = yourChangesOf(withChanges(change({ blocks: [['sy-000B', accepted]] })), MAIN);
		expect(y.never.some((b) => b.key === 'sy-000B')).toBe(false);
		expect(y.changed.find((b) => b.key === 'sy-000B')?.row?.cause).toBe('never-accepted');
		expect(y.accepted.some((k) => k.key === accepted)).toBe(false);
		const stands = y.changed.find((b) => b.key === accepted);
		expect(stands?.row).toBeUndefined();
		expect(stands?.editedWith).toBe('sy-000B');
	});

	it('keeps a block taken in with its source, its edit on it', () => {
		const x = withChanges(change({}));
		x.unresolved = x.unresolved!.map((r) => (r.key === 'sy-0001' ? { ...r, cause: 'adopted' as const, source_label: 'From the copy' } : r));
		const y = yourChangesOf(x, MAIN);
		expect(y.changed.some((b) => b.key === 'sy-0001')).toBe(false);
		expect(y.taken).toEqual([{ label: 'From the copy', rows: [expect.objectContaining({ key: 'sy-0001', edit: expect.anything() })] }]);
	});

	it('leaves another document\'s file out', () => {
		const y = yourChangesOf(withChanges(change({ documents: ['drafting/talk.tex'] })), MAIN);
		expect(y.changed.find((b) => b.key === 'sy-0001')?.edit).toBeUndefined();
	});
});

describe('what stands apart, and what Review counts', () => {
	it('sets a file in no document apart, and an empty new file with it', () => {
		const lone = change({ path: 'notes/a.md', blocks: [[]], documents: [] });
		const empty = change({ path: 'drafting/new.tex', kind: 'new', hunks: 0, blocks: [] });
		expect(otherFiles(withChanges(lone, empty, change({}))).map((c) => c.path)).toEqual(['notes/a.md', 'drafting/new.tex']);
	});

	it('counts a block once, never-accepted ones only when edited', () => {
		const waits = m.unresolved!.filter((r) => r.cause !== 'never-accepted').length;
		expect(yourChangesCount(withChanges())).toBe(waits);
		expect(yourChangesCount(withChanges(change({})))).toBe(waits);
		expect(yourChangesCount(withChanges(change({ blocks: [['sy-000B']] })))).toBe(waits + 1);
	});

	it('counts text outside any block by its file, and a file in no document', () => {
		const waits = m.unresolved!.filter((r) => r.cause !== 'never-accepted').length;
		expect(yourChangesCount(withChanges(change({ hunks: 2, blocks: [[], []] }), change({ path: 'notes/a.md', blocks: [[]], documents: [] })))).toBe(waits + 2);
	});

	it('says how many rows of one document wait', () => {
		const waits = m.unresolved!.filter((r) => r.cause !== 'never-accepted').length;
		const y = yourChangesOf(withChanges(change({ hunks: 2, blocks: [['sy-0001'], []] })), MAIN);
		expect(waitingIn(y)).toBe(y.changed.length + 1);
		expect(waitingIn(y)).toBeLessThanOrEqual(waits + 1);
	});
});

import { describe, expect, it } from 'vitest';
import type { Manifest, UnresolvedReview } from '$lib/manifest/types';
import { documentsWithBlocks, groupsOf, notesOf, takenLabel, waitingCount } from './queue';

const row = (key: string, cause: UnresolvedReview['cause'], more: Partial<UnresolvedReview> = {}): UnresolvedReview => ({ key, cause, pull: '', changed_text: false, refusal: '', ...more });

const m = {
	nodes: {
		a: { reached_by: ['main.tex'] },
		b: { reached_by: ['main.tex'] },
		c: { reached_by: ['main.tex', 'talk.tex'] },
		d: { reached_by: ['main.tex'] },
		e: { reached_by: ['talk.tex'] },
		f: { reached_by: ['main.tex'] }
	},
	keys: {
		a: { key: 'a', node: 'a', kind: 'statement', acceptance: { author: 'X', date: '2026-11-01', fresh: false } },
		b: { key: 'b', node: 'b', kind: 'statement' },
		c: { key: 'c', node: 'c', kind: 'statement' },
		d: { key: 'd', node: 'd', kind: 'statement' },
		e: { key: 'e', node: 'e', kind: 'statement' },
		f: { key: 'f', node: 'f', kind: 'statement', acceptance: { author: 'X', date: '2026-11-01', fresh: true }, reviews: { open: { revision: 2, question: 0 } } }
	},
	unresolved: [
		row('a', 'earlier-change'),
		row('b', 'adopted', { contribution: '.loom/copies/examples-shared.tex' }),
		row('c', 'adopted', { source_label: 'Taken in from the copy “aidoc”' }),
		row('d', 'never-accepted', { refusal: 'It is marked incomplete.' }),
		row('e', 'never-accepted')
	],
	diagnostics: [{ severity: 'warning', code: 'loom:missing-proof', message: '', locations: [], keys: ['d'] }],
	annotation_types: [{ id: 'revision', name: 'Revision' }]
} as unknown as Manifest;

describe('blocks not freshly accepted', () => {
	it("groups one document's blocks by why they wait, and folds those accepted apart", () => {
		const g = groupsOf(m, 'main.tex');
		expect(g.changed.map((r) => r.key)).toEqual(['a']);
		expect(g.taken.map((t) => [t.label, t.rows.map((r) => r.key)])).toEqual([
			['Taken in from the copy “examples-shared”', ['b']],
			['Taken in from the copy “aidoc”', ['c']]
		]);
		expect(g.never.map((r) => r.key)).toEqual(['d']);
		expect(g.accepted.map((k) => k.key)).toEqual(['f']);
		expect(groupsOf(m, 'talk.tex').never.map((r) => r.key)).toEqual(['e']);
	});

	it('counts what changed or was taken in, not what was never accepted', () => {
		expect(waitingCount(m)).toBe(3);
	});

	it('heads a taken-in group by its source, the copy named when loom gives no label', () => {
		expect([takenLabel(row('x', 'adopted', { contribution: 'a/b/copy.tex' })), takenLabel(row('x', 'incoming-pull'))]).toEqual(['Taken in from the copy “copy”', 'Taken in from a pull']);
	});

	it('offers only documents that reach a block', () => {
		expect(documentsWithBlocks(m, [{ path: 'main.tex' }, { path: 'empty.tex' }]).map((d) => d.path)).toEqual(['main.tex']);
	});

	it('notes a statement owed a proof and the annotations open on it', () => {
		expect([notesOf(m, 'd'), notesOf(m, 'f'), notesOf(m, 'e')]).toEqual([['no proof yet'], ['2 open revisions'], []]);
	});
});

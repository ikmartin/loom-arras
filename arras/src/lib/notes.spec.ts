import { describe, expect, it, vi } from 'vitest';
import type { Manifest } from '$lib/manifest/types';
import { notesWhere, noteWhere } from './notes';
import { reviewLanding, sectionsOf } from './review/sections';
import { toApply, toConsider } from './review/suggestions';
import { itemForQuilt } from './workspace/links';
import { linkName } from './workspace/names';

vi.mock('$app/navigation', () => ({ goto: vi.fn(async () => {}) }));

// The least of a manifest that notes and Review's new sections read (plan 0.22.8).
const note = (id: string, target: object, extra: object = {}) => ({ id, when: '2026-10-01', author: { kind: 'person', id: 'Tester' }, session: 's-2026-10-01-p8efk5', target, body: '', faded: false, detached: false, ...extra });
const m = {
	corpus: { name: 'q', root_label: 'q' },
	masters: [{ path: 'paper/main.tex', default: true }],
	nodes: { 'q-0001': { kind: 'environment', taxon: 'lemma', numbers: {}, reached_by: ['paper/main.tex'] } },
	keys: {},
	regions: {},
	references: { Arden24: { citekey: 'Arden24', bib: { title: 'A work' }, artifacts: { pdf: true } } },
	annotations: {
		'a-2026-10-01-cvhc9q': { id: 'a-2026-10-01-cvhc9q', kind: 'suggestion', target: { key: 'q-0001' }, status: 'open', in_reply_to: null, payload: 'Each orbit', placement: 'replace' },
		'a-2026-10-01-7r1qv5': { id: 'a-2026-10-01-7r1qv5', kind: 'suggestion', target: { key: 'q-0001' }, status: 'open', in_reply_to: null, payload: null },
		'a-2026-10-01-t80mpe': { id: 'a-2026-10-01-t80mpe', kind: 'suggestion', target: { key: 'q-0001' }, status: 'resolved', in_reply_to: null },
		'a-2026-10-01-5qj7dk': { id: 'a-2026-10-01-5qj7dk', kind: 'objection', target: { key: 'q-0001' }, status: 'open', in_reply_to: null }
	},
	sessions: [],
	threads: {},
	diagnostics: [],
	files: [{ path: 'notes/a.md', kind: 'markdown', bytes: 1 }],
	notes: {
		'n-2026-10-01-yp3fkn': note('n-2026-10-01-yp3fkn', { file: 'notes/a.md' }, { when: '2026-10-01', quote: 'The orbit is finite, as the lemma says.' }),
		'n-2026-10-01-8db5r2': note('n-2026-10-01-8db5r2', { key: 'q-0001' }, { when: '2026-10-02', faded: true }),
		'n-2026-10-01-chvjxn': note('n-2026-10-01-chvjxn', { citekey: 'Arden24' }, { when: '2026-10-03', page: 3, rects: [[1, 2, 3, 4]] })
	},
	changes: [{ path: 'notes/a.md', kind: 'changed', diff: 'changes/notes/a.md.diff' }],
	changes_since: { who: 'Tester', when: '2026-10-01T08:00:00Z' }
} as unknown as Manifest;

describe('notes', () => {
	it('are listed newest first, a faded one only when asked for', () => {
		expect(notesWhere(m, () => true).map((n) => n.id)).toEqual(['n-2026-10-01-chvjxn', 'n-2026-10-01-yp3fkn']);
		expect(notesWhere(m, () => true, true)).toHaveLength(3);
	});

	it('say where they are, open there, and are named by their words', () => {
		expect(noteWhere(m.notes!['n-2026-10-01-chvjxn'])).toBe('Arden24, p. 3');
		// a note on the whole work names the work, and opens on its Info
		const whole = { ...m.notes!['n-2026-10-01-chvjxn'], id: 'n-2026-10-01-0hbm3w', page: undefined };
		expect(noteWhere(whole)).toBe('Arden24');
		expect(itemForQuilt({ ...m, notes: { ...m.notes, [whole.id]: whole } }, whole.id)).toEqual({ kind: 'work', id: 'Arden24', view: 'info' });
		expect(itemForQuilt(m, 'n-2026-10-01-yp3fkn')).toEqual({ kind: 'file', id: 'notes/a.md' });
		expect(itemForQuilt(m, 'n-2026-10-01-chvjxn')).toEqual({ kind: 'work', id: 'Arden24', place: { page: 3 } });
		expect(linkName(m, 'quilt:n-2026-10-01-yp3fkn')).toBe('“The orbit is finite, as the lemma says.”');
	});
});

describe('Review as the meta view', () => {
	it('leads with the person\'s text, and counts the suggestions with text to put in', () => {
		const sections = sectionsOf(m);
		expect(sections.map((s) => s.id)).toEqual(['changes', 'proposed', 'problems', 'library', 'record']);
		expect(sections.find((s) => s.id === 'changes')!.waits).toBe(1);
		// a count is what waits for the author: an open session waits for no one
		expect(sections.find((s) => s.id === 'record')!.waits).toBe(0);
		expect(reviewLanding(sections)).toBe(sections.find((s) => s.id === 'changes')!.href);
		expect(toApply(m).map((a) => a.id)).toEqual(['a-2026-10-01-cvhc9q']);
		// one in prose alone is weighed, not applied, and not counted
		expect(toConsider(m).map((a) => a.id)).toEqual(['a-2026-10-01-7r1qv5']);
		expect(sections.find((s) => s.id === 'proposed')!.waits).toBe(1);
	});
});

import { describe, expect, it, vi } from 'vitest';
import type { Manifest } from '$lib/manifest/types';
import { reviewLanding, sectionsOf } from './sections';
import { editAnswering, openEdits } from './suggestions';
import { itemForQuilt } from '$lib/workspace/links';

vi.mock('$app/navigation', () => ({ goto: vi.fn(async () => {}) }));

// The least of a manifest that Review's sections and an annotation on a PDF's page read.
const m = {
	corpus: { name: 'q', root_label: 'q' },
	masters: [{ path: 'paper/main.tex', default: true }],
	nodes: { 'q-0001': { kind: 'environment', taxon: 'lemma', numbers: {}, reached_by: ['paper/main.tex'] } },
	keys: {},
	regions: {},
	references: { Arden24: { citekey: 'Arden24', work: 'arXiv:2401.00001', bib: { title: 'A work' }, artifacts: { pdf: true } } },
	annotations: {
		'a-2026-10-01-7r1qv5': { id: 'a-2026-10-01-7r1qv5', type: 'suggestion', target: { key: 'q-0001' }, status: 'open', in_reply_to: null },
		'a-2026-10-01-5qj7dk': { id: 'a-2026-10-01-5qj7dk', type: 'revision', target: { key: 'q-0001' }, status: 'open', in_reply_to: null },
		'a-2026-10-01-pdf001': { id: 'a-2026-10-01-pdf001', type: null, target: { key: 'notes/a.pdf', file: 'notes/a.pdf', page: 2 }, status: 'open', in_reply_to: null, mark: 'box', rects: [[1, 2, 3, 4]] },
		'a-2026-10-01-work01': { id: 'a-2026-10-01-work01', type: null, target: { key: 'arXiv:2401.00001', work: 'Arden24', page: null }, status: 'open', in_reply_to: null }
	},
	suggested_edits: {
		'e-2026-10-01-cvhc9q': { id: 'e-2026-10-01-cvhc9q', target: { key: 'q-0001', hash: '' }, quote: 'Every orbit', with: 'Each orbit', placement: 'replace', answers: 'a-2026-10-01-7r1qv5', status: 'open', created: '2026-10-01T10:00:00Z' },
		'e-2026-10-01-t80mpe': { id: 'e-2026-10-01-t80mpe', target: { key: 'q-0001', hash: '' }, quote: 'Every orbit', with: 'All orbits', placement: 'replace', answers: null, status: 'discarded', created: '2026-10-01T11:00:00Z' }
	},
	sessions: [],
	threads: {},
	diagnostics: [],
	files: [{ path: 'notes/a.md', kind: 'markdown', bytes: 1 }, { path: 'notes/a.pdf', kind: 'pdf', bytes: 1 }],
	changes: [
		{ id: 'c-1a2b3c4d', kind: 'edit', path: 'notes/a.md', key: null, documents: [], old: 'a', new: 'b', state: 'ready' },
		{ id: 'e-2026-10-01-cvhc9q', kind: 'suggested', path: 'paper/main.tex', key: 'q-0001', documents: ['paper/main.tex'], old: 'Every orbit', new: 'Each orbit', state: 'ready', answers: 'a-2026-10-01-7r1qv5' }
	],
	changes_since: { who: 'Tester', when: '2026-10-01T08:00:00Z' }
} as unknown as Manifest;

describe('Review as the meta view', () => {
	it("leads with the person's text, and counts every pending change there, a suggested edit among them", () => {
		const sections = sectionsOf(m);
		expect(sections.map((s) => s.id)).toEqual(['changes', 'proposed', 'problems', 'library', 'record']);
		expect(sections.find((s) => s.id === 'changes')!.waits).toBe(2);
		// a count is what waits for the author: an open session waits for no one
		expect(sections.find((s) => s.id === 'record')!.waits).toBe(0);
		expect(reviewLanding(sections)).toBe(sections.find((s) => s.id === 'changes')!.href);
		// a discarded one is not counted
		expect(openEdits(m).map((e) => e.id)).toEqual(['e-2026-10-01-cvhc9q']);
		// it is kept or discarded where it stands, so nothing is proposed
		expect(sections.find((s) => s.id === 'proposed')!.waits).toBe(0);
		// and the annotation it answers knows it
		expect(editAnswering(m, 'a-2026-10-01-7r1qv5')?.id).toBe('e-2026-10-01-cvhc9q');
		expect(editAnswering(m, 'a-2026-10-01-5qj7dk')).toBeUndefined();
	});
});

describe('an annotation on a PDF', () => {
	it("opens a project PDF at its page with its mark, and a cited work's Info when it is on the whole work", () => {
		expect(itemForQuilt(m, 'a-2026-10-01-pdf001')).toEqual({ kind: 'file', id: 'notes/a.pdf', anchor: 'page=2', note: 'a-2026-10-01-pdf001' });
		expect(itemForQuilt(m, 'a-2026-10-01-work01')).toEqual({ kind: 'work', id: 'Arden24', view: 'info' });
	});
});

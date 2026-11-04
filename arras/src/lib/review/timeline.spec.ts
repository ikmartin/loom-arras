import { describe, expect, it } from 'vitest';
import type { CanonDoc, HistoryAct, Manifest } from '$lib/manifest/types';
import { actWords, actsOf, neighbours, versionLabel, versionsOf } from './timeline';

const v = (step: string, more: Partial<CanonDoc> = {}): CanonDoc => ({ path: `.loom/history/${step}-v/v${step}.tex`, stem: `v${step}`, title: '', fragment: '', hash: '', step, in: 'drafting/main.tex', ...more });

describe('a document’s versions', () => {
	const m = { canon: [v('0003', { message: 'Kept an edit', kept_for: 'keep' }), v('0001', { action: 'import', message: 'ignored' }), v('0005', { message: 'Before referee' }), v('0004', { in: 'drafting/talk.tex' })] } as unknown as Manifest;

	it('are its own, oldest first, each named by the act it was kept at', () => {
		expect(versionsOf(m, 'drafting/main.tex').map(versionLabel)).toEqual(['Imported', 'Kept an edit', 'Before referee']);
	});

	it('step older and newer among the document’s own, and past the newest to the live text', () => {
		const n = neighbours(m, v('0003').path);
		expect([n?.older?.step, n?.newer?.step, n?.doc]).toEqual(['0001', '0005', 'drafting/main.tex']);
		expect(neighbours(m, v('0005').path)?.newer).toBeNull();
	});
});

describe('everything recorded', () => {
	const a = (action: string, more: Partial<HistoryAct> = {}): HistoryAct => ({ action, when: '2026-11-04T00:00:00Z', ...more });

	it('says each act in words', () => {
		expect([
			actWords(a('keep', { path: 'drafting/nodes/x.tex' })),
			actWords(a('keep', { paths: ['a', 'b'] })),
			actWords(a('undo', { path: 'README.md', to: 'sha256:1' })),
			actWords(a('undo', { path: 'new.md', to: undefined })),
			actWords(a('stamp', { landmark: 'l', message: 'Before referee', in: 'drafting/main.tex' })),
			actWords(a('restore', { in: 'drafting/main.tex', version: 'v.tex' })),
			actWords(a('restore', { path: 'README.md' })),
			actWords(a('move', { from: 'notes/a.md', to: 'drafts/b.md' })),
			actWords(a('move', { from: 'drafting-ai/x.tex', to: '.loom/copies/x.tex' })),
			actWords(a('something-new'))
		]).toEqual([
			'Kept an edit to x.tex',
			'Kept every change (2 files)',
			'Undid an edit to README.md',
			'Removed the new file new.md, keeping its text',
			'Recorded the version “Before referee” of main.tex',
			'Put main.tex back as a version',
			'Put back in README.md the text an undo set aside',
			'Moved a.md to b.md',
			'Moved drafting-ai/x.tex to .loom/copies/x.tex',
			'something new'
		]);
	});

	it('lists them newest first, leaving out the versions a timeline shows beside their act, and keeps a document’s own when asked', () => {
		const m = {
			history: { steps: [], acts: [a('keep', { path: 'drafting/main.tex' }), a('stamp', { kept_for: 'keep', in: 'drafting/main.tex', landmark: 'l' }), a('page-write', { path: 'notes/a.md', page: 'notes/a.md' })] }
		} as unknown as Manifest;
		expect(actsOf(m).map((x) => x.action)).toEqual(['page-write', 'keep']);
		expect(actsOf(m, 'drafting/main.tex', new Set(['drafting/main.tex'])).map((x) => x.action)).toEqual(['keep']);
	});
});

// The workbench's pure parts: routing a document by kind, the tone a conflicted state reads as, the badge that names a recorded text, and grouping diagnostics by what they are about.
import { describe, expect, it } from 'vitest';
import { canonUrl, docUrl } from './nav';
import { stateClass, stateTone } from './state';
import { versionLabel } from './badges';
import { groupBySubject, subjectOf } from './diagnostics';
import type { Diagnostic, Key } from './manifest/types';

const m = {
	masters: [{ path: 'drafting/main.tex' }],
	canon: [{ path: 'canon/widgets-v1.tex' }]
};

describe('routing', () => {
	it('sends a landmark to its own page and a draft to the read view', () => {
		expect(canonUrl('canon/widgets-v1.tex')).toBe('/canon/widgets-v1');
		expect(docUrl(m, 'canon/widgets-v1.tex')).toBe('/canon/widgets-v1');
		expect(docUrl(m, 'drafting/main.tex')).toBe('/master/main');
		expect(docUrl(null, 'drafting/main.tex')).toBe('/master/main');
	});
});

describe('states', () => {
	const labels = { incomplete: { color: 'negative' as const }, conflicted: { color: 'negative' as const } };
	it('tells conflicted from incomplete although the interface colours them alike', () => {
		expect(stateTone(labels, 'conflicted')).toBe('conflicted');
		expect(stateTone(labels, 'incomplete')).toBe('incomplete');
		expect(stateClass(labels, 'conflicted')).toBe('tone-conflicted');
	});
	it('falls back for a state it has never seen', () => {
		expect(stateTone(labels, 'invented')).toBe('loose');
	});
});

describe('version label', () => {
	it('names the step a key\'s current text was recorded at, and says nothing otherwise', () => {
		expect(versionLabel({ version: { step: '0003', name: 'paper-v2' } } as Key)).toBe('text of @3 (paper-v2)');
		expect(versionLabel({ version: { step: '0001' } } as Key)).toBe('text of @1');
		expect(versionLabel({} as Key)).toBe('');
		expect(versionLabel(undefined)).toBe('');
	});
});

describe('subjects', () => {
	const d = (code: string, subject?: string): Diagnostic =>
		({ severity: 'error', code, message: '', locations: [], keys: [], subject }) as Diagnostic;
	it('treats a diagnostic that names no subject as being about the source', () => {
		expect(subjectOf(d('dangling-link'))).toBe('source');
		expect(subjectOf(d('loom:canon-edited', 'record'))).toBe('record');
	});
	it('groups source first, then the record, then anything else', () => {
		const groups = groupBySubject([d('a', 'record'), d('b'), d('c', 'elsewhere'), d('d', 'source')]);
		expect(groups.map((g) => g.subject)).toEqual(['source', 'record', 'elsewhere']);
		expect(groups[0].items).toHaveLength(2);
	});
});

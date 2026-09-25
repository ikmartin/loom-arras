import { describe, expect, it } from 'vitest';
import { groupBySubject, groupDiagnostics, subjectOf } from './diagnostics';
import type { Diagnostic } from './manifest/types';

describe('diagnostics grouping', () => {
	it('groups by code, errors first, and gives unknown codes the generic affordance', () => {
		const groups = groupDiagnostics([
			{ severity: 'info', code: 'zzz:made-up', message: 'x', locations: [], keys: [] },
			{ severity: 'error', code: 'duplicate-id', message: 'y', locations: [], keys: [] },
			{ severity: 'error', code: 'duplicate-id', message: 'z', locations: [], keys: [] }
		]);
		expect(groups.map((g) => [g.code, g.items.length, g.affordance])).toEqual([
			['duplicate-id', 2, 'both-locations'],
			['zzz:made-up', 1, 'generic']
		]);
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

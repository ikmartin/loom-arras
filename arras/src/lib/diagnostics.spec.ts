import { describe, expect, it } from 'vitest';
import { groupDiagnostics } from './diagnostics';

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

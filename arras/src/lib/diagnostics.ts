// Diagnostics grouped by code with the reserved-code affordances of book 10.6. Unknown codes render generically; nothing here fails on a code it has never seen.
import type { Diagnostic } from './manifest/types';

export interface Group {
	code: string;
	severity: string;
	items: Diagnostic[];
	affordance: 'both-locations' | 'source' | 'site' | 'paths' | 'cycle' | 'filter' | 'generic';
}

const AFFORDANCE: Record<string, Group['affordance']> = {
	'duplicate-id': 'both-locations',
	'dangling-link': 'source',
	'missing-include': 'site',
	'double-inclusion': 'paths',
	'inclusion-cycle': 'cycle',
	unreachable: 'filter'
};

export function groupDiagnostics(items: Diagnostic[]): Group[] {
	const map = new Map<string, Group>();
	for (const d of items) {
		let g = map.get(d.code);
		if (!g) {
			g = { code: d.code, severity: d.severity, items: [], affordance: AFFORDANCE[d.code] ?? 'generic' };
			map.set(d.code, g);
		}
		g.items.push(d);
	}
	const order = { error: 0, warning: 1, info: 2 } as Record<string, number>;
	return [...map.values()].sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3) || a.code.localeCompare(b.code));
}

export function countBySeverity(items: Diagnostic[]): Record<string, number> {
	const out: Record<string, number> = {};
	for (const d of items) out[d.severity] = (out[d.severity] ?? 0) + 1;
	return out;
}

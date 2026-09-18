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

/** The two kinds of thing a diagnostic can be about: the source, and loom's own record of it (book 10.2.5). A diagnostic that names no subject is about the source. */
export function subjectOf(d: Diagnostic): string {
	return d.subject ?? 'source';
}

const SUBJECT_ORDER = ['source', 'record'];

/** Diagnostics by subject, source first, in the order they were given. */
export function groupBySubject(items: Diagnostic[]): { subject: string; items: Diagnostic[] }[] {
	const map = new Map<string, Diagnostic[]>();
	for (const d of items) {
		const s = subjectOf(d);
		if (!map.has(s)) map.set(s, []);
		map.get(s)!.push(d);
	}
	return [...map.entries()]
		.map(([subject, xs]) => ({ subject, items: xs }))
		.sort((a, b) => {
			const ai = SUBJECT_ORDER.indexOf(a.subject);
			const bi = SUBJECT_ORDER.indexOf(b.subject);
			return (ai < 0 ? 9 : ai) - (bi < 0 ? 9 : bi) || a.subject.localeCompare(b.subject);
		});
}

export function countBySeverity(items: Diagnostic[]): Record<string, number> {
	const out: Record<string, number> = {};
	for (const d of items) out[d.severity] = (out[d.severity] ?? 0) + 1;
	return out;
}

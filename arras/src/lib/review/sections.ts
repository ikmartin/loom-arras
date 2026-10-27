// Review's sections, the quilt's management, each with a count of what waits for the author there: the column lists them, and the count is what a glance at it is for.

import type { Manifest } from '$lib/manifest/types';
import { route } from '$lib/paths';

export interface Section {
	id: 'needs-review' | 'incoming' | 'library' | 'sessions' | 'history' | 'problems';
	label: string;
	href: string;
	/** What waits for the author there; 0 shows no count. */
	waits: number;
	/** What the count counts, for its title. */
	says: string;
}

/** The proposed results waiting to be verified, the works with no copy filed that are not declared unreadable, and the open citation suggestions. */
export function libraryWaits(m: Manifest): { proposed: number; unfiled: number; citations: number } {
	const works = Object.values(m.references ?? {});
	return {
		proposed: works.reduce((n, r) => n + Object.values(r.results ?? {}).filter((x) => x.state === 'proposed').length, 0),
		unfiled: works.filter((r) => !r.artifacts?.pdf && !r.unreadable && !r.version_of).length,
		citations: Object.values(m.annotations ?? {}).filter((a) => a.kind === 'citation' && !a.in_reply_to && !a.discarded && a.status === 'open').length
	};
}

/** Every section, in the order the column lists them; Sessions and History only where the corpus has them. */
export function sectionsOf(m: Manifest): Section[] {
	const review = (m.unresolved ?? []).filter((r) => r.status === 'needs-review').length;
	const incoming = (m.contributions ?? []).length;
	const lib = libraryWaits(m);
	const open = (m.sessions ?? []).filter((s) => s.state === 'open').length;
	const orphans = (m.canon ?? []).filter((c) => c.step && !c.in).length;
	const problems = m.diagnostics.filter((d) => d.severity === 'error' || d.severity === 'warning').length;
	const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
	const sections: Section[] = [
		{ id: 'needs-review', label: 'Needs review', href: route('/review'), waits: review, says: count(review, 'block needs review', 'blocks need review') },
		{ id: 'incoming', label: 'Incoming', href: route('/review/incoming'), waits: incoming, says: count(incoming, 'contribution waits', 'contributions wait') },
		{
			id: 'library',
			label: 'Library',
			href: route('/review/library'),
			waits: lib.proposed + lib.unfiled + lib.citations,
			says: [count(lib.proposed, 'proposed result', 'proposed results'), count(lib.unfiled, 'work with no copy', 'works with no copy'), count(lib.citations, 'citation suggestion', 'citation suggestions')].join(', ')
		},
		{ id: 'sessions', label: 'Sessions', href: route('/review/sessions'), waits: open, says: count(open, 'open session', 'open sessions') },
		{ id: 'history', label: 'History', href: route('/review/history'), waits: orphans, says: count(orphans, 'landmark no draft leads to', 'landmarks no draft leads to') },
		{ id: 'problems', label: 'Problems', href: route('/review/problems'), waits: problems, says: count(problems, 'error or warning', 'errors and warnings') }
	];
	return sections.filter((x) => (x.id !== 'sessions' || m.publishes?.discussions !== false) && (x.id !== 'history' || (m.history?.steps.length ?? 0) > 0 || (m.canon ?? []).length > 0));
}

/** Which section a route is, by its route id. */
export function sectionOf(routeId: string | null): Section['id'] | null {
	const at = (routeId ?? '').replace(/^\/review\/?/, '');
	if (routeId === '/review') return 'needs-review';
	return (['incoming', 'library', 'sessions', 'history', 'problems'] as const).find((id) => at === id) ?? null;
}

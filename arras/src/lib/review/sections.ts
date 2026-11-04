// Review's sections, the quilt's management, each with a count of what waits for the author there and nothing else: the column lists them, and the count is what a glance at it is for, so a section where nothing waits (Sessions) shows none. Review is the meta view (plan 0.22.8): what changed in the open files since the person's look, then the mathematics to accept, the contributions to take in, the suggestions to apply, the library, sessions, history and problems.

import type { Manifest } from '$lib/manifest/types';
import { route } from '$lib/paths';
import { needsYou } from '$lib/library';
import { yoursCount } from '$lib/diagnostics';
import { waitingCount } from './queue';

export interface Section {
	id: 'changes' | 'needs-review' | 'incoming' | 'suggestions' | 'library' | 'sessions' | 'history' | 'problems';
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

/** The open suggestions, each waiting for the author to apply its patch: neither replies nor withdrawn. */
export function openSuggestions(m: Manifest) {
	return Object.values(m.annotations ?? {}).filter((a) => a.kind === 'suggestion' && !a.in_reply_to && !a.discarded && a.status === 'open');
}

/** Every section, in the order the column lists them; Changes only after a look, Sessions and History only where the corpus has them. */
export function sectionsOf(m: Manifest): Section[] {
	const review = waitingCount(m);
	const incoming = (m.contributions ?? []).length;
	const lib = libraryWaits(m);
	const wanting = needsYou(m);
	const open = (m.sessions ?? []).filter((s) => s.state === 'open').length;
	const orphans = (m.canon ?? []).filter((c) => c.step && !c.in).length;
	const problems = yoursCount(m);
	const changed = (m.changes ?? []).length;
	const suggestions = openSuggestions(m).length;
	const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
	const sections: Section[] = [
		{ id: 'changes', label: 'Changes', href: route('/review/changes'), waits: changed, says: count(changed, 'file changed since your look', 'files changed since your look') },
		{ id: 'needs-review', label: 'Needs review', href: route('/review'), waits: review, says: count(review, 'block changed or taken in', 'blocks changed or taken in') },
		{ id: 'incoming', label: 'Incoming', href: route('/review/incoming'), waits: incoming, says: count(incoming, 'contribution waits', 'contributions wait') },
		{ id: 'suggestions', label: 'Suggestions', href: route('/review/suggestions'), waits: suggestions, says: count(suggestions, 'suggestion to apply', 'suggestions to apply') },
		{
			id: 'library',
			label: 'Library',
			href: route('/review/library'),
			waits: wanting + lib.citations,
			says: [count(wanting, 'work needs you', 'works need you'), count(lib.citations, 'citation suggestion', 'citation suggestions')].join(', ')
		},
		// an open session waits for no one, so it is said on hover and never counted
		{ id: 'sessions', label: 'Sessions', href: route('/review/sessions'), waits: 0, says: count(open, 'open session', 'open sessions') },
		{ id: 'history', label: 'History', href: route('/review/history'), waits: orphans, says: count(orphans, 'landmark no draft leads to', 'landmarks no draft leads to') },
		{ id: 'problems', label: 'Problems', href: route('/review/problems'), waits: problems, says: count(problems, 'error or warning in your files', 'errors and warnings in your files') }
	];
	return sections.filter(
		(x) =>
			(x.id !== 'changes' || !!m.changes_since) &&
			(x.id !== 'sessions' || m.publishes?.discussions !== false) &&
			(x.id !== 'history' || (m.history?.steps.length ?? 0) > 0 || (m.canon ?? []).length > 0)
	);
}

/** Which section a route is, by its route id. */
export function sectionOf(routeId: string | null): Section['id'] | null {
	const at = (routeId ?? '').replace(/^\/review\/?/, '');
	if (routeId === '/review') return 'needs-review';
	return (['changes', 'incoming', 'suggestions', 'library', 'sessions', 'history', 'problems'] as const).find((id) => at === id) ?? null;
}

/** Where the Review tab opens: the first section where something waits, else Changes once there is a look, else Needs review. */
export function reviewLanding(sections: Section[]): string {
	return (sections.find((s) => s.waits > 0) ?? sections.find((s) => s.id === 'changes') ?? sections.find((s) => s.id === 'needs-review'))?.href ?? route('/review');
}

// Review's sections, the quilt's management, each with a line saying what it is for and a count of what waits for the author there and nothing else: the column lists them, and the count is what a glance at it is for, so a section where nothing waits shows none. Review is the meta view (plan 0.22.8): the person's text and what waits on it, what others propose, what is wrong, and what has been done.

import type { Manifest } from '$lib/manifest/types';
import { route } from '$lib/paths';
import { yoursCount } from '$lib/diagnostics';
import { proposedCount } from './proposed';
import { yourTextCount } from './yourText';

export interface Section {
	id: 'text' | 'proposed' | 'problems' | 'record';
	label: string;
	/** What the section is for, under its name. */
	blurb: string;
	href: string;
	/** What waits for the author there; 0 shows no count. */
	waits: number;
	/** What the count counts, for its title. */
	says: string;
}

/** Every section, in the order the column lists them; Record only where the corpus has something for it. */
export function sectionsOf(m: Manifest): Section[] {
	const text = yourTextCount(m);
	const proposed = proposedCount(m);
	const open = (m.sessions ?? []).filter((s) => s.state === 'open').length;
	const orphans = (m.canon ?? []).filter((c) => c.step && !c.in).length;
	const problems = yoursCount(m);
	const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
	const sections: Section[] = [
		{ id: 'text', label: 'Your text', blurb: 'edits to keep, mathematics to accept', href: route('/review'), waits: text, says: count(text, 'edit or block waits on you', 'edits and blocks wait on you') },
		{ id: 'proposed', label: 'Proposed to you', blurb: 'from agents and collaborators', href: route('/review/proposed'), waits: proposed, says: count(proposed, 'proposal to decide', 'proposals to decide') },
		{ id: 'problems', label: 'Problems', blurb: "what's wrong in your files", href: route('/review/problems'), waits: problems, says: count(problems, 'error or warning in your files', 'errors and warnings in your files') },
		{ id: 'record', label: 'Record', blurb: 'versions, sessions, everything done', href: route('/review/record'), waits: orphans, says: [count(open, 'open session', 'open sessions'), count(orphans, 'version no document leads to', 'versions no document leads to')].join(', ') }
	];
	return sections.filter((x) => x.id !== 'record' || m.publishes?.discussions !== false || (m.history?.steps.length ?? 0) > 0 || (m.canon ?? []).length > 0);
}

/** Which section a route is, by its route id. */
export function sectionOf(routeId: string | null): Section['id'] | null {
	if (routeId === '/review') return 'text';
	if (routeId === '/review/record' || routeId?.startsWith('/review/record/')) return 'record';
	return (['proposed', 'problems'] as const).find((id) => routeId === `/review/${id}`) ?? null;
}

/** Where the Review tab opens: the first section where something waits, else Your text. */
export function reviewLanding(sections: Section[]): string {
	return (sections.find((s) => s.waits > 0) ?? sections.find((s) => s.id === 'text'))?.href ?? route('/review');
}

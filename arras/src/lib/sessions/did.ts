// What a session did, read from its command log: the annotations it recorded, grouped by the block they are on, and every other command it ran, one row per command however often it ran. Nothing is read from a command's words; what a line names (`names`) and what it made (`annotation`) are loom's.
import type { Annotation, Manifest, Thread } from '$lib/manifest/types';

type Line = Thread['log'][number];
export type Named = NonNullable<Line['names']>[number];

/** The annotations a session made or changed on one block, each once, in the order the log first names them. */
export interface Recorded {
	key: string;
	annotations: Annotation[];
}

/** A command the session ran, with how many times and when last, and what it names. */
export interface Ran {
	command: string;
	count: number;
	last: string;
	names: Named[];
}

/**
 * The log as the session's record: what it recorded, by block, and what else it ran, by command, each in the order the log first holds it.
 *
 * Parameters
 * ----------
 * m : Pick<Manifest, 'annotations'>
 *     The manifest, for the annotations a line names.
 * log : Line[]
 *     The session's command log (`threads[id].log`).
 *
 * Returns
 * -------
 * { recorded: Recorded[]; ran: Ran[] }
 */
export function didOf(m: Pick<Manifest, 'annotations'>, log: Line[]): { recorded: Recorded[]; ran: Ran[] } {
	const recorded = new Map<string, Recorded>();
	const seen = new Set<string>();
	const ran = new Map<string, Ran>();
	for (const e of log) {
		const a = e.annotation ? m.annotations[e.annotation] : undefined;
		if (a) {
			if (seen.has(a.id)) continue;
			seen.add(a.id);
			const key = a.target.key;
			if (!recorded.has(key)) recorded.set(key, { key, annotations: [] });
			recorded.get(key)!.annotations.push(a);
			continue;
		}
		const r = ran.get(e.command);
		if (r) {
			r.count += 1;
			if (e.time > r.last) r.last = e.time;
		} else ran.set(e.command, { command: e.command, count: 1, last: e.time, names: e.names ?? [] });
	}
	return { recorded: [...recorded.values()], ran: [...ran.values()] };
}

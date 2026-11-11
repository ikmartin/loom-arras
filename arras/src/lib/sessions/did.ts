// What a session did, read from its command log: every command it ran, one row per command however often it ran. Nothing is read from a command's words; what a line names (`names`) is loom's. Annotations belong to no session, so the log names none.
import type { Thread } from '$lib/manifest/types';

type Line = Thread['log'][number];
export type Named = NonNullable<Line['names']>[number];

/** A command the session ran, with how many times and when last, and what it names. */
export interface Ran {
	command: string;
	count: number;
	last: string;
	names: Named[];
}

/**
 * The log as the session's record: what it ran, by command, in the order the log first holds it.
 *
 * Parameters
 * ----------
 * log : Line[]
 *     The session's command log (`threads[id].log`).
 *
 * Returns
 * -------
 * { ran: Ran[] }
 */
export function didOf(log: Line[]): { ran: Ran[] } {
	const ran = new Map<string, Ran>();
	for (const e of log) {
		const r = ran.get(e.command);
		if (r) {
			r.count += 1;
			if (e.time > r.last) r.last = e.time;
		} else ran.set(e.command, { command: e.command, count: 1, last: e.time, names: e.names ?? [] });
	}
	return { ran: [...ran.values()] };
}

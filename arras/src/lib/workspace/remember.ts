// The workspace's address remembered across visits, per corpus, so `/` reopens what was open as it was left: a reload, or the next day, as well as a return from Review. In this browser only, as the display preferences are; a browser that cannot store it just starts at the default document.

import type { Manifest } from '$lib/manifest/types';
import { itemFromPath } from './item';

const KEY = 'arras.workspace';

function read(): Record<string, string> {
	try {
		const raw = globalThis.localStorage?.getItem(KEY);
		const o = raw ? JSON.parse(raw) : {};
		return o && typeof o === 'object' ? (o as Record<string, string>) : {};
	} catch {
		return {};
	}
}

/** The address last open in this corpus, or `''`. */
export function remembered(corpus: string): string {
	const at = read()[corpus];
	return typeof at === 'string' ? at : '';
}

/** Keep the address now open in this corpus. */
export function remember(corpus: string, address: string): void {
	try {
		const all = read();
		if (all[corpus] === address) return;
		all[corpus] = address;
		globalThis.localStorage?.setItem(KEY, JSON.stringify(all));
	} catch {
		// a browser that cannot store it still has the address for this visit, in the workspace
	}
}

/** The address remembered for this corpus, when what its first pane opens is still in it; `''` otherwise, so a deleted draft or a removed work falls through to the default. */
export function rememberedIn(m: Manifest): string {
	const at = remembered(m.corpus.name);
	const it = at ? itemFromPath(m, at) : null;
	if (!it) return '';
	const there =
		it.kind === 'document'
			? m.masters.some((x) => x.path === it.id) || (m.canon ?? []).some((x) => x.path === it.id)
			: it.kind === 'work'
				? !!m.references?.[it.id]
				: it.kind === 'session'
					? (m.sessions ?? []).some((x) => x.id === it.id) || !!m.threads[it.id]
					: it.kind === 'page'
						? it.id === 'state' && !!m.research_state
						: !!m.nodes[it.id];
	return there ? at : '';
}

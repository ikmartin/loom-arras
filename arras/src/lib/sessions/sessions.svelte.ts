// Which session the viewer is showing, and what that means for the page (plan 0.13 §5, §7).
//
// **The selection governs the page, not only the panel.** Whatever the side panel is showing — this session, or all —
// is what the content marks, so a tick's count is of *visible* annotations. Because a page can therefore look lightly
// annotated when it is not, the content pane says how many are hidden rather than letting the reader believe the page.
//
// It is a view, never a write target: writing always lands in the session loom says is active, whatever is being shown.
// A reader looking at everything and writing into the active one is the common case, and a viewer that silently moved
// the write target when the view changed would be filing work where it was not meant to go.

import type { Annotation, Manifest, SessionRow } from '$lib/manifest/types';

const KEY = 'arras.session-view';

class SessionView {
	/** The session being shown, or `all`. Never where writing goes. */
	showing = $state<string>('all');
	/** Whether a closed session's annotations are shown; they are hidden by default, which is what closing one is for. */
	closed = $state(false);

	load(): void {
		try {
			const raw = globalThis.localStorage?.getItem(KEY);
			const o = raw ? JSON.parse(raw) : {};
			if (typeof o?.showing === 'string') this.showing = o.showing;
			this.closed = o?.closed === true;
		} catch {
			// a viewer that cannot read its stored view shows everything, which is the honest default
		}
	}

	save(): void {
		try {
			globalThis.localStorage?.setItem(KEY, JSON.stringify({ showing: this.showing, closed: this.closed }));
		} catch {
			// a viewer that cannot store the view still uses it for this session
		}
	}
}

export const sessionView = new SessionView();

/** The session loom is writing into, or null when it says none is active. */
export function active(m: Manifest | null): SessionRow | null {
	return (m?.sessions ?? []).find((s) => s.active) ?? null;
}

/** Whether an annotation is visible under the current selection. */
export function visible(m: Manifest | null, a: Annotation): boolean {
	const showing = sessionView.showing;
	if (showing !== 'all') return a.run === showing;
	if (sessionView.closed) return true;
	const shut = new Set((m?.sessions ?? []).filter((s) => s.state !== 'open').map((s) => s.id));
	return !shut.has(a.run);
}

/** How many of `list` the selection is hiding, for the quiet notice in the content pane's header. */
export function hidden(m: Manifest | null, list: readonly Annotation[]): number {
	return list.filter((a) => !visible(m, a)).length;
}

/** Sessions grouped the way the panel shows them: the active one, the other open ones, and the closed. */
export function grouped(m: Manifest | null): { active: SessionRow | null; recent: SessionRow[]; closed: SessionRow[] } {
	const rows = m?.sessions ?? [];
	return {
		active: rows.find((s) => s.active) ?? null,
		recent: rows.filter((s) => !s.active && s.state === 'open'),
		closed: rows.filter((s) => s.state !== 'open')
	};
}

/** What one session holds: how many are open in it, who took part, and how many arrived in the current round. */
export function summary(m: Manifest | null, id: string): { open: number; who: string[]; fresh: number } {
	const rows = Object.values(m?.annotations ?? {}).filter((a) => a.run === id && !a.in_reply_to && !a.discarded);
	const since = (m?.sessions ?? []).find((s) => s.id === id)?.opened ?? '';
	return {
		open: rows.filter((a) => a.status !== 'resolved').length,
		who: [...new Set(Object.values(m?.annotations ?? {}).filter((a) => a.run === id).map((a) => a.author.id))],
		fresh: since ? Object.values(m?.annotations ?? {}).filter((a) => a.run === id && a.created >= since).length : 0
	};
}

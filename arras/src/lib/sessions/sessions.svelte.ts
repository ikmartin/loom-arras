// The session selection, and what it governs (plan 0.13.1).
//
// **One selection, shared by open and closed sessions alike.** There is no "selected open session" and no separate
// "selected closed session"; there is a selected session, or none, and it is where writes land. The session travels
// with the write from the writer's own context — the author's from this selection, an agent's from the session it is
// attached to — so nothing reads a global pointer, and an agent asked in one session answers into it however the
// author has since moved.
//
// **The view toggle filters annotations, never the list.** `current` draws the selected session's annotations; `all`
// draws every session the closed setting admits. The panel's list always shows every session, because it is how a
// reader navigates and hiding rows would only make sessions hard to find.
//
// A write is available only while an *open* session is selected. Nothing is created automatically: the courtesy of
// opening a session so the first note has somewhere to go belongs to the terminal, where there is no selection to
// consult, and in the viewer it would silently decide where work was filed.

import type { Annotation, Manifest, SessionRow } from '$lib/manifest/types';

const KEY = 'arras.session-view';

class SessionView {
	/** The session writes land in, or null when none is selected. Open or closed — one selection covers both. */
	selected = $state<string | null>(null);
	/** `current` draws only the selected session's annotations; `all` draws every session `showClosed` admits. */
	view = $state<'current' | 'all'>('all');
	/** Whether closed sessions' annotations are drawn at all. Hidden by default, which is what closing one is for. */
	showClosed = $state(false);

	load(): void {
		try {
			const raw = globalThis.localStorage?.getItem(KEY);
			const o = raw ? JSON.parse(raw) : {};
			this.selected = typeof o?.selected === 'string' ? o.selected : null;
			this.view = o?.view === 'current' ? 'current' : 'all';
			this.showClosed = o?.showClosed === true;
		} catch {
			// a viewer that cannot read its stored view shows everything and selects nothing, which is the honest default
		}
	}

	save(): void {
		try {
			globalThis.localStorage?.setItem(KEY, JSON.stringify({ selected: this.selected, view: this.view, showClosed: this.showClosed }));
		} catch {
			// a viewer that cannot store the view still uses it for this visit
		}
	}

	/** Select one, or deselect it when it is already selected — which is how the author detaches from every session. */
	pick(id: string, m: Manifest | null): void {
		if (this.selected === id) {
			this.selected = null;
		} else {
			this.selected = id;
			// A closed session cannot be selected and hidden at once, so selecting one admits the closed.
			if (row(m, id)?.state !== 'open') this.showClosed = true;
		}
		this.save();
	}

	/** After a session closes or goes: the selection cannot stand, and `current` would have nothing to draw. */
	dropped(id: string): void {
		if (this.selected !== id) return;
		this.selected = null;
		if (this.view === 'current') this.view = 'all';
		this.save();
	}
}

export const sessionView = new SessionView();

function row(m: Manifest | null, id: string | null): SessionRow | null {
	return id ? ((m?.sessions ?? []).find((s) => s.id === id) ?? null) : null;
}

/** The selected session, or null. */
export function selected(m: Manifest | null): SessionRow | null {
	return row(m, sessionView.selected);
}

/**
 * Why a write is unavailable, or `''` when it is allowed.
 *
 * The two sentences live here and are read by every write surface, so the interface cannot word the same refusal two ways.
 */
export function writable(m: Manifest | null): string {
	const s = selected(m);
	if (!s) return 'No session selected: either select a session or start a new session.';
	if (s.state !== 'open') return 'Selected session is closed: either select an open session or reopen the closed session.';
	return '';
}

/** Whether an annotation is drawn under the current view. */
export function visible(m: Manifest | null, a: Annotation): boolean {
	if (sessionView.view === 'current') return a.run === sessionView.selected;
	if (sessionView.showClosed) return true;
	const shut = new Set((m?.sessions ?? []).filter((s) => s.state !== 'open').map((s) => s.id));
	return !shut.has(a.run);
}

/** How many of `list` the view is hiding, for the quiet notice in the content pane's header. */
export function hidden(m: Manifest | null, list: readonly Annotation[]): number {
	return list.filter((a) => !visible(m, a)).length;
}

/** The one list the panel draws, and the closed ones behind their own section. */
export function grouped(m: Manifest | null): { open: SessionRow[]; closed: SessionRow[] } {
	const rows = m?.sessions ?? [];
	return { open: rows.filter((s) => s.state === 'open'), closed: rows.filter((s) => s.state !== 'open') };
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

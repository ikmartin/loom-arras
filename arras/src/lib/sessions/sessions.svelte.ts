// The session selection, and what it governs (plan 0.13.1).
//
// **One selection, shared by open and closed sessions alike.** There is no "selected open session" and no separate
// "selected closed session"; there is a selected session, or none, and it is where writes land. The session travels
// with the write from the writer's own context — the author's from this selection, an agent's from the session it is
// attached to — so nothing reads a global pointer, and an agent asked in one session answers into it however the
// author has since moved.
//
// **Annotations belong to no session.** An annotation carries its author, time and version, and is written whatever is selected; a session is a sitting with its transcript, and the selection is where a write that names one goes, such as verifying a proposed result. Hiding every annotation is a pane's own (`workspace.hideNotes`).
//
// A write that names a session is available only while an *open* one is selected. Nothing is created automatically: the courtesy of
// opening a session so the first note has somewhere to go belongs to the terminal, where there is no selection to
// consult, and in the viewer it would silently decide where work was filed.

import type { Manifest, SessionRow } from '$lib/manifest/types';

const KEY = 'arras.session-view';

class SessionView {
	/** The session writes land in, or null when none is selected. Open or closed — one selection covers both. */
	selected = $state<string | null>(null);
	/** Names asked for and not yet in the manifest, by session id: a rename shows at once rather than after the publisher rebuilds. */
	renamed = $state<Record<string, string>>({});

	load(): void {
		try {
			const raw = globalThis.localStorage?.getItem(KEY);
			const o = raw ? JSON.parse(raw) : {};
			this.selected = typeof o?.selected === 'string' ? o.selected : null;
		} catch {
			// a viewer that cannot read its stored selection selects nothing, which is the honest default
		}
	}

	save(): void {
		try {
			globalThis.localStorage?.setItem(KEY, JSON.stringify({ selected: this.selected }));
		} catch {
			// a viewer that cannot store the selection still uses it for this visit
		}
	}

	/** Select one: where writes go. Selecting the selected session again keeps it; `clear` is how the author detaches from every session. Reading a session's transcript selects nothing; only choosing it does. */
	select(id: string): void {
		this.selected = id;
		this.save();
	}

	/** Select nothing: writes that name a session are refused until something is selected. */
	clear(): void {
		this.selected = null;
		this.save();
	}

	/** After a session closes or goes: the selection cannot stand. */
	dropped(id: string): void {
		if (this.selected === id) this.clear();
	}
}

export const sessionView = new SessionView();

function row(m: Manifest | null, id: string | null): SessionRow | null {
	return id ? ((m?.sessions ?? []).find((s) => s.id === id) ?? null) : null;
}

/** A session's name as the reader last set it: the pending rename while the manifest still carries the old one. */
export function titleOf(s: SessionRow): string {
	return sessionView.renamed[s.id] ?? s.title;
}

/** The selected session, or null. */
export function selected(m: Manifest | null): SessionRow | null {
	return row(m, sessionView.selected);
}

/**
 * Why a write that names a session (verifying or discarding a proposed result) is unavailable, or `''` when it is allowed. An annotation names none.
 *
 * The two sentences live here and are read by every write surface, so the interface cannot word the same refusal two ways.
 */
export function writable(m: Manifest | null): string {
	const s = selected(m);
	if (!s) return 'No session selected: either select a session or start a new session.';
	if (s.state !== 'open') return 'Selected session is closed: either select an open session or reopen the closed session.';
	return '';
}

/** The one list the picker draws, and the closed ones behind their own section. */
export function grouped(m: Manifest | null): { open: SessionRow[]; closed: SessionRow[] } {
	const rows = m?.sessions ?? [];
	// Most recently touched first. The index is append-only and was shown in creation order, so the sitting you were in five minutes ago sat at the bottom of the list under everything you had finished with.
	const recent = (a: SessionRow, b: SessionRow) => (b.opened || b.created).localeCompare(a.opened || a.created);
	return {
		open: rows.filter((s) => s.state === 'open').sort(recent),
		closed: rows.filter((s) => s.state !== 'open').sort(recent)
	};
}

/**
 * The picker's list narrowed by its find field.
 *
 * A case-blind match on the title as the reader last set it (a pending rename included) and the purpose; a blank field matches all. `closedCount` counts every closed session, found or not, since it labels the fold that holds them.
 */
export function findSessions(m: Manifest | null, find: string): { open: SessionRow[]; closed: SessionRow[]; closedCount: number } {
	const all = grouped(m);
	const q = find.trim().toLowerCase();
	const hit = (s: SessionRow) => !q || `${titleOf(s)} ${s.purpose ?? ''}`.toLowerCase().includes(q);
	return { open: all.open.filter(hit), closed: all.closed.filter(hit), closedCount: all.closed.length };
}

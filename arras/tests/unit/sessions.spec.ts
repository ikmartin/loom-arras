// One selection and what it governs (plan 0.13.1). The three axes that decide whether an annotation is drawn — the view, the session's state, and whether closed ones are admitted — are independent, so they are tested as a grid rather than as a happy path.
import { beforeEach, describe, expect, it } from 'vitest';
import { findSessions, grouped, hidden, selected, sessionView, visible, writable } from '$lib/sessions/sessions.svelte';
import { touched, when } from '$lib/sessions/when';
import type { Annotation, Manifest, SessionRow } from '$lib/manifest/types';

function session(id: string, state: string, title = id): SessionRow {
	return { id, title, state, created: '2026-09-01T10:00:00Z', opened: '2026-09-01T10:00:00Z', rounds: 1, active: false };
}

function note(id: string, run: string): Annotation {
	return { id, run, target: { key: 'n-1' }, kind: 'note', body: '', author: { id: 'a', kind: 'human' }, created: '2026-09-02T10:00:00Z', status: 'open' } as unknown as Annotation;
}

const m = {
	sessions: [session('s-open', 'open'), session('s-other', 'open'), session('s-shut', 'closed')],
	annotations: {}
} as unknown as Manifest;

beforeEach(() => {
	sessionView.selected = null;
	sessionView.view = 'all';
	sessionView.showClosed = false;
});

describe('the selection', () => {
	it('is one selection, shared by open and closed sessions', () => {
		sessionView.select('s-open', m);
		expect(selected(m)?.id).toBe('s-open');
		// picking a closed one moves the same selection rather than keeping a second
		sessionView.select('s-shut', m);
		expect(selected(m)?.id).toBe('s-shut');
	});

	it('keeps the selection when the selected row is picked again; clearing is how the author detaches', () => {
		sessionView.select('s-open', m);
		sessionView.select('s-open', m);
		expect(sessionView.selected).toBe('s-open');
		sessionView.view = 'current';
		sessionView.clear();
		expect(sessionView.selected).toBeNull();
		expect(sessionView.view).toBe('all');
	});

	it('admits closed sessions when one is selected, so selected-and-hidden cannot arise', () => {
		expect(sessionView.showClosed).toBe(false);
		sessionView.select('s-shut', m);
		expect(sessionView.showClosed).toBe(true);
	});

	it('clears, and widens the view, when the selected session goes', () => {
		sessionView.select('s-open', m);
		sessionView.view = 'current';
		sessionView.dropped('s-other');
		expect(sessionView.selected).toBe('s-open'); // a different session going leaves it alone
		sessionView.dropped('s-open');
		expect(sessionView.selected).toBeNull();
		expect(sessionView.view).toBe('all'); // `current` with nothing selected has nothing to draw
	});
});

describe('whether a write is allowed', () => {
	it('refuses with nothing selected, and says which of the two problems it is', () => {
		expect(writable(m)).toBe('No session selected: either select a session or start a new session.');
	});

	it('refuses a closed session with the other sentence', () => {
		sessionView.select('s-shut', m);
		expect(writable(m)).toBe('Selected session is closed: either select an open session or reopen the closed session.');
	});

	it('allows it only with an open session selected', () => {
		sessionView.select('s-open', m);
		expect(writable(m)).toBe('');
	});
});

describe('what the page draws', () => {
	/** The sessions whose note `visible` draws, one note per session. */
	const drawn = () => [note('a', 's-open'), note('b', 's-other'), note('c', 's-shut')].filter((n) => visible(m, n)).map((n) => n.run);

	it('under `current`, only the selected session, whatever its state', () => {
		sessionView.select('s-open', m);
		sessionView.view = 'current';
		expect(drawn()).toEqual(['s-open']);
	});

	it('under `current` with nothing selected, nothing at all', () => {
		sessionView.view = 'current';
		expect(drawn()).toEqual([]);
	});

	it('under `all`, every open session but no closed one', () => {
		expect(drawn()).toEqual(['s-open', 's-other']);
	});

	it('under `all` with closed admitted, the closed ones too', () => {
		sessionView.showClosed = true;
		expect(drawn()).toEqual(['s-open', 's-other', 's-shut']);
	});

	it('counts what it is keeping off the page', () => {
		expect(hidden(m, [note('a', 's-open'), note('c', 's-shut')])).toBe(1);
	});
});

describe('the list', () => {
	it('separates open from closed and never filters by the view', () => {
		sessionView.view = 'current';
		sessionView.selected = 's-open';
		const g = grouped(m);
		expect(g.open.map((s) => s.id)).toEqual(['s-open', 's-other']);
		expect(g.closed.map((s) => s.id)).toEqual(['s-shut']);
	});
});

describe("the picker's find field", () => {
	const found = (q: string) => {
		const g = findSessions(rows, q);
		return { open: g.open.map((s) => s.id), closed: g.closed.map((s) => s.id), closedCount: g.closedCount };
	};
	const rows = {
		sessions: [
			{ ...session('s-ref', 'open', 'Referee report'), purpose: 'answer the referee' },
			session('s-talk', 'open', 'Talk slides'),
			{ ...session('s-old', 'closed', 'Old referee pass'), purpose: 'first round' }
		],
		annotations: {}
	} as unknown as Manifest;
	beforeEach(() => (sessionView.renamed = {}));

	it('lists everything when blank, and counts every closed session', () => {
		expect(found('  ')).toEqual({ open: ['s-ref', 's-talk'], closed: ['s-old'], closedCount: 1 });
	});

	it('matches the title and the purpose, blind to case and surrounding space', () => {
		expect(found(' REFEREE ')).toEqual({ open: ['s-ref'], closed: ['s-old'], closedCount: 1 });
		expect(found('first round')).toEqual({ open: [], closed: ['s-old'], closedCount: 1 });
	});

	it('matches a pending rename rather than the name the manifest still carries', () => {
		sessionView.renamed['s-talk'] = 'Colloquium';
		expect(found('colloq').open).toEqual(['s-talk']);
		expect(found('slides').open).toEqual([]);
	});

	it('finds nothing, and still counts the closed fold, when nothing matches', () => {
		expect(found('zzz')).toEqual({ open: [], closed: [], closedCount: 1 });
	});
});

describe('when a session was touched', () => {
	const now = new Date('2026-09-21T12:00:00');
	it('says it the way a person would', () => {
		expect(when('2026-09-21T09:00:00', now)).toBe('today');
		expect(when('2026-09-20T09:00:00', now)).toBe('yesterday');
		expect(when('2026-09-17T09:00:00', now)).toBe('Thursday');
		expect(when('2026-09-14T09:00:00', now)).toBe('last week');
		expect(when('', now)).toBe('');
	});

	it('says of a closed session that it closed then', () => {
		expect(touched('2026-09-21T09:00:00', 'open', now)).toBe('today');
		expect(touched('2026-09-21T09:00:00', 'closed', now)).toBe('closed today');
	});
});

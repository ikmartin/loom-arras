// A session's transcript as the Chat reads it (plan 0.14): the build's pages for what was said before, and — where a publisher is serving — a poll of `/_api/events` for what lands now.
//
// **Out of the manifest.** Every viewer polls the manifest, so a long conversation there would make every poll pay for it. The build writes the transcript beside it in pages of a hundred events (specs/manifest.md §10.1), which a viewer reads with or without a publisher; the session's `seq` in the manifest says which page is the last.
//
// **A gap resyncs rather than stitching.** The poll's answer carries the inbox's own last sequence number; when what arrived starts further on than what we hold, some were missed, and the honest response is to ask again from where we are.

import { base } from '$app/paths';
import { dataUrl } from '$lib/paths';
import type { WriteResult } from '$lib/write';

/** An annotation a message carried, as the inbox recorded it. */
export interface Change {
	id: string;
	kind: string;
	target: string;
	act: string;
	by: string;
	body?: string;
	work?: string | null;
	page?: number | null;
}

/** One event in a session's inbox, in its published form. */
export interface ChatEvent {
	seq: number;
	kind: string;
	who: string;
	when: string;
	body?: string;
	body_html?: string;
	changed?: Change[];
}

export interface Listener {
	who: string;
	kind: string;
}

/** What the publisher says of the agent it may start for a turn (plan 0.14): whether it does, the agent's name, and how the last turn went. */
export interface AgentState {
	launch: boolean;
	name: string;
	state?: 'running' | 'done' | 'failed' | 'stopped';
	error?: string;
	activity?: string;
	/** When the last turn started, so a turn begun after a send can be told from one before it. */
	started?: string;
	/** What keeps loom from starting the agent at all, where launching is on. */
	blocked?: string;
}

/** The publisher's answer to a posted message: the session it landed in and who was listening. */
export interface Posted extends WriteResult {
	session?: string;
	seq?: number;
	attached?: Listener[];
}

/** Events per page in the build (specs/manifest.md §10.1). */
export const PAGE = 100;

export class Transcript {
	readonly session: string;
	events = $state<ChatEvent[]>([]);
	/** The lowest page loaded, so scrolling up knows what to ask for next; 0 once the first page is in. */
	page = $state(0);
	/** Who the publisher says is listening, or null where no publisher answers. */
	attached = $state<Listener[] | null>(null);
	/** The agent the publisher starts, or null where no publisher answers. */
	agent = $state<AgentState | null>(null);
	loading = $state(false);

	constructor(session: string) {
		this.session = session;
	}

	/** The last sequence number held. */
	get last(): number {
		return this.events.length ? this.events[this.events.length - 1].seq : 0;
	}

	/** Whether there are earlier pages to load. */
	get more(): boolean {
		return this.page > 1;
	}

	#merge(got: ChatEvent[]): void {
		if (!got.length) return;
		const by = new Map(this.events.map((e) => [e.seq, e]));
		for (const e of got) by.set(e.seq, e);
		this.events = [...by.values()].sort((a, b) => a.seq - b.seq);
	}

	async #page(n: number): Promise<ChatEvent[]> {
		try {
			const r = await fetch(dataUrl(`transcripts/${encodeURIComponent(this.session)}/${n}.json`));
			if (!r.ok) return [];
			const j = await r.json();
			return Array.isArray(j?.events) ? j.events : [];
		} catch {
			return [];
		}
	}

	/** The page holding message `seq`. A page that does not meet what is held replaces it: merged, the gap between them would read as nothing said there, and scrolling up would never fill it. */
	async load(seq: number): Promise<void> {
		const n = Math.max(1, Math.ceil(seq / PAGE));
		this.loading = true;
		const got = seq ? await this.#page(n) : [];
		const meets = this.events.length > 0 && (n - 1) * PAGE + 1 <= this.last + 1 && n * PAGE >= this.events[0].seq - 1;
		if (meets) this.page = Math.min(this.page, n);
		else {
			this.events = [];
			this.page = n;
		}
		this.#merge(got);
		this.loading = false;
	}

	/** The page before the earliest one held. */
	async older(): Promise<void> {
		if (!this.more || this.loading) return;
		this.loading = true;
		const n = this.page - 1;
		this.#merge(await this.#page(n));
		this.page = n;
		this.loading = false;
	}

	/** The last sequence number a serving publisher holds, or null where none answers: the manifest's goes stale under a publisher, since a message rebuilds nothing. */
	async latest(): Promise<number | null> {
		try {
			const r = await fetch(`${base}/_api/events?session=${encodeURIComponent(this.session)}&since=${Number.MAX_SAFE_INTEGER}`);
			if (!r.ok) return null;
			const j = await r.json();
			return typeof j?.seq === 'number' ? j.seq : null;
		} catch {
			return null;
		}
	}

	/** What has landed since the last message held, from a serving publisher; nothing where none answers. */
	async poll(): Promise<void> {
		const since = this.last;
		try {
			const r = await fetch(`${base}/_api/events?session=${encodeURIComponent(this.session)}&since=${since}`);
			if (!r.ok) return;
			const j = await r.json();
			const got: ChatEvent[] = Array.isArray(j?.events) ? j.events : [];
			this.attached = Array.isArray(j?.attached) ? j.attached : [];
			this.agent = j?.agent && typeof j.agent === 'object' ? j.agent : null;
			// events we were not given between what we hold and what arrived: ask again from the start
			if (got.length && got[0].seq > since + 1 && since > 0) {
				await this.load(j.seq ?? got[got.length - 1].seq);
				return;
			}
			this.#merge(got);
		} catch {
			/* a publisher that stopped answering leaves the transcript as it was */
		}
	}
}

/** Whether a speaker declared themselves an agent: the word `Agent`, `AI`, `bot` or `assistant` in their name, as loom decides it. */
export function isAgent(who: string): boolean {
	return /\b(agent|ai|bot|assistant)\b/i.test(who);
}

/** What a message carried, as one line of counts: kinds in the order they first appear, replies counted apart (`carried 2 questions, 1 note, 1 reply`). Never the annotations themselves, which are read where they stand. */
export function carried(changed: Change[] | undefined): string {
	if (!changed?.length) return '';
	const counts = new Map<string, number>();
	for (const c of changed) {
		const what = c.act === 'replied' ? 'reply' : c.kind;
		counts.set(what, (counts.get(what) ?? 0) + 1);
	}
	const plural = (w: string, n: number) => (n === 1 ? w : w === 'reply' ? 'replies' : `${w}s`);
	return 'carried ' + [...counts].map(([w, n]) => `${n} ${plural(w, n)}`).join(', ');
}

/** One row of what the next message will carry, as the publisher reports it. */
export interface PacketRow {
	id: string;
	kind: string;
	act: string;
	target: string;
	work?: string | null;
	page?: number | null;
}

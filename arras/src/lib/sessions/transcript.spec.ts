// The Chat's transcript against a stubbed network: the build's pages under `build/transcripts/`, and a publisher's `/_api/events` that says what landed since a sequence number.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Transcript, type ChatEvent } from './transcript.svelte';

const ev = (seq: number): ChatEvent => ({ seq, kind: 'message', who: 'Ann', when: '2026-09-24T10:00:00Z', body: `m${seq}` });
const range = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => a + i);
const seqs = (t: Transcript) => t.events.map((e) => e.seq);

/** A stub network: `pages[n]` the build's page n, `events(since)` the publisher's answer or null for none serving. Every URL asked for is kept. */
function network(pages: Record<number, number[]>, events: ((since: number) => unknown) | null) {
	const asked: string[] = [];
	vi.stubGlobal('fetch', async (url: string) => {
		asked.push(url);
		const page = /\/build\/transcripts\/s-1\/(\d+)\.json$/.exec(url);
		if (page) {
			const held = pages[Number(page[1])];
			return held ? Response.json({ events: held.map(ev) }) : new Response('', { status: 404 });
		}
		const api = /\/_api\/events\?session=s-1&since=(\d+)$/.exec(url);
		if (api && events) return Response.json(events(Number(api[1])));
		if (api) throw new TypeError('fetch failed');
		return new Response('', { status: 404 });
	});
	return asked;
}

afterEach(() => vi.unstubAllGlobals());

describe('a poll', () => {
	it('merges what arrives right after what is held, asking for no page', async () => {
		const asked = network({ 1: [1, 2, 3] }, (since) => ({ seq: 5, events: [4, 5].filter((s) => s > since).map(ev), attached: [{ who: 'Referee', kind: 'terminal' }], agent: { launch: true, name: 'Claude' } }));
		const t = new Transcript('s-1');
		await t.load(3);
		await t.poll();
		expect(seqs(t)).toEqual([1, 2, 3, 4, 5]);
		expect(asked.filter((u) => u.includes('/transcripts/'))).toHaveLength(1);
		expect(asked.at(-1)).toBe('/_api/events?session=s-1&since=3');
		expect(t.attached).toEqual([{ who: 'Referee', kind: 'terminal' }]);
		expect(t.agent).toEqual({ launch: true, name: 'Claude' });
	});

	it('takes what arrives into an empty transcript, which has nothing to have missed', async () => {
		network({}, () => ({ seq: 6, events: [5, 6].map(ev) }));
		const t = new Transcript('s-1');
		await t.poll();
		expect(seqs(t)).toEqual([5, 6]);
	});

	it('reloads from the server’s seq when what arrived skips past what is held, and ends contiguous', async () => {
		// the publisher answers with 6 and 7; 4 and 5 were never delivered, and the build's page 1 now holds them
		const pages: Record<number, number[]> = { 1: [1, 2, 3] };
		const asked = network(pages, () => ({ seq: 7, events: [6, 7].map(ev) }));
		const t = new Transcript('s-1');
		await t.load(3);
		pages[1] = range(1, 7);
		await t.poll();
		expect(seqs(t)).toEqual(range(1, 7));
		expect(asked.at(-1)).toBe('/build/transcripts/s-1/1.json');
	});

	it('reloads the page the server’s seq is on, not the page of the last event it sent', async () => {
		// the inbox has run on to 120: its page does not meet 1–3, so it replaces them rather than leaving a hole
		const asked = network({ 1: [1, 2, 3], 2: range(101, 120) }, () => ({ seq: 120, events: [6, 7].map(ev) }));
		const t = new Transcript('s-1');
		await t.load(3);
		await t.poll();
		expect(asked.at(-1)).toBe('/build/transcripts/s-1/2.json');
		expect(seqs(t)).toEqual(range(101, 120));
		expect(t.page).toBe(2);
		expect(t.more).toBe(true);
	});

	it('leaves the transcript as it was when no publisher answers', async () => {
		network({ 1: [1, 2, 3] }, null);
		const t = new Transcript('s-1');
		await t.load(3);
		await t.poll();
		expect(seqs(t)).toEqual([1, 2, 3]);
		expect(t.attached).toBeNull();
		expect(t.agent).toBeNull();
	});
});

describe('the latest sequence number', () => {
	it('is the publisher’s own count', async () => {
		const asked = network({}, () => ({ seq: 42, events: [] }));
		expect(await new Transcript('s-1').latest()).toBe(42);
		expect(asked).toEqual([`/_api/events?session=s-1&since=${Number.MAX_SAFE_INTEGER}`]);
	});

	it('is null when no publisher answers, or its answer carries no count', async () => {
		network({}, null);
		expect(await new Transcript('s-1').latest()).toBeNull();
		vi.stubGlobal('fetch', async () => new Response('', { status: 404 }));
		expect(await new Transcript('s-1').latest()).toBeNull();
		network({}, () => ({ events: [] }));
		expect(await new Transcript('s-1').latest()).toBeNull();
	});
});

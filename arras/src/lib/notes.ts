// Notes, a quote among them (plan 0.22.8): one gesture on anything shown writes a note with no type, filed in the selected session, which an agent reads with `loom since`. A note fades after two weeks unless it is kept or something durable links to it; the publisher computes `faded`, and the viewer hides a faded note until the reader asks.

import type { Manifest, Note } from '$lib/manifest/types';
import { store } from '$lib/manifest/client.svelte';
import { write } from '$lib/write';

/** What a note is on, as the write API takes it: a key, a cited work or one of its pages, a shown file, a message (`SESSION#SEQ`) or a session, with the words or the region it quotes. */
export interface Quoted {
	target: string;
	quote?: string;
	page?: number;
	rects?: number[][];
	body?: string;
}

/** Write the note and redraw; the refusal, where there is one, is the answer. */
export async function quote(q: Quoted): Promise<string> {
	const done = await write('note', { ...q });
	if (!done.ok) return done.error?.message ?? 'the publisher refused it';
	void store.refresh();
	return '';
}

/** Keep a note, so it never fades. */
export async function keep(id: string): Promise<string> {
	const done = await write('note-keep', { note: id });
	if (!done.ok) return done.error?.message ?? 'the publisher refused it';
	void store.refresh();
	return '';
}

/** The notes `m` has, newest first, faded ones only when they are asked for. */
export function notesWhere(m: Manifest | null, on: (n: Note) => boolean, faded = false): Note[] {
	return Object.values(m?.notes ?? {})
		.filter((n) => !n.erased && (faded || !n.faded) && on(n))
		.sort((a, b) => b.when.localeCompare(a.when));
}

/** Where a note is, in words a reader knows: the file, the key, the work's page, the message, the session. */
export function noteWhere(n: Note): string {
	const t = n.target;
	if (t.file) return t.file + (n.page ? `, p. ${n.page}` : '');
	if (t.key) return t.key;
	if (t.citekey) return n.page ? `${t.citekey}, p. ${n.page}` : t.citekey;
	if (t.message) return `message ${t.message.seq}`;
	return 'the session';
}

/** What "Ask an agent" writes on a work with no overview: a person's note on the whole work, which an agent reads as it reads any note a person writes. */
export const ASK_OVERVIEW = 'Read this paper through and write its overview.';

/** Ask an agent for `citekey`'s overview, with a person's note on the whole work in the selected session; the refusal, where there is one. */
export function askOverview(citekey: string): Promise<string> {
	return quote({ target: citekey, body: ASK_OVERVIEW });
}

/** The newest unfaded note a person wrote asking for `citekey`'s overview: the ask still standing. */
export function askedFor(m: Manifest | null, citekey: string): Note | undefined {
	return notesWhere(m, (n) => n.target.citekey === citekey && !n.page && n.author.kind === 'person' && n.body === ASK_OVERVIEW)[0];
}

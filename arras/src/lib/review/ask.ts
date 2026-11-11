// "Ask an agent" for a work with no overview (plan 0.24.3): a person's annotation on the whole work, asking that it be read through and its overview written, which an agent hears of as it hears of any annotation a person writes. The viewer starts no agent and loom calls no model.

import type { Annotation, Manifest } from '$lib/manifest/types';
import { store } from '$lib/manifest/client.svelte';
import { textOf } from '$lib/pdf/marks';
import { write } from '$lib/write';

/** What the ask says. */
export const ASK_OVERVIEW = 'Read this paper through and write its overview.';

/** Ask an agent for `citekey`'s overview; '' once asked, else the publisher's refusal. */
export async function askOverview(citekey: string): Promise<string> {
	const done = await write('annotate', { target: citekey, message: ASK_OVERVIEW });
	if (!done.ok) return done.error?.message ?? 'the publisher refused it';
	void store.refresh();
	return '';
}

/** The newest open annotation a person wrote on the whole of `citekey` asking for its overview: the ask still standing. */
export function askedFor(m: Manifest | null, citekey: string): Annotation | undefined {
	return Object.values(m?.annotations ?? {})
		.filter((a) => a.target.work === citekey && !a.target.page && !a.in_reply_to && a.status === 'open' && a.author.kind === 'person' && textOf(a.body_html) === ASK_OVERVIEW)
		.sort((a, b) => b.created.localeCompare(a.created))[0];
}

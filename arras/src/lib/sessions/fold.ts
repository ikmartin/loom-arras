// A report folded after its first block (plan 0.21.2). An agent writes a mode's report as one message, its blocks under `## [name]` headings, and the publisher puts each block in a `<section data-block="NAME">`; a long report shows its first block and a control, and the rest is mounted only when opened, so its mathematics is typeset only then.
//
// Read from the string, not a parsed document: the publisher renders a message's Markdown with raw HTML off, so the only `<section data-block="` in a body is one the publisher wrote, always at the top level.

/** A message split at its second block: what shows, what is folded, and the folded blocks' names. */
export interface Folded {
	head: string;
	rest: string;
	names: string[];
}

/** Characters of text the folded part must exceed: a short tail is never hidden behind a control. */
export const FOLD_AT = 500;

const BLOCK = /<section data-block="([a-z][a-z0-9-]*)">/g;

/** `html` folded after its first block, or null when it has one block or none, or too little after the first to hide. */
export function split(html: string): Folded | null {
	const opens = [...html.matchAll(BLOCK)];
	if (opens.length < 2) return null;
	const at = opens[1].index ?? 0;
	const rest = html.slice(at);
	if (rest.replace(/<[^>]*>/g, '').trim().length <= FOLD_AT) return null;
	return { head: html.slice(0, at), rest, names: opens.slice(1).map((m) => m[1]) };
}

// Links into a cited work (book 10.4.1): `loom:<scheme>:<value>#page=N` or `#quote=TEXT` in a comment names a place in a paper by the work's global identifier, never by a citekey, so it survives a bibliography re-export and means the same thing to a collaborator whose citekeys differ.
import { artifactUrl } from '$lib/paths';
// The link form is the interface's (specs/dialect.md §2.13); nothing here knows the publisher.

import type { Manifest, Reference } from '$lib/manifest/types';
import { resolve } from '$lib/works';

export interface WorkLink {
	/** `scheme:value`, the scheme lowercased. */
	id: string;
	page?: number;
	quote?: string;
}

const PREFIX = 'loom:';

/** Whether an href is a work link. */
export function isWorkLink(href: string | null | undefined): boolean {
	return !!href && href.toLowerCase().startsWith(PREFIX);
}

/** A work link's identifier and anchor, or null when the href is not one. */
export function parseWorkLink(href: string): WorkLink | null {
	if (!isWorkLink(href)) return null;
	const body = href.slice(PREFIX.length);
	const [target, fragment = ''] = body.split(/#(.*)/s, 2);
	const at = target.indexOf(':');
	if (at < 1 || at === target.length - 1) return null;
	const link: WorkLink = { id: normalId(target) };
	for (const part of fragment.split('&')) {
		const eq = part.indexOf('=');
		if (eq < 0) continue;
		const key = part.slice(0, eq);
		const value = safeDecode(part.slice(eq + 1));
		if (key === 'page' && /^\d+$/.test(value) && Number(value) > 0) link.page = Number(value);
		if (key === 'quote' && value.trim()) link.quote = value.trim();
	}
	return link;
}

function safeDecode(s: string): string {
	try {
		return decodeURIComponent(s.replace(/\+/g, ' '));
	} catch {
		return s;
	}
}

/** An identifier in one spelling: the scheme lowercased, and a DOI's value too, since DOIs are case-insensitive. */
export function normalId(id: string): string {
	const at = id.indexOf(':');
	if (at < 1) return id;
	const scheme = id.slice(0, at).trim().toLowerCase();
	const value = id.slice(at + 1).trim();
	return `${scheme}:${scheme === 'doi' ? value.toLowerCase() : value}`;
}

export interface WorkTarget {
	/** The reference that states this identifier, if the corpus cites the work at all. */
	ref?: Reference;
	/** The fetched PDF when the copy on file is the very artifact the identifier names. */
	local?: string;
	/** A copy is on file, but it is another artifact of the same work (a preprint for a published article, or the reverse), so its pages need not match. */
	otherCopy?: { id: string; url: string };
	/** The identifier's own resolver, with the page where the resolver honours one. */
	external?: string;
}

/**
 * Where a link into a work can be opened.
 *
 * A local copy is offered only when it is filed under the identifier the link names: a link to page 9 of a published article must not open page 9 of the preprint, because that is exactly where the two differ. A copy of another artifact of the same work is reported separately, so the reader can open it knowing the pages may not match.
 */
export function locate(m: Manifest, link: WorkLink): WorkTarget {
	const ref = Object.values(m.references).find((r) => (r.works ?? (r.work ? [r.work] : [])).some((w) => normalId(w) === link.id));
	const out: WorkTarget = { ref, external: externalUrl(link) };
	if (ref?.artifacts?.pdf && ref.work) {
		const url = artifactUrl(ref.artifacts.dir);
		if (normalId(ref.work) === link.id) out.local = url + (link.page ? `#page=${link.page}` : '');
		else out.otherCopy = { id: ref.work, url };
	}
	return out;
}

/** The identifier at its own service: arXiv's PDF at the page, a DOI's landing page, or whatever `works.ts` resolves the scheme to. */
export function externalUrl(link: WorkLink): string | undefined {
	const [scheme, ...rest] = link.id.split(':');
	const value = rest.join(':');
	if (scheme === 'arxiv') return `https://arxiv.org/pdf/${value}` + (link.page ? `#page=${link.page}` : '');
	return resolve(link.id)?.href;
}

/** The page a digest locator names, as written by extraction: `Proposition 3.1, p.~18`, `p. 18`, `pp. 18–20`, `page 18`. */
export function pageOf(locator: string | undefined): number | undefined {
	const m = (locator ?? '').match(/\b(?:pp?\.|pages?)\s*~?\s*(\d+)/i);
	return m ? Number(m[1]) : undefined;
}

/**
 * The link into the artifact a digest was extracted from, at a result's page, when that artifact is on file.
 *
 * A digest's numbers and pages are those of the version it was extracted from, so a page link must open that version and no other.
 */
export function digestPageLink(ref: Reference | undefined, locator: string | undefined): WorkLink | null {
	const page = pageOf(locator);
	const from = ref?.digest?.extracted_from;
	if (!page || !from || !ref?.artifacts?.pdf || !ref.work || normalId(ref.work) !== normalId(from)) return null;
	return { id: normalId(from), page };
}

// Filters live in the URL, so a filtered view is a link: the home page's cards open the review table already showing what they count, and back and forward move between filters.

import { goto } from '$app/navigation';

/**
 * Set one query parameter on the current page, replacing the history entry.
 *
 * Parameters
 * ----------
 * url : URL
 *     The page's current URL (`page.url`).
 * name : string
 *     The parameter.
 * value : string
 *     The new value; the empty string, or `fallback`, removes the parameter so the default view keeps a bare URL.
 * fallback : string, default ''
 *     The value that means "no filter".
 */
export function setQuery(url: URL, name: string, value: string, fallback = ''): Promise<void> {
	const next = new URL(url);
	if (!value || value === fallback) next.searchParams.delete(name);
	else next.searchParams.set(name, value);
	return goto(next.pathname + next.search + next.hash, { replaceState: true, keepFocus: true, noScroll: true });
}

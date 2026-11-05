// Where the reader last was in each work: a reader's convenience and never the corpus's, so it lives in this browser and is written nowhere else, per corpus as the workspace's address is (`workspace/remember.ts`). Every storage access is guarded, as the preferences' are: a browser that cannot store it opens each work at its start.

const KEY = 'arras.positions';

/** A place in a paper: the page at the top of the view, and how far down it as a share of its height. Both are the page's own terms, so a place holds at any zoom or width, and whether or not the pages around it have been drawn yet. */
export interface PagePlace {
	page: number;
	share: number;
}

/** The file a place was taken in: its own identifier (pdf.js's `fingerprints[0]`, the PDF's trailer ID, else a hash of its first bytes) and its page count. */
export interface PaperFile {
	id: string;
	pages: number;
}

interface Kept extends PagePlace {
	file: string;
	pages: number;
}

type All = Record<string, Record<string, Kept>>;

function read(): All {
	try {
		const raw = globalThis.localStorage?.getItem(KEY);
		const o = raw ? JSON.parse(raw) : {};
		return o && typeof o === 'object' ? (o as All) : {};
	} catch {
		return {};
	}
}

/**
 * Where the reader last was in a work, or null where they have not been or the file is no longer the one they were in.
 *
 * A place in another file is another paper's page, and page 12 of an edition says nothing about page 12 of a preprint, so a changed file opens at its start rather than somewhere plausible.
 */
export function keptPlace(corpus: string, citekey: string, file: PaperFile): PagePlace | null {
	const k = read()[corpus]?.[citekey];
	if (!k || k.file !== file.id || k.pages !== file.pages) return null;
	if (!Number.isInteger(k.page) || k.page < 1 || k.page > file.pages) return null;
	if (typeof k.share !== 'number' || !(k.share >= 0 && k.share < 1)) return null;
	return { page: k.page, share: k.share };
}

/** Keep where the reader is in a work. The top of its first page is where it opens anyway, so nothing is kept for it. */
export function keepPlace(corpus: string, citekey: string, file: PaperFile, place: PagePlace): void {
	try {
		const all = read();
		const here = (all[corpus] ??= {});
		if (place.page === 1 && place.share === 0) delete here[citekey];
		else here[citekey] = { page: place.page, share: Math.round(place.share * 1e4) / 1e4, file: file.id, pages: file.pages };
		globalThis.localStorage?.setItem(KEY, JSON.stringify(all));
	} catch {
		// a browser that cannot store it still has the place for this tab, in the item's view
	}
}

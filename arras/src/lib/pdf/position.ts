// Where the reader last was in each PDF: a reader's convenience and never the corpus's, so it lives in this browser and is written nowhere else. Every storage access is guarded, as the preferences' are: a browser that cannot store it opens each paper at its start.
//
// A place belongs to the file and not to what it was opened as, so a work's paper and the same bytes among the project's files are one place, and another file behind a work has none of its own yet: page 12 of an edition says nothing about page 12 of a preprint.

const KEY = 'arras.places';

/** A place in a paper: the page at the top of the view, and how far down it as a share of its height. Both are the page's own terms, so a place holds at any zoom or width, and whether or not the pages around it have been drawn yet. */
export interface PagePlace {
	page: number;
	share: number;
}

/** Which file a place is in: its own identifier (pdf.js's `fingerprints[0]`, the PDF's trailer ID, else a hash of its first bytes) and its page count. */
export interface PaperFile {
	id: string;
	pages: number;
}

const keyOf = (file: PaperFile) => `${file.id}:${file.pages}`;

function read(): Record<string, PagePlace> {
	try {
		const raw = globalThis.localStorage?.getItem(KEY);
		const o = raw ? JSON.parse(raw) : {};
		return o && typeof o === 'object' ? (o as Record<string, PagePlace>) : {};
	} catch {
		return {};
	}
}

/** Where the reader last was in a file, or null where they have not been or what is stored is no place in it. */
export function keptPlace(file: PaperFile): PagePlace | null {
	const k = read()[keyOf(file)];
	if (!k || !Number.isInteger(k.page) || k.page < 1 || k.page > file.pages) return null;
	if (typeof k.share !== 'number' || !(k.share >= 0 && k.share < 1)) return null;
	return { page: k.page, share: k.share };
}

/** Keep where the reader is in a file. The top of its first page is where it opens anyway, so nothing is kept for it. */
export function keepPlace(file: PaperFile, place: PagePlace): void {
	try {
		const all = read();
		if (place.page === 1 && place.share === 0) delete all[keyOf(file)];
		else all[keyOf(file)] = { page: place.page, share: Math.round(place.share * 1e4) / 1e4 };
		globalThis.localStorage?.setItem(KEY, JSON.stringify(all));
	} catch {
		// a browser that cannot store it still has the place for this tab, in the item's view
	}
}

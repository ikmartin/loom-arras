// Marks to and from a PDF's own annotations (plan 0.28): "Save a copy" writes them through pdf.js into a copy of the file, and "Take in" reads what another program wrote. Loom's log stays the record; a PDF is what it is exported to and imported from.
//
// Everything here takes the pdf.js library as an argument, so it runs in a test under node as it does in the page.

import type { PDFDocumentProxy, PDFPageProxy } from 'pdfjs-dist';
import { bound, type MarkColor, type MarkKind, nearestColor, ON_WORDS } from './marks';

type Pdfjs = typeof import('pdfjs-dist');

/** What a copy holds for one mark, or for an annotation on a work's page. */
export interface Outgoing {
	page: number;
	kind: MarkKind;
	rects: number[][];
	strokes?: number[][];
	body: string;
	by: string;
	/** Its colour in the copy, 0–255, where it has one of its own. */
	color?: number[];
}

/** An annotation in the file to leave out of the copy, since one of loom's now stands for it. */
export interface Replaced {
	page: number;
	ref: string;
}

/** What a PDF's annotation comes to as an annotation: `annotations-take`'s item. One on words carries its `style`, a drawing its `mark`. */
export interface Incoming {
	page: number;
	mark?: MarkKind;
	style?: MarkKind;
	rects?: number[][];
	strokes?: number[][];
	body: string;
	/** The nearest of the nine to its own colour, where it has one. */
	color?: MarkColor;
	origin: { by?: string; subtype: string; color?: number[]; ref?: string };
}

const YELLOW = [255, 235, 60];
const INK = [60, 60, 66];
const PEN = 1.5;
/** The writer's editor key: pdf.js takes anything under this prefix as an annotation to add. */
const NEW = 'pdfjs_internal_editor_';
const TYPE = { freetext: 3, highlight: 9, ink: 15 };
/** The size a `text` mark is set at, in the copy and on the page. */
export const TEXT_SIZE = 11;

const two = (v: number) => Math.round(v * 100) / 100;

/** The points of the page's top-left space as PDF user space, through the page's own view, which holds its rotation and origin. */
function mapper(page: PDFPageProxy) {
	const view = page.getViewport({ scale: 1 });
	const at = (x: number, y: number): [number, number] => {
		const [ux, uy] = view.convertToPdfPoint(x, y);
		return [two(ux), two(uy)];
	};
	const box = (r: readonly number[]): number[] => {
		const [ax, ay] = at(r[0], r[1]);
		const [bx, by] = at(r[2], r[3]);
		return [Math.min(ax, bx), Math.min(ay, by), Math.max(ax, bx), Math.max(ay, by)];
	};
	const corners = (r: readonly number[]): number[] => [...at(r[0], r[1]), ...at(r[2], r[1]), ...at(r[0], r[3]), ...at(r[2], r[3])];
	const polygon = (r: readonly number[]): number[] => [...at(r[0], r[3]), ...at(r[2], r[3]), ...at(r[2], r[1]), ...at(r[0], r[1])];
	return { at, box, corners, polygon, rotation: page.rotate };
}

/** A stroke in the form pdf.js writes as Ink: each point after four empty control values, which draws straight lines. */
function inkPaths(strokes: number[][], at: (x: number, y: number) => [number, number]) {
	const lines: number[][] = [];
	const points: number[][] = [];
	for (const s of strokes) {
		const line: number[] = [];
		const flat: number[] = [];
		for (let i = 0; i + 1 < s.length; i += 2) {
			const [x, y] = at(s[i], s[i + 1]);
			line.push(NaN, NaN, NaN, NaN, x, y);
			flat.push(x, y);
		}
		lines.push(line);
		points.push(flat);
	}
	return { lines, points };
}

/** The outline of a box, an oval or an arrow as strokes: pdf.js writes no Square, Circle or Line, and every reader draws Ink. */
export function outlineOf(m: Pick<Outgoing, 'kind' | 'rects' | 'strokes'>): number[][] {
	const [x0, y0, x1, y1] = bound(m.rects);
	if (m.kind === 'box') return [[x0, y0, x1, y0, x1, y1, x0, y1, x0, y0]];
	if (m.kind === 'oval') {
		const out: number[] = [];
		for (let i = 0; i <= 48; i++) {
			const t = (i / 48) * 2 * Math.PI;
			out.push(two((x0 + x1) / 2 + (Math.cos(t) * (x1 - x0)) / 2), two((y0 + y1) / 2 + (Math.sin(t) * (y1 - y0)) / 2));
		}
		return [out];
	}
	if (m.kind === 'arrow' && m.strokes?.[0]) return [m.strokes[0], ...arrowHead(m.strokes[0])];
	return m.strokes ?? [];
}

/** The two short lines of an arrow's head, at the stroke's end. */
export function arrowHead(s: readonly number[], size = 8): number[][] {
	const [ex, ey, fx, fy] = [s[s.length - 2], s[s.length - 1], s[s.length - 4], s[s.length - 3]];
	const a = Math.atan2(ey - fy, ex - fx);
	const wing = (d: number) => [two(ex - size * Math.cos(a + d)), two(ey - size * Math.sin(a + d)), ex, ey];
	return [wing(0.45), wing(-0.45)];
}

/** Words broken to fit a width, by a rough measure of the writer's Helvetica: pdf.js sets each line as given and wraps nothing. */
export function wrapped(words: string, width: number, size = TEXT_SIZE): string {
	const per = Math.max(8, Math.floor(width / (size * 0.5)));
	const lines: string[] = [];
	for (const para of words.split(/\r?\n/)) {
		let line = '';
		for (const word of para.split(' ')) {
			if (line && (line + ' ' + word).length > per) {
				lines.push(line);
				line = word;
			} else line = line ? line + ' ' + word : word;
		}
		lines.push(line);
	}
	return lines.join('\n');
}

/** A mark on a thin band of its rectangle, as the appearance of an underline or a strike-through. */
function band(r: readonly number[], kind: string): number[] {
	const h = Math.max(0.8, (r[3] - r[1]) * 0.07);
	const y = kind === 'strike' ? (r[1] + r[3]) / 2 : r[3] - h;
	return [r[0], y, r[2], y + h];
}

/** The outline of a pin, a small speech bubble filling its rectangle. */
function pinShape(r: readonly number[]): number[] {
	const [x0, y0, x1, y1] = r;
	const w = x1 - x0;
	const h = y1 - y0;
	return [x0, y0, x1, y0, x1, y0 + h * 0.72, x0 + w * 0.48, y0 + h * 0.72, x0 + w * 0.22, y1, x0 + w * 0.26, y0 + h * 0.72, x0, y0 + h * 0.72];
}

/** Put a copy's marks in the document's annotation storage, ready for pdf.js to write; what it wrote as a Highlight to be renamed is returned. */
async function fill(doc: PDFDocumentProxy, marks: readonly Outgoing[], replaced: readonly Replaced[]): Promise<{ renames: Rename[]; left: number }> {
	const store = doc.annotationStorage;
	const renames: Rename[] = [];
	let n = 0;
	let left = 0;
	const pages = new Map<number, PDFPageProxy>();
	const page = async (i: number) => {
		if (!pages.has(i)) pages.set(i, await doc.getPage(i));
		return pages.get(i)!;
	};
	for (const r of replaced) {
		if (r.page < 1 || r.page > doc.numPages) continue;
		const p = await page(r.page);
		const found = (await p.getAnnotations()).find((a) => a.id === r.ref);
		if (found) store.setValue(`${NEW}${n++}`, { annotationType: TYPE.highlight, deleted: true, id: r.ref, pageIndex: r.page - 1, popupRef: found.popupRef });
	}
	for (const m of marks) {
		if (m.page < 1 || m.page > doc.numPages || !m.rects?.length) {
			left++;
			continue;
		}
		const p = await page(m.page);
		const map = mapper(p);
		const whole = map.box(bound(m.rects));
		// copied, since these reach the worker and a colour may be a reactive proxy of the manifest's
		const color = m.color ? Array.from(m.color) : null;
		const common = { pageIndex: m.page - 1, rotation: 0, user: m.by, structTreeParentId: null };
		const popup = m.body && m.kind !== 'text' ? { popup: { contents: m.body, deleted: false, rect: [whole[2] + 4, whole[3] - 100, whole[2] + 184, whole[3]] } } : {};
		const key = `${NEW}${n++}`;
		if (m.kind === 'text') {
			const [x0, , x1] = bound(m.rects);
			store.setValue(key, { ...common, annotationType: TYPE.freetext, rect: whole, rotation: map.rotation, color: color ?? INK, fontSize: TEXT_SIZE, value: wrapped(m.body, x1 - x0) });
		} else if (ON_WORDS.includes(m.kind) || m.kind === 'pin') {
			const shapes = m.kind === 'pin' ? [polygonOf(pinShape(m.rects[0]), map.at)] : m.rects.map((r) => map.polygon(m.kind === 'highlight' ? r : band(r, m.kind)));
			store.setValue(key, {
				...common,
				annotationType: TYPE.highlight,
				rect: whole,
				// yellow marks a band or a pin well and a thin line hardly at all
				color: color ?? (m.kind === 'highlight' || m.kind === 'pin' ? YELLOW : INK),
				opacity: 1,
				thickness: 12,
				quadPoints: new Float32Array(m.rects.flatMap((r) => map.corners(r))),
				outlines: shapes,
				...popup
			});
			if (m.kind !== 'highlight') renames.push({ rect: whole, name: SUBTYPES[m.kind] });
		} else {
			store.setValue(key, {
				...common,
				annotationType: TYPE.ink,
				rect: padded(whole, PEN),
				color: color ?? INK,
				opacity: 1,
				thickness: PEN,
				paths: inkPaths(outlineOf(m), map.at),
				...popup
			});
		}
	}
	return { renames, left };
}

const padded = (r: number[], by: number) => [two(r[0] - by), two(r[1] - by), two(r[2] + by), two(r[3] + by)];

function polygonOf(points: readonly number[], at: (x: number, y: number) => [number, number]): number[] {
	const out: number[] = [];
	for (let i = 0; i + 1 < points.length; i += 2) out.push(...at(points[i], points[i + 1]));
	return out;
}

const SUBTYPES: Record<string, string> = { underline: 'Underline', strike: 'StrikeOut', pin: 'Text' };

/** One annotation written as a Highlight that is to be another subtype. */
export interface Rename {
	rect: number[];
	name: string;
}

/**
 * Rename annotations pdf.js wrote as Highlights, in place and at the same length.
 *
 * pdf.js creates no Underline, StrikeOut or Text annotation, so each goes through as a Highlight with its own appearance and comment, found again here by its rectangle. `Highlight` is nine letters and every name here at most nine, so with spaces after it, which PDF ignores, not one object moves and the file's cross-reference still stands.
 */
export function renameSubtypes(bytes: Uint8Array, renames: readonly Rename[], from = 0): void {
	if (!renames.length) return;
	const text = new TextDecoder('latin1').decode(bytes.subarray(from));
	const wanted = [...renames];
	const FIELD = '/Subtype /Highlight';
	for (let at = text.indexOf(FIELD); at >= 0 && wanted.length; at = text.indexOf(FIELD, at + 1)) {
		const end = text.indexOf('endobj', at);
		const found = /\/Rect \[([^\]]*)\]/.exec(text.slice(at, end < 0 ? undefined : end));
		const rect = found?.[1].trim().split(/\s+/).map(Number) ?? [];
		const hit = wanted.findIndex((w) => rect.length === 4 && w.rect.every((v, i) => Math.abs(v - rect[i]) < 0.02));
		if (hit < 0) continue;
		const name = wanted[hit].name.padEnd(9, ' ');
		const start = from + at + FIELD.length - 9;
		for (let i = 0; i < 9; i++) bytes[start + i] = name.charCodeAt(i);
		wanted.splice(hit, 1);
	}
}

/**
 * A copy of a PDF with marks written into it, its original bytes unchanged before them.
 *
 * Parameters
 * ----------
 * lib : pdf.js
 *     The library.
 * source : object
 *     What `getDocument` opens: its own document, since an open one is shared between panes and this one's annotation storage must not reach them.
 * marks : Outgoing[]
 *     What to write.
 * replaced : Replaced[], default []
 *     Annotations in the file to leave out, since one of loom's stands for each.
 *
 * Returns
 * -------
 * object
 *     `bytes`, the copy; `written`, how many marks it holds; `left`, how many could not be placed.
 */
export async function annotatedCopy(lib: Pdfjs, source: Parameters<Pdfjs['getDocument']>[0], marks: readonly Outgoing[], replaced: readonly Replaced[] = []): Promise<{ bytes: Uint8Array; written: number; left: number }> {
	const task = lib.getDocument(source);
	const doc = await task.promise;
	try {
		const { length } = await doc.getDownloadInfo();
		const { renames, left } = await fill(doc, marks, replaced);
		const bytes = new Uint8Array(await doc.saveDocument());
		renameSubtypes(bytes, renames, Math.min(length, bytes.length));
		return { bytes, written: marks.length - left, left };
	} finally {
		await task.destroy();
	}
}

const MARK_OF: Record<string, MarkKind> = {
	Highlight: 'highlight',
	Underline: 'underline',
	Squiggly: 'underline',
	StrikeOut: 'strike',
	Text: 'pin',
	Caret: 'pin',
	FreeText: 'text',
	Square: 'box',
	Stamp: 'box',
	Circle: 'oval',
	Line: 'arrow',
	Ink: 'ink',
	PolyLine: 'ink',
	Polygon: 'ink'
};
/** What belongs to a PDF rather than to its reader: a link, a form field, and a comment's own window. */
const NOT_MARKS = new Set(['Link', 'Widget', 'Popup']);

interface Raw {
	id: string;
	subtype: string;
	rect?: number[];
	quadPoints?: ArrayLike<number> | null;
	inkLists?: ArrayLike<number>[];
	vertices?: ArrayLike<number>;
	lineCoordinates?: ArrayLike<number>;
	color?: ArrayLike<number> | null;
	contentsObj?: { str?: string };
	titleObj?: { str?: string };
	popupRef?: string | null;
}

/** One annotation as a mark: its words and place in the page's top-left points; null for what a mark cannot hold. */
function incoming(a: Raw, page: PDFPageProxy, keepRef: boolean): Incoming | null {
	const mark = MARK_OF[a.subtype];
	if (!mark || !a.rect) return null;
	const view = page.getViewport({ scale: 1 });
	const pt = (x: number, y: number): number[] => view.convertToViewportPoint(x, y).map(two);
	const line = (flat: ArrayLike<number>): number[] => {
		const out: number[] = [];
		for (let i = 0; i + 1 < flat.length; i += 2) out.push(...pt(flat[i], flat[i + 1]));
		return out;
	};
	const box = (r: ArrayLike<number>): number[] => {
		const [ax, ay] = pt(r[0], r[1]);
		const [bx, by] = pt(r[2], r[3]);
		return [Math.min(ax, bx), Math.min(ay, by), Math.max(ax, bx), Math.max(ay, by)];
	};
	const body = (a.contentsObj?.str ?? '').trim();
	const origin = {
		...(a.titleObj?.str ? { by: a.titleObj.str } : {}),
		subtype: a.subtype,
		...(a.color?.length === 3 ? { color: Array.from(a.color) } : {}),
		...(keepRef ? { ref: a.id } : {})
	};
	const color = a.color?.length === 3 ? nearestColor(a.color) : undefined;
	const base = { page: page.pageNumber, ...(ON_WORDS.includes(mark) ? { style: mark } : { mark }), body, origin, ...(color ? { color } : {}) };
	if (ON_WORDS.includes(mark)) {
		const q = a.quadPoints;
		const rects: number[][] = [];
		if (q) for (let i = 0; i + 7 < q.length; i += 8) {
			const quad = line(Array.from(q).slice(i, i + 8));
			const xs = quad.filter((_, k) => k % 2 === 0);
			const ys = quad.filter((_, k) => k % 2 === 1);
			rects.push([Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]);
		}
		return { ...base, rects: rects.length ? rects : [box(a.rect)] };
	}
	if (a.subtype === 'Line' && a.lineCoordinates) return { ...base, strokes: [line(a.lineCoordinates)] };
	if (a.subtype === 'Ink' && a.inkLists?.length) return { ...base, strokes: Array.from(a.inkLists).map(line).filter((s) => s.length >= 4) };
	if ((a.subtype === 'PolyLine' || a.subtype === 'Polygon') && a.vertices) return { ...base, strokes: [line(a.vertices)] };
	if (mark === 'pin' || mark === 'text') return body ? { ...base, rects: [box(a.rect)] } : null;
	if (mark === 'box' || mark === 'oval') return { ...base, rects: [box(a.rect)] };
	return null;
}

/**
 * Every annotation of a PDF that a mark can hold, and how many it cannot.
 *
 * Parameters
 * ----------
 * doc : PDFDocumentProxy
 *     The PDF.
 * keepRef : boolean, default false
 *     Whether each names its place in the file, for taking in the file being read.
 *
 * Returns
 * -------
 * object
 *     `items`, what `annotations-take` writes; `skipped`, how many a mark cannot hold.
 */
export async function readAnnotations(doc: PDFDocumentProxy, keepRef = false): Promise<{ items: Incoming[]; skipped: number }> {
	const items: Incoming[] = [];
	let skipped = 0;
	for (let n = 1; n <= doc.numPages; n++) {
		const page = await doc.getPage(n);
		for (const a of (await page.getAnnotations()) as Raw[]) {
			if (NOT_MARKS.has(a.subtype)) continue;
			const item = incoming(a, page, keepRef);
			if (item) items.push(item);
			else skipped++;
		}
	}
	return { items, skipped };
}

const wordsOf = async (page: PDFPageProxy) => new Set((await page.getTextContent()).items.flatMap((i) => ('str' in i ? i.str.toLowerCase().split(/\s+/) : [])).filter((w) => w.length > 2));

/**
 * Why `other`'s annotations have no place on `doc`, or '' where they do.
 *
 * A save through another program can change a few characters and move words by a fraction of a point, so this asks only that the pages agree in number and size and, on a sample of pages with words, that most words are shared.
 */
export async function notTheSamePaper(doc: PDFDocumentProxy, other: PDFDocumentProxy): Promise<string> {
	if (doc.numPages !== other.numPages) return `That PDF has ${other.numPages} ${other.numPages === 1 ? 'page' : 'pages'} and this one has ${doc.numPages}, so its annotations have no place here.`;
	const step = Math.max(1, Math.floor(doc.numPages / 8));
	for (let n = 1; n <= doc.numPages; n += step) {
		const [a, b] = await Promise.all([doc.getPage(n), other.getPage(n)]);
		const [va, vb] = [a.getViewport({ scale: 1 }), b.getViewport({ scale: 1 })];
		if (Math.abs(va.width - vb.width) > 2 || Math.abs(va.height - vb.height) > 2) return `Page ${n} of that PDF is a different size, so its annotations have no place here.`;
		const [wa, wb] = await Promise.all([wordsOf(a), wordsOf(b)]);
		if (wa.size < 8 || wb.size < 8) continue;
		const shared = [...wa].filter((w) => wb.has(w)).length;
		if (shared / Math.min(wa.size, wb.size) < 0.8) return `Page ${n} of that PDF reads differently, so its annotations have no place here.`;
	}
	return '';
}

/** One page of the new file: which document it comes from, 0 for the one being edited and 1… for those inserted, its index there, and how far to turn it. */
export interface NewPage {
	from: number;
	index: number;
	rotate: number;
}

/**
 * A new PDF from pages of this one and others, turned as asked.
 *
 * pdf.js writes the pages, their annotations with them, and has no way to turn one; a page's `/Rotate` is rewritten afterwards in its written object, at the same length, taking the room from the space in its `/Type /Page`.
 *
 * Parameters
 * ----------
 * lib : pdf.js
 *     The library.
 * source : object
 *     What `getDocument` opens for the PDF being edited.
 * order : NewPage[]
 *     The new file's pages, in order.
 * others : Uint8Array[], default []
 *     The PDFs pages are inserted from, `from` 1 being the first.
 * marks : Outgoing[], default []
 *     What to write into the pages, as a saved copy holds it.
 * replaced : Replaced[], default []
 *     Annotations in the file to leave out, since one of loom's stands for each.
 *
 * Returns
 * -------
 * Uint8Array
 *     The new file.
 */
export async function editedPages(lib: Pdfjs, source: Parameters<Pdfjs['getDocument']>[0], order: readonly NewPage[], others: readonly Uint8Array[] = [], marks: readonly Outgoing[] = [], replaced: readonly Replaced[] = []): Promise<Uint8Array> {
	// marks go in first, as a copy, since the page editor writes its objects where a rename could not reach them
	const task = lib.getDocument(marks.length || replaced.length ? { data: (await annotatedCopy(lib, source, marks, replaced)).bytes, verbosity: 0 } : source);
	const doc = await task.promise;
	try {
		// one entry to a run, since pdf.js sorts the pages of an entry into their own order
		const runs: { document: Uint8Array | null; includePages: number[] }[] = [];
		let last: NewPage | null = null;
		for (const p of order) {
			if (last && last.from === p.from && p.index > last.index) runs[runs.length - 1].includePages.push(p.index);
			else runs.push({ document: p.from === 0 ? null : others[p.from - 1], includePages: [p.index] });
			last = p;
		}
		const bytes = new Uint8Array(await doc.extractPages(runs));
		if (order.some((p) => p.rotate % 360 !== 0)) await turnPages(lib, bytes, order);
		return bytes;
	} finally {
		await task.destroy();
	}
}

/** Add each page's turn to its `/Rotate`, in place. */
async function turnPages(lib: Pdfjs, bytes: Uint8Array, order: readonly NewPage[]): Promise<void> {
	const task = lib.getDocument({ data: bytes.slice(), verbosity: 0 });
	const doc = await task.promise;
	try {
		const text = new TextDecoder('latin1').decode(bytes);
		for (let i = 0; i < order.length; i++) {
			const turn = ((order[i].rotate % 360) + 360) % 360;
			if (!turn) continue;
			const page = await doc.getPage(i + 1);
			const { num, gen } = page.ref as { num: number; gen: number };
			const at = text.indexOf(`\n${num} ${gen} obj\n`);
			const end = at < 0 ? -1 : text.indexOf('endobj', at);
			const obj = at < 0 || end < 0 ? '' : text.slice(at, end);
			const found = /\/Rotate (\d+) /.exec(obj);
			if (!found || !obj.includes('/Type /Page')) throw new Error(`could not turn page ${i + 1}`);
			const now = (Number(found[1]) + turn) % 360;
			// `/Rotate 0 ` holds 90 as it stands, and with the space in `/Type /Page` a three-digit angle
			const swapped = obj.replace('/Type /Page', '/Type/Page').replace(found[0], `/Rotate ${now}`.padEnd(found[0].length + 1, ' '));
			if (swapped.length !== obj.length) throw new Error(`could not turn page ${i + 1}`);
			for (let k = 0; k < swapped.length; k++) bytes[at + k] = swapped.charCodeAt(k);
		}
	} finally {
		await task.destroy();
	}
}

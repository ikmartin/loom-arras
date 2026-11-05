// What a mark on a PDF page is, and the geometry drawing one needs (plan 0.28). A mark is a note whose `mark` says how it is drawn (specs/manifest.md, Notes); all of it is in points from the page's top left, the space the rest of `lib/pdf` draws in.

import type { Note } from '$lib/manifest/types';

export type MarkKind = 'highlight' | 'underline' | 'strike' | 'pin' | 'ink' | 'text' | 'box' | 'oval' | 'arrow';

/** The tools on a page: the reader's two, and one for each mark. `rect` draws a `box` mark, since `box` already names the tool that draws a region to annotate. */
export type PageTool = 'select' | 'box' | 'highlight' | 'underline' | 'strike' | 'pin' | 'ink' | 'text' | 'rect' | 'oval' | 'arrow';

export const ON_WORDS: readonly string[] = ['highlight', 'underline', 'strike'];
export const STROKED: readonly string[] = ['ink', 'arrow'];
export const SAYING: readonly string[] = ['pin', 'text'];
/** The tools that take the pointer from the page's words: everything but reading and the word marks. */
export const DRAWING: readonly string[] = ['pin', 'ink', 'text', 'rect', 'oval', 'arrow'];

export interface PageMark {
	id: string;
	page: number;
	kind: MarkKind;
	rects: number[][];
	strokes?: number[][];
	body: string;
	quote?: string;
	/** A plain note with a place, drawn faintly: a quote, or a region. It has no `mark`, so it fades and does not move. */
	plain?: boolean;
	who?: string;
	when?: string;
}

/** The mark a tool draws. */
export function kindOf(tool: string): MarkKind | null {
	if (tool === 'rect') return 'box';
	return tool === 'select' || tool === 'box' ? null : (tool as MarkKind);
}

/** How a note is drawn on its page, or null where it is not: no place, faded or detached (A3, A6), or erased. */
export function markOf(n: Note): PageMark | null {
	if (!n.page || !n.rects?.length || n.detached || n.faded || n.erased) return null;
	const base = { id: n.id, page: n.page, rects: n.rects, body: n.body, quote: n.quote, who: n.author?.id, when: n.when };
	if (n.mark) return { ...base, kind: n.mark as MarkKind, strokes: n.strokes };
	return { ...base, kind: n.quote ? 'underline' : 'box', plain: true };
}

/** Whether a mark has a place of its own to move: words are the place of a mark on them. */
export function movable(m: PageMark): boolean {
	return !m.plain && !ON_WORDS.includes(m.kind);
}

/** The one rectangle round `rects`. */
export function bound(rects: readonly (readonly number[])[]): number[] {
	return [Math.min(...rects.map((r) => r[0])), Math.min(...rects.map((r) => r[1])), Math.max(...rects.map((r) => r[2])), Math.max(...rects.map((r) => r[3]))];
}

const tenth = (v: number) => Math.round(v * 10) / 10;

/**
 * The rectangles of a selection as one per line.
 *
 * A range over a text layer gives a rectangle per span it crosses, overlapping and uneven. Two stand on one line when they overlap by half the height of the shorter, and on it they merge unless a gap wider than the line is tall stands between them, as between two columns.
 */
export function mergeLines(rects: readonly (readonly number[])[]): number[][] {
	const lines: number[][][] = [];
	for (const r of [...rects].sort((a, b) => a[1] - b[1] || a[0] - b[0])) {
		const line = lines.find((l) => {
			const [, top, , bottom] = bound(l);
			const overlap = Math.min(bottom, r[3]) - Math.max(top, r[1]);
			return overlap >= Math.min(bottom - top, r[3] - r[1]) / 2;
		});
		if (line) line.push([...r]);
		else lines.push([[...r]]);
	}
	const out: number[][] = [];
	for (const line of lines) {
		const [, top, , bottom] = bound(line);
		const gap = bottom - top;
		let run: number[] | null = null;
		for (const r of line.sort((a, b) => a[0] - b[0])) {
			if (run && r[0] <= run[2] + gap) run = [run[0], Math.min(run[1], r[1]), Math.max(run[2], r[2]), Math.max(run[3], r[3])];
			else {
				if (run) out.push(run);
				run = r;
			}
		}
		if (run) out.push(run);
	}
	return out.map((r) => r.map(tenth));
}

/** A stroke with the points that add less than `tolerance` taken out (Douglas–Peucker) and the rest to a tenth of a point: the manifest carries it. */
export function simplify(points: readonly number[], tolerance = 0.4): number[] {
	const n = points.length / 2;
	if (n <= 2) return points.map(tenth);
	const keep = new Uint8Array(n);
	keep[0] = keep[n - 1] = 1;
	const stack: [number, number][] = [[0, n - 1]];
	while (stack.length) {
		const [a, b] = stack.pop()!;
		const [ax, ay, bx, by] = [points[a * 2], points[a * 2 + 1], points[b * 2], points[b * 2 + 1]];
		const len = Math.hypot(bx - ax, by - ay) || 1;
		let far = -1;
		let most = tolerance;
		for (let i = a + 1; i < b; i++) {
			const d = Math.abs((bx - ax) * (ay - points[i * 2 + 1]) - (ax - points[i * 2]) * (by - ay)) / len;
			if (d > most) {
				most = d;
				far = i;
			}
		}
		if (far >= 0) {
			keep[far] = 1;
			stack.push([a, far], [far, b]);
		}
	}
	const out: number[] = [];
	for (let i = 0; i < n; i++) if (keep[i]) out.push(tenth(points[i * 2]), tenth(points[i * 2 + 1]));
	return out;
}

/** The rectangle round a stroke list. */
export function boundOfStrokes(strokes: readonly (readonly number[])[]): number[] {
	const xs = strokes.flatMap((s) => s.filter((_, i) => i % 2 === 0));
	const ys = strokes.flatMap((s) => s.filter((_, i) => i % 2 === 1));
	return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

/** A mark's place mapped from one rectangle onto another: moving is the case where they are the same size. */
export function refit(m: PageMark, to: readonly number[]): Pick<PageMark, 'rects' | 'strokes'> {
	const from = bound(m.rects);
	const sx = from[2] > from[0] ? (to[2] - to[0]) / (from[2] - from[0]) : 1;
	const sy = from[3] > from[1] ? (to[3] - to[1]) / (from[3] - from[1]) : 1;
	const fit = (x: number, y: number): [number, number] => [tenth(to[0] + (x - from[0]) * sx), tenth(to[1] + (y - from[1]) * sy)];
	const rects = m.rects.map((r) => [...fit(r[0], r[1]), ...fit(r[2], r[3])]);
	if (!m.strokes) return { rects };
	const strokes = m.strokes.map((s) => {
		const out: number[] = [];
		for (let i = 0; i + 1 < s.length; i += 2) out.push(...fit(s[i], s[i + 1]));
		return out;
	});
	return { rects: [boundOfStrokes(strokes)], strokes };
}

function nearSegment(x: number, y: number, ax: number, ay: number, bx: number, by: number): number {
	const dx = bx - ax;
	const dy = by - ay;
	const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy || 1)));
	return Math.hypot(x - (ax + t * dx), y - (ay + t * dy));
}

/**
 * The mark at a point on the page, or null: the smallest one, so a mark inside another can still be reached.
 *
 * Marks take no pointer, so a press on a highlight can begin a selection like one on any other words; a click that selected nothing is asked here what it landed on.
 */
export function markAt(marks: readonly PageMark[], x: number, y: number, slack = 4): PageMark | null {
	let best: PageMark | null = null;
	let least = Infinity;
	for (const m of marks) {
		let on: boolean;
		if (m.strokes) {
			on = m.strokes.some((s) => {
				for (let i = 0; i + 3 < s.length; i += 2) if (nearSegment(x, y, s[i], s[i + 1], s[i + 2], s[i + 3]) <= slack) return true;
				return false;
			});
		} else on = m.rects.some((r) => x >= r[0] && x <= r[2] && y >= r[1] && y <= r[3]);
		if (!on) continue;
		const [x0, y0, x1, y1] = bound(m.rects);
		const area = (x1 - x0) * (y1 - y0);
		if (area < least) {
			least = area;
			best = m;
		}
	}
	return best;
}

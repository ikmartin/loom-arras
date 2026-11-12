// What a reader does with the annotations on one PDF's pages: which are drawn and how, which are listed because they have no place on a page, the writes Annotate and the drawing tools make in the look in hand, a mark moved, and the copy and the taking-in. The surfaces that show a PDF (a cited work's pages, a project PDF) each make one and hand it to `MarkedDoc`; the page components stay dumb and report what the reader did.
//
// **Every annotation on the pages is drawn here**, on words or drawn with a tool, in its own look: a project PDF's record says where each stands now, and a cited work's sidecar places one its words or a box anchor. Every write goes through the history (`review/history.svelte.ts`), so the toolbar's Undo takes it back.
//
// **A mark shows at once.** A write publishes a new manifest only after a moment, and a mark that appeared a second after the press would read as a press that failed. So what has been written but not yet published is held here and drawn with the rest, and each is let go once the manifest says the same.

import { store } from '$lib/manifest/client.svelte';
import type { Annotation } from '$lib/manifest/types';
import { can, write, type WriteResult } from '$lib/write';
import { hand, handPayload, lookOf, passes, type Annotating } from '$lib/review/annotating.svelte';
import { annotate, edit } from '$lib/review/history.svelte';
import { say } from '$lib/review/toasts.svelte';
import { ui } from '$lib/ui.svelte';
import { document_, pdfjs, sourceOf } from './document';
import { boundOfStrokes, copyColor, markOf, mergeLines, ON_WORDS, type MarkKind, type PageMark } from './marks';
import { annotatedCopy, notTheSamePaper, readAnnotations, type Incoming, type Outgoing, type Replaced } from './portable';

type Place = Pick<PageMark, 'rects' | 'strokes'>;

/** What a desk works on. A function, since it follows a component's props. */
export interface Surface {
	/** What a write names: a project PDF's path or a citekey. */
	on: string;
	/** Whether an annotation is on this PDF's pages. */
	owns: (a: Annotation) => boolean;
	/** Where an annotation stands when its record does not say: a cited work's sidecar places one by its words or a box. */
	rectsOf?: (a: Annotation) => number[][] | undefined;
	/** Where the PDF is served. */
	url: string;
	/** Its name, for a saved copy. */
	name: string;
	/** The item's annotating, whose filter the marks drawn follow. */
	notes?: Annotating;
	/** Whether the pane hides every annotation. */
	hidden?: boolean;
}

const INK_PAUSE = 900;

export class MarkDesk {
	/** The mark whose popup is open, which can be moved. */
	selected = $state('');
	/** The place a new annotation is being written about, lit while its popup is open. */
	lit = $state<PageMark | null>(null);
	/** Whether this viewer's publisher takes the writes. */
	writes = $state(false);
	/** How many annotations the PDF holds that no annotation of loom's stands for yet, once counted. */
	here = $state<number | null>(null);
	busy = $state(false);
	/** Whether the pages editor is open. */
	pages = $state(false);

	#surface: () => Surface;
	#pending = $state<PageMark[]>([]);
	#changed = $state<Record<string, Partial<PageMark>>>({});
	#fresh = 0;
	#ink: { id: string; page: number; timer: ReturnType<typeof setTimeout> } | null = null;

	constructor(surface: () => Surface) {
		this.#surface = surface;
		void can('annotate').then((yes) => (this.writes = yes));
	}

	/** What the desk works on now. */
	surface(): Surface {
		return this.#surface();
	}

	/** The top-level annotations on this PDF's pages, as published. */
	rows = $derived<Annotation[]>(Object.values(store.manifest?.annotations ?? {}).filter((a) => !a.in_reply_to && (a.target.page ?? 0) > 0 && this.#surface().owns(a)));
	/** Each annotation on the pages with where it is drawn, or null for one with no place on a page now. */
	placed = $derived<{ a: Annotation; m: PageMark | null }[]>(this.rows.map((a) => ({ a, m: markOf(a, this.#surface().rectsOf?.(a)) })));

	/** What is drawn: every annotation with a place, under the item's filter and the pane's hiding, with what is on its way laid over them. A resolved one is drawn while settled annotations are shown. */
	marks = $derived.by<PageMark[]>(() => {
		const s = this.#surface();
		if (s.hidden) return [];
		const out: PageMark[] = [];
		for (const { a, m } of this.placed) {
			if (!m) continue;
			if (s.notes && !passes(store.manifest, a, s.notes, ui.showSettled)) continue;
			out.push({ ...m, ...this.#changed[a.id] });
		}
		const have = new Set(out.map((m) => m.id));
		return [...out, ...this.#pending.filter((m) => !have.has(m.id)), ...(this.lit ? [this.lit] : [])];
	});

	/** The annotations on the pages with no place on one now: detached on a changed file, or a box whose words the sidecar has not placed. Listed, never drawn. */
	detached = $derived<Annotation[]>(this.placed.filter((p) => !p.m).map((p) => p.a));

	/** The annotations in the file that one of loom's stands for, by reference; the pages leave them undrawn. */
	hides = $derived<string[]>(this.rows.flatMap((a) => (a.hides ? [a.hides] : [])));

	/** Let go of what the manifest now says; called whenever it changes. */
	settle(): void {
		const live = new Map(this.rows.map((a) => [a.id, a]));
		if (this.#pending.some((m) => live.has(m.id))) this.#pending = this.#pending.filter((m) => !live.has(m.id));
		const changed: Record<string, Partial<PageMark>> = {};
		for (const [id, over] of Object.entries(this.#changed)) {
			const row = live.get(id);
			const now = row ? markOf(row, this.#surface().rectsOf?.(row)) : null;
			const same = now && (over.rects === undefined || JSON.stringify(now.rects) === JSON.stringify(over.rects)) && (over.strokes === undefined || JSON.stringify(now.strokes) === JSON.stringify(over.strokes));
			if (row && !same) changed[id] = over;
		}
		if (Object.keys(changed).length !== Object.keys(this.#changed).length) this.#changed = changed;
	}

	/**
	 * Write one mark in the look in hand: its type, and its look where it sets one, as Annotate writes words on a document.
	 *
	 * Parameters
	 * ----------
	 * kind : MarkKind
	 *     A drawing's tool, or the style of one on words.
	 * page : int
	 * place : {rects, strokes?}
	 *     In points from the page's top left.
	 * extra : {quote?, message?}
	 *
	 * Returns
	 * -------
	 * str
	 *     The new annotation's id, or '' when refused.
	 */
	async write(kind: MarkKind, page: number, place: Place, extra: { quote?: string; message?: string } = {}): Promise<string> {
		const m = store.manifest;
		const look = lookOf(m, hand.value);
		const fresh = `pending-${++this.#fresh}`;
		this.#pending = [...this.#pending, { id: fresh, page, kind, ...place, body: extra.message ?? '', quote: extra.quote, color: look.color as PageMark['color'], weight: look.weight, opacity: look.opacity }];
		const res = await annotate({ ...this.body(kind, page, place), ...(extra.quote ? { quote: extra.quote } : {}), ...(extra.message ? { message: extra.message } : {}) });
		if (!res.ok) {
			this.#pending = this.#pending.filter((p) => p.id !== fresh);
			say({ title: 'Not written', lines: [res.error?.message ?? 'the publisher refused it'] });
			return '';
		}
		const id = (res.result ?? '').split(/\s+/)[0];
		this.#pending = this.#pending.map((p) => (p.id === fresh ? { ...p, id } : p));
		return id;
	}

	/** What an `annotate` of a mark sends besides what it says: where it is, its tool, its type and its look, a mark on words in the style the hand holds. */
	body(kind: MarkKind, page: number, place: Place): Record<string, unknown> {
		const words = ON_WORDS.includes(kind);
		const payload = handPayload(store.manifest, hand.value);
		// a drawing's tool draws it, so the style in hand is not its own
		const look = payload.look && !words ? Object.fromEntries(Object.entries(payload.look).filter(([k]) => k !== 'style')) : payload.look;
		return { target: this.#surface().on, page, ...(words ? {} : { mark: kind }), ...place, ...(payload.type ? { type: payload.type } : {}), ...(look && Object.keys(look).length ? { look } : {}) };
	}

	/** The style Annotate marks words in: the hand's. */
	style(): MarkKind {
		return lookOf(store.manifest, hand.value).style as MarkKind;
	}

	/** Mark selected words in the hand's style, one rectangle to a line. */
	markWords(e: { page: number; text: string; rects: number[][] }): void {
		void this.write(this.style(), e.page, { rects: mergeLines(e.rects) }, { quote: e.text });
	}

	/** Mark a region in the hand's style, where a page has no words to select or the drag found none. */
	markRegion(e: { page: number; rects: number[][] }): void {
		if (e.rects[0] && e.rects[0][2] - e.rects[0][0] > 3) void this.write(this.style(), e.page, { rects: e.rects });
	}

	/** What a drawing tool drew, a pin and words on the page excepted, which say something first: lines of ink close together are one mark; anything else is written. */
	draw(e: { kind: MarkKind; page: number; rects?: number[][]; strokes?: number[][] }): void {
		if (e.kind === 'ink' && e.strokes) {
			this.#inkLine(e.page, e.strokes[0]);
			return;
		}
		void this.write(e.kind, e.page, e.strokes ? { rects: [boundOfStrokes(e.strokes)], strokes: e.strokes } : { rects: e.rects ?? [] });
	}

	#inkLine(page: number, line: number[]): void {
		const open = this.#ink;
		if (open && open.page === page) {
			clearTimeout(open.timer);
			this.#pending = this.#pending.map((m) => {
				if (m.id !== open.id) return m;
				const strokes = [...(m.strokes ?? []), line];
				return { ...m, strokes, rects: [boundOfStrokes(strokes)] };
			});
			open.timer = setTimeout(() => this.flush(), INK_PAUSE);
			return;
		}
		this.flush();
		const id = `pending-${++this.#fresh}`;
		const look = lookOf(store.manifest, hand.value);
		this.#pending = [...this.#pending, { id, page, kind: 'ink', strokes: [line], rects: [boundOfStrokes([line])], body: '', color: look.color as PageMark['color'], weight: look.weight, opacity: look.opacity }];
		this.#ink = { id, page, timer: setTimeout(() => this.flush(), INK_PAUSE) };
	}

	/** Write the lines of ink being drawn, which a pause or a change of tool ends. */
	flush(): void {
		const open = this.#ink;
		if (!open) return;
		clearTimeout(open.timer);
		this.#ink = null;
		const held = this.#pending.find((m) => m.id === open.id);
		this.#pending = this.#pending.filter((m) => m.id !== open.id);
		if (held?.strokes) void this.write('ink', held.page, { rects: held.rects, strokes: held.strokes });
	}

	/** Move or resize a mark, which the toolbar's Undo puts back. */
	move(e: { id: string } & Place): void {
		const a = store.manifest?.annotations[e.id];
		if (!a) return;
		const now: Place = { rects: e.rects, ...(e.strokes ? { strokes: e.strokes } : {}) };
		this.#changed = { ...this.#changed, [e.id]: { ...this.#changed[e.id], ...now } };
		void edit(a, now).then((res) => {
			if (res.ok) return;
			const { [e.id]: _, ...rest } = this.#changed;
			this.#changed = rest;
			say({ title: 'Not moved', lines: [res.error?.message ?? 'the publisher refused it'] });
		});
	}

	/** Every mark as a saved copy holds it, and how many have no place on a page any more. */
	#outgoing(): { marks: Outgoing[]; left: number } {
		const marks: Outgoing[] = [];
		let left = 0;
		for (const { a, m } of this.placed) {
			if (!m) {
				left++;
				continue;
			}
			const over = this.#changed[a.id];
			const color = copyColor(m.kind, m.color, a.origin?.color);
			marks.push({ page: m.page, kind: m.kind, rects: over?.rects ?? m.rects, strokes: over?.strokes ?? m.strokes, body: m.body, by: a.origin?.by ?? a.author?.id ?? '', weight: m.weight, opacity: m.opacity, ...(color ? { color } : {}) });
		}
		for (const m of this.#pending) {
			const color = copyColor(m.kind, m.color);
			marks.push({ page: m.page, kind: m.kind, rects: m.rects, strokes: m.strokes, body: m.body, by: '', weight: m.weight, opacity: m.opacity, ...(color ? { color } : {}) });
		}
		return { marks, left };
	}

	/** The annotations in the file to leave out of a copy, since one of loom's stands for each. */
	#replaced(): Replaced[] {
		return this.rows.flatMap((a) => (a.hides && a.target.page ? [{ page: a.target.page, ref: a.hides }] : []));
	}

	/** What a page edit writes into its new file. */
	carried(): { marks: Outgoing[]; replaced: Replaced[] } {
		return { marks: this.#outgoing().marks, replaced: this.#replaced() };
	}

	/** Save a copy of the PDF with its marks written in, through the browser, and say what it holds. */
	async saveCopy(): Promise<void> {
		this.flush();
		this.busy = true;
		try {
			const { marks, left } = this.#outgoing();
			const lib = await pdfjs();
			const { bytes, written, left: unplaced } = await annotatedCopy(lib, sourceOf(this.#surface().url), marks, this.#replaced());
			download(bytes, this.#surface().name.replace(/\.pdf$/i, '') + '-annotated.pdf');
			const out = left + unplaced;
			say({ title: 'Saved a copy', lines: [`It holds ${written} ${written === 1 ? 'annotation' : 'annotations'}${out ? `; ${out} ${out === 1 ? 'has' : 'have'} no place on a page and ${out === 1 ? 'was' : 'were'} left out` : ''}.`] });
		} catch (exc) {
			say({ title: 'Could not save a copy', lines: [exc instanceof Error ? exc.message : String(exc)] });
		} finally {
			this.busy = false;
		}
	}

	/** Count the annotations in the PDF being read that none of loom's stands for. */
	async countHere(): Promise<void> {
		try {
			const { items } = await readAnnotations(await document_(this.#surface().url), true);
			this.here = items.filter((i) => !this.hides.includes(i.origin.ref ?? '')).length;
		} catch {
			this.here = null;
		}
	}

	async #take(items: Incoming[], skipped: number): Promise<void> {
		if (!items.length) {
			say({ title: 'Nothing taken in', lines: [skipped ? `That PDF holds nothing a mark can hold (${skipped} left).` : 'That PDF holds no annotations.'] });
			return;
		}
		const res = (await write('annotations-take', { target: this.#surface().on, items })) as WriteResult & { taken?: number; already?: number; skipped?: number };
		if (!res.ok) {
			say({ title: 'Not taken in', lines: [res.error?.message ?? 'the publisher refused it'] });
			return;
		}
		void store.refresh();
		const left = skipped + (res.skipped ?? 0);
		say({ title: `Took in ${res.taken ?? 0}`, lines: [`${res.already ? `${res.already} ${res.already === 1 ? 'was' : 'were'} here already. ` : ''}${left ? `${left} could not be held.` : ''}`.trim()].filter(Boolean) });
	}

	/** Take in the annotations of the PDF being read, which then stop being drawn from the file. */
	async takeHere(): Promise<void> {
		this.busy = true;
		try {
			const { items, skipped } = await readAnnotations(await document_(this.#surface().url), true);
			await this.#take(items.filter((i) => !this.hides.includes(i.origin.ref ?? '')), skipped);
			this.here = 0;
		} catch (exc) {
			say({ title: 'Could not read this PDF', lines: [exc instanceof Error ? exc.message : String(exc)] });
		} finally {
			this.busy = false;
		}
	}

	/** Take in the annotations of another copy of this PDF, one a person marked elsewhere. */
	async takeFrom(file: File): Promise<void> {
		this.busy = true;
		const lib = await pdfjs();
		const task = lib.getDocument(sourceOf(new Uint8Array(await file.arrayBuffer())));
		try {
			const other = await task.promise;
			const why = await notTheSamePaper(await document_(this.#surface().url), other);
			if (why) {
				say({ title: 'Not taken in', lines: [why] });
				return;
			}
			const { items, skipped } = await readAnnotations(other);
			await this.#take(items, skipped);
		} catch (exc) {
			say({ title: `Could not read ${file.name}`, lines: [exc instanceof Error ? exc.message : String(exc)] });
		} finally {
			await task.destroy();
			this.busy = false;
		}
	}
}

/** Hand bytes to the browser as a file to save. */
export function download(bytes: Uint8Array, name: string): void {
	const url = URL.createObjectURL(new Blob([bytes as BlobPart], { type: 'application/pdf' }));
	const a = document.createElement('a');
	a.href = url;
	a.download = name;
	document.body.append(a);
	a.click();
	a.remove();
	setTimeout(() => URL.revokeObjectURL(url), 10000);
}

/** Bytes as base64, a run at a time, since a call's arguments are limited. */
export function base64(bytes: Uint8Array): string {
	let out = '';
	for (let i = 0; i < bytes.length; i += 0x8000) out += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
	return btoa(out);
}

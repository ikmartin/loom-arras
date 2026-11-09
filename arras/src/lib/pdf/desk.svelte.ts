// What a reader does with marks on one PDF (plan 0.28): which are drawn, which is being looked at, the writes, their undo, and the copy and the taking-in. The surfaces that show a PDF each make one and hand it to `MarkedDoc`; the page components stay dumb and report what the reader did.
//
// **A mark shows at once.** A write publishes a new manifest only after a moment, and a highlight that appeared a second after the press would read as a press that failed. So what has been written but not yet published is held here and drawn with the rest, and each is let go once the manifest says the same.

import { store } from '$lib/manifest/client.svelte';
import type { Note } from '$lib/manifest/types';
import { prefs } from '$lib/prefs.svelte';
import { can, write, type WriteResult } from '$lib/write';
import { document_, pdfjs, sourceOf } from './document';
import { boundOfStrokes, copyColor, markOf, mergeLines, type MarkColor, type MarkKind, type PageMark } from './marks';
import { annotatedCopy, notTheSamePaper, readAnnotations, type Incoming, type Outgoing, type Replaced } from './portable';

type Box = { left: number; top: number; width: number; height: number };
type Place = Pick<PageMark, 'rects' | 'strokes'>;

/** What a desk works on. A function, since it follows a component's props. */
export interface Surface {
	/** What a write names: a shown file's path or a citekey. */
	on: string;
	/** Whether a note is on this PDF. */
	owns: (n: Note) => boolean;
	/** Where the PDF is served. */
	url: string;
	/** Its name, for a saved copy. */
	name: string;
	/** What else a saved copy holds: the annotations on a work's pages. */
	extras?: () => Outgoing[];
}

interface Step {
	undo: () => Promise<void>;
	redo: () => Promise<void>;
}

/** What is being written before there is a mark: a pin or words on the page, which say something first. */
export interface Composing {
	kind: MarkKind;
	page: number;
	rects: number[][];
	at: Box;
}

/** A comment the PDF holds, being read. */
export interface Reading {
	subtype: string;
	body: string;
	by: string;
	at: Box;
}

/** The desk the reader used last, which the keyboard speaks to when two panes each show a PDF. */
let last: MarkDesk | null = null;
const INK_PAUSE = 900;

export class MarkDesk {
	selected = $state('');
	composing = $state<Composing | null>(null);
	reading = $state<Reading | null>(null);
	said = $state('');
	/** Whether this viewer's publisher takes the writes. */
	writes = $state(false);
	/** How many annotations the PDF holds that no note stands for yet, once counted. */
	here = $state<number | null>(null);
	busy = $state(false);

	#surface: () => Surface;
	#pending = $state<PageMark[]>([]);
	#changed = $state<Record<string, Partial<PageMark>>>({});
	#gone = $state<string[]>([]);
	#undo = $state<Step[]>([]);
	#redo = $state<Step[]>([]);
	#fresh = 0;
	#ink: { id: string; page: number; timer: ReturnType<typeof setTimeout> } | null = null;

	constructor(surface: () => Surface) {
		this.#surface = surface;
		void can('note-change').then((yes) => (this.writes = yes));
	}

	/** The notes on this PDF, as published. */
	#rows = $derived<Note[]>(Object.values(store.manifest?.notes ?? {}).filter((n) => this.#surface().owns(n)));

	/** What is drawn: the published marks with what is on its way laid over them. */
	marks = $derived.by<PageMark[]>(() => {
		const out: PageMark[] = [];
		for (const n of this.#rows) {
			if (this.#gone.includes(n.id)) continue;
			const m = markOf(n);
			if (m) out.push({ ...m, ...this.#changed[n.id] });
		}
		const have = new Set(out.map((m) => m.id));
		// the place stays lit while what is said about it is being written
		const c = this.composing;
		const lit: PageMark[] = c ? [{ id: 'composing', page: c.page, kind: c.kind === 'pin' ? 'pin' : 'box', rects: c.rects, body: '', plain: c.kind !== 'pin', color: c.kind === 'pin' ? prefs.markColor : '' }] : [];
		return [...out, ...this.#pending.filter((m) => !have.has(m.id)), ...lit];
	});

	/** The annotations in the file that a note stands for, by reference; the pages leave them undrawn. */
	hides = $derived<string[]>(this.#rows.flatMap((n) => (n.hides ? [n.hides] : [])));
	canUndo = $derived(this.#undo.length > 0);
	canRedo = $derived(this.#redo.length > 0);

	/** Let go of what the manifest now says; called whenever it changes. */
	settle(): void {
		const rows = this.#rows;
		const live = new Map(rows.filter((n) => !n.erased).map((n) => [n.id, n]));
		if (this.#pending.some((m) => live.has(m.id))) this.#pending = this.#pending.filter((m) => !live.has(m.id));
		if (this.#gone.some((id) => !live.has(id))) this.#gone = this.#gone.filter((id) => live.has(id));
		const changed: Record<string, Partial<PageMark>> = {};
		for (const [id, over] of Object.entries(this.#changed)) {
			const row = live.get(id);
			const same = row && (over.body === undefined || row.body === over.body) && (over.rects === undefined || JSON.stringify(row.rects) === JSON.stringify(over.rects)) && (over.strokes === undefined || JSON.stringify(row.strokes) === JSON.stringify(over.strokes)) && (over.color === undefined || (row.color ?? '') === over.color);
			if (row && !same) changed[id] = over;
		}
		if (Object.keys(changed).length !== Object.keys(this.#changed).length) this.#changed = changed;
	}

	#done(res: WriteResult): boolean {
		if (res.ok) {
			this.said = '';
			void store.refresh();
			return true;
		}
		this.said = res.error?.message ?? 'the publisher refused it';
		return false;
	}

	#step(step: Step): void {
		this.#undo = [...this.#undo, step];
		this.#redo = [];
		last = this;
	}

	async #write(kind: MarkKind, page: number, place: Place, { body = '', quote, color = prefs.markColor }: { body?: string; quote?: string; color?: MarkColor | '' } = {}): Promise<string> {
		const fresh = `pending-${++this.#fresh}`;
		this.#pending = [...this.#pending, { id: fresh, page, kind, ...place, body, quote, color }];
		const res = await write('note', { target: this.#surface().on, page, mark: kind, ...place, ...(body ? { body } : {}), ...(quote ? { quote } : {}), ...(color ? { color } : {}) });
		if (!this.#done(res)) {
			this.#pending = this.#pending.filter((m) => m.id !== fresh);
			return '';
		}
		const id = String((res as WriteResult & { note?: string }).note);
		this.#pending = this.#pending.map((m) => (m.id === fresh ? { ...m, id } : m));
		if (this.selected === fresh) this.selected = id;
		this.#step({
			undo: () => this.#erase(id),
			redo: () => this.#restore(id)
		});
		return id;
	}

	async #erase(id: string): Promise<void> {
		this.#gone = [...this.#gone, id];
		if (this.selected === id) this.selected = '';
		if (!this.#done(await write('note-erase', { note: id }))) this.#gone = this.#gone.filter((g) => g !== id);
	}

	async #restore(id: string): Promise<void> {
		this.#gone = this.#gone.filter((g) => g !== id);
		this.#done(await write('note-restore', { note: id }));
	}

	async #change(id: string, over: Partial<PageMark>): Promise<void> {
		this.#changed = { ...this.#changed, [id]: { ...this.#changed[id], ...over } };
		this.#pending = this.#pending.map((m) => (m.id === id ? { ...m, ...over } : m));
		if (!this.#done(await write('note-change', { note: id, ...over }))) {
			const { [id]: _, ...rest } = this.#changed;
			this.#changed = rest;
		}
	}

	/** A word mark on what was selected, one rectangle to a line. */
	markWords(kind: MarkKind, e: { page: number; text: string; rects: number[][] }): void {
		void this.#write(kind, e.page, { rects: mergeLines(e.rects) }, { quote: e.text });
	}

	/** A word mark on a region, where a page has no words to select. */
	markRegion(kind: MarkKind, e: { page: number; rects: number[][] }): void {
		if (e.rects[0] && e.rects[0][2] - e.rects[0][0] > 3) void this.#write(kind, e.page, { rects: e.rects });
	}

	/** What a drawing tool drew: a pin and words wait for what they say; lines of ink close together are one mark; anything else is written. */
	draw(e: { kind: MarkKind; page: number; rects?: number[][]; strokes?: number[][]; client: Box }): void {
		last = this;
		if (e.kind === 'pin' || e.kind === 'text') {
			this.composing = { kind: e.kind, page: e.page, rects: e.rects ?? [], at: e.client };
			return;
		}
		if (e.kind === 'ink' && e.strokes) {
			this.#inkLine(e.page, e.strokes[0]);
			return;
		}
		void this.#write(e.kind, e.page, e.strokes ? { rects: [boundOfStrokes(e.strokes)], strokes: e.strokes } : { rects: e.rects ?? [] });
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
		this.#pending = [...this.#pending, { id, page, kind: 'ink', strokes: [line], rects: [boundOfStrokes([line])], body: '', color: prefs.markColor }];
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
		if (held?.strokes) void this.#write('ink', held.page, { rects: held.rects, strokes: held.strokes }, { color: held.color });
	}

	/** Write what was being composed, if it says anything. */
	async compose(body: string): Promise<void> {
		const c = this.composing;
		this.composing = null;
		const words = body.trim();
		if (!c || !words) return;
		await this.#write(c.kind, c.page, { rects: c.kind === 'text' ? [fitted(c.rects[0], words)] : c.rects }, { body: words });
	}

	/** Look at a mark, or at nothing. */
	pick(id: string): void {
		last = this;
		this.selected = id;
		this.reading = null;
		this.composing = null;
	}

	/** Say something else in a mark. */
	say(id: string, body: string): void {
		const m = this.marks.find((n) => n.id === id);
		const was = m?.body ?? '';
		const now = body.trim();
		if (!m || now === was) return;
		void this.#change(id, { body: now });
		this.#step({ undo: () => this.#change(id, { body: was }), redo: () => this.#change(id, { body: now }) });
	}

	/** Give a mark another colour, leaving the colour in the hand as it was. */
	recolor(id: string, color: MarkColor | ''): void {
		const m = this.marks.find((n) => n.id === id);
		const was = m?.color ?? '';
		if (!m || color === was) return;
		void this.#change(id, { color });
		this.#step({ undo: () => this.#change(id, { color: was }), redo: () => this.#change(id, { color }) });
	}

	/** Move or resize a mark. */
	move(e: { id: string } & Place): void {
		const m = this.marks.find((n) => n.id === e.id);
		if (!m) return;
		const was: Place = { rects: m.rects, ...(m.strokes ? { strokes: m.strokes } : {}) };
		const now: Place = { rects: e.rects, ...(e.strokes ? { strokes: e.strokes } : {}) };
		void this.#change(e.id, now);
		this.#step({ undo: () => this.#change(e.id, was), redo: () => this.#change(e.id, now) });
	}

	/** Take a mark off the page. */
	erase(id: string): void {
		void this.#erase(id);
		this.#step({ undo: () => this.#restore(id), redo: () => this.#erase(id) });
	}

	async undo(): Promise<void> {
		this.flush();
		const step = this.#undo.at(-1);
		if (!step) return;
		this.#undo = this.#undo.slice(0, -1);
		this.#redo = [...this.#redo, step];
		await step.undo();
	}

	async redo(): Promise<void> {
		const step = this.#redo.at(-1);
		if (!step) return;
		this.#redo = this.#redo.slice(0, -1);
		this.#undo = [...this.#undo, step];
		await step.redo();
	}

	/** The keyboard: undo, redo, erase what is being looked at, and Escape, which `disarm` answers when nothing is open. */
	key(e: KeyboardEvent, disarm: () => void): void {
		if (last !== this || (e.target as HTMLElement | null)?.closest('input, textarea, select, [contenteditable]')) return;
		const command = e.metaKey || e.ctrlKey;
		if (command && e.key.toLowerCase() === 'z') {
			if (!this.writes) return;
			e.preventDefault();
			void (e.shiftKey ? this.redo() : this.undo());
		} else if ((e.key === 'Delete' || e.key === 'Backspace') && this.selected && this.writes) {
			e.preventDefault();
			this.erase(this.selected);
		} else if (e.key === 'Escape') {
			if (this.selected || this.reading || this.composing) this.pick('');
			else disarm();
		}
	}

	/** Every mark and placed note as a saved copy holds it, and how many notes on the pages have no place there. */
	#outgoing(): { marks: Outgoing[]; left: number } {
		const marks: Outgoing[] = [];
		let left = 0;
		for (const n of this.#rows) {
			if (n.erased || !n.page) continue;
			const m = this.#gone.includes(n.id) ? null : markOf(n);
			if (!m) {
				if (!n.faded && !this.#gone.includes(n.id)) left++;
				continue;
			}
			const over = this.#changed[n.id];
			const color = copyColor(m.kind, over?.color ?? m.color, n.origin?.color);
			marks.push({ page: m.page, kind: m.kind, rects: over?.rects ?? m.rects, strokes: over?.strokes ?? m.strokes, body: over?.body ?? m.body, by: n.origin?.by ?? n.author?.id ?? '', ...(color ? { color } : {}) });
		}
		for (const m of this.#pending) {
			const color = copyColor(m.kind, m.color);
			marks.push({ page: m.page, kind: m.kind, rects: m.rects, strokes: m.strokes, body: m.body, by: '', ...(color ? { color } : {}) });
		}
		return { marks: [...marks, ...(this.#surface().extras?.() ?? [])], left };
	}

	/** The annotations in the file to leave out of a copy, since a note stands for each. */
	#replaced(): Replaced[] {
		return this.#rows.flatMap((n) => (n.hides && n.page ? [{ page: n.page, ref: n.hides }] : []));
	}

	/** What a page edit writes into its new file. */
	carried(): { marks: Outgoing[]; replaced: Replaced[] } {
		return { marks: this.#outgoing().marks, replaced: this.#replaced() };
	}

	/** Save a copy of the PDF with its marks written in, through the browser. */
	async saveCopy(): Promise<void> {
		this.flush();
		this.busy = true;
		this.said = '';
		try {
			const { marks, left } = this.#outgoing();
			const lib = await pdfjs();
			const { bytes, written, left: unplaced } = await annotatedCopy(lib, sourceOf(this.#surface().url), marks, this.#replaced());
			download(bytes, this.#surface().name.replace(/\.pdf$/i, '') + '-annotated.pdf');
			const out = left + unplaced;
			this.said = `Saved a copy with ${written} ${written === 1 ? 'annotation' : 'annotations'}${out ? `; ${out} ${out === 1 ? 'note has' : 'notes have'} no place on a page and ${out === 1 ? 'was' : 'were'} left out` : ''}.`;
		} catch (exc) {
			this.said = `Could not save a copy: ${exc instanceof Error ? exc.message : String(exc)}`;
		} finally {
			this.busy = false;
		}
	}

	/** Count the annotations in the PDF being read that no note stands for. */
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
			this.said = skipped ? `That PDF holds nothing a mark can hold (${skipped} left).` : 'That PDF holds no annotations.';
			return;
		}
		const res = (await write('notes-take', { target: this.#surface().on, items })) as WriteResult & { taken?: number; already?: number; skipped?: number };
		if (!this.#done(res)) return;
		const left = skipped + (res.skipped ?? 0);
		this.said = `Took in ${res.taken ?? 0}${res.already ? `; ${res.already} ${res.already === 1 ? 'was' : 'were'} here already` : ''}${left ? `; ${left} could not be held` : ''}.`;
	}

	/** Take in the annotations of the PDF being read, which then stop being drawn from the file. */
	async takeHere(): Promise<void> {
		this.busy = true;
		try {
			const { items, skipped } = await readAnnotations(await document_(this.#surface().url), true);
			await this.#take(items.filter((i) => !this.hides.includes(i.origin.ref ?? '')), skipped);
			this.here = 0;
		} catch (exc) {
			this.said = `Could not read this PDF: ${exc instanceof Error ? exc.message : String(exc)}`;
		} finally {
			this.busy = false;
		}
	}

	/** Take in the annotations of another copy of this PDF, one a person marked elsewhere. */
	async takeFrom(file: File): Promise<void> {
		this.busy = true;
		this.said = '';
		const lib = await pdfjs();
		const task = lib.getDocument(sourceOf(new Uint8Array(await file.arrayBuffer())));
		try {
			const other = await task.promise;
			const why = await notTheSamePaper(await document_(this.#surface().url), other);
			if (why) {
				this.said = why;
				return;
			}
			const { items, skipped } = await readAnnotations(other);
			await this.#take(items, skipped);
		} catch (exc) {
			this.said = `Could not read ${file.name}: ${exc instanceof Error ? exc.message : String(exc)}`;
		} finally {
			await task.destroy();
			this.busy = false;
		}
	}
}

/** The rectangle words on the page stand in: as wide as asked, as tall as their lines by a rough measure of the writer's face. */
function fitted(r: number[], words: string): number[] {
	const width = r[2] - r[0];
	const per = Math.max(8, Math.floor(width / 5.5));
	const lines = words.split('\n').reduce((n, l) => n + Math.max(1, Math.ceil(l.length / per)), 0);
	return [r[0], r[1], r[2], r[1] + lines * 13.5 + 3];
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


// Annotating in the viewer: the look in hand, remembered in this browser, and each open item's annotating state (its tool, its annotations and pending changes in reading order, the one open, how the changes are shown, the side list and its filter). The fragment registers what only it can do, opening an annotation or a change at its mark; the toolbar, the side list and the popup read and call it.
//
// Nothing here reads a type's id to decide anything: a type's `open`, `notes` and look do.

import type { Annotation, AnnotationType, Look, Manifest, PendingChange } from '$lib/manifest/types';
import { documentLabel, keyName } from '$lib/workspace/names';
import { ui } from '$lib/ui.svelte';
import { COLORS, STYLES, typeOf } from './annotationTypes';
import { acted } from './acted.svelte';
import { authorOf, changeById } from './changes';

/** loom's plain look, where the quilt's types file sets none (records/types.py `PLAIN`). */
export const PLAIN: Look = { color: 'yellow', style: 'highlight', weight: 2, opacity: 60 };

/** What is in hand: a type, or Plain (none), each with what is set over its look, only where it differs. What is set over Plain is kept while a type is held, so Plain comes back as it was left whatever was held between. */
export interface Hand {
	type: string | null;
	/** Set over the type's look; empty while Plain is held. */
	over: Partial<Look>;
	/** Set over the quilt's plain look. */
	plain: Partial<Look>;
}

/** What a reader holds before choosing anything: Plain, in the quilt's plain look. */
export const FIRST_HAND: Hand = { type: null, over: {}, plain: {} };

type Typed = Pick<Manifest, 'annotation_types' | 'annotation_plain'> | null | undefined;

/** The quilt's plain look: how an annotation with no type that sets no look is drawn. */
export function plainOf(m: Typed): Look {
	return m?.annotation_plain ?? PLAIN;
}

/** The type `id` names, while the quilt has it. */
export function typeById(m: Typed, id: string | null | undefined): AnnotationType | undefined {
	return id ? m?.annotation_types?.find((t) => t.id === id) : undefined;
}

/**
 * The whole look a hand draws with.
 *
 * Parameters
 * ----------
 * m : Manifest
 *     For the quilt's types.
 * hand : Hand
 *     The type and the look set over it.
 *
 * Returns
 * -------
 * Look
 *     Its type's look, or with Plain the quilt's plain look, under what is set on it.
 */
export function lookOf(m: Typed, hand: Hand): Look {
	const t = typeById(m, hand.type);
	return t ? { ...t.look, ...hand.over } : { ...plainOf(m), ...hand.plain };
}

/** `hand` with one field of its look set: kept as an override only where it differs from the look under it, so a hand that matches its type, or the plain look, follows it. */
export function withLook(m: Typed, hand: Hand, change: Partial<Look>): Hand {
	const t = typeById(m, hand.type);
	const base = t ? t.look : plainOf(m);
	const set: Partial<Look> = { ...(t ? hand.over : hand.plain) };
	for (const [k, v] of Object.entries(change) as [keyof Look, never][]) {
		if (base[k] === v) delete set[k];
		else set[k] = v;
	}
	return t ? { ...hand, over: set } : { ...hand, type: null, over: {}, plain: set };
}

/** `hand` with type `id`, or Plain for null: a type takes its own look; Plain takes its own, as it was last left. */
export function withType(m: Typed, hand: Hand, id: string | null): Hand {
	return { type: typeById(m, id) ? id : null, over: {}, plain: { ...hand.plain } };
}

/** A look as read from storage or a write, each field kept only when it can be drawn. */
function cleanLook(o: unknown): Partial<Look> {
	if (!o || typeof o !== 'object') return {};
	const x = o as Record<string, unknown>;
	const out: Partial<Look> = {};
	if ((COLORS as readonly string[]).includes(x.color as string)) out.color = x.color as string;
	if ((STYLES as readonly string[]).includes(x.style as string)) out.style = x.style as Look['style'];
	if (Number.isInteger(x.weight) && (x.weight as number) >= 1 && (x.weight as number) <= 5) out.weight = x.weight as number;
	if (Number.isInteger(x.opacity) && (x.opacity as number) >= 0 && (x.opacity as number) <= 100) out.opacity = x.opacity as number;
	return out;
}

const HAND_KEY = 'arras.annotate.hand';

/** The look in hand, for every document: kept in this browser, so the next visit annotates as the last one did. */
class HandState {
	type = $state<string | null>(FIRST_HAND.type);
	over = $state<Partial<Look>>({ ...FIRST_HAND.over });
	plain = $state<Partial<Look>>({ ...FIRST_HAND.plain });

	constructor() {
		try {
			const raw = globalThis.localStorage?.getItem(HAND_KEY);
			if (!raw) return;
			const o = JSON.parse(raw) as { type?: unknown; over?: unknown; plain?: unknown };
			this.type = typeof o.type === 'string' && o.type ? o.type : null;
			this.over = this.type ? cleanLook(o.over) : {};
			this.plain = cleanLook(o.plain);
		} catch {
			// a browser that stores nothing starts from the first hand
		}
	}

	get value(): Hand {
		return { type: this.type, over: { ...this.over }, plain: { ...this.plain } };
	}

	set(next: Hand): void {
		this.type = next.type;
		this.over = { ...next.over };
		this.plain = { ...next.plain };
		try {
			globalThis.localStorage?.setItem(HAND_KEY, JSON.stringify(next));
		} catch {
			// kept for this visit only
		}
	}
}

export const hand = new HandState();

/** What the hand writes on an `annotate`: its type, and its look only where it sets one, so what it leaves follows the type or the quilt's plain look. */
export function handPayload(m: Typed, h: Hand): { type?: string; look?: Partial<Look> } {
	const out: { type?: string; look?: Partial<Look> } = {};
	if (h.type && typeById(m, h.type)) out.type = h.type;
	const set = out.type ? h.over : h.plain;
	if (Object.keys(set).length) out.look = { ...set };
	return out;
}

/** What an `edit` sends to give annotation `a` type `id`, or Plain for null: either drops the annotation's own look (`look: null`), so it is drawn in the type's or the plain look and follows later edits to it. */
export function retype(m: Typed, a: Annotation, id: string | null): { type: string | null; look: null } {
	const t = typeById(m, id);
	return { type: t ? t.id : null, look: null };
}

/** What an `edit` sends to take annotation `a`'s type away and keep the look it is drawn with, as its own. */
export function keepLook(a: Annotation): { type: null; look: Look } {
	return { type: null, look: { ...a.look } };
}

/** The first keys of a comment typed at an annotation just marked, before its popup opened: the popup starts its field with them. */
class Seed {
	id = $state('');
	text = $state('');
}

export const commentSeed = new Seed();

/** The keys typed for annotation `id` before its popup opened, taken once; null when none were. */
export function takeSeed(id: string): string | null {
	if (!id || commentSeed.id !== id) return null;
	const text = commentSeed.text;
	commentSeed.id = '';
	commentSeed.text = '';
	return text;
}

/** The type an annotation's look has been changed from, while the quilt has it and the look differs from it; null otherwise. What the "Changed from" line names. */
export function changedFrom(m: Typed, a: Pick<Annotation, 'type' | 'look'>): AnnotationType | null {
	const t = typeById(m, a.type);
	if (!t) return null;
	const x = t.look;
	const y = a.look;
	return x.color === y.color && x.style === y.style && x.weight === y.weight && x.opacity === y.opacity ? null : t;
}

/** The quilt's types as `types-save` takes them, in order, with type `id`'s look replaced by `look` where both are given. */
export function typesPayload(m: Typed, id?: string, look?: Look): Record<string, unknown>[] {
	return (m?.annotation_types ?? []).map((t) => {
		const l = id && look && t.id === id ? look : t.look;
		return { id: t.id, name: t.name, color: l.color, style: l.style, weight: l.weight, opacity: l.opacity, open: t.open, notes: t.notes, instructions: t.instructions };
	});
}

/** A new annotation to write from the popup: what it is on, the words it marks if any, the document it is read in, and the place's name for the popup's head. */
export interface Draft {
	target: string;
	quote?: string;
	in?: string;
	name: string;
	/** What else the annotation is written with: on a PDF page, its page, its rectangles and the tool that drew it (`mark`). */
	extra?: Record<string, unknown>;
}

/** The tool in hand on a text: Annotate (selecting words marks them), Comment (a click leaves a comment there), or neither, when a selection offers Quote. */
export type Tool = 'annotate' | 'comment' | null;
/** Which list stands beside the text. */
export type Side = 'comments' | 'notes' | null;
/** What the list and the stepper go through: annotations and changes, or one of them. With annotations alone the text shows what the person has kept. */
export type Layer = 'all' | 'annotations' | 'changes';
/** How the text shows its pending changes: in place, old words struck and new underlined (`markup`), or with every one made (`final`). */
export type ChangesView = 'markup' | 'final';

/** One open item's annotating: what the toolbar, the side list and the fragment share. */
export class Annotating {
	tool = $state<Tool>(null);
	/** The top-level annotations and the pending changes read here, by id, in reading order: those with a mark in the order their first marks stand, then those on the whole document and the changes drawn nowhere. The fragment sets it as it wires. */
	order = $state<string[]>([]);
	/** The annotation or change whose popup is open, or null. */
	open = $state<string | null>(null);
	/** What the list and the stepper go through. */
	layer = $state<Layer>('all');
	/** How the text shows its pending changes. */
	view = $state<ChangesView>('markup');
	side = $state<Side>(null);
	/** Authors the filter leaves out, by id. */
	hidden = $state<string[]>([]);
	/** To do: only open annotations, of types that stay open, from others than the reader. */
	todo = $state(false);
	/** Whether the fragment shows anything to annotate yet. */
	ready = $state(false);
	/** A new annotation being written in a popup, not saved until its button is pressed: words marked (`annotate`) or a place clicked (`comment`). */
	drafting = $state<'annotate' | 'comment' | null>(null);
	/** The annotation Annotate just marked, whose comment typing starts until the next selection. */
	marked = $state<string | null>(null);

	/** Open annotation or change `id` at its mark, scrolled to it; registered by the fragment. False when it has no mark here. */
	show: (id: string) => boolean = () => false;
	/** Close the popup; registered by the fragment. */
	close: () => void = () => {};
}

/**
 * What the hint under the toolbar says: what the tool in hand does, or what can be done to the annotation open; '' at rest.
 *
 * Parameters
 * ----------
 * m : Manifest
 * s : Annotating
 *     The item's tool and the annotation open.
 * h : Hand
 *     The type in hand, which Annotate marks with.
 *
 * Returns
 * -------
 * str
 */
export function hintFor(m: (Pick<Manifest, 'annotation_types'> & Partial<Pick<Manifest, 'changes'>>) | null | undefined, s: Pick<Annotating, 'tool' | 'open'> & Partial<Pick<Annotating, 'drafting' | 'marked'>>, h: Hand): string {
	if (s.drafting) return `Not saved yet: write the comment, then press ${s.drafting === 'annotate' ? 'Annotate' : 'Comment'}. Esc discards it.`;
	if (s.tool === 'annotate' && s.marked) return 'Marked. Start typing to add a comment, or select more text.';
	if (s.tool === 'annotate') {
		const t = typeById(m, h.type);
		return `Annotate is on. Select text to mark it ${t ? `as ${t.name}` : 'in the plain look'}. Number keys switch type, 0 for Plain. Esc stops.`;
	}
	if (s.tool === 'comment') return 'Comment is on. Click where the comment should go. Esc stops.';
	if (s.open && changeById(m, s.open)) return 'Change selected. Keep or Discard it in its popup, Esc closes it.';
	if (s.open) return 'Annotation selected. Its popup changes it, Delete removes it, Esc closes it.';
	return '';
}

/** Whether `a` is open: open, and of a type that stays open until resolved. */
export function isOpen(m: Typed, a: Annotation): boolean {
	return a.status === 'open' && !!typeOf(m, a)?.open;
}

/** Whether `a` is in the reader's To do: open, and not the reader's own. */
export function isTodo(m: Pick<Manifest, 'annotation_types' | 'reviewer'> | null | undefined, a: Annotation): boolean {
	return isOpen(m, a) && a.author.id !== m?.reviewer?.name;
}

/** Whether the side list and the text show `a` under the filter: its author not left out, resolved ones only while settled annotations are shown, and only To do while To do is on. */
export function passes(m: Pick<Manifest, 'annotation_types' | 'reviewer'> | null | undefined, a: Annotation, s: Pick<Annotating, 'hidden' | 'todo'>, showSettled = ui.showSettled): boolean {
	if (s.hidden.includes(a.author.id)) return false;
	if (a.status !== 'open' && !showSettled) return false;
	return !s.todo || isTodo(m, a);
}

/** The annotations the stepper and the Comments list go through: `order` under the filter. */
export function sequence(m: Manifest | null | undefined, s: Pick<Annotating, 'order' | 'hidden' | 'todo'>, showSettled = ui.showSettled): Annotation[] {
	if (!m) return [];
	return s.order.map((id) => m.annotations[id]).filter((a): a is Annotation => !!a && passes(m, a, s, showSettled));
}

/** One thing the stepper and the list go through: an annotation, or a pending change. */
export type Entry = { id: string; a: Annotation; c?: undefined } | { id: string; c: PendingChange; a?: undefined };

/** Whether the list and the text show change `c` under the filter: changes listed, its author not left out, and not kept or discarded a moment ago. A pending change is always something to do. */
export function changePasses(c: PendingChange, s: Pick<Annotating, 'hidden' | 'layer'>): boolean {
	return s.layer !== 'annotations' && !s.hidden.includes(authorOf(c).id) && !(c.id in acted.map);
}

/**
 * What the stepper and the Comments list go through: `order` under the filter, annotations and changes alike.
 *
 * Parameters
 * ----------
 * m : Manifest
 * s : Annotating
 *     The order, the filter and which layer is listed.
 * showSettled : bool
 *     Whether resolved annotations are shown.
 *
 * Returns
 * -------
 * Entry[]
 */
export function entries(m: Manifest | null | undefined, s: Pick<Annotating, 'order' | 'hidden' | 'todo' | 'layer'>, showSettled = ui.showSettled): Entry[] {
	if (!m) return [];
	const out: Entry[] = [];
	for (const id of s.order) {
		const a = m.annotations[id];
		if (a) {
			if (s.layer !== 'changes' && passes(m, a, s, showSettled)) out.push({ id, a });
			continue;
		}
		const c = changeById(m, id);
		if (c && changePasses(c, s)) out.push({ id, c });
	}
	return out;
}

/** Everyone who wrote one of these annotations, the reader first, by id and the name shown. */
export function authors(m: Pick<Manifest, 'reviewer'> | null | undefined, list: Annotation[]): { id: string; name: string }[] {
	const seen = new Map<string, string>();
	for (const a of list) if (!seen.has(a.author.id)) seen.set(a.author.id, a.author.label ?? a.author.id);
	const me = m?.reviewer?.name;
	return [...seen].map(([id, name]) => ({ id, name })).sort((x, y) => (x.id === me ? -1 : y.id === me ? 1 : x.name.localeCompare(y.name)));
}

/** An annotation's comment as plain words, for a label or a title: its rendering with the markup taken out. */
export function plain(html: string): string {
	return html
		.replace(/<[^>]*>/g, ' ')
		.replace(/&nbsp;/g, ' ')
		.replace(/&lt;/g, '<')
		.replace(/&gt;/g, '>')
		.replace(/&quot;/g, '"')
		.replace(/&#39;/g, "'")
		.replace(/&amp;/g, '&')
		.replace(/\s+/g, ' ')
		.trim();
}

/** Whether `a` says anything, which gives its margin icon the speech bubble's shape. */
export function says(a: Annotation): boolean {
	return plain(a.body_html) !== '';
}

/** One group of the Notes list: a document, a work or a PDF, by the name a reader uses. */
export interface NotesGroup {
	label: string;
	notes: Annotation[];
}

/** The document `a` is read in, as the Notes list groups it: the document it names; else, for a key, the document it is, or the first that reaches its node; a cited work's citekey; a project PDF's path. */
export function documentOf(m: Manifest, a: Annotation): string {
	if (a.in) return a.in;
	if (a.target.file) return a.target.file;
	if (a.target.work) return a.target.work;
	const key = a.target.key;
	if (m.masters.some((x) => x.path === key)) return key;
	const owner = m.regions?.[key]?.container ?? m.keys[key]?.node ?? key;
	return m.nodes[owner]?.reached_by?.[0] ?? key;
}

/**
 * The Notes list: every top-level annotation whose type is listed in Notes, from every document and work, grouped by document in the order the groups first appear.
 *
 * Parameters
 * ----------
 * m : Manifest
 *
 * Returns
 * -------
 * NotesGroup[]
 *     Each group's label is the document's file name, a work's citekey or a PDF's file name.
 */
export function notesIn(m: Manifest | null | undefined): NotesGroup[] {
	if (!m) return [];
	const groups = new Map<string, Annotation[]>();
	for (const a of Object.values(m.annotations ?? {})) {
		if (a.in_reply_to || !typeOf(m, a)?.notes) continue;
		const at = documentOf(m, a);
		const list = groups.get(at);
		if (list) list.push(a);
		else groups.set(at, [a]);
	}
	return [...groups].map(([at, notes]) => ({ label: m.masters.some((x) => x.path === at) ? documentLabel(m.masters, at) : (at.split('/').pop() ?? at), notes }));
}

/** How many annotations the Notes list holds, from every document. */
export function notesCount(m: Manifest | null | undefined): number {
	return notesIn(m).reduce((n, g) => n + g.notes.length, 0);
}

/** How many of the annotations read here are listed in Notes: what the Notes badge on this item's toolbar counts. */
export function notesHere(m: Manifest | null | undefined, s: Pick<Annotating, 'order'>): number {
	if (!m) return 0;
	return s.order.filter((id) => {
		const a = m.annotations[id];
		return !!a && !a.in_reply_to && !!typeOf(m, a)?.notes;
	}).length;
}

/** Where `a` stands, in the words a reader uses: the page of a PDF or a work, else the key's name. */
export function placeOf(m: Manifest, a: Annotation): string {
	if (a.target.page) return `page ${a.target.page}`;
	return keyName(m, a.target.key);
}

/** What "Written on earlier words" shows for `a`: the words it was written on and the version to open (`fragment`, '' where none is kept), or null when its words still stand. One carried onto new words when a change was kept names the words it was written on. */
export function earlier(a: Annotation): { words: string; fragment: string; at: boolean } | null {
	if (a.earlier) return { words: a.earlier.quote, fragment: a.version?.fragment ?? '', at: a.version?.at ?? false };
	return a.version ? { words: a.quote ?? '', fragment: a.version.fragment, at: a.version.at } : null;
}

/** What Quote puts on the clipboard: the words, quoted, then where they came from as a link an agent can follow. */
export function quoted(words: string, name: string, href: string): string {
	return `> ${words}\n— [${name}](${href})`;
}

// The viewer's own preferences (book 15.2, 15.7): the body typeface, the body size, the line width, the theme, how a document is set, and where comments stand.
// They are arras's and never the corpus's, so they live in this browser and are written nowhere else. Every storage access is guarded: a private window, cleared site data, or a thumbnail capture can make localStorage throw or come back empty, and the viewer must render anyway.

export type Face = 'serif' | 'sans';
export type Size = 's' | 'm' | 'l';
export type Width = 'narrow' | 'mid' | 'wide';
export type Theme = 'light' | 'dark' | 'system';
/**
 * How a document and its results are set. Four, named for how they are chosen rather than described, so all four fit one row of the settings panel.
 *
 * `p1` and `p2` are the compiled page: justified text, run-in theorem heads, numbers, and no colour on a result at all — the paper as `amsart` sets it, with the viewer's machinery intact. `p2` adds the page boundaries of the real compiled PDF, taken from the numbers loom publishes, so a divider falls exactly where a page ended. `b1` is the measured column with a taxon accent at the edge; `b2` is the wider setting a website reads, with sans heads and a tinted panel.
 *
 * It applies to the read view and to a node's own page alike, because a result should not change character depending on which page it is standing on.
 */
export type Format = 'p1' | 'p2' | 'b1' | 'b2';
/**
 * Where an annotation stands when it is opened (plan 0.13 §7).
 *
 * `floating` opens a box over the text, anchored to the mark and inset from the window; `margin` stands it in a column beside the text; `inline` opens it in place, pushing the text apart, and is the Authoring View's alone. A click opens one and hovering never does — the box a pointer brought up could not be read without holding the pointer still, and could not be clicked into at all.
 */
export type Comments = 'floating' | 'inline';

const KEY = 'arras.prefs';

export interface Prefs {
	/** The workspace's ratio: how much of the frame the left pane takes, 0.2 to 0.8, half by default since neither pane is primary. One ratio — a reader sets the shape of their screen once. */
	divider: number;
	/** Whether the side panel is showing. It collapses independently of the split and goes first, because on a narrow window it is the column the reader needs least (plan 0.13 §7). */
	panel: boolean;
	/** How large a rendered page is drawn, per renderer kind (`pdf` today): a reader who wants a paper larger wants every paper larger, and the document's own size is the `size` setting. A second renderer gets its own entry rather than the PDF's number. */
	zoom: Record<string, number>;
	/** Whether each result's id and state stand in the left gutter. Off by default: a reader reading the paper does not need every key beside it, and the reader who does is working on the corpus rather than reading it. */
	ids: boolean;
	face: Face;
	size: Size;
	width: Width;
	theme: Theme;
	format: Format;
	comments: Comments;
}

export const DEFAULTS: Prefs = { divider: 0.5, panel: true, ids: false, zoom: { pdf: 1.4 }, face: 'serif', size: 'm', width: 'mid', theme: 'system', format: 'p1', comments: 'floating' };

const FACES: Face[] = ['serif', 'sans'];
const SIZES: Size[] = ['s', 'm', 'l'];
const WIDTHS: Width[] = ['narrow', 'mid', 'wide'];
const THEMES: Theme[] = ['light', 'dark', 'system'];
const FORMATS: Format[] = ['p1', 'p2', 'b1', 'b2'];
const COMMENTS: Comments[] = ['floating', 'inline'];

/** A stored blob narrowed to valid values; anything unrecognised falls back to the default for that field. */
export function coerce(raw: unknown): Prefs {
	const o = (raw ?? {}) as Partial<Record<keyof Prefs, unknown>>;
	const pick = <T extends string>(v: unknown, allowed: T[], fallback: T): T =>
		typeof v === 'string' && (allowed as string[]).includes(v) ? (v as T) : fallback;
	const ratio = typeof o.divider === 'number' && Number.isFinite(o.divider) ? o.divider : DEFAULTS.divider;
	// a number is what this stored before it was per kind; it was the PDF's
	const stored = typeof o.zoom === 'number' ? { pdf: o.zoom } : typeof o.zoom === 'object' && o.zoom ? o.zoom : {};
	const zoom: Record<string, number> = { ...DEFAULTS.zoom };
	for (const [kind, v] of Object.entries(stored as Record<string, unknown>)) {
		if (typeof v === 'number' && Number.isFinite(v)) zoom[kind] = Math.min(3, Math.max(0.5, v));
	}
	return {
		divider: Math.min(0.8, Math.max(0.2, ratio)),
		panel: o.panel !== false,
		ids: o.ids === true,
		zoom,
		face: pick(o.face, FACES, DEFAULTS.face),
		size: pick(o.size, SIZES, DEFAULTS.size),
		width: pick(o.width, WIDTHS, DEFAULTS.width),
		theme: pick(o.theme, THEMES, DEFAULTS.theme),
		format: pick(o.format, FORMATS, DEFAULTS.format),
		comments: pick(o.comments, COMMENTS, DEFAULTS.comments)
	};
}

export function read(): Prefs {
	try {
		const raw = globalThis.localStorage?.getItem(KEY);
		return coerce(raw ? JSON.parse(raw) : {});
	} catch {
		return { ...DEFAULTS };
	}
}

export function write(p: Prefs): void {
	try {
		globalThis.localStorage?.setItem(KEY, JSON.stringify(p));
	} catch {
		// a viewer that cannot store its preferences still uses them for this session
	}
}

/** The attributes the stylesheet keys off. `theme: 'system'` sets none, leaving the media query in charge. */
export function attributes(p: Prefs): Record<string, string | null> {
	return {
		'data-face': p.face,
		'data-size': p.size,
		'data-width': p.width,
		'data-theme': p.theme === 'system' ? null : p.theme,
		'data-format': p.format,
		'data-comments': p.comments,
		'data-ids': p.ids ? 'yes' : null,
	};
}

class PrefsState {
	divider = $state<number>(DEFAULTS.divider);
	panel = $state<boolean>(DEFAULTS.panel);
	ids = $state<boolean>(DEFAULTS.ids);
	zoom = $state<Record<string, number>>({ ...DEFAULTS.zoom });
	face = $state<Face>(DEFAULTS.face);
	size = $state<Size>(DEFAULTS.size);
	width = $state<Width>(DEFAULTS.width);
	theme = $state<Theme>(DEFAULTS.theme);
	format = $state<Format>(DEFAULTS.format);
	comments = $state<Comments>(DEFAULTS.comments);

	get current(): Prefs {
		return { divider: this.divider, panel: this.panel, ids: this.ids, zoom: this.zoom, face: this.face, size: this.size, width: this.width, theme: this.theme, format: this.format, comments: this.comments };
	}

	load(override?: Partial<Prefs>): void {
		const p = coerce({ ...read(), ...(override ?? {}) });
		this.divider = p.divider;
		this.panel = p.panel;
		this.ids = p.ids;
		this.zoom = { ...p.zoom };
		this.face = p.face;
		this.size = p.size;
		this.width = p.width;
		this.theme = p.theme;
		this.format = p.format;
		this.comments = p.comments;
	}

	/** Apply to <html> and persist. Called from one effect in the layout. */
	apply(): void {
		const el = globalThis.document?.documentElement;
		if (el) {
			for (const [k, v] of Object.entries(attributes(this.current))) {
				if (v === null) el.removeAttribute(k);
				else el.setAttribute(k, v);
			}
		}
		write(this.current);
	}
}

export const prefs = new PrefsState();

// The viewer's own preferences (book 15.2, 15.7): the navigation shell, the body typeface, the body size, the line width, the theme, how a document is set, and where comments stand.
// They are arras's and never the corpus's, so they live in this browser and are written nowhere else. Every storage access is guarded: a private window, cleared site data, or a thumbnail capture can make localStorage throw or come back empty, and the viewer must render anyway.

export type Shell = 'a' | 'c';
export type Face = 'serif' | 'sans';
export type Size = 's' | 'm' | 'l';
export type Width = 'narrow' | 'mid' | 'wide';
export type Theme = 'light' | 'dark' | 'system';
/** How a document and its results are set: `paper` is the measured, numbered column a mathematician reads; `blog` is the wider, quieter setting a website reads. It applies to the read view and to a node's own page alike, because a result should not change character depending on which page it is standing on. */
export type Format = 'paper' | 'blog';
/** `margin` stands a comment beside its node; `inline` shows it as a highlight on the text that expands where it is; `hover` opens the same box as a floating panel the pointer brings up, free to overlap the text and the gutter. */
export type Comments = 'margin' | 'inline' | 'hover';

const KEY = 'arras.prefs';

export interface Prefs {
	shell: Shell;
	face: Face;
	size: Size;
	width: Width;
	theme: Theme;
	format: Format;
	comments: Comments;
}

export const DEFAULTS: Prefs = { shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'system', format: 'paper', comments: 'margin' };

// A stored `b`, the retired tabs shell, is not in the list, so it falls back to the default like any unknown value.
const SHELLS: Shell[] = ['a', 'c'];
const FACES: Face[] = ['serif', 'sans'];
const SIZES: Size[] = ['s', 'm', 'l'];
const WIDTHS: Width[] = ['narrow', 'mid', 'wide'];
const THEMES: Theme[] = ['light', 'dark', 'system'];
const FORMATS: Format[] = ['paper', 'blog'];
const COMMENTS: Comments[] = ['margin', 'inline', 'hover'];

/** A stored blob narrowed to valid values; anything unrecognised falls back to the default for that field. */
export function coerce(raw: unknown): Prefs {
	const o = (raw ?? {}) as Partial<Record<keyof Prefs, unknown>>;
	const pick = <T extends string>(v: unknown, allowed: T[], fallback: T): T =>
		typeof v === 'string' && (allowed as string[]).includes(v) ? (v as T) : fallback;
	return {
		shell: pick(o.shell, SHELLS, DEFAULTS.shell),
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
		'data-shell': p.shell,
		'data-face': p.face,
		'data-size': p.size,
		'data-width': p.width,
		'data-theme': p.theme === 'system' ? null : p.theme,
		'data-format': p.format,
		'data-comments': p.comments
	};
}

class PrefsState {
	shell = $state<Shell>(DEFAULTS.shell);
	face = $state<Face>(DEFAULTS.face);
	size = $state<Size>(DEFAULTS.size);
	width = $state<Width>(DEFAULTS.width);
	theme = $state<Theme>(DEFAULTS.theme);
	format = $state<Format>(DEFAULTS.format);
	comments = $state<Comments>(DEFAULTS.comments);

	get current(): Prefs {
		return { shell: this.shell, face: this.face, size: this.size, width: this.width, theme: this.theme, format: this.format, comments: this.comments };
	}

	load(override?: Partial<Prefs>): void {
		const p = coerce({ ...read(), ...(override ?? {}) });
		this.shell = p.shell;
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

// MathJax 3, TeX input and SVG output, bundled from the mathjax package so nothing loads from a CDN and a deployed site works offline. Macros come from the manifest at startup; a fragment naming a per-fragment set gets those definitions applied before its math is typeset.
import type { Macro } from '$lib/manifest/types';

type MJ = {
	typesetPromise: (els: Element[]) => Promise<void>;
	typesetClear: (els: Element[]) => void;
	startup: { promise: Promise<void> };
	texReset?: () => void;
};

declare global {
	interface Window {
		MathJax: unknown;
	}
}

let loaded: Promise<MJ> | null = null;
let currentMacros: Record<string, string | [string, number]> = {};

function toConfig(macros: Macro[]): Record<string, string | [string, number]> {
	const out: Record<string, string | [string, number]> = {};
	for (const m of macros) out[m.name] = m.args > 0 ? [m.body, m.args] : m.body;
	return out;
}

export function ensureMathJax(macros: Macro[]): Promise<MJ> {
	if (!loaded) {
		currentMacros = toConfig(macros);
		window.MathJax = {
			tex: {
				inlineMath: [['\\(', '\\)']],
				displayMath: [['\\[', '\\]']],
				processEscapes: true,
				packages: { '[+]': ['ams', 'amscd', 'boldsymbol', 'mathtools', 'newcommand', 'color', 'cancel', 'bbox', 'html', 'unicode', 'verb', 'mhchem', 'physics', 'textmacros'] },
				macros: currentMacros,
				tags: 'none'
			},
			// One glyph cache for the page, not one per expression. A local cache puts a `<defs>` block inside every container whose paths sit thousands of pixels above it in the SVG's coordinate space, and a scroll container counts that as content: every display block then had a vertical scrollbar beside a formula that fitted.
			svg: { fontCache: 'global' },
			options: { skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'] },
			startup: { typeset: false }
		};
		// the full component carries every TeX extension, so \color and friends never trigger a runtime load from a path that does not exist offline
		loaded = import('mathjax/es5/tex-svg-full.js').then(async () => {
			const mj = window.MathJax as MJ;
			await mj.startup.promise;
			return mj;
		});
	}
	return loaded;
}

function macroPrefix(macros: Macro[]): string {
	return macros.map((m) => (m.args > 0 ? `\\renewcommand{\\${m.name}}[${m.args}]{${m.body}}` : `\\renewcommand{\\${m.name}}{${m.body}}`)).join('');
}

/** Typesetting is serialised: MathJax is not safe to enter twice, and a document typesetting in the background shares it with titles and previews. */
let queue: Promise<unknown> = Promise.resolve();
function run(mj: MJ, els: Element[]): Promise<void> {
	const next = queue.then(() => mj.typesetPromise(els));
	queue = next.catch(() => {});
	return next;
}

/** How many formulas one pass typesets before the page gets a turn. */
const BATCH = 160;

/**
 * Typeset the mathematics inside `el`.
 *
 * A short fragment is typeset in one pass. A long one — a whole document, where two or three thousand formulas took over a second before anything showed — is typeset in batches: first everything up to `until` (the element a link points at) or the first screenful, and the returned promise resolves once that part is done, so the caller can reveal and scroll; the rest follows in batches that yield to the page between them. Everything above the reader is typeset before the promise resolves, so nothing above them changes height afterwards and the page never jumps under them.
 *
 * Parameters
 * ----------
 * el : Element
 *     The container.
 * defaults : Macro[]
 *     The corpus-wide macros, applied when MathJax first loads.
 * perFragment : Macro[], default []
 *     A digest's own macros, defined ahead of the first formula.
 * until : Element | null, default null
 *     Typeset at least through this element before resolving.
 *
 * Returns
 * -------
 * Promise<void>
 *     Resolves when the part the reader will see first is typeset; the remainder continues while the element stays in the document.
 */
export async function typeset(el: Element, defaults: Macro[], perFragment: Macro[] = [], until: Element | null = null): Promise<void> {
	const mj = await ensureMathJax(defaults);
	const items = [...el.querySelectorAll('.math')];
	if (perFragment.length) {
		const first = items[0];
		if (first) first.textContent = macroPrefix(perFragment) + (first.textContent ?? '');
	}
	if (items.length <= BATCH) {
		await run(mj, [el]);
		return;
	}
	// the first part: through the linked element, or through what fits on the first screen
	let cut = 0;
	if (until) {
		cut = items.findIndex((m) => until.compareDocumentPosition(m) & Node.DOCUMENT_POSITION_FOLLOWING);
		if (cut < 0) cut = items.length;
	}
	const screen = window.innerHeight * 1.5;
	while (cut < items.length && items[cut].getBoundingClientRect().top < screen) cut++;
	cut = Math.min(items.length, Math.max(cut, BATCH));
	for (let i = 0; i < cut; i += BATCH) await run(mj, items.slice(i, Math.min(cut, i + BATCH)));
	void (async () => {
		for (let i = cut; i < items.length; i += BATCH) {
			await new Promise((r) => setTimeout(r, 0));
			if (!el.isConnected) return;
			await run(mj, items.slice(i, i + BATCH));
		}
	})();
}

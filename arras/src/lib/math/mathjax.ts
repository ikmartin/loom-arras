// MathJax 3, TeX input and SVG output, bundled from the mathjax package so nothing loads from a CDN and a deployed site works offline. Macros come from the manifest at startup; a fragment naming a per-fragment set gets those definitions applied before its math is typeset.
import type { Macro } from '$lib/manifest/types';

/** One formula in MathJax's list of what it has typeset; once typeset, `start.node` is its output's container. */
type MathItem = { start: { node: Node } };

type MJ = {
	typesetPromise: (els: Element[]) => Promise<void>;
	typesetClear: (els: Element[]) => void;
	startup: { promise: Promise<void>; document?: { math: Iterable<MathItem> & { remove: (...items: MathItem[]) => void } } };
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
				// `tags: 'none'` gives MathJax no labels, so a `\ref` outside mathematics could only ever read `???`; loom turns a fragment's own into links, and one in a message or a note reads as written
				processRefs: false,
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

/** A fragment's macro set as one formula of definitions. `\renewcommand` alone: MathJax's never checks that a macro exists, and it has no `\providecommand`, whose argument it would read as math and fail on, showing the formula's source instead. */
function macroPrefix(macros: Macro[]): string {
	return macros.map((m) => (m.args > 0 ? `\\renewcommand{\\${m.name}}[${m.args}]{${m.body}}` : `\\renewcommand{\\${m.name}}{${m.body}}`)).join('');
}

/** Queue a fragment's macro set for definition: one formula of `\renewcommand`, typeset in a holder off the page and removed.
 *
 * MathJax keeps a definition page-wide (WQ-51), so whatever is queued next sees it; call it in the same task as the fragment's own `run`. Not written into one of the fragment's own formulas, which need not open with `\(` or `\[` (an `align`, a formula already typeset), and outside a delimiter MathJax reads the definitions as prose. */
function define(mj: MJ, macros: Macro[]): void {
	const holder = document.createElement('span');
	holder.setAttribute('aria-hidden', 'true');
	holder.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
	holder.textContent = `\\(${macroPrefix(macros)}\\)`;
	document.body.append(holder);
	void run(mj, [holder])
		.catch(() => {})
		.finally(() => holder.remove());
}

/** Typesetting is serialised: MathJax is not safe to enter twice, and a document typesetting in the background shares it with titles and previews. */
let queue: Promise<unknown> = Promise.resolve();
function run(mj: MJ, els: Element[]): Promise<void> {
	const next = queue.then(() => {
		prune(mj);
		return mj.typesetPromise(els);
	});
	queue = next.catch(() => {});
	return next;
}

/** Forget the formulas whose output has left the page. MathJax lists every formula it has typeset and each entry holds its output, so a document replaced or a box closed would otherwise stay alive for good, and every later typeset would walk its entries. Run inside the queue, where nothing is being typeset. */
function prune(mj: MJ): void {
	const list = mj.startup.document?.math;
	if (!list) return;
	const gone: MathItem[] = [];
	for (const item of list) if (!item.start.node.isConnected) gone.push(item);
	for (let i = 0; i < gone.length; i += 1000) list.remove(...gone.slice(i, i + 1000));
}

/** Give the page a turn between batches, so input and painting are never held behind a whole document. */
function yieldToPage(): Promise<void> {
	const s = (globalThis as { scheduler?: { yield?: () => Promise<void> } }).scheduler;
	return s?.yield ? s.yield() : new Promise((r) => setTimeout(r, 0));
}

/** How many formulas one pass typesets before the page gets a turn.
 *
 * 160 was one long task of 90-100ms on a 1250-formula document, which is a visible stall; 48 costs a few more yields and keeps each pass around 30ms, under the 50ms a frame can absorb. The first screen of a document holds about 25 formulas, so a document still reveals in one pass. */
const BATCH = 48;

/**
 * Typeset the mathematics inside `el`.
 *
 * A short fragment is typeset in one pass. A long one — a whole document, where two or three thousand formulas took over a second before anything showed — is typeset in batches, each of which gives the page a turn before the next: first everything up to `until` (the element a link points at) or the first screenful, and the returned promise resolves once that part is done, so the caller can reveal and scroll; then the rest. Everything above the reader is typeset before the promise resolves, so nothing above them changes height afterwards and the page never jumps under them.
 *
 * Parameters
 * ----------
 * el : Element
 *     The container.
 * defaults : Macro[]
 *     The corpus-wide macros, applied when MathJax first loads.
 * perFragment : Macro[], default []
 *     The fragment's own macro set (a landmark's, a digest's), defined just before its formulas are typeset.
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
	// queued in this task, with the first pass below, so nothing typeset between the two sees another fragment's set
	if (perFragment.length && items.length) define(mj, perFragment);
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
	// MathJax resolves on microtasks alone, so batches that only awaited one another ran as one task: every batch yields
	for (let i = 0; i < cut; i += BATCH) {
		if (i) await yieldToPage();
		if (!el.isConnected) return;
		await run(mj, items.slice(i, Math.min(cut, i + BATCH)));
	}
	void (async () => {
		for (let i = cut; i < items.length; i += BATCH) {
			await yieldToPage();
			if (!el.isConnected) return;
			await run(mj, items.slice(i, i + BATCH));
		}
	})();
}

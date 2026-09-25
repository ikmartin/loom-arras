// PDF.js, loaded the way MathJax is (`$lib/math/mathjax.ts`): a dynamic import the first time a paper is opened, so a reader who never opens one pays nothing for it. Bundled rather than fetched from a CDN, so a deployed site works offline, and the worker is emitted by the bundler from `import.meta.url` rather than pointed at `static/` — a hand-written path would lose the base prefix, which `src/lib/paths.spec.ts` checks.

import { base } from '$app/paths';
import type { PDFDocumentProxy, PageViewport } from 'pdfjs-dist';

type Pdfjs = typeof import('pdfjs-dist');

let loaded: Promise<Pdfjs> | null = null;

/** The library, loaded once per page load, with its worker wired. */
export function pdfjs(): Promise<Pdfjs> {
	if (!loaded) {
		loaded = import('pdfjs-dist').then((lib) => {
			lib.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).href;
			return lib;
		});
	}
	return loaded;
}

const open = new Map<string, Promise<PDFDocumentProxy>>();

/** One document per URL, shared between everything that draws it: the pane, a preview, the proposal box.
 *
 * The standard fonts and the CMaps are served from this bundle's own `static/`, staged there by
 * `scripts/pdfjs-assets.mjs`. Both are fetched per document and only when one needs them — a paper that embeds all its
 * fonts asks for neither — so they cost package weight and nothing at load. A deployed corpus must render offline, and
 * a viewer that silently falls back to another font is worse than a larger one, because a reader cannot see which
 * glyphs moved.
 */
export function document_(url: string): Promise<PDFDocumentProxy> {
	let doc = open.get(url);
	if (!doc) {
		doc = pdfjs().then((lib) =>
			lib.getDocument({
				url,
				standardFontDataUrl: `${base}/pdfjs/standard_fonts/`,
				cMapUrl: `${base}/pdfjs/cmaps/`,
				cMapPacked: true
			}).promise
		);
		open.set(url, doc);
	}
	return doc;
}

/** Forget a document, so the next call reopens it: for a paper whose bytes changed under the viewer. */
export function forget(url?: string): void {
	if (url === undefined) open.clear();
	else open.delete(url);
}

/**
 * A rectangle in loom's space — points, origin top left — as CSS percentages of the page it sits on.
 *
 * Geometry is recorded in the space `pdftotext -bbox-layout` emits, which is what the sidecar publishes. PDF user space
 * has its origin at the bottom left, so a viewer that hands these to PDF.js's own transform draws every highlight
 * mirrored; percentages of the page box avoid the question entirely and survive zoom, which is why the conversion
 * happens once here and nowhere else.
 */
export function asPercent(
	quad: readonly number[],
	box: { width: number; height: number }
): { left: string; top: string; width: string; height: string } {
	const [x0, y0, x1, y1] = quad;
	return {
		left: `${(x0 / box.width) * 100}%`,
		top: `${(y0 / box.height) * 100}%`,
		width: `${((x1 - x0) / box.width) * 100}%`,
		height: `${((y1 - y0) / box.height) * 100}%`
	};
}

/** The page's own size in points, which is per page and not per document: a scan's pages differ by a point or two. */
export function boxOf(viewport: PageViewport): { width: number; height: number } {
	return { width: viewport.width, height: viewport.height };
}

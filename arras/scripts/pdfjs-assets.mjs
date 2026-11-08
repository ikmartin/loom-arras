// Copy what PDF.js fetches into `static/`, where the bundle can serve it under its own base path: standard fonts, CMaps, the decoders for a scan's JPEG 2000 and JBIG2 images and for ICC colour, and the CMYK profile.
//
// Each is **fetched per document and only when a document needs it**, so they cost package weight and nothing at load. Shipping them rather than pointing at a CDN is the same decision the worker's is: a deployed corpus must render offline, and a viewer that silently drops to a fallback font or leaves out an image is worse than one that is a little larger, because the reader cannot tell what moved or went missing.
//
// Copied at build time from the dependency rather than committed in arras: they are pdfjs-dist's bytes and they change with its version. The QuickJS build in `wasm/` is left behind, since it runs a PDF's own scripts and the viewer never asks for that.

import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const from = join(here, 'node_modules', 'pdfjs-dist');
const into = join(here, 'static', 'pdfjs');

if (!existsSync(from)) {
	console.error('pdfjs-dist is not installed; run npm install');
	process.exit(1);
}

rmSync(into, { recursive: true, force: true });
for (const what of ['standard_fonts', 'cmaps', 'wasm', 'iccs']) {
	const src = join(from, what);
	if (!existsSync(src)) {
		console.error(`pdfjs-dist has no ${what}/`);
		process.exit(1);
	}
	mkdirSync(join(into, what), { recursive: true });
	cpSync(src, join(into, what), { recursive: true, filter: (path) => !basename(path).startsWith('quickjs') });
}
console.log(`pdfjs: fonts, CMaps, decoders and profile staged in static/pdfjs/`);

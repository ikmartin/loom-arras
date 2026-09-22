// Copy PDF.js's standard fonts and CMaps into `static/`, where the bundle can serve them under its own base path.
//
// Both are **fetched per document and only when a document needs them** — a paper embedding all its fonts asks for
// neither — so they cost package weight and nothing at load. Shipping them rather than pointing at a CDN is the same
// decision the worker's is: a deployed corpus must render offline, and a viewer that silently drops to a fallback font
// is worse than one that is a little larger, because the reader cannot tell which glyphs moved.
//
// Copied at build time from the dependency rather than committed: they are pdfjs-dist's bytes, they change with its
// version, and 2.4MB of somebody else's fonts in git is 2.4MB in every clone forever.

import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const from = join(here, 'node_modules', 'pdfjs-dist');
const into = join(here, 'static', 'pdfjs');

if (!existsSync(from)) {
	console.error('pdfjs-dist is not installed; run npm install');
	process.exit(1);
}

rmSync(into, { recursive: true, force: true });
for (const what of ['standard_fonts', 'cmaps']) {
	const src = join(from, what);
	if (!existsSync(src)) {
		console.error(`pdfjs-dist has no ${what}/`);
		process.exit(1);
	}
	mkdirSync(join(into, what), { recursive: true });
	cpSync(src, join(into, what), { recursive: true });
}
console.log(`pdfjs: standard fonts and CMaps staged in static/pdfjs/`);

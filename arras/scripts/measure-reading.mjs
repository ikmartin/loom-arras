// What a page of a paper costs to put on screen, and whether a selection made in this browser comes back from loom as
// an anchor (plan 0.13 step 1, item 6). A script and not a test: it reports numbers for a decision, it asserts nothing,
// and it reads PDFs that are not in version control.
//
//   npm run build && node scripts/measure-reading.mjs [FILE ...]
//
// Two phases, because they need different things served. **Cost** wants any PDF at all, including ones that live only
// in ~/Downloads, so it serves a scratch directory and drives pdfjs itself — the same version the viewer bundles, at the
// same scale, through the same three stages. **Round trip** wants the real publisher, so it runs one against a demo
// quilt and asks the real endpoint, from the real page, about text the browser's own text layer produced.

import { spawn } from 'node:child_process';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { homedir } from 'node:os';
import { extname, join, resolve } from 'node:path';
import { chromium } from '@playwright/test';

const here = resolve(import.meta.dirname, '..');
const workspace = resolve(here, '..');
const SCALE = 1.4;
const MARKS = 40;
const THRESHOLD = 150; // the plan's abort condition, in ms per page

const PDFS = (
	process.argv.length > 2
		? process.argv.slice(2).map((p) => resolve(p))
		: [
				join(workspace, 'demos/showcase/digests/storage/doi/10.4171_showcase_19-2/paper.pdf'),
				join(workspace, 'demos/kpsv/digests/storage/arxiv/2106.09819/paper.pdf'),
				join(homedir(), 'Downloads/atiyahbott_moment.pdf'),
				join(homedir(), 'Downloads/BF02441086.pdf')
			]
).filter((p) => existsSync(p));

const TYPES = { '.mjs': 'text/javascript', '.js': 'text/javascript', '.html': 'text/html', '.pdf': 'application/pdf' };

// Served rather than set as content: a page on `about:blank` cannot import a module over http.
const PAGE_HTML =
	'<!doctype html><meta charset="utf-8"><body style="margin:0"><div id="host" style="position:relative">' +
	'<canvas id="c"></canvas><div id="t" style="position:absolute;inset:0;overflow:hidden;line-height:1;opacity:.2"></div>' +
	'<div id="m" style="position:absolute;inset:0"></div></div>';

/** A read-only server: the harness page at /, and each named root beneath its prefix. */
function serveFiles(roots) {
	const server = createServer((req, res) => {
		const rel = decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\/+/, '');
		if (rel === '') {
			res.writeHead(200, { 'Content-Type': 'text/html' }).end(PAGE_HTML);
			return;
		}
		for (const [prefix, root] of Object.entries(roots)) {
			if (!rel.startsWith(prefix)) continue;
			const file = join(root, rel.slice(prefix.length));
			if (!existsSync(file) || !statSync(file).isFile()) continue;
			res.writeHead(200, { 'Content-Type': TYPES[extname(file)] ?? 'application/octet-stream' });
			createReadStream(file).pipe(res);
			return;
		}
		res.writeHead(404).end('no');
	});
	return new Promise((ok) => server.listen(0, '127.0.0.1', () => ok({ server, port: server.address().port })));
}

async function waitFor(url, tries = 160) {
	for (let i = 0; i < tries; i++) {
		try {
			if ((await fetch(url)).ok) return true;
		} catch {
			/* not up yet */
		}
		await new Promise((r) => setTimeout(r, 250));
	}
	return false;
}

/** Render one page the way the pane does and time each stage, plus an overlay of `marks` rectangles. */
function cost(page, url, n, marks) {
	return page.evaluate(
		async ([url, n, scale, marks]) => {
			const lib = window.pdfjs;
			const t0 = performance.now();
			// one document per url, as `document_()` keeps it: only the first page of a paper pays the open
			window.docs ??= new Map();
			if (!window.docs.has(url)) window.docs.set(url, lib.getDocument({ url }).promise);
			const doc = await window.docs.get(url);
			const p = await doc.getPage(n);
			const viewport = p.getViewport({ scale });
			const canvas = document.getElementById('c');
			const ratio = window.devicePixelRatio || 1;
			canvas.width = Math.floor(viewport.width * ratio);
			canvas.height = Math.floor(viewport.height * ratio);
			canvas.style.width = `${viewport.width}px`;
			canvas.style.height = `${viewport.height}px`;
			const ctx = canvas.getContext('2d');
			ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
			const t1 = performance.now();
			await p.render({ canvasContext: ctx, viewport, canvas }).promise;
			const t2 = performance.now();
			const holder = document.getElementById('t');
			holder.replaceChildren();
			holder.style.setProperty('--scale-factor', String(scale));
			const content = await p.getTextContent();
			await new lib.TextLayer({ textContentSource: content, container: holder, viewport }).render();
			const t3 = performance.now();
			const over = document.getElementById('m');
			over.replaceChildren();
			for (let i = 0; i < marks; i++) {
				const d = document.createElement('div');
				d.style.cssText = `position:absolute;left:${10 + (i % 7)}%;top:${(i * 3) % 95}%;width:60%;height:1.4%;background:rgb(217 119 87 / .22)`;
				over.append(d);
			}
			void over.getBoundingClientRect().height; // force the layout the paint would have forced
			return {
				pages: doc.numPages,
				size: [Math.round(viewport.width / scale), Math.round(viewport.height / scale)],
				items: content.items.length,
				chars: holder.textContent.trim().length,
				open: t1 - t0,
				render: t2 - t1,
				text: t3 - t2,
				overlay: performance.now() - t3
			};
		},
		[url, n, SCALE, marks]
	);
}

const ms = (v) => v.toFixed(1).padStart(7);
const shortly = (p) => p.replace(workspace + '/', '').replace(homedir(), '~').slice(-30).padEnd(30);

async function phaseCost() {
	const { server, port } = await serveFiles({ 'pdfjs/': join(here, 'node_modules/pdfjs-dist'), 'pdf/': '/' });
	const browser = await chromium.launch();
	const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
	page.on('pageerror', (e) => console.error('page error:', e.message));
	await page.goto(`http://127.0.0.1:${port}/`);
	await page.addScriptTag({
		type: 'module',
		content: `import * as lib from 'http://127.0.0.1:${port}/pdfjs/build/pdf.min.mjs';
			lib.GlobalWorkerOptions.workerSrc = 'http://127.0.0.1:${port}/pdfjs/build/pdf.worker.min.mjs';
			window.pdfjs = lib;`
	});
	await page.waitForFunction(() => !!window.pdfjs);

	console.log(`\n## Cost per page, Chromium, scale ${SCALE}, ${MARKS} overlay rectangles\n`);
	console.log('document                       page   size      items   chars     open  render    text overlay   total');
	for (const pdf of PDFS) {
		const url = `http://127.0.0.1:${port}/pdf${pdf}`;
		await page.evaluate(() => window.docs?.clear());
		const cold = await cost(page, url, 1, MARKS); // the first page of a paper also pays for opening the document
		console.log(`${shortly(pdf)}  opened in ${cold.open.toFixed(0)} ms, ${cold.pages} pages`);
		const wanted = [...new Set([1, 2, Math.ceil(cold.pages / 2), cold.pages])].filter((n) => n <= cold.pages);
		for (const n of wanted) {
			// twice: the first pass pays for the font cache and the worker's first message, and a pane being scrolled
			// through a paper pays neither
			await cost(page, url, n, MARKS);
			const r = await cost(page, url, n, MARKS);
			const total = r.open + r.render + r.text + r.overlay;
			const size = `${r.size[0]}x${r.size[1]}`.padEnd(9);
			console.log(
				`${shortly(pdf)} ${String(n).padStart(4)}  ${size} ${String(r.items).padStart(5)}  ${String(r.chars).padStart(6)}` +
					` ${ms(r.open)} ${ms(r.render)} ${ms(r.text)} ${ms(r.overlay)} ${ms(total)}${total > THRESHOLD ? '  OVER' : ''}`
			);
		}
	}
	await browser.close();
	server.close();
}

async function phaseRoundTrip({ quilt, citekey, page: pageNo, port }) {
	const bundle = join(here, 'build');
	if (!existsSync(join(bundle, 'index.html'))) throw new Error('build the viewer first: npm run build');
	const publisher = spawn('uv', ['run', 'loom', 'serve', '--quilt', quilt, '--port', String(port), '--no-compile'], {
		cwd: join(workspace, 'loom'),
		env: { ...process.env, LOOM_ARRAS_BUNDLE: bundle },
		stdio: 'ignore'
	});
	try {
		if (!(await waitFor(`http://127.0.0.1:${port}/build/manifest.json`))) throw new Error('the publisher never came up');
		const browser = await chromium.launch();
		const page = await browser.newPage({ viewport: { width: 1500, height: 1100 } });
		const noise = [];
		page.on('console', (m) => m.type() === 'error' && noise.push(m.text()));
		await page.goto(`http://127.0.0.1:${port}/digest/${citekey}?page=${pageNo}`);
		await page.waitForSelector('[data-testid="reading"] canvas');
		await page.waitForFunction(() => document.querySelectorAll('.text span').length > 0);

		console.log(`\n## Round trip, ${citekey} page ${pageNo} under the publisher\n`);
		const marks = await page.locator('[data-mark]').count();
		const anchored = await page.locator('[data-testid^="anchored-"]').count();
		console.log(`drawn: ${marks} rectangle(s) over ${anchored} anchored result(s)`);

		// the pane's own path: select through the component, and read what it says loom answered
		const said = await page.evaluate(async () => {
			const spans = [...document.querySelectorAll('.text span')].filter((s) => s.textContent.trim());
			const range = document.createRange();
			range.setStart(spans[2].firstChild, 0);
			range.setEnd(spans[Math.min(6, spans.length - 1)].firstChild, 1);
			const sel = getSelection();
			sel.removeAllRanges();
			sel.addRange(range);
			document.querySelector('.text').dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
			for (let i = 0; i < 80; i++) {
				const el = document.querySelector('[data-testid="located"]');
				if (el && !el.textContent.startsWith('asking')) return el.textContent;
				await new Promise((r) => setTimeout(r, 50));
			}
			return '(no answer)';
		});
		console.log(`through the pane: ${said.replace(/\n/g, ' ')}`);

		// and the rate: many selections of the browser's own text, each asked of the real endpoint
		const asked = await page.evaluate(
			async ([citekey, pageNo]) => {
				const spans = [...document.querySelectorAll('.text span')].filter((s) => s.textContent.trim().length > 1);
				const out = [];
				for (let width = 3; width <= 12; width += 3) {
					for (let i = 0; i + width < spans.length; i += Math.max(1, Math.floor(spans.length / 9))) {
						const range = document.createRange();
						range.setStart(spans[i].firstChild, 0);
						range.setEnd(spans[i + width].firstChild, spans[i + width].textContent.length);
						const sel = getSelection();
						sel.removeAllRanges();
						sel.addRange(range);
						const text = sel.toString().trim();
						if (text.split(/\s+/).length < 4) continue;
						const res = await fetch('/_api/locate', {
							method: 'POST',
							headers: { 'Content-Type': 'application/json' },
							body: JSON.stringify({ citekey, page: pageNo, text })
						});
						const j = await res.json().catch(() => ({}));
						out.push({ words: text.split(/\s+/).length, basis: j.anchor?.basis ?? j.error?.code ?? '?' });
					}
				}
				return out;
			},
			[citekey, pageNo]
		);
		const byText = asked.filter((r) => r.basis === 'text').length;
		const byBox = asked.filter((r) => r.basis === 'box').length;
		console.log(
			`selections asked: ${asked.length}; placed in the page's text: ${byText}; geometry only: ${byBox};` +
				` refused: ${asked.length - byText - byBox}`
		);
		const spread = asked.filter((r) => r.basis !== 'text').map((r) => `${r.words}w:${r.basis}`);
		if (spread.length) console.log(`not placed by text: ${spread.join(', ')}`);
		if (noise.length) console.log(`console errors: ${[...new Set(noise)].join(' | ')}`);
		await browser.close();
	} finally {
		publisher.kill('SIGINT');
	}
}

await phaseCost();
await phaseRoundTrip({ quilt: join(workspace, 'demos/showcase'), citekey: 'Bellamy19', page: 2, port: 8794 });

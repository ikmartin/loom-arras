#!/usr/bin/env node
// An exploratory browser, steered one step at a time (plan 0.13 §13 step 8).
//
// The e2e suites are scripted: they assert a thing that was already decided. The reading study needs the opposite — an
// agent playing the author, choosing what to do next from what it just saw, and photographing it. That cannot be a
// spec file, because a spec is written before the run and the whole point is that the run decides.
//
// So: one long-lived browser, and one command per call. `serve` holds the browser open; every other invocation is a
// client that posts a step to it and prints what came back. Each reply carries the URL and anything the page logged
// since the last step, so a steerer notices breakage without having to ask.
//
// **It drives the real handlers.** `select` builds a DOM Range over the text layer and dispatches a genuine `mouseup`,
// which is what `PdfPage.svelte` listens for; `drag` moves the real mouse, which is what the box tool's pointer
// events need. A harness that faked either would be testing itself.
//
//   node scripts/drive.mjs serve --url http://127.0.0.1:8791/ &
//   node scripts/drive.mjs goto /library/Arden25?page=2
//   node scripts/drive.mjs see [data-testid=pdf-doc]
//   node scripts/drive.mjs shot the-paper-open
//   node scripts/drive.mjs stop
import { createServer } from 'node:http';
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const STATE = join(ROOT, '.drive.json');

const HELP = `steer a browser, one step per call

  serve --url URL [--port N] [--shots DIR] [--headed]   hold a browser open (run this in the background first)

  goto PATH                 navigate, relative to --url
  click SEL                 click the first match
  dblclick SEL              double-click it, which is what travels
  hover SEL                 move the real mouse onto it: a link's preview
  press KEY [SEL]           a key, on SEL or on the page
  fill SEL TEXT             type into a field
  drag SEL x0 y0 x1 y1      drag inside SEL, in fractions of its box: the box tool
  select SEL                select SEL's text and release, which is what the selection tool reads
  see [SEL]                 the visible text of SEL, or of the page
  shot NAME                 a screenshot into --shots
  size W H                  resize the window, as a narrower screen would be
  eval JS                   run it in the page and print the result
  stop                      close the browser
`;

/** The visible text of an element, flattened and capped: a steerer reads this, and a whole page of LaTeX is not a step. */
const SEEN = 4000;

async function serve(args) {
	const { chromium } = await import('playwright');
	const base = args.url ?? 'http://127.0.0.1:8791/';
	const port = Number(args.port ?? 4399);
	const shots = resolve(ROOT, args.shots ?? '../docs/reports/images/0.13-reading-layer/shots');
	mkdirSync(shots, { recursive: true });

	const browser = await chromium.launch({ headless: !args.headed });
	const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const page = await context.newPage();
	// Kept since the last step rather than for ever: a steerer wants what this step broke, not the session's history.
	let said = [];
	page.on('console', (m) => m.type() === 'error' && said.push('console: ' + m.text()));
	page.on('pageerror', (e) => said.push('pageerror: ' + e.message));

	const el = (sel) => page.locator(sel).first();

	const steps = {
		goto: async ([path]) => {
			await page.goto(new URL(path ?? '/', base).href, { waitUntil: 'domcontentloaded' });
			await page.waitForTimeout(400); // the manifest poll and the first render
			return 'at ' + page.url();
		},
		click: async ([sel]) => (await el(sel).click(), 'clicked ' + sel),
		dblclick: async ([sel]) => (await el(sel).dblclick(), 'double-clicked ' + sel),
		hover: async ([sel]) => (await el(sel).hover(), 'hovered ' + sel),
		size: async ([w, h]) => (await page.setViewportSize({ width: Number(w), height: Number(h) }), `sized ${w}x${h}`),
		press: async ([key, sel]) => (sel ? await el(sel).press(key) : await page.keyboard.press(key), 'pressed ' + key),
		fill: async ([sel, ...text]) => (await el(sel).fill(text.join(' ')), 'filled ' + sel),
		drag: async ([sel, x0, y0, x1, y1]) => {
			const box = await el(sel).boundingBox();
			if (!box) throw new Error(sel + ' is not on the page');
			const at = (fx, fy) => [box.x + box.width * Number(fx), box.y + box.height * Number(fy)];
			await page.mouse.move(...at(x0, y0));
			await page.mouse.down();
			await page.mouse.move(...at(x1, y1), { steps: 8 }); // in steps, because the box follows pointermove
			await page.mouse.up();
			return `dragged inside ${sel}`;
		},
		select: async ([sel]) => {
			const got = await el(sel).evaluate((node) => {
				const range = document.createRange();
				range.selectNodeContents(node);
				const sel = window.getSelection();
				sel?.removeAllRanges();
				sel?.addRange(range);
				// the real handler is on mouseup, so the selection must be released the way a pointer releases it
				node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
				return sel?.toString() ?? '';
			});
			return 'selected: ' + got.slice(0, 300);
		},
		see: async ([sel]) => {
			const text = await (sel ? el(sel) : page.locator('body')).innerText();
			return text.replace(/\n{3,}/g, '\n\n').slice(0, SEEN);
		},
		shot: async ([name]) => {
			const to = join(shots, (name ?? 'shot').replace(/[^\w.-]+/g, '-') + '.png');
			await page.screenshot({ path: to });
			return 'wrote ' + to;
		},
		eval: async (argv) => JSON.stringify(await page.evaluate(argv.join(' ')), null, 1) ?? 'undefined'
	};

	const server = createServer((req, res) => {
		let body = '';
		req.on('data', (c) => (body += c));
		req.on('end', async () => {
			const { step, argv } = JSON.parse(body || '{}');
			const answer = async () => {
				if (step === 'stop') return 'stopping';
				const run = steps[step];
				if (!run) throw new Error('no such step: ' + step);
				return await run(argv ?? []);
			};
			let out, bad;
			try {
				out = await answer();
			} catch (e) {
				bad = String(e.message ?? e);
			}
			const logged = said;
			said = [];
			res.writeHead(bad ? 400 : 200, { 'Content-Type': 'application/json' });
			res.end(JSON.stringify({ out, error: bad, url: page.url(), said: logged }));
			if (step === 'stop') {
				server.close();
				await browser.close();
				rmSync(STATE, { force: true });
			}
		});
	});
	server.listen(port, '127.0.0.1', () => {
		writeFileSync(STATE, JSON.stringify({ port, base, shots }) + '\n');
		process.stdout.write(`steering ${base} on ${port}; shots into ${shots}\n`);
	});
}

async function client(step, argv) {
	let state;
	try {
		state = JSON.parse(readFileSync(STATE, 'utf8'));
	} catch {
		process.stderr.write('no browser is open: run `node scripts/drive.mjs serve --url ...` in the background first\n');
		process.exit(2);
	}
	const res = await fetch(`http://127.0.0.1:${state.port}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ step, argv })
	});
	const said = await res.json();
	if (said.said?.length) process.stderr.write(said.said.join('\n') + '\n');
	if (said.error) {
		process.stderr.write(said.error + '\n');
		process.exit(1);
	}
	process.stdout.write(String(said.out ?? '') + '\n');
	if (step !== 'see' && step !== 'eval') process.stdout.write('  — ' + said.url + '\n');
}

const [step, ...argv] = process.argv.slice(2);
if (!step || step === '--help' || step === 'help') {
	process.stdout.write(HELP);
} else if (step === 'serve') {
	const flags = {};
	for (let i = 0; i < argv.length; i++) {
		if (!argv[i].startsWith('--')) continue;
		const name = argv[i].slice(2);
		flags[name] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
	}
	await serve(flags);
} else {
	await client(step, argv);
}

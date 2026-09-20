// Round three: every settings row, and the other interactions a reader feels, on a real corpus. Not a gate -- it prints numbers.
// Run with: PERF_BUILD=../demos/relloc/build npx playwright test --config playwright.perf.config.ts tests/perf/probe3.e2e.ts
import { test, type Page } from '@playwright/test';

const REPEAT = 3;

/** Install an Event Timing observer; `interaction` is what the browser reports as the click's latency to the next paint (INP). */
async function observe(page: Page) {
	await page.evaluate(() => {
		const w = window as any;
		w.__ev = [];
		w.__lt = [];
		new PerformanceObserver((l) => {
			for (const e of l.getEntries() as any[]) if (e.name === 'click' || e.name === 'pointerup' || e.name === 'pointerdown') w.__ev.push({ name: e.name, d: e.duration, p: e.processingEnd - e.processingStart, t: e.startTime });
		}).observe({ type: 'event', durationThreshold: 16, buffered: false } as any);
		new PerformanceObserver((l) => {
			for (const e of l.getEntries()) w.__lt.push({ d: e.duration, t: e.startTime });
		}).observe({ type: 'longtask' });
	});
}

async function settle(page: Page) {
	await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 50)))));
}

/** Click, then report the event's duration (click start to next paint) and the long-task time inside the window. */
async function measure(page: Page, selector: string): Promise<{ inp: number; wall: number; lt: number }> {
	await settle(page);
	await page.evaluate(() => {
		(window as any).__ev = [];
		(window as any).__lt = [];
	});
	const t0 = await page.evaluate(() => performance.now());
	await page.click(selector);
	const wall = await page.evaluate(
		(t0) => new Promise<number>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(performance.now() - t0)))),
		t0
	);
	await page.waitForTimeout(300);
	const { ev, lt } = await page.evaluate(() => ({ ev: (window as any).__ev as any[], lt: (window as any).__lt as any[] }));
	const inp = Math.max(0, ...ev.map((e) => e.d));
	return { inp: Math.round(inp), wall: Math.round(wall), lt: Math.round(lt.reduce((n, e) => n + e.d, 0)) };
}

function row(label: string, xs: { inp: number; wall: number; lt: number }[]) {
	const med = (k: 'inp' | 'wall' | 'lt') => xs.map((x) => x[k]).sort((a, b) => a - b)[Math.floor(xs.length / 2)];
	// eslint-disable-next-line no-console
	console.log(`  ${label.padEnd(34)} inp ${String(med('inp')).padStart(5)}  wall ${String(med('wall')).padStart(5)}  longtask ${String(med('lt')).padStart(5)}   [${xs.map((x) => x.inp).join(' ')}]`);
}

test('settings rows and interactions on a real corpus', async ({ page }) => {
	test.setTimeout(600000);
	await page.setViewportSize({ width: 1400, height: 900 });
	await page.goto('/');
	await page.waitForSelector('main h1');
	const doc = await page.evaluate(async () => {
		const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
		const master = m.masters.find((x: any) => x.default) ?? m.masters[0];
		return '/master/' + master.path.replace(/^.*\//, '').replace(/\.tex$/, '');
	});
	await page.goto(doc);
	await page.waitForSelector('.fragment .math');
	// until every formula is typeset
	await page.waitForFunction(() => document.querySelectorAll('.fragment .math').length > 0 && document.querySelectorAll('.fragment .math:not(:has(mjx-container))').length === 0, null, { timeout: 60000 });
	await page.waitForTimeout(500);
	const stats = await page.evaluate(() => ({ el: document.querySelectorAll('*').length, math: document.querySelectorAll('mjx-container').length }));
	// eslint-disable-next-line no-console
	console.log(`\n  ${doc}: ${stats.el} elements, ${stats.math} formulas`);
	await observe(page);

	await page.click('[data-testid=settings-toggle]');
	await page.waitForSelector('[data-testid=settings-panel]');

	const rows: [string, string[]][] = [
		['size', ['l', 's', 'm']],
		['face', ['sans', 'serif']],
		['width', ['wide', 'narrow', 'mid']],
		['theme', ['dark', 'light', 'system']],
		['format', ['p2', 'b1', 'b2', 'p1']],
		['comments', ['inline', 'hover', 'margin']]
	];
	for (const [name, values] of rows) {
		for (const v of values) {
			const xs = [];
			for (let i = 0; i < REPEAT; i++) {
				xs.push(await measure(page, `[data-testid=${name}-${v}]`));
				// back to the first value so every repetition is a real change
				if (i < REPEAT - 1) {
					const back = values[(values.indexOf(v) + values.length - 1) % values.length];
					await page.click(`[data-testid=${name}-${back}]`);
				}
			}
			row(`${name} -> ${v}`, xs);
		}
	}
	// opening and closing the panel itself
	await page.click('[data-testid=settings-toggle]');
	row('settings toggle (open)', [await measure(page, '[data-testid=settings-toggle]')]);

	// scrolling the read view: frames over a programmatic smooth-ish scroll
	const scroll = await page.evaluate(async () => {
		const gaps: number[] = [];
		let last = performance.now();
		const step = () =>
			new Promise<void>((r) =>
				requestAnimationFrame(() => {
					const n = performance.now();
					gaps.push(n - last);
					last = n;
					r();
				})
			);
		const max = document.documentElement.scrollHeight;
		for (let y = 0; y < max; y += 400) {
			window.scrollTo(0, y);
			await step();
		}
		gaps.sort((a, b) => a - b);
		return { frames: gaps.length, p50: Math.round(gaps[gaps.length >> 1]), p95: Math.round(gaps[Math.floor(gaps.length * 0.95)]), max: Math.round(gaps[gaps.length - 1]), total: Math.round(gaps.reduce((a, b) => a + b, 0)) };
	});
	// eslint-disable-next-line no-console
	console.log(`  scroll whole doc                   frames ${scroll.frames} p50 ${scroll.p50} p95 ${scroll.p95} max ${scroll.max} total ${scroll.total}`);
	await page.evaluate(() => window.scrollTo(0, 0));

	// hover preview on a cross-reference
	const refSel = '.fragment a[href*="#"], .fragment a[href*="/node/"]';
	const ref = page.locator(refSel).nth(5);
	if (await ref.count()) {
		await ref.scrollIntoViewIfNeeded();
		await settle(page);
		const t0 = Date.now();
		await ref.hover();
		const ok = await page.waitForSelector('[data-testid=link-preview], .preview', { timeout: 5000 }).then(() => true, () => false);
		// eslint-disable-next-line no-console
		console.log(`  hover preview                      ${ok ? Date.now() - t0 + ' ms' : 'no preview seen'}`);
	}

	// navigations: a node page, the graph, and back to the document, each to its heading
	const nodeUrl = await page.evaluate(async () => {
		const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
		const k = Object.keys(m.nodes)[Math.floor(Object.keys(m.nodes).length / 2)];
		return '/node/' + encodeURIComponent(k);
	});
	for (const [label, url, sel] of [
		['client nav: node page', nodeUrl, 'main .fragment'],
		['client nav: graph', '/graph', 'main svg, main canvas'],
		['client nav: back to document', doc, '.fragment .math mjx-container']
	] as const) {
		const t0 = Date.now();
		await page.evaluate((u) => {
			const a = document.createElement('a');
			a.href = u;
			document.body.appendChild(a);
			a.click();
			a.remove();
		}, url);
		await page.waitForURL('**' + url.split('#')[0]);
		await page.waitForSelector(sel, { timeout: 30000 });
		const lt = await page.evaluate(() => new Promise<number>((r) => setTimeout(() => r(((window as any).__lt ?? []).length), 10)));
		// eslint-disable-next-line no-console
		console.log(`  ${label.padEnd(34)} ${Date.now() - t0} ms (${lt} long tasks)`);
		await page.waitForTimeout(1500);
	}
});

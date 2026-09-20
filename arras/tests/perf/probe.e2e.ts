// Measuring before optimising (running-requests: "test out 6 potential optimizations, implement the top 3").
// Not a gate -- it prints numbers. Run with: npx playwright test --config playwright.perf.config.ts
import { test } from '@playwright/test';

async function time(page: import('@playwright/test').Page, label: string, fn: () => Promise<void>) {
	const t0 = Date.now();
	await fn();
	// eslint-disable-next-line no-console
	console.log(`  ${label.padEnd(46)} ${Date.now() - t0} ms`);
}

test('where the time goes', async ({ page }) => {
	// whichever document this corpus calls its main one
	await page.goto('/');
	await page.waitForSelector('main h1');
	const doc = await page.evaluate(async () => {
		const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
		const master = m.masters.find((x: any) => x.default) ?? m.masters[0];
		return '/master/' + master.path.replace(/^.*\//, '').replace(/\.tex$/, '');
	});
	await page.goto(doc);
	await page.waitForSelector('.fragment');
	await page.waitForTimeout(2500);

	await time(page, '1. a settings attribute flip (size)', async () => {
		await page.evaluate(async () => {
			const el = document.documentElement;
			el.setAttribute('data-size', el.getAttribute('data-size') === 'l' ? 'm' : 'l');
			await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
		});
	});

	await time(page, '2. forced style+layout of the document', async () => {
		await page.evaluate(async () => {
			document.body.getBoundingClientRect();
			void document.body.offsetHeight;
		});
	});

	await time(page, '3. re-deriving every annotation filter once', async () => {
		await page.evaluate(async () => {
			const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
			const keys = Object.keys(m.keys);
			let n = 0;
			for (const k of keys) n += Object.values(m.annotations).filter((a: any) => a.target.key === k).length;
			return n;
		});
	});

	await time(page, '4. re-parsing the manifest', async () => {
		await page.evaluate(async () => {
			const text = await (await fetch(new URL('/build/manifest.json', location.href))).text();
			JSON.parse(text);
		});
	});

	await time(page, '5. counting typeset formulas in the DOM', async () => {
		await page.evaluate(() => document.querySelectorAll('mjx-container').length);
	});

	await time(page, '6. a full route change and back', async () => {
		await page.goto('/graph');
		await page.waitForSelector('main h1');
		await page.goto(doc);
		await page.waitForSelector('.fragment');
	});

	// The experiments: each is applied, measured, and undone, so the numbers are comparable against the baseline above.
	await time(page, 'X1. flip again with content-visibility on blocks', async () => {
		await page.evaluate(async () => {
			const s = document.createElement('style');
			s.id = 'x1';
			s.textContent = '.fragment .env, .fragment section { content-visibility: auto; contain-intrinsic-size: auto 240px; }';
			document.head.appendChild(s);
			await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
			const el = document.documentElement;
			el.setAttribute('data-size', el.getAttribute('data-size') === 'l' ? 'm' : 'l');
			await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
		});
	});
	await page.evaluate(() => document.getElementById('x1')?.remove());

	await time(page, 'X2. annotations indexed by target once', async () => {
		await page.evaluate(async () => {
			const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
			const byKey = new Map<string, unknown[]>();
			for (const a of Object.values(m.annotations) as any[]) {
				const list = byKey.get(a.target.key) ?? [];
				list.push(a);
				byKey.set(a.target.key, list);
			}
			let n = 0;
			for (const k of Object.keys(m.keys)) n += (byKey.get(k) ?? []).length;
			return n;
		});
	});

	await time(page, 'X3. flip with the document detached', async () => {
		await page.evaluate(async () => {
			const frag = document.querySelector('.fragment') as HTMLElement | null;
			const parent = frag?.parentElement ?? null;
			const next = frag?.nextSibling ?? null;
			if (frag && parent) parent.removeChild(frag);
			const el = document.documentElement;
			el.setAttribute('data-size', el.getAttribute('data-size') === 'l' ? 'm' : 'l');
			await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
			if (frag && parent) parent.insertBefore(frag, next);
		});
	});

	const counts = await page.evaluate(() => ({
		elements: document.querySelectorAll('*').length,
		formulas: document.querySelectorAll('mjx-container').length,
		svgPaths: document.querySelectorAll('mjx-container path').length
	}));
	// eslint-disable-next-line no-console
	console.log(`  DOM: ${counts.elements} elements, ${counts.formulas} formulas, ${counts.svgPaths} glyph paths`);
});

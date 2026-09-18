// Photographing a corpus built to break things, and timing what it costs to render.
import { test } from '@playwright/test';

const OUT = '../records/images';

test('what the viewer does with hostile input', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	const bad: string[] = [];
	page.on('pageerror', (e) => bad.push('pageerror: ' + e.message));
	page.on('console', (m) => m.type() === 'error' && bad.push('console: ' + m.text()));
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', format: 'paper', comments: 'margin' })));

	const t0 = Date.now();
	await page.goto('/node/hx-0001');
	await page.waitForSelector('main h1');
	await page.waitForTimeout(1500);
	// eslint-disable-next-line no-console
	console.log(`  node page with hostile markup: ${Date.now() - t0} ms`);
	await page.screenshot({ path: `${OUT}/hostile-injection.png` });

	// did anything execute?
	const pwned = await page.evaluate(() => (window as unknown as Record<string, unknown>).__pwned ?? null);
	// eslint-disable-next-line no-console
	console.log(`  window.__pwned = ${JSON.stringify(pwned)}`);

	const t1 = Date.now();
	await page.goto('/node/hx-0013');
	await page.waitForSelector('main h1');
	await page.waitForTimeout(3000);
	// eslint-disable-next-line no-console
	console.log(`  node page with a 3000-term formula: ${Date.now() - t1} ms`);
	await page.screenshot({ path: `${OUT}/hostile-scale.png` });

	const t2 = Date.now();
	await page.goto('/graph');
	await page.waitForSelector('main h1');
	await page.waitForTimeout(3000);
	// eslint-disable-next-line no-console
	console.log(`  graph of 300+ nodes: ${Date.now() - t2} ms`);
	await page.screenshot({ path: `${OUT}/hostile-graph.png` });

	await page.goto('/problems');
	await page.waitForSelector('main h1');
	await page.waitForTimeout(800);
	await page.screenshot({ path: `${OUT}/hostile-problems.png` });

	// eslint-disable-next-line no-console
	console.log('  page errors: ' + (bad.length ? JSON.stringify(bad.slice(0, 4)) : 'none'));
});

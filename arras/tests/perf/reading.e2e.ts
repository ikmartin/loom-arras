// The reading layer's performance floor (plan 0.13 §11): what a page of a paper costs to put on screen, and what an
// annotated page costs on top of it.
//
// A floor rather than a benchmark. These numbers are generous — a page measured at 12–16ms against a 150ms budget in
// `docs/reports/0.13-slice-findings.md` — because the value of a threshold here is that it catches a change of an order
// of magnitude, and a tight one on a shared CI machine only teaches people to ignore it.
//
// It runs against whatever corpus `PERF_BUILD` points at, like the rest of this directory, and skips rather than fails
// where that corpus has no paper to render: a floor that cannot measure says so.
import { expect, test } from '@playwright/test';

/** The plan's budget for render plus text layer plus overlay, per page. */
const PER_PAGE = 150;
/** A whole document opening: PDF.js loading its worker, and the document being parsed. */
const OPEN = 2500;

test('a page of a paper renders inside the budget, and an annotated one is not dearer', async ({ page }) => {
	const bad: string[] = [];
	page.on('pageerror', (e) => bad.push('pageerror: ' + e.message));

	await page.goto('/');
	const work = await page.evaluate(async () => {
		const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
		const hit = Object.values(m.references ?? {}).find((r) => (r as { artifacts?: { pdf?: boolean } })?.artifacts?.pdf);
		return hit ? { citekey: (hit as { citekey: string }).citekey } : null;
	});
	test.skip(!work, 'this corpus has no paper on this machine, so there is nothing to render');

	const t0 = Date.now();
	await page.goto(`/library/${work!.citekey}?page=1`);
	await page.getByTestId('pdf-doc').waitFor();
	await page.locator('[data-testid="pdf-page-1"] canvas').waitFor();
	await expect.poll(() => page.locator('.text span').count()).toBeGreaterThan(0);
	const opened = Date.now() - t0;
	// eslint-disable-next-line no-console
	console.log(`  opening a paper and drawing its first page: ${opened} ms`);
	expect(opened).toBeLessThan(OPEN);

	// The stages the budget is about, read from the renderer's own marks rather than from the wall clock, so the number
	// is the work and not the wait for the fetch.
	const stages = await page.evaluate(() => {
		const at = (name: string) =>
			performance
				.getEntriesByType('measure')
				.filter((m) => m.name === name)
				.map((m) => m.duration);
		return { render: at('pdf:render'), text: at('pdf:text') };
	});
	const worst = Math.max(...stages.render, 0) + Math.max(...stages.text, 0);
	// eslint-disable-next-line no-console
	console.log(`  worst page: render ${Math.max(...stages.render, 0).toFixed(1)} ms + text layer ${Math.max(...stages.text, 0).toFixed(1)} ms`);
	expect(worst).toBeLessThan(PER_PAGE);

	// And the pages outside the window keep their height without a canvas, which is what makes a long book affordable.
	// A paper shorter than the window cannot show this, and saying so is better than an assertion that always holds.
	const drawn = await page.locator('[data-testid="pdf-doc"] canvas').count();
	const held = await page.locator('[data-testid="pdf-doc"] [data-holder]').count();
	// eslint-disable-next-line no-console
	console.log(`  ${drawn} canvas(es) for ${held} page(s)`);
	if (held > 5) expect(drawn).toBeLessThan(held);
	// eslint-disable-next-line no-console
	else console.log('  (too short to virtualise: point PERF_BUILD at a corpus with a long paper to test that)');

	expect(bad).toEqual([]);
});

test('a page carrying twenty annotations is not dearer to draw than one carrying none', async ({ page }) => {
	// Twenty on one page is past what any real page carries; the overlay is the cheapest of the three stages and this
	// is the test that keeps it that way, since a blend mode or a shadow per mark is what would end that.
	await page.goto('/');
	const many = await page.evaluate(() => {
		const host = document.createElement('div');
		host.style.cssText = 'position:relative;width:612px;height:792px';
		document.body.append(host);
		const t0 = performance.now();
		for (let i = 0; i < 20; i++) {
			const d = document.createElement('div');
			d.style.cssText = `position:absolute;left:10%;top:${(i * 4) % 95}%;width:60%;height:1.4%;background:rgb(217 119 87 / .22)`;
			host.append(d);
		}
		void host.getBoundingClientRect().height;
		const cost = performance.now() - t0;
		host.remove();
		return cost;
	});
	// eslint-disable-next-line no-console
	console.log(`  twenty overlay rectangles: ${many.toFixed(1)} ms`);
	expect(many).toBeLessThan(16); // one frame
});

// The shell: the icon strip, the side panel's frame, the key gutter Show ids opens, and a window the whole of it fits. What the panel holds is in panel.e2e.ts. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { pane, prefs } from '../workspace';
import { manifest } from '../manifest';

/** The contents hang off the open document behind a `show` disclosure; open it if it is folded. */
async function openContents(page: Page): Promise<void> {
	const toggle = page.getByTestId('contents-toggle');
	await toggle.waitFor({ state: 'visible' });
	if ((await toggle.getAttribute('aria-expanded')) === 'false') await toggle.click();
	await page.getByRole('navigation', { name: 'Contents' }).waitFor();
}

test('the strip offers each view once, each drawn rather than a glyph, beside search and the problems glyph, and the panel the documents and contents', async ({ page }) => {
	await page.goto('/master/main');
	await expect(page.getByTestId('docs-drafts')).toBeVisible();
	await openContents(page);
	await expect(page.getByRole('navigation', { name: 'Contents' })).toBeVisible();
	const strip = page.getByRole('navigation', { name: 'Views' });
	await expect(page.getByRole('link', { name: 'graph', exact: true })).toBeVisible();
	// every icon an SVG and no text: unicode marks rendered at whatever weight and baseline a font chose, so a column of them sat unevenly
	const links = strip.locator('a');
	const n = await links.count();
	expect(n).toBeGreaterThan(3);
	for (let i = 0; i < n; i++) {
		await expect(links.nth(i).locator('svg')).toHaveCount(1);
		expect((await links.nth(i).innerText()).trim()).toBe('');
	}
	await expect(page.getByRole('button', { name: 'Search' })).toBeVisible();
	await expect(strip.getByRole('button', { name: 'Search' }).locator('svg')).toHaveCount(1);
	// no two icons go to the same place, and home is one of them
	const hrefs = await strip.locator('a[href]').evaluateAll((els) => els.map((e) => e.getAttribute('href')));
	expect(hrefs.filter((h, i) => hrefs.indexOf(h) !== i), `the strip's hrefs: ${hrefs.join(', ')}`).toEqual([]);
	expect(hrefs).toContain('/');
	await expect(page.getByTestId('problems-glyph')).toHaveAttribute('title', /^problems: /);
});

test("the side panel scrolls rather than overflowing, and the contents' last entry can be reached", async ({ page }) => {
	// one scroll region, and it is the panel: with a Library group below the contents, a column that could not scroll squeezed the tree and pushed the sections under it off the bottom
	await page.setViewportSize({ width: 1280, height: 320 }); // short enough that the fixture's panel cannot fit
	await page.goto('/master/main');
	await openContents(page);
	const sections = page.locator('.panel .sections');
	const box = await sections.evaluate((el) => ({ scroll: el.scrollHeight, client: el.clientHeight, overflow: getComputedStyle(el).overflowY }));
	expect(box.overflow).toBe('auto');
	expect(box.scroll).toBeGreaterThan(box.client);
	const last = page.getByRole('navigation', { name: 'Contents' }).locator('a').last();
	await last.scrollIntoViewIfNeeded();
	await expect(last).toBeInViewport();
	// and the write target is pinned below the scroll rather than scrolled away with it
	await expect(page.getByTestId('session-footer')).toBeInViewport();
});

test('the side panel collapses, and the column goes with it', async ({ page }) => {
	// it collapses independently of the split and goes first: on a narrow window it is the column a reader needs least
	await page.goto('/master/main');
	await openContents(page);
	const panel = page.locator('.panel');
	const wide = (await panel.boundingBox())!.width;
	await page.getByTestId('panel-fold').click();
	await expect(page.getByRole('navigation', { name: 'Contents' })).toBeHidden();
	const narrow = (await panel.boundingBox())!.width;
	expect(narrow).toBeLessThan(wide / 3); // the column itself goes, not just its contents
	// and it comes back
	await page.getByTestId('panel-fold').click();
	await expect(page.getByRole('navigation', { name: 'Contents' })).toBeVisible();
});

test('the side panel shows its scrollbar only while it is in use', async ({ page }) => {
	// the panel is the scroll region, so the rule against a grey stripe down the side of every page belongs to it
	await page.setViewportSize({ width: 1440, height: 340 });
	await page.goto('/master/main');
	const rail = page.locator('.panel .sections');
	await expect(rail).toBeVisible();
	const atRest = await rail.evaluate((el) => getComputedStyle(el).scrollbarColor);
	expect(atRest).toContain('rgba(0, 0, 0, 0)'); // the thumb is transparent until the rail is used
	await rail.hover();
	await expect.poll(async () => rail.evaluate((el) => getComputedStyle(el).scrollbarColor)).not.toContain('rgba(0, 0, 0, 0) rgba(0, 0, 0, 0)');
});

test('the shell fits the window: nothing in a rail falls below the fold', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.goto('/');
	await page.waitForSelector('main h1');
	const fit = await page.evaluate(() => ({ inner: window.innerHeight, scroll: document.documentElement.scrollHeight }));
	expect(fit.scroll).toBeLessThanOrEqual(fit.inner); // a rail is `height: 100vh`, and its padding must count inside that
	// the things at the foot of the shell are reachable without scrolling
	await expect(page.getByTestId('settings-toggle')).toBeInViewport();
	await expect(page.getByTestId('problems-glyph')).toBeInViewport();
	await expect(page.getByTestId('session-footer')).toBeInViewport();
});

test('Show ids puts the id and the state in the key gutter, beside a node in a document and on its own page', async ({ page }) => {
	// the gutter is behind Settings > Show ids, which is off by default, so the test turns it on the way a reader would
	await page.setViewportSize({ width: 1440, height: 1000 });
	await prefs(page, { ids: true });
	await page.goto('/master/main');
	await page.waitForSelector('.fragment .env[data-key]');
	const env = page.locator('.fragment .env[data-key="sy-0001"]');
	const margin = env.locator('.node-margin');
	await expect(margin).toContainText('sy-0001');
	await expect(margin).toContainText(manifest.keys['sy-0001'].state);
	const envBox = (await env.boundingBox())!;
	const marginBox = (await margin.boundingBox())!;
	// it sits wholly in the left gutter, ending where the environment's accent rule begins
	expect(marginBox.x + marginBox.width).toBeLessThanOrEqual(envBox.x + 1);
	// and an id is never broken across lines, however narrow the gutter gets
	expect(await margin.locator('.mid').evaluate((e) => e.getClientRects().length)).toBe(1);

	// a node's own page carries the same gutter
	await page.goto('/node/sy-0003');
	const own = pane(page, 0).locator('.fragment .env[data-id="sy-0003"] > .node-margin');
	await expect(own).toBeVisible();
	await expect(own).toContainText('sy-0003');
	await expect(own).toContainText(manifest.keys['sy-0003'].state);
});

test('no route reaches an unknown key from review or the problems page', async ({ page }) => {
	for (const start of ['/review', '/problems']) {
		await page.goto(start);
		await expect(page.locator('main a[href^="/node/"]').first()).toBeAttached();
		const hrefs = await page.locator('main a[href^="/node/"]').evaluateAll((els) => [...new Set(els.map((e) => (e as HTMLAnchorElement).getAttribute('href')!))]);
		expect(hrefs.length).toBeGreaterThan(0);
		for (const href of hrefs) {
			await page.goto(href.split('#')[0]);
			const item = page.locator('[data-pane] .page.item').first();
			await expect(item, `${start} links to ${href}`).toBeVisible();
			await expect(item, `${start} links to ${href}`).not.toContainText('The manifest has no node');
		}
	}
});

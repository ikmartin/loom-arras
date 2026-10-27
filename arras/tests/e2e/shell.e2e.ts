// The shell: the column's frame (its head, the two primary views, its footer), the key gutter Show ids opens, and a window the whole of it fits. What the column holds is in panel.e2e.ts, the frame at each width in frame.e2e.ts. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { pane, prefs } from '../workspace';
import { manifest } from '../manifest';

/** The Outline is the focused document's, beneath the documents; wait for it. */
async function openContents(page: Page): Promise<void> {
	await page.getByRole('navigation', { name: 'Contents' }).waitFor();
}

test('the column leads with the quilt, Settings and the fold, then Docs and Review, and holds no list of views', async ({ page }) => {
	await page.goto('/master/main');
	await expect(page.getByTestId('docs-drafts')).toBeVisible();
	await openContents(page);
	await expect(page.getByRole('navigation', { name: 'Contents' })).toBeVisible();
	await expect(page.getByTestId('quilt-name')).toHaveText(manifest.corpus.name);
	await expect(page.getByTestId('settings-toggle')).toBeVisible();
	await expect(page.getByTestId('panel-fold')).toBeVisible();
	const primary = page.getByRole('navigation', { name: 'Primary views' });
	await expect(primary.getByRole('link')).toHaveText(['Docs', 'Review']);
	await expect(page.getByTestId('primary-docs')).toHaveAttribute('aria-current', 'page');
	await expect(page.getByTestId('primary-review')).toHaveAttribute('href', '/review');
	// the icon strip and its views are gone; search is ⌘K alone, and the problems chip is in the column's footer
	await expect(page.getByRole('navigation', { name: 'Views', exact: true })).toHaveCount(0);
	await expect(page.getByTestId('column-search')).toHaveCount(0);
	await expect(page.getByTestId('problems-chip')).toHaveAttribute('title', /^problems: /);
	await expect(page.getByTestId('problems-chip')).toContainText(String(manifest.diagnostics.filter((d: { severity: string }) => d.severity === 'error' || d.severity === 'warning').length));
});

test('Review is current on the quilt-management pages, and Docs everywhere else', async ({ page }) => {
	for (const [path, on] of [['/review', 'review'], ['/review/problems', 'review'], ['/graph', 'docs'], ['/review/library', 'review'], ['/review/sessions', 'review'], ['/review/history', 'review'], ['/master/main', 'docs']] as const) {
		await page.goto(path);
		await expect(page.getByTestId(`primary-${on}`), path).toHaveAttribute('aria-current', 'page');
	}
});

test("the side panel scrolls rather than overflowing, and the contents' last entry can be reached", async ({ page }) => {
	// the documents scroll in their own box and the outline in its own: a column that could not scroll squeezed the tree and pushed what was under it off the bottom
	await page.setViewportSize({ width: 1280, height: 320 }); // short enough that the fixture's documents cannot fit
	await page.goto('/master/main');
	await openContents(page);
	const docs = page.getByTestId('docs-part');
	const box = await docs.evaluate((el) => ({ scroll: el.scrollHeight, client: el.clientHeight, overflow: getComputedStyle(el).overflowY }));
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

test('a scrollbar shows only while its panel or pane is being scrolled', async ({ page }) => {
	// hidden at rest, whether or not the pointer is over it; shown while it moves, and gone again a moment after
	await page.setViewportSize({ width: 1440, height: 340 });
	await page.goto('/master/main');
	const hidden = 'rgba(0, 0, 0, 0) rgba(0, 0, 0, 0)';
	const color = (el: import('@playwright/test').Locator) => el.evaluate((e) => getComputedStyle(e).scrollbarColor);
	for (const region of [page.getByTestId('docs-part'), page.getByTestId('pane-0').locator('> .body')]) {
		await expect(region).toBeVisible();
		expect(await color(region)).toBe(hidden);
		await region.hover();
		expect(await color(region)).toBe(hidden);
		await region.evaluate((e) => e.scrollBy(0, 60));
		await expect.poll(() => color(region)).not.toBe(hidden);
		await expect.poll(() => color(region), { timeout: 3000 }).toBe(hidden);
	}
});

test('the shell fits the window: nothing in a rail falls below the fold', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.goto('/');
	await page.waitForSelector('[data-testid="pane-0"]');
	const fit = await page.evaluate(() => ({ inner: window.innerHeight, scroll: document.documentElement.scrollHeight }));
	expect(fit.scroll).toBeLessThanOrEqual(fit.inner); // a rail is `height: 100vh`, and its padding must count inside that
	// the things at the foot of the shell are reachable without scrolling
	await expect(page.getByTestId('settings-toggle')).toBeInViewport();
	await expect(page.getByTestId('problems-chip')).toBeInViewport();
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
	for (const start of ['/review', '/review/problems']) {
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

// Screenshots for the workspace's feature reports (records/), as distinct from the book's reference figures in shots.spec.ts. Run with `npm run shots:report`; the images land in records/images/, or in `ARRAS_SHOTS_OUT` when it is set.
import { expect, test, type Page } from '@playwright/test';
import { outDir, settle, still } from './settle';

const OUT = outDir('../records/images');

/** Store the display preferences a shot is taken under, before the app reads them. */
async function under(page: Page, prefs: Record<string, string> = {}): Promise<void> {
	await page.goto('/');
	await page.evaluate((p) => localStorage.setItem('arras.prefs', JSON.stringify({ face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'floating', ...p })), prefs);
}

async function shot(page: Page, name: string, path: string): Promise<void> {
	await under(page);
	await page.goto(path);
	await settle(page);
	await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
}

test.use({ viewport: { width: 1440, height: 900 } });

test('a corpus that has everything', async ({ page }) => {
	// the counterpart to tests/shots-minimal: the same viewer against a corpus declaring all four capabilities, so the two images beside each other are the whole of what `publishes` does
	await shot(page, 'capability-full-home', '/');
	await shot(page, 'node-page', '/node/sy-0003');
	await shot(page, 'review-ledger', '/review');
});

test('a run reviewed', async ({ page }) => {
	// a session read on its own: what it did, beside the document it is about, and its Chat; and the link working, a finding opening its mark in the other pane
	const beside = '/master/main?beside=' + encodeURIComponent('/session/s-2026-09-16-0001?view=did');
	await shot(page, 'session-did', beside);
	await shot(page, 'session-discussion', '/session/s-2026-09-16-0001');
	await page.goto(beside);
	await page.waitForSelector('[data-pane="0"] .fragment [data-annotation]');
	await page.locator('[data-pane="0"] > .body').evaluate((el) => (el.scrollTop = el.scrollHeight));
	await page.locator('[data-pane="1"]').getByTestId('did-annotation').first().click();
	await expect(page.locator('[data-pane="0"]').getByTestId('comment-expanded').first()).toBeVisible();
	await settle(page);
	await page.screenshot({ path: `${OUT}/session-linked.png` });
});

test('a node read three ways', async ({ page }) => {
	// what a result rests on, what it says as written, and what an agent proposed for it
	await under(page);

	// what it rests on stands in its context, beside it
	await page.goto('/node/sy-0003?beside=' + encodeURIComponent('/context/sy-0003'));
	await page.getByTestId('closure-open').locator('> summary').click();
	await page.getByTestId('closure-depth-2').click();
	await expect(page.getByTestId('closure-panel').locator('ol.stack > li').first()).toBeVisible();
	await settle(page);
	await page.screenshot({ path: `${OUT}/closure-stack.png` });

	await page.goto('/node/sy-0003');
	await page.waitForSelector('[data-pane] .fragment');
	await page.getByTestId('source-toggle').first().click();
	await expect(page.getByTestId('verbatim').first()).toBeVisible();
	await still(page);
	await page.screenshot({ path: `${OUT}/verbatim.png` });

	await page.goto('/node/sy-0004');
	await page.getByTestId('toggle-annotations').click();
	await expect(page.getByTestId('payload').first()).toBeVisible();
	await settle(page);
	await page.screenshot({ path: `${OUT}/payload.png` });
});

test('the graph coloured by taxon', async ({ page }) => {
	await shot(page, 'graph-taxa', '/graph');
});

test('the same document, set two ways', async ({ page }) => {
	// the compiled page and the web page, each in its first setting
	for (const format of ['p1', 'b1'] as const) {
		await under(page, { format });
		await page.goto('/master/main');
		await expect(page.locator('html')).toHaveAttribute('data-format', format);
		await settle(page);
		await page.screenshot({ path: `${OUT}/format-${format}.png` });
	}
});

// Screenshots for the workspace's feature reports (records/), as distinct from the book's reference figures in shots.spec.ts. Run with `npm run shots:report`; the images land in records/images/ and are referenced by the reports there.
import { test, type Page } from '@playwright/test';

const OUT = '../records/images';

async function settle(page: Page) {
	// a page's title, or in reading mode a pane's content, since an item draws no chrome and a session no title
	await page.waitForSelector('main h1, [data-pane] > .body > *', { timeout: 15000 });
	await page.waitForTimeout(700); // MathJax and the force simulation
}

async function shot(page: Page, name: string, path: string, opts: { shell?: 'a' | 'c'; theme?: 'light' | 'dark' } = {}) {
	await page.goto('/');
	await page.evaluate(
		([shell, theme]) => localStorage.setItem('arras.prefs', JSON.stringify({ shell, face: 'serif', size: 'm', width: 'mid', theme, comments: 'floating' })),
		[opts.shell ?? 'c', opts.theme ?? 'light']
	);
	await page.goto(path);
	await settle(page);
	await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
}

test.use({ viewport: { width: 1440, height: 900 } });

test('a corpus that has everything', async ({ page }) => {
	// The counterpart to tests/shots-minimal: the same viewer against a corpus declaring all four capabilities, so the
	// two images beside each other are the whole of what `publishes` does.
	await shot(page, 'capability-full-home', '/');
	await shot(page, 'node-page', '/node/sy-0003');
	await shot(page, 'review-ledger', '/review');
});

test('a run reviewed', async ({ page }) => {
	// A session read on its own (plan 0.13.3 E3): what it did, the report under it, beside the document it is about; and the link working, a finding opening its mark in the other pane.
	await shot(page, 'session-did', '/master/main?beside=' + encodeURIComponent('/session/s-2026-09-16-0001?view=did'));
	await shot(page, 'session-discussion', '/session/s-2026-09-16-0001');
	await page.goto('/master/main?beside=' + encodeURIComponent('/session/s-2026-09-16-0001?view=did'));
	await page.waitForSelector('[data-pane="0"] .fragment [data-annotation]');
	await page.locator('[data-pane="0"] > .body').evaluate((el) => (el.scrollTop = el.scrollHeight));
	await page.locator('[data-pane="1"] [data-annotation-id]').first().click();
	await page.waitForTimeout(900);
	await page.screenshot({ path: `${OUT}/session-linked.png` });
});

test('a node read three ways', async ({ page }) => {
	// Plan 0.11 Parts D, E and F: what a result rests on, what it says as written, and what an agent proposed for it.
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'floating' })));

	// what it rests on stands in its context, beside it (plan 0.13.3 phase 4)
	await page.goto('/node/sy-0003?beside=' + encodeURIComponent('/context/sy-0003'));
	await page.waitForSelector('[data-testid="closure-open"]');
	await page.getByTestId('closure-open').locator('> summary').click();
	await page.getByTestId('closure-depth-2').click();
	await page.waitForTimeout(900);
	await page.screenshot({ path: `${OUT}/closure-stack.png` });

	await page.goto('/node/sy-0003');
	await page.waitForSelector('[data-pane] .fragment');
	await page.getByTestId('source-toggle').first().click();
	await page.waitForTimeout(400);
	await page.screenshot({ path: `${OUT}/verbatim.png` });

	await page.goto('/node/sy-0004');
	await page.getByTestId('toggle-annotations').click();
	await page.waitForSelector('[data-testid="payload"]');
	await page.waitForTimeout(700);
	await page.screenshot({ path: `${OUT}/payload.png` });

	await page.goto('/session/s-2026-09-16-0001?view=did');
	await page.waitForSelector('[data-testid="notation"]');
	await page.getByTestId('notation').locator('summary').click();
	await page.waitForTimeout(800);
	await page.screenshot({ path: `${OUT}/notation.png` });
});

test('the graph coloured by taxon', async ({ page }) => {
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'floating' })));
	await page.goto('/graph');
	await page.waitForSelector('main h1');
	await page.waitForTimeout(1600); // the force simulation settling
	await page.screenshot({ path: `${OUT}/graph-taxa.png` });
});

test('the same document, set two ways', async ({ page }) => {
	for (const format of ['paper', 'blog'] as const) {
		await page.goto('/');
		await page.evaluate(
			(f) => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', format: f, comments: 'floating' })),
			format
		);
		await page.goto('/master/main');
		await page.waitForSelector('main h1');
		await page.waitForTimeout(900);
		await page.screenshot({ path: `${OUT}/format-${format}.png` });
	}
});

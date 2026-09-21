// Screenshots for the workspace's feature reports (records/), as distinct from the book's reference figures in shots.spec.ts. Run with `npm run shots:report`; the images land in records/images/ and are referenced by the reports there.
import { test, type Page } from '@playwright/test';

const OUT = '../records/images';

async function settle(page: Page) {
	await page.waitForSelector('main h1', { timeout: 15000 });
	await page.waitForTimeout(700); // MathJax and the force simulation
}

async function shot(page: Page, name: string, path: string, opts: { shell?: 'a' | 'c'; theme?: 'light' | 'dark' } = {}) {
	await page.goto('/');
	await page.evaluate(
		([shell, theme]) => localStorage.setItem('arras.prefs', JSON.stringify({ shell, face: 'serif', size: 'm', width: 'mid', theme, comments: 'margin' })),
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
	await shot(page, 'capability-full-rail', '/', { shell: 'a' });
	await shot(page, 'node-page', '/node/sy-0003');
	await shot(page, 'review-ledger', '/review');
});

test('a run reviewed', async ({ page }) => {
	// The centre of plan 0.11: the document on the left, the report on the right, linked both ways.
	await shot(page, 'split-view', '/thread/s-2026-09-16-0001');
	await page.getByTestId('tab-journal').click();
	await page.waitForTimeout(400);
	await page.screenshot({ path: `${OUT}/split-view-journal.png` });
	await page.getByTestId('tab-report').click();
	await page.waitForTimeout(300);
	// and the link working: a finding clicked, the document scrolled to its mark
	await page.locator('.pane.left').evaluate((el) => (el.scrollTop = el.scrollHeight));
	await page.locator('.pane.right [data-annotation-id]').first().click();
	await page.waitForTimeout(900);
	await page.screenshot({ path: `${OUT}/split-view-linked.png` });
});

test('a node read three ways', async ({ page }) => {
	// Plan 0.11 Parts D, E and F: what a result rests on, what it says as written, and what an agent proposed for it.
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'margin' })));

	await page.goto('/node/sy-0003');
	await page.waitForSelector('main h1');
	await page.getByTestId('closure-open').locator('> summary').click();
	await page.getByTestId('closure-depth-2').click();
	await page.waitForTimeout(900);
	await page.screenshot({ path: `${OUT}/closure-stack.png` });

	await page.goto('/node/sy-0003');
	await page.waitForSelector('main h1');
	await page.getByTestId('source-toggle').first().click();
	await page.waitForTimeout(400);
	await page.screenshot({ path: `${OUT}/verbatim.png` });

	await page.goto('/node/sy-0004');
	await page.waitForSelector('[data-testid="payload"]');
	await page.waitForTimeout(700);
	await page.screenshot({ path: `${OUT}/payload.png` });

	await page.goto('/thread/s-2026-09-16-0001');
	await page.waitForSelector('[data-testid="notation"]');
	await page.getByTestId('notation').locator('summary').click();
	await page.waitForTimeout(800);
	await page.screenshot({ path: `${OUT}/notation.png` });
});

test('the graph coloured by taxon', async ({ page }) => {
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'margin' })));
	await page.goto('/graph');
	await page.waitForSelector('main h1');
	await page.waitForTimeout(1600); // the force simulation settling
	await page.screenshot({ path: `${OUT}/graph-taxa.png` });
});

test('the same document, set two ways', async ({ page }) => {
	for (const format of ['paper', 'blog'] as const) {
		await page.goto('/');
		await page.evaluate(
			(f) => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', format: f, comments: 'margin' })),
			format
		);
		await page.goto('/master/main');
		await page.waitForSelector('main h1');
		await page.waitForTimeout(900);
		await page.screenshot({ path: `${OUT}/format-${format}.png` });
	}
});

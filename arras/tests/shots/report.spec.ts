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

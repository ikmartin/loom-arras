// The viewer's reference figures: arras photographed rendering the vendored fixture, so the design shows what exists rather than what was drawn.
// Run with `npm run shots`; the images are committed under docs/design/figures/, or written to `ARRAS_SHOTS_OUT` when it is set.
import { test, type Page } from '@playwright/test';
import { outDir, settle, still } from './settle';

const OUT = outDir('../docs/design/figures');

async function shot(page: Page, name: string, path: string, opts: { theme?: 'light' | 'dark' } = {}) {
	await page.goto('/');
	await page.evaluate((theme) => localStorage.setItem('arras.prefs', JSON.stringify({ face: 'serif', size: 'm', width: 'mid', theme, comments: 'floating' })), opts.theme ?? 'light');
	await page.goto(path);
	await settle(page);
	await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
}

test.use({ viewport: { width: 1440, height: 900 } });

test('the reference figures', async ({ page }) => {
	await shot(page, 'page-home', '/');
	await shot(page, 'page-read-master', '/master/main');
	await shot(page, 'page-node', '/node/sy-0003');
	await shot(page, 'page-review', '/review');
	await shot(page, 'page-problems', '/review/problems');

	await page.goto('/graph');
	await settle(page);
	await page.screenshot({ path: `${OUT}/page-graph-dots.png` });
	for (const drawing of ['box', 'sections', 'reading']) {
		// Sections and Reading Order draw one document, so the scope is the default document from there on
		if (drawing === 'sections') await page.getByLabel('Scope', { exact: true }).selectOption('drafting/main.tex');
		await page.getByTestId(`layout-${drawing}`).click();
		await still(page);
		await page.screenshot({ path: `${OUT}/page-graph-${drawing}.png` });
	}

	await shot(page, 'page-node-dark', '/node/sy-0003', { theme: 'dark' });
});

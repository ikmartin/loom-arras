// The reference figures of book 15.9: the viewer photographed rendering the vendored fixture, so the chapter shows what exists rather than what was drawn during design.
// Run with `npm run shots`; the images are committed and supersede the hand-drawn SVGs.
import { test, type Page } from '@playwright/test';

const OUT = '../docs/book/figures';

async function settle(page: Page) {
	await page.waitForSelector('main h1, [data-pane] > .body > *', { timeout: 15000 });
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

test('the reference figures', async ({ page }) => {
	await shot(page, 'page-home', '/');
	await shot(page, 'page-read-master', '/master/main');
	await shot(page, 'page-node', '/node/sy-0003');
	await shot(page, 'page-review', '/review');
	await shot(page, 'page-problems', '/problems');

	await page.goto('/graph');
	await settle(page);
	await page.screenshot({ path: `${OUT}/page-graph-dots.png` });
	for (const drawing of ['box', 'sections', 'reading']) {
		await page.getByTestId(`layout-${drawing}`).click();
		await page.waitForTimeout(900);
		await page.screenshot({ path: `${OUT}/page-graph-${drawing}.png` });
	}

	await shot(page, 'shell-a-rail-sections', '/master/main', { shell: 'a' });
	await shot(page, 'shell-c-icon-strip', '/master/main', { shell: 'c' });
	await shot(page, 'page-node-dark', '/node/sy-0003', { theme: 'dark' });
});

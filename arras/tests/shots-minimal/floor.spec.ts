// The app photographed against the interface floor: a manifest written by nobody's publisher, with no documents, no review ledger, no bibliography and no discussions. Paired with tests/shots/report.spec.ts, these images are what plan 0.11 Part I (R2b) actually changed.
import { expect, test, type Page } from '@playwright/test';

const OUT = '../records/images';

async function settle(page: Page) {
	await page.waitForSelector('main h1', { timeout: 15000 });
	await page.waitForTimeout(400);
}

async function shot(page: Page, name: string, path: string, shell: 'a' | 'c' = 'c') {
	await page.goto('/');
	await page.evaluate(
		(s) => localStorage.setItem('arras.prefs', JSON.stringify({ shell: s, face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'margin' })),
		shell
	);
	await page.goto(path);
	await settle(page);
	await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
}

test.use({ viewport: { width: 1440, height: 900 } });

test('a corpus that has none of it', async ({ page }) => {
	await shot(page, 'capability-floor-home', '/');
	await shot(page, 'capability-floor-rail', '/', 'a');
	// The claim the images are evidence for: no read view, no review, no bibliography, no discussions.
	await page.goto('/');
	await settle(page);
	const nav = page.locator('nav');
	for (const gone of ['read', 'review', 'references', 'threads']) {
		await expect(nav.getByRole('link', { name: gone, exact: true })).toHaveCount(0);
	}
	for (const kept of ['home', 'graph', 'problems']) {
		await expect(nav.getByRole('link', { name: kept, exact: true }).first()).toBeVisible();
	}
});

// The app photographed against the interface floor: a manifest written by nobody's publisher, with no documents, no review ledger, no bibliography and no discussions. Paired with tests/shots/report.spec.ts, which photographs a corpus that has all of them. The images land in docs/reports/images/, or in `ARRAS_SHOTS_OUT` when it is set.
import { expect, test, type Page } from '@playwright/test';
import { outDir, settle } from '../shots/settle';

const OUT = outDir('../docs/reports/images');

async function shot(page: Page, name: string, path: string) {
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'margin' })));
	await page.goto(path);
	await settle(page);
	await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
}

test.use({ viewport: { width: 1440, height: 900 } });

test('a corpus that has none of it', async ({ page }) => {
	await shot(page, 'capability-floor-home', '/');
	// the claim the images are evidence for: no read view, no review, no bibliography, no discussions
	await page.goto('/');
	await settle(page);
	// it opens on how to start, with no publisher's advice to give; Review is not offered, the column holds no Library, and the development shelf no threads
	await expect(page.getByTestId('how-to-start')).toBeVisible();
	await expect(page.getByTestId('start-step')).toHaveCount(0);
	await expect(page.getByTestId('primary-review')).toHaveCount(0);
	await expect(page.getByTestId('library-toggle')).toHaveCount(0);
	await page.getByTestId('settings-toggle').click();
	await expect(page.getByTestId('settings-development').getByRole('link', { name: 'threads', exact: true })).toHaveCount(0);
	await expect(page.getByTestId('settings-development').getByRole('link', { name: 'tags', exact: true })).toBeVisible();
	// while Docs and the problems chip stand
	await expect(page.getByTestId('primary-docs')).toBeVisible();
	await expect(page.getByTestId('problems-chip')).toBeVisible();
});

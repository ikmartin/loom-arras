// The app photographed against the interface floor: a manifest written by nobody's publisher, with no documents, no review ledger, no bibliography and no discussions. Paired with tests/shots/report.spec.ts, which photographs a corpus that has all of them. The images land in records/images/, or in `ARRAS_SHOTS_OUT` when it is set.
import { expect, test, type Page } from '@playwright/test';
import { outDir, settle } from '../shots/settle';

const OUT = outDir('../records/images');

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
	// the claim the images are evidence for: no read view, no review, no bibliography, no discussions
	await page.goto('/');
	await settle(page);
	// the strip offers no read or review view, and the panel no Library
	for (const gone of ['read', 'review']) await expect(page.getByTestId(`view-${gone}`)).toHaveCount(0);
	await expect(page.getByTestId('library-toggle')).toHaveCount(0);
	await expect(page.getByRole('navigation', { name: 'Views' }).getByRole('link', { name: 'threads', exact: true })).toHaveCount(0);
	// while home, graph and problems stand
	for (const kept of ['home', 'graph']) await expect(page.getByTestId(`view-${kept}`)).toBeVisible();
	await expect(page.getByTestId('problems-glyph')).toBeVisible();
});

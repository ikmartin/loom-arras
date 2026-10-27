// The frame at each width the layout defines: the column open beside two panes; the column folded to its rail below 1200px; one pane below the workspace's two-pane width. At each, what must stay in reach does, every pane draws its toolbar, and nothing scrolls sideways.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane } from '../workspace';
import { servePapers } from '../manifest';

async function open(page: Page, width: number): Promise<void> {
	await servePapers(page);
	await page.setViewportSize({ width, height: 900 });
	await page.goto('/master/main' + beside('/library/Kre99'));
	await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
}

const fits = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

test('1440: the column open, its two views, its footer, and two panes each with its toolbar', async ({ page }) => {
	await open(page, 1440);
	await expect(page.locator('.panel.away')).toHaveCount(0);
	await expect(page.getByTestId('primary-docs')).toBeVisible();
	await expect(page.getByTestId('primary-review')).toBeVisible();
	await expect(page.getByTestId('problems-chip')).toBeInViewport();
	await expect(page.getByTestId('session-footer-name')).toBeInViewport();
	for (const i of [0, 1]) await expect(pane(page, i).getByTestId('item-controls')).toBeVisible();
	expect(await fits(page)).toBe(true);
});

test('1100: the column folded to its rail, two panes each with its toolbar', async ({ page }) => {
	await open(page, 1100);
	await expect(page.locator('.panel.away')).toHaveCount(1);
	for (const id of ['panel-fold', 'problems-chip', 'session-footer']) await expect(page.getByTestId(id)).toBeInViewport();
	await expect(page.getByTestId('primary-docs')).toHaveCount(0);
	for (const i of [0, 1]) await expect(pane(page, i).getByTestId('item-controls')).toBeVisible();
	expect(await fits(page)).toBe(true);
	// unfolded for this visit, the two views are back
	await page.getByTestId('panel-fold').click();
	await expect(page.getByTestId('primary-review')).toBeVisible();
});

test('700: one pane under one strip of both panes\' tabs, with its toolbar', async ({ page }) => {
	await open(page, 700);
	await expect(page.getByTestId('narrow-strip')).toBeVisible();
	await expect(page.getByTestId('narrow-strip').getByTestId('item-tab')).toHaveCount(2);
	await expect(page.locator('[data-pane]')).toHaveCount(1);
	await expect(page.locator('[data-pane] [data-testid="item-controls"]')).toBeVisible();
	expect(await fits(page)).toBe(true);
});

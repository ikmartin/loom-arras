import { expect, test } from '@playwright/test';

test('home page renders the fixture manifest', async ({ page }) => {
	await page.goto('/');
	await expect(page.locator('h1')).toHaveText('Widgets, gadgets, and their fixed loci');
	await expect(page.getByRole('link', { name: 'sy-0003' })).toBeVisible();
	await expect(page.getByTestId('counts')).toContainText('nodes');
});

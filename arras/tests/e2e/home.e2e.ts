import { expect, test } from '@playwright/test';

test('home page renders the hand-written manifest', async ({ page }) => {
	await page.goto('/');
	await expect(page.locator('h1')).toHaveText('Hand-written manifest');
	await expect(page.getByText('hw-0002')).toBeVisible();
});

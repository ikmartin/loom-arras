import { expect, test } from '@playwright/test';

test('home page renders the fixture manifest', async ({ page }) => {
	await page.goto('/');
	await expect(page.locator('main h1')).toHaveText('Widgets, gadgets, and their fixed loci');
	await expect(page.getByTestId('counts')).toContainText('nodes');
});

test('home page leads with the four metric cards, each opening the table of what it counts', async ({ page }) => {
	await page.goto('/');
	for (const name of ['accepted', 'stale', 'incomplete', 'errors']) {
		await expect(page.getByTestId(`card-${name}`)).toBeVisible();
	}
	await expect(page.getByTestId('card-accepted')).toHaveAttribute('href', '/review?show=accepted');
	await expect(page.getByTestId('card-stale')).toHaveAttribute('href', '/review?show=stale');
	await expect(page.getByTestId('card-errors')).toHaveAttribute('href', '/problems?severity=error');
	await page.getByTestId('card-incomplete').click();
	await expect(page).toHaveURL(/\/review\?show=incomplete$/);
	await expect(page.getByTestId('filter-show')).toHaveValue('incomplete');
});

test('home page lists the documents and what needs attention', async ({ page }) => {
	await page.goto('/');
	await expect(page.locator('main').getByRole('link', { name: 'Widgets, gadgets, and their fixed loci' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Needs attention' })).toBeVisible();
});

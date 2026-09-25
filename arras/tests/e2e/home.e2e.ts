import { expect, test } from '@playwright/test';

test('home page renders the fixture manifest', async ({ page }) => {
	await page.goto('/');
	await expect(page.locator('main h1')).toHaveText('Widgets, gadgets, and their fixed loci');
});

test('home page leads with corpus metrics without pretending they are one document table', async ({ page }) => {
	await page.goto('/');
	for (const name of ['accepted', 'stale', 'incomplete', 'errors']) {
		await expect(page.getByTestId(`card-${name}`)).toBeVisible();
	}
	await expect(page.getByTestId('card-accepted')).not.toHaveAttribute('href', /./);
	await expect(page.getByTestId('card-stale')).not.toHaveAttribute('href', /./);
	await expect(page.getByTestId('card-incomplete')).not.toHaveAttribute('href', /./);
	await expect(page.getByTestId('card-errors')).toHaveAttribute('href', '/problems?severity=error');
});

test('home page lists the documents and what needs attention', async ({ page }) => {
	await page.goto('/');
	// the landmarks carry the same title, so the assertion names the documents list rather than the page
	await expect(page.locator('main ul').first().getByRole('link', { name: 'Widgets, gadgets, and their fixed loci' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Needs attention' })).toBeVisible();
});

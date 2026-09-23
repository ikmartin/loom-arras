import { expect, test } from '@playwright/test';

test('home page renders the fixture manifest', async ({ page }) => {
	await page.goto('/');
	await expect(page.locator('main h1')).toHaveText('Widgets, gadgets, and their fixed loci');
	await expect(page.getByTestId('problems-glyph')).toHaveAttribute('title', /^problems: /);
});

test('home page leads with four metric cards which open the complete review table', async ({ page }) => {
	await page.goto('/');
	for (const name of ['accepted', 'stale', 'incomplete', 'errors']) {
		await expect(page.getByTestId(`card-${name}`)).toBeVisible();
	}
	await expect(page.getByTestId('card-accepted')).toHaveAttribute('href', '/review?show=all');
	await expect(page.getByTestId('card-stale')).toHaveAttribute('href', '/review?show=all');
	await expect(page.getByTestId('card-errors')).toHaveAttribute('href', '/problems?severity=error');
	await page.getByTestId('card-incomplete').click();
	await expect(page).toHaveURL(/\/review\?show=all$/);
	await expect(page.getByRole('navigation', { name: 'Review views' }).getByRole('link', { name: 'All' })).toHaveAttribute('aria-current', 'page');
});

test('home page lists the documents and what needs attention', async ({ page }) => {
	await page.goto('/');
	// the landmarks carry the same title, so the assertion names the documents list rather than the page
	await expect(page.locator('main ul').first().getByRole('link', { name: 'Widgets, gadgets, and their fixed loci' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Needs attention' })).toBeVisible();
});

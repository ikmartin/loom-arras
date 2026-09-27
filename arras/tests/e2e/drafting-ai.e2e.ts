// The documents an agent edits (book 4.4, 15.2; plan 0.17.1): the fixture's agent copy of main.tex, `drafting-ai/aidoc.tex`, is listed apart under its own directory, is never given a Review tab or a place among the home page's documents, and its derived nodes are left out of every whole-quilt view while a scope on the copy shows them.
import { expect, test } from '@playwright/test';

test("an agent's document is listed under its own directory, apart from the working drafts", async ({ page }) => {
	await page.goto('/');
	await expect(page.getByTestId('docs-drafts')).not.toContainText('aidoc.tex');
	await expect(page.getByTestId('docs-drafts-ai')).toContainText('aidoc.tex');
	await expect(page.getByText('drafting-ai/', { exact: true })).toBeVisible();
	// the home page's documents are the person's
	await expect(page.locator('main ul').first().getByRole('link', { name: 'Widgets, gadgets, and their fixed loci' })).toHaveCount(1);
});

test("Review gives an agent's document no tab", async ({ page }) => {
	await page.goto('/review');
	const tabs = page.getByRole('navigation', { name: 'Review views' });
	await expect(tabs.getByRole('link', { name: 'main.tex' })).toBeVisible();
	await expect(tabs.getByRole('link', { name: 'aidoc.tex' })).toHaveCount(0);
	// an address naming it falls back to the default document
	await page.goto('/review?document=drafting-ai%2Faidoc.tex');
	await expect(tabs.getByRole('link', { name: 'main.tex' })).toHaveAttribute('aria-current', 'page');
});

test("the whole quilt counts each of the person's nodes once, and a scope on the copy shows its own", async ({ page }) => {
	await page.goto('/graph');
	await expect(page.getByTestId('gnode-sy-0003')).toBeVisible();
	await expect(page.getByTestId('gnode-sy-0003-ai')).toHaveCount(0);
	// the person's documents come first in Scope, the agent's after them
	const scope = page.getByLabel('Scope', { exact: true });
	await expect(scope.locator('option').last()).toHaveText(/aidoc\.tex/);
	await scope.selectOption('drafting-ai/aidoc.tex');
	await expect(page.getByTestId('gnode-sy-0003-ai')).toBeVisible();
});

// The documents an agent edits (15.2, plan 0.17.1): the fixture's agent document, drafted from main.tex, `drafting-ai/aidoc.tex`, is listed apart under AI Drafts, is never given a Review tab, and its derived nodes are left out of every whole-quilt view while a scope on the copy shows them.
import { expect, test } from '@playwright/test';

test("an agent's document is listed under AI Drafts, apart from the working drafts, in the same label as theirs", async ({ page }) => {
	await page.goto('/');
	await expect(page.getByTestId('docs-drafts')).not.toContainText('aidoc.tex');
	await expect(page.getByTestId('docs-drafts-ai')).toContainText('aidoc.tex');
	const labels = page.getByTestId('docs-part').locator('p.rail-label');
	await expect(labels.filter({ hasText: /^AI Drafts$/ })).toBeVisible();
	const size = (text: RegExp) => labels.filter({ hasText: text }).evaluate((e) => getComputedStyle(e).fontSize);
	expect(await size(/^AI Drafts$/)).toBe(await size(/^Drafts$/));
	// `/` opens the person's default document, never the agent's
	await expect(page).toHaveURL(/\/master\/main$/);
});

test("Review gives an agent's document no tab", async ({ page }) => {
	await page.goto('/review');
	const tabs = page.getByRole('navigation', { name: 'Review views' });
	await tabs.getByRole('link', { name: 'Documents' }).click();
	await expect(page.getByLabel('Document', {exact:true})).toHaveValue('drafting/main.tex');
	await expect(tabs.getByRole('link', { name: 'aidoc.tex' })).toHaveCount(0);
	// an address naming it falls back to the default document
	await page.goto('/review?document=drafting-ai%2Faidoc.tex');
	await expect(page.getByLabel('Document', {exact:true})).toHaveValue('drafting/main.tex');
	await expect(page.getByLabel('Document', {exact:true}).locator('option[value="drafting-ai/aidoc.tex"]')).toHaveCount(0);
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

// The documents an agent edits (plan 0.17.1, 0.22.6): the fixture's agent copy of main.tex, `.loom/copies/aidoc.tex`, sits beneath main.tex in the Docs column, is never given a Review tab, and its derived nodes are left out of every whole-quilt view while a scope on the copy shows them.
import { expect, test } from '@playwright/test';

test("an agent's copy sits beneath the document it copies, and nowhere else in the column", async ({ page }) => {
	await page.goto('/');
	const drafts = page.getByTestId('docs-drafts');
	const main = drafts.locator(':scope > li').filter({ has: page.getByRole('link', { name: 'main.tex', exact: true }) });
	await expect(main.getByTestId('docs-copies')).toContainText('aidoc.tex');
	await expect(drafts.locator(':scope > li > a', { hasText: 'aidoc.tex' })).toHaveCount(0);
	await expect(page.getByTestId('docs-agent')).toHaveCount(0);
	// indented under its document, as a tree's child is
	const x = async (name: string) => (await page.getByTestId('docs-part').getByRole('link', { name, exact: true }).boundingBox())!.x;
	expect(await x('aidoc.tex')).toBeGreaterThan(await x('main.tex'));
	// `/` opens the person's default document, never the agent's
	await expect(page).toHaveURL(/\/master\/drafting\/main$/);
});

test("Review gives an agent's document no tab", async ({ page }) => {
	await page.goto('/review');
	const tabs = page.getByRole('navigation', { name: 'Review views' });
	await tabs.getByRole('link', { name: 'Documents' }).click();
	await expect(page.getByLabel('Document', {exact:true})).toHaveValue('drafting/main.tex');
	await expect(tabs.getByRole('link', { name: 'aidoc.tex' })).toHaveCount(0);
	// an address naming it falls back to the default document
	await page.goto('/review?document=.loom%2Fcopies%2Faidoc.tex');
	await expect(page.getByLabel('Document', {exact:true})).toHaveValue('drafting/main.tex');
	await expect(page.getByLabel('Document', {exact:true}).locator('option[value=".loom/copies/aidoc.tex"]')).toHaveCount(0);
});

test("the whole quilt counts each of the person's nodes once, and a scope on the copy shows its own", async ({ page }) => {
	await page.goto('/graph');
	await expect(page.getByTestId('gnode-sy-0003')).toBeVisible();
	await expect(page.getByTestId('gnode-sy-0003-ai')).toHaveCount(0);
	// the person's documents come first in Scope, the agent's after them
	const scope = page.getByLabel('Scope', { exact: true });
	await expect(scope.locator('option').last()).toHaveText(/aidoc\.tex/);
	await scope.selectOption('.loom/copies/aidoc.tex');
	await expect(page.getByTestId('gnode-sy-0003-ai')).toBeVisible();
});

// The documents an agent edits (plan 0.17.1, 0.22.6): the fixture's agent copy of main.tex, `.loom/copies/aidoc.tex`, sits beneath main.tex in the Docs column, is never given a Review tab, and its derived nodes are left out of every whole-quilt view while a scope on the copy shows them.
import { expect, test } from '@playwright/test';

test("an agent's copy sits beneath the document it copies, and nowhere else in the column", async ({ page }) => {
	await page.goto('/');
	const tree = page.getByTestId('docs-tree');
	const main = tree.getByTestId('docs-file').filter({ has: page.getByRole('link', { name: 'main.tex', exact: true }) });
	await expect(main.getByTestId('docs-copies')).toContainText('aidoc.tex');
	// the copy lives under `.loom/`, which the tree hides, so its one row is the one beneath its document
	await expect(tree.getByRole('link', { name: 'aidoc.tex' })).toHaveCount(1);
	await expect(page.getByTestId('docs-agent')).toHaveCount(0);
	// indented under its document, as a tree's child is
	const x = async (name: string) => (await page.getByTestId('docs-part').getByRole('link', { name, exact: true }).boundingBox())!.x;
	expect(await x('aidoc.tex')).toBeGreaterThan(await x('main.tex'));
	// `/` opens the quilt's front door, never the agent's document
	await expect(page).toHaveURL(/\/file\/README\.md$/);
});

test("Your text offers an agent's document no place", async ({ page }) => {
	await page.goto('/review');
	const picker = page.getByTestId('review-document');
	await expect(picker).toHaveValue('drafting/main.tex');
	await expect(picker.locator('option[value=".loom/copies/aidoc.tex"]')).toHaveCount(0);
	// an address naming it falls back to the default document
	await page.goto('/review?document=.loom%2Fcopies%2Faidoc.tex');
	await expect(picker).toHaveValue('drafting/main.tex');
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

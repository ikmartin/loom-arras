// A document's compiled PDF (plan 0.29.1): a row under its document in the tree opens it to read, and a new compile opens it again where the reader is, with nobody asking. The suite serves with `--no-compile`, so the test stands in for the compile by putting PDFs where one writes.
import { appendFileSync, copyFileSync, mkdirSync, utimesSync } from 'node:fs';
import { join } from 'node:path';
import { ARRAS, expect, test } from '../served';
import { pane } from '../workspace';

const WORKS = join(ARRAS, '../loom/tests/quilts/sources/showcase-works');
const built = (root: string) => join(root, '.loom/build/drafting/main/main.pdf');

/** Put a PDF where a compile of drafting/main.tex writes, a minute on from now so its time differs from the last. */
function compiled(root: string, pdf: string, minutes: number): void {
	mkdirSync(join(root, '.loom/build/drafting/main'), { recursive: true });
	copyFileSync(join(WORKS, pdf), built(root));
	const at = new Date(Date.now() + minutes * 60_000);
	utimesSync(built(root), at, at);
}

test.use({
	prepareQuilt: async ({}, use) => {
		await use(({ root }) => compiled(root, 'arden-cycle-spaces.pdf', 0));
	}
});

test("a document's compiled PDF opens from its row in the tree, and a new compile opens it again at the reader's page", async ({ page, served }) => {
	await page.goto('/master/drafting/main');
	const row = page.getByTestId('docs-tree').getByTestId('docs-pdf').and(page.locator('[data-document="drafting/main.tex"]'));
	await expect(row.getByRole('link')).toHaveText('PDF');
	await row.getByRole('link').click();
	await expect(page).toHaveURL(/\/pdf\/drafting\/main$/);
	const paper = pane(page, 0).getByTestId('pdf-item');
	await expect(paper.locator('canvas').first()).toBeVisible();
	await expect(page.getByTestId('page-count')).toHaveText('/ 2');
	await expect(pane(page, 0).getByTestId('item-tab').filter({ hasText: 'main.tex · PDF' })).toHaveCount(1);
	// it is read here, not marked: no markup bar's switch among its tools
	await expect(page.getByTestId('markup-toggle')).toHaveCount(0);

	const at = page.getByTestId('page-at');
	await at.fill('2');
	await at.press('Enter');
	await expect(at).toHaveValue('2');

	// a compile replaces the PDF, and the next publication carries its time
	compiled(served.root, 'arden-cycle-spaces-v2.pdf', 1);
	appendFileSync(join(served.root, 'notes/intro.md'), '\nAnother line.\n');
	await expect(page.getByTestId('page-count')).toHaveText('/ 3');
	await expect(at).toHaveValue('2');
	await expect(page).toHaveURL(/\/pdf\/drafting\/main$/);
});

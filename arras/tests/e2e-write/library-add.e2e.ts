// Adding works by hand under a running `loom serve` (plan 0.24.2): a pasted BibTeX entry, read at once and written into loom's bibliography; a dropped PDF that matches no work, offered an entry from its own pages; and a DOI, which asks for the network the synthetic quilt has off.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '../served';

const ENTRY = '@article{Ost18,\n  author = {Ostrander, D.},\n  title = {Widget categories and their duals},\n  year = {2018},\n  journal = {J. Widget Theory}\n}';

/** A real one-page PDF whose text is `lines`, which pdftotext reads back. */
function pdf(lines: string[]): Buffer {
	const stream = 'BT /F1 18 Tf 72 700 Td ' + lines.map((l, i) => `${i ? '0 -26 Td ' : ''}(${l}) Tj`).join(' ') + ' ET';
	return Buffer.from(`%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length ${stream.length}>>stream
${stream}
endstream endobj
trailer<</Root 1 0 R>>
%%EOF`);
}

test('a pasted BibTeX entry is read at once, added to loom\'s bibliography, and opens on its Info', async ({ page, served }) => {
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await page.getByTestId('add-text').fill(ENTRY);
	await expect(page.getByTestId('add-kind')).toHaveText('BibTeX entry');
	await expect(page.getByTestId('add-found')).toContainText('Widget categories and their duals');
	await expect(page.getByTestId('add-key')).toHaveText('Ost18');
	await page.getByTestId('add-fetch').uncheck();
	await page.getByTestId('add-add').click();
	await expect(page).toHaveURL(/\/library\/Ost18/);
	await expect(page.getByTestId('work-added')).toHaveText('added by hand, not cited yet');
	expect(readFileSync(join(served.root, '.loom/digests/bibliography.bib'), 'utf8')).toContain('loom-added');
});

test('a dropped PDF that matches no work is offered an entry from its own pages, and filed under it', async ({ page }) => {
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await page.getByTestId('add-file').setInputFiles({ name: 'Halberd - 2021 - Gadget towers.pdf', mimeType: 'application/pdf', buffer: pdf(['Gadget towers', 'arXiv:2102.11789']) });
	await expect(page.getByTestId('add-found')).toContainText('Gadget towers');
	await page.getByTestId('add-fetch').uncheck();
	await page.getByTestId('add-file-new').click();
	await expect(page).toHaveURL(/\/library\/Hal21/);
	await expect(page.getByTestId('status-paper')).toContainText('filed');
});

test('a DOI asks for the network before it is looked up, where the quilt has it off', async ({ page }) => {
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await page.getByTestId('add-text').fill('https://doi.org/10.5555/widget.2018.031');
	await expect(page.getByTestId('add-kind')).toHaveText('DOI');
	await page.getByTestId('add-look-up').click();
	await expect(page.getByTestId('network-ask')).toContainText('Looking this up needs the network');
	await page.getByRole('button', { name: 'Cancel' }).first().click();
	await expect(page.getByTestId('network-ask')).toHaveCount(0);
	await expect(page.getByTestId('add-add')).toBeDisabled();
});

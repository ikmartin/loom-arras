// Adding works by hand under a running `loom serve` (plan 0.24.2): a pasted BibTeX entry, read at once and written into loom's bibliography; a dropped PDF, kept whatever is known about it and with no question about the network; a work's own upload from its Info; and a DOI, which asks for the network the synthetic quilt has off.
import { existsSync, readFileSync } from 'node:fs';
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

/** A real PDF of several pages, each with its `lines`. */
function pdfOf(pages: string[][]): Buffer {
	const kids = pages.map((_, i) => `${4 + 2 * i} 0 R`).join(' ');
	const objects = pages.flatMap((lines, i) => {
		const stream = 'BT /F1 18 Tf 72 700 Td ' + lines.map((l, j) => `${j ? '0 -26 Td ' : ''}(${l}) Tj`).join(' ') + ' ET';
		return [`${4 + 2 * i} 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 3 0 R>>>>/Contents ${5 + 2 * i} 0 R>>endobj`, `${5 + 2 * i} 0 obj<</Length ${stream.length}>>stream\n${stream}\nendstream endobj`];
	});
	return Buffer.from(`%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[${kids}]/Count ${pages.length}>>endobj\n3 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n${objects.join('\n')}\ntrailer<</Root 1 0 R>>\n%%EOF`);
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

test('a dropped PDF is added from its metadata, filled in where it can be guessed, with the Add button', async ({ page }) => {
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await expect(page.getByTestId('add-add')).toBeDisabled();
	await page.getByTestId('add-file').setInputFiles({ name: 'Halberd - 2021 - Gadget towers.pdf', mimeType: 'application/pdf', buffer: pdf(['Gadget towers', 'arXiv:2102.11789']) });
	await expect(page.getByTestId('add-metadata')).toContainText('Metadata:');
	await expect(page.getByTestId('add-chosen')).toHaveText('Halberd - 2021 - Gadget towers.pdf');
	await expect(page.getByTestId('add-title')).toHaveValue('Gadget towers');
	await expect(page.getByTestId('add-author')).toHaveValue('Halberd');
	await expect(page.getByTestId('add-year')).toHaveValue('2021');
	await expect(page.getByTestId('add-work')).not.toContainText('No work in the library');
	await page.getByTestId('add-add').click();
	await expect(page).toHaveURL(/\/library\/Hal21/);
	await expect(page.getByTestId('status-paper')).toContainText('filed');
});

test('a PDF that is no published work, with no identifier, is kept and asks for nothing', async ({ page, served }) => {
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await page.getByTestId('add-file').setInputFiles({ name: 'Stats_for_Quants__1753634802.pdf', mimeType: 'application/pdf', buffer: pdf(['Statistics For Quants', 'Revision Notes']) });
	await expect(page.getByTestId('add-title')).toHaveValue('Statistics For Quants');
	await page.getByTestId('add-title').fill('Statistics for Quants: Revision Notes');
	await page.getByTestId('add-author').fill('Jha, Amit Kumar');
	await page.getByTestId('add-add').click();
	await expect(page.getByTestId('network-ask')).toHaveCount(0);
	await expect(page).toHaveURL(/\/library\/Jha/);
	await expect(page.getByTestId('status-paper')).toContainText('filed');
	await expect(page.getByTestId('work-status')).not.toContainText('Fetch it');
	const bib = readFileSync(join(served.root, '.loom/digests/bibliography.bib'), 'utf8');
	expect(bib).toContain('Statistics for Quants: Revision Notes');
	const home = /loom-file = \{(file\/[0-9a-f]+)\}/.exec(bib)![1];
	expect(existsSync(join(served.root, '.loom/digests/storage', home, 'paper.pdf'))).toBe(true);
	// it reads as a work: its text opens, and it is nothing the library's page asks about
	await page.goto(page.url().replace(/\?.*$/, ''));
	await expect(page.getByTestId('pdf-page-1').locator('canvas')).toBeAttached();
	// and what a run reads off it arrives behind the filing
	await expect.poll(() => existsSync(join(served.root, '.loom/digests/storage', home, 'pages/0001.txt'))).toBe(true);
	await page.goto('/review/library');
	await expect(page.locator('[data-testid^="ledger-Jha"]')).toBeVisible();
	await expect(page.locator('[data-testid^="problem-Jha"]')).toHaveCount(0);
});

test('a PDF the library has as a work is filed there by Add, unless the person says it is another', async ({ page, served }) => {
	test.slow(); // three acts, each a publication
	const entry = ENTRY.replace('Ost18', 'Ost20');
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await page.getByTestId('add-text').fill(entry);
	await page.getByTestId('add-fetch').uncheck();
	await page.getByTestId('add-add').click();
	await expect(page).toHaveURL(/\/library\/Ost20/);

	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	const shows = pdf(['Widget categories and their duals', 'D. Ostrander']);
	await page.getByTestId('add-file').setInputFiles({ name: 'first.pdf', mimeType: 'application/pdf', buffer: shows });
	await expect(page.getByTestId('add-matches')).toContainText('Ost20');
	await expect(page.getByTestId('add-metadata')).toHaveCount(0);
	// the person knows better: it is another work, with metadata of its own
	await page.getByTestId('add-different').click();
	await expect(page.getByTestId('add-title')).toHaveValue('Widget categories and their duals');
	await page.getByTestId('add-title').fill('Notes on widget categories');
	await page.getByTestId('add-add').click();
	await expect(page).not.toHaveURL(/\/library\/Ost20/);
	await expect(page).toHaveURL(/\/library\/[A-Z]/);
	expect(readFileSync(join(served.root, '.loom/digests/bibliography.bib'), 'utf8')).toContain('Notes on widget categories');

	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await page.getByTestId('add-file').setInputFiles({ name: 'second.pdf', mimeType: 'application/pdf', buffer: pdf(['Widget categories and their duals', 'D. Ostrander', 'a second printing']) });
	await expect(page.getByTestId('add-matches')).toContainText('Ost20');
	await page.getByTestId('add-add').click();
	await expect(page).toHaveURL(/\/library\/Ost20/);
	await expect(page.getByTestId('status-paper')).toContainText('filed');
});

test("a work's Info takes the person's own PDF, whatever its pages show", async ({ page, served }) => {
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await page.getByTestId('add-text').fill(ENTRY.replace('Ost18', 'Ost19'));
	await page.getByTestId('add-fetch').uncheck();
	await page.getByTestId('add-add').click();
	await expect(page).toHaveURL(/\/library\/Ost19/);
	await expect(page.getByTestId('run-get')).toContainText('Fetch it');
	await page.getByTestId('status-upload').click();
	await page.getByTestId('add-file').setInputFiles({ name: 'cover scan.pdf', mimeType: 'application/pdf', buffer: pdf(['Nothing of its title here']) });
	await expect(page.getByTestId('add-notice')).toContainText('on your word, though it does not show it is Ost19');
	await page.getByTestId('add-done').click();
	await expect(page.getByTestId('status-paper')).toContainText('filed');
	await expect(page.getByTestId('status-upload')).toHaveCount(0);
	expect(readFileSync(join(served.root, '.loom/digests/storage/copied.json'), 'utf8')).toContain('cover scan.pdf');
});

test('reading a filed text says how far it has got, and a clean read leaves nothing behind', async ({ page, served }) => {
	test.slow();
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	const pages = Array.from({ length: 40 }, (_, i) => [`A long set of notes, page ${i + 1}`, 'with some words on it']);
	await page.getByTestId('add-file').setInputFiles({ name: 'Long notes.pdf', mimeType: 'application/pdf', buffer: pdfOf(pages) });
	await expect(page.getByTestId('add-title')).toHaveValue('A long set of notes, page 1');
	await page.getByTestId('add-add').click();
	await expect(page).toHaveURL(/\/library\/Lon/);
	const home = /loom-file = \{(file\/[0-9a-f]+)\}/.exec(readFileSync(join(served.root, '.loom/digests/bibliography.bib'), 'utf8'))![1];
	await expect.poll(() => existsSync(join(served.root, '.loom/digests/storage', home, 'pages/0040.txt'))).toBe(true);
	await expect(page.getByTestId('status-paper')).toContainText('filed');
	await expect(page.getByTestId('job-progress')).toHaveCount(0);
});

test('the same PDF dropped again says where it already is, and there is nothing to add', async ({ page }) => {
	const buffer = pdf(['A note held once', 'with some words']);
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await page.getByTestId('add-file').setInputFiles({ name: 'held.pdf', mimeType: 'application/pdf', buffer });
	await expect(page.getByTestId('add-title')).toHaveValue('A note held once');
	await page.getByTestId('add-add').click();
	await expect(page).toHaveURL(/\/library\/Not/);
	await page.goto('/review/library');
	await page.getByTestId('review-add').click();
	await page.getByTestId('add-file').setInputFiles({ name: 'held again.pdf', mimeType: 'application/pdf', buffer });
	await expect(page.getByTestId('add-matches')).toContainText('already in the library');
	await expect(page.getByTestId('add-add')).toHaveCount(0);
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

// Plan 0.7: the PDF viewer and links into cited works (WQ-21), the work graph (WQ-05), and identity candidates (WQ-04) as the viewer shows them.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));

// the smallest PDF a browser accepts, so the viewer has something real to load
const PDF = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj
trailer<</Root 1 0 R>>
%%EOF`;

async function serve(page: Page, edit: (m: typeof manifest) => void) {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		edit(m);
		await route.fulfill({ json: m });
	});
	await page.route('**/refs/**/paper.pdf', (route) => route.fulfill({ body: PDF, contentType: 'application/pdf' }));
}

function linkInComment(m: typeof manifest, href: string) {
	m.annotations['a-2026-09-16-0001'].body_html = `<p>The hypothesis is used in <a href="${href}">Kresch, Theorem 2.1</a>.</p>`;
}

test.describe('links into cited works', () => {
	test('a link in a comment opens the fetched paper at its page, and Escape closes it', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			linkInComment(m, 'loom:arxiv:math/9810166v2#page=4');
		});
		await page.goto('/node/sy-0003');
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect(page).toHaveURL(/\/node\/sy-0003$/); // the reader stays where they were
		const viewer = page.getByTestId('pdf-viewer');
		await expect(viewer).toBeVisible();
		await expect(viewer.getByTestId('pdf-frame')).toHaveAttribute('src', '/refs/arxiv/math_9810166v2/paper.pdf#page=4');
		await expect(viewer).toContainText('Cycle groups for Artin stacks');
		await expect(viewer).toContainText('page 4');
		await page.keyboard.press('Escape');
		await expect(viewer).toHaveCount(0);
	});

	test('a paper not fetched on this machine says so and links to its source at the page', async ({ page }) => {
		await serve(page, (m) => linkInComment(m, 'loom:arxiv:math/9810166v2#page=4'));
		await page.goto('/node/sy-0003');
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect(page.getByTestId('pdf-absent')).toContainText('has not been fetched on this machine');
		await expect(page.getByTestId('pdf-external')).toHaveAttribute('href', 'https://arxiv.org/pdf/math/9810166v2#page=4');
		await expect(page.getByTestId('pdf-frame')).toHaveCount(0);
	});

	test('a link to another version of the work warns before opening the copy on file', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			m.references.Kre99.works = ['arXiv:math/9810166v2', 'doi:10.1007/s002220050351'];
			linkInComment(m, 'loom:doi:10.1007/s002220050351#page=4');
		});
		await page.goto('/node/sy-0003');
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect(page.getByTestId('pdf-absent')).toContainText('a different version');
		await expect(page.getByTestId('pdf-frame')).toHaveCount(0);
		await page.getByTestId('pdf-open-anyway').click();
		await expect(page.getByTestId('pdf-frame')).toHaveAttribute('src', '/refs/arxiv/math_9810166v2/paper.pdf#page=4');
	});

	test('a quote anchor is shown to look for', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			linkInComment(m, 'loom:arxiv:math/9810166v2#quote=Artin%20stacks');
		});
		await page.goto('/node/sy-0003');
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect(page.getByTestId('pdf-quote')).toContainText('Look for “Artin stacks”');
	});

	test('a digest result links its page into the version it was extracted from, and the viewer closes on an outside press', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.goto('/digest/Kre99');
		const link = page.getByTestId('page-link').first();
		await expect(link).toHaveText('p. 4');
		await link.click();
		await expect(page.getByTestId('pdf-frame')).toHaveAttribute('src', '/refs/arxiv/math_9810166v2/paper.pdf#page=4');
		await page.mouse.click(5, 5);
		await expect(page.getByTestId('pdf-viewer')).toHaveCount(0);
	});

	test('with no copy on file a digest page is plain text', async ({ page }) => {
		await page.goto('/digest/Kre99');
		await expect(page.locator('main')).toContainText('Theorem 2.1, p. 4');
		await expect(page.getByTestId('page-link')).toHaveCount(0);
	});
});

test.describe('the work graph', () => {
	test('each cited work is one node, and a paper opens its reference', async ({ page }) => {
		await page.goto('/graph');
		await expect(page.getByTestId('gnode-Kre99-thm-2.1')).toHaveCount(1);
		await page.getByTestId('filter-cited').selectOption('papers');
		await expect(page.getByTestId('gnode-paper:Kre99')).toBeVisible();
		await expect(page.getByTestId('gnode-paper:Har77')).toBeVisible(); // cited, never digested
		await expect(page.getByTestId('gnode-Kre99-thm-2.1')).toHaveCount(0);
		await expect(page.getByTestId('gnode-sy-0003')).toHaveCount(1); // the corpus's own results are unchanged

		await page.getByTestId('gnode-paper:Kre99').click();
		await expect(page.locator('aside')).toContainText('Cycle groups for Artin stacks');
		await expect(page.locator('aside')).toContainText('digest of 2');

		await page.getByTestId('layout-layered').click();
		await expect(page.getByTestId('gnode-paper:Kre99').locator('rect.paper-box')).toBeVisible();
		await page.getByTestId('gnode-paper:Kre99').dblclick();
		await expect(page).toHaveURL(/\/digest\/Kre99$/);
	});
});

test.describe('identity candidates', () => {
	test('a lookup proposal is shown as unconfirmed on a work that states no identifier', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Har77.candidates = [{ id: 'doi:10.1007/978-1-4757-3849-0', source: 'zbMATH Open, Crossref', confidence: 1, strength: 'strong', title: 'Algebraic geometry' }];
		});
		await page.goto('/references');
		const c = page.getByTestId('candidate-Har77');
		await expect(c).toHaveText('doi?');
		await expect(c).toHaveAttribute('href', 'https://doi.org/10.1007/978-1-4757-3849-0');
		await expect(c).toHaveAttribute('title', /unconfirmed/);
		// a work that states its identifier shows no candidate even if one were recorded
		await expect(page.getByTestId('candidate-Kre99')).toHaveCount(0);
	});
});

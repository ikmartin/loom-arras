// Plan 0.7: the PDF viewer and links into cited works (WQ-21), the work graph (WQ-05), and identity candidates (WQ-04) as the viewer shows them.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

/** The Library opens on the paper now (the digest is a derived index, never what a title click meant), so a test about the digest asks for it. */
async function digestTab(page: import('@playwright/test').Page) {
	await page.getByTestId('tab-digest').click();
}

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));
const kreschPdf = `/${manifest.references.Kre99.artifacts.dir}/paper.pdf`;

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
	await page.route('**/digests/storage/**/paper.pdf', (route) => route.fulfill({ body: PDF, contentType: 'application/pdf' }));
}

function linkInComment(m: typeof manifest, href: string) {
	m.annotations['a-2026-09-16-0001'].body_html = `<p>The hypothesis is used in <a href="${href}">Kresch, Theorem 2.1</a>.</p>`;
}

test.describe('links into cited works', () => {
	test('a link in a comment lands in the Library View at its page, and back returns', async ({ page }) => {
		// Plan 0.13 item 6: a copy on this machine opens where the page is read beside its discussion, not in a modal.
		// The link is written in the one locator syntax, and the fragment form written before it is still read.
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			linkInComment(m, 'cited:arxiv:math/9810166v2?page=4');
		});
		await page.goto('/node/sy-0003');
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect(page).toHaveURL(/\/library\/Kre99\?page=4$/);
		await expect(page.getByTestId('pdf-doc')).toBeVisible();
		await expect(page.getByTestId('pdf-viewer')).toHaveCount(0); // no modal for a copy that is here
		await expect(page.getByTestId('beside')).toBeVisible(); // and it opens split, the paper beside its discussion
		await page.goBack();
		await expect(page).toHaveURL(/\/node\/sy-0003$/);
	});

	test('a paper not fetched on this machine says so and links to its source at the page', async ({ page }) => {
		await serve(page, (m) => linkInComment(m, 'cited:arxiv:math/9810166v2#page=4'));
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
			linkInComment(m, 'cited:doi:10.1007/s002220050351#page=4');
		});
		await page.goto('/node/sy-0003');
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect(page.getByTestId('pdf-absent')).toContainText('a different version');
		await expect(page.getByTestId('pdf-frame')).toHaveCount(0);
		await page.getByTestId('pdf-open-anyway').click();
		await expect(page.getByTestId('pdf-frame')).toBeVisible();
	});

	test('a quote anchor travels in the URL, in the same keys the app uses', async ({ page }) => {
		// The place itself is lit by the publisher mapping the quote onto the page, which the reading suite covers
		// under `loom serve`; here there is no publisher, so what is checked is that the link carried it whole.
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			linkInComment(m, 'cited:arxiv:math/9810166v2#quote=Artin%20stacks');
		});
		await page.goto('/node/sy-0003');
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect(page).toHaveURL(/\/library\/Kre99\?page=1&quote=Artin\+stacks$/);
		await expect(page.getByTestId('pdf-doc')).toBeVisible();
	});

	test('a digest result links its page into the version it was extracted from, and the viewer closes on an outside press', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.goto('/library/Kre99');
		await digestTab(page);
		const link = page.getByTestId('page-link').first();
		await expect(link).toHaveText('p. 4');
		await link.click();
		await expect(page.getByTestId('pdf-frame')).toBeVisible();
		await page.mouse.click(5, 5);
		await expect(page.getByTestId('pdf-viewer')).toHaveCount(0);
	});

	test('with no copy on file a digest page is plain text', async ({ page }) => {
		await page.goto('/library/Kre99');
		await digestTab(page);
		await expect(page.locator('main')).toContainText('Theorem 2.1, p. 4');
		await expect(page.getByTestId('page-link')).toHaveCount(0);
	});
});

test.describe('the work graph', () => {
	test('shows what the corpus wrote, and none of the literature it cites', async ({ page }) => {
		// Plan 0.12 §9.2. Digesting one cited paper brings in a hundred external nodes of which two or three carry weight,
		// and even filtered to the reached ones they crowded out what the view exists to show. They have their own place.
		await page.goto('/graph');
		await expect(page.getByTestId('gnode-sy-0003')).toHaveCount(1); // the corpus's own results are unchanged
		await expect(page.getByTestId('gnode-Kre99-thm-2.1')).toHaveCount(0);
		await expect(page.locator('[data-testid^="gnode-paper:"]')).toHaveCount(0);
		await expect(page.getByTestId('filter-cited')).toHaveCount(0); // the control went with them, not just the default
	});
});

test.describe('the digest view', () => {
	test('is the seventh view, and lists the cited works with what has been read of them', async ({ page }) => {
		await page.goto('/library');
		await expect(page.getByTestId('library-works')).toBeVisible();
		await expect(page.getByTestId('library-works')).toContainText('Kre99');
		await expect(page.locator('nav [aria-current="page"], nav .current').first()).toBeVisible();
	});

	test('merges a proposal into the page it is about, with both texts beside each other', async ({ page }) => {
		await serve(page, (m) => {
			const r = m.references.Kre99;
			r.proposed = { file: 'digests/Kre99.proposed.tex', fragment: '', nodes: ['Kre99-thm-9.9'] };
			r.results = {
				...(r.results ?? {}),
				'Kre99-thm-9.9': {
					state: 'proposed',
					level: 1,
					class: 'anchored',
					page: 12,
					artifact: 'df039aa2ab80',
					origin: [{ act: 'proposed', by: 'run:2026-09-18T20-00', when: '2026-09-18T20:00:00Z' }],
					source_text: 'Every cycle group of an Artin stack is generated by integral cycles.',
					statement: 'Every cycle group of an Artin stack is generated by integral cycles.'
				}
			};
		});
		await page.goto('/library/Kre99');
		await digestTab(page);
		const box = page.getByTestId('proposal');
		await expect(box).toHaveCount(1);
		await expect(page.getByTestId('proposal-flag')).toHaveText('proposed');
		// the one non-negotiable: a surface that offers verify without showing both texts is a bug
		await expect(page.getByTestId('proposal-source')).toContainText('generated by integral cycles');
		await expect(page.getByTestId('proposal-statement')).toContainText('generated by integral cycles');
		await expect(box).toContainText('p.12');
		await expect(box).toContainText('run:2026-09-18T20-00');
	});

	test('shows the page itself, and names the words of the rendering the page does not have', async ({ page }) => {
		// the text layer keeps one "X" for a stack and its space, so a symbol is judged from the page or not at all
		// (DR-179). The page is rendered here rather than fetched as an image: nothing is drawn at build time any more.
		await page.route('**/spans/**.json', (route) =>
			route.fulfill({ json: { artifact: 'df039aa2ab80', pages: {}, quads: { 'Kre99-thm-9.9': [[72, 100, 400, 116]] } } })
		);
		await serve(page, (m) => {
			const r = m.references.Kre99;
			r.artifacts.pdf = true;
			r.spans = { path: 'spans/arxiv/math_9810166v2.json', sha256: 'abc' };
			r.proposed = { file: 'digests/Kre99.proposed.tex', fragment: '', nodes: ['Kre99-thm-9.9'] };
			r.results = {
				'Kre99-thm-9.9': {
					state: 'proposed',
					level: 1,
					class: 'anchored',
					page: 1,
					artifact: 'df039aa2ab80',
					origin: [],
					source_text: 'Every cycle group is generated by integral cycles.',
					statement: 'Every cycle group (in the sense of Deligne--Mumford) is generated by integral cycles.',
					page_text: 'Theorem 9.9. Every cycle group is generated by integral cycles.',
					not_on_page: ['sense', 'Deligne', 'Mumford']
				}
			};
		});
		await page.goto('/library/Kre99');
		await digestTab(page);
		await expect(page.getByTestId('proposal-paper')).toBeVisible();
		await expect(page.getByTestId('proposal-paper').getByTestId('pdf-page-1')).toBeVisible();
		// the quotation is marked on the page, which is what the author's eye is led to
		await expect(page.getByTestId('mark-Kre99-thm-9.9').first()).toBeVisible();
		await expect(page.getByTestId('proposal-added')).toContainText('Deligne');
		await expect(page.getByTestId('proposal-noimage')).toHaveCount(0);
		// and the page's own text, which is what the anchor check runs against, is still reachable
		await page.getByTestId('proposal-pagetext').getByRole('group').or(page.getByText("the page's text")).first().click();
		await expect(page.getByTestId('proposal-page')).toContainText('Every cycle group');
	});

	test('with no PDF on the building machine it says there is no image, rather than showing nothing', async ({ page }) => {
		await serve(page, (m) => {
			const r = m.references.Kre99;
			r.proposed = { file: 'digests/Kre99.proposed.tex', fragment: '', nodes: ['Kre99-thm-9.9'] };
			r.results = {
				'Kre99-thm-9.9': {
					state: 'proposed',
					level: 1,
					class: 'anchored',
					page: 12,
					artifact: 'df039aa2ab80',
					origin: [],
					source_text: 'Every cycle group is generated by integral cycles.',
					statement: 'Every cycle group is generated by integral cycles.',
					page_text: 'Theorem 9.9. Every cycle group is generated by integral cycles.'
				}
			};
		});
		await page.goto('/library/Kre99');
		await digestTab(page);
		await expect(page.getByTestId('proposal-noimage')).toBeVisible();
		await expect(page.getByTestId('proposal-added')).toHaveCount(0);
	});

	test('the backlog is the same view filtered, not another page', async ({ page }) => {
		await serve(page, (m) => {
			const r = m.references.Kre99;
			r.results = { 'Kre99-thm-9.9': { state: 'proposed', level: 1, class: 'anchored', page: 1, artifact: 'x', origin: [] } };
		});
		await page.goto('/library');
		await page.getByTestId('show-proposed').click();
		await expect(page).toHaveURL(/show=proposed/);
		await expect(page.getByTestId('pending-Kre99')).toHaveText('1');
		await expect(page.getByTestId('library-works').locator('tbody tr')).toHaveCount(1);
	});
});

test.describe('identity candidates', () => {
	test('a lookup proposal is shown as unconfirmed on a work that states no identifier', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Har77.candidates = [{ id: 'doi:10.1007/978-1-4757-3849-0', source: 'zbMATH Open, Crossref', confidence: 1, strength: 'strong', title: 'Algebraic geometry' }];
		});
		await page.goto('/library');
		const c = page.getByTestId('candidate-Har77');
		await expect(c).toHaveText('doi?');
		await expect(c).toHaveAttribute('href', 'https://doi.org/10.1007/978-1-4757-3849-0');
		await expect(c).toHaveAttribute('title', /unconfirmed/);
		// a work that states its identifier shows no candidate even if one were recorded
		await expect(page.getByTestId('candidate-Kre99')).toHaveCount(0);
	});
});

test.describe('what the reading study found', () => {
	test('a filed paper can be opened whether or not anything is anchored to it yet', async ({ page }) => {
		// The "Read the paper" row was gated on the pages the work's *results* sit on, so a paper that had been filed
		// and not yet extracted or proposed from — the state every newly filed paper is in — offered no way into the
		// reader at all. The Library now opens on the paper, so the guarantee is stronger: it is already open, and a
		// work with no digest has no Digest tab to hide it behind.
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			m.references.Kre99.results = {};
			m.references.Kre99.digest = null;
		});
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('pdf-doc')).toBeVisible();
		await expect(page.getByTestId('tab-digest')).toHaveCount(0);
	});

	test('a verb that needs no panel still shows why it was refused', async ({ page }) => {
		// `resolve` is one click, so it opens no panel — and the refusal rendered only inside a panel, so the publisher's
		// reason was dropped. In the study the reader clicked resolve, nothing happened, and the log took the event twice.
		await serve(page, () => {});
		// the fixture is served by `vite preview`, which has no write API; the verbs appear only where one is advertised
		await page.route('**/_api', (route) =>
			route.fulfill({ json: { write_api: 1, capabilities: ['comment', 'reply', 'resolve', 'edit', 'discard'], token: 't' } })
		);
		await page.route('**/_api/resolve', (route) =>
			route.fulfill({
				status: 400,
				contentType: 'application/json',
				body: JSON.stringify({ error: { code: 'no-such-run', message: 'no author name: add name = "Your Name" under [author]' } })
			})
		);
		await page.goto('/node/sy-0003');
		const said = page.getByTestId('verb-said').first();
		// with nothing selected the write never leaves the viewer, and the verb says which condition is unmet
		await page.getByTestId('verb-resolve').first().click();
		await expect(said).toContainText('No session selected');
		// with one selected the request reaches the publisher, and *its* refusal is what gets shown
		await page.getByTestId('session-s-2026-09-16-0001').click();
		await page.getByTestId('verb-resolve').first().click();
		await expect(said).toBeVisible();
		await expect(said).toContainText('no author name');
	});
});

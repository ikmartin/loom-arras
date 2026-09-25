// The Library: the ledger of cited works and the panel's one list of them, a work opened on its paper or its digest, a proposal read against its page, and the links into a cited work from what the corpus says about it. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { pane } from '../workspace';
import { manifest, serve, servePapers } from '../manifest';

/** A work opens on its paper; a test about its digest asks for that view. */
async function digestTab(page: Page): Promise<void> {
	await page.getByTestId('tab-digest').click();
}

/** A node lists no annotations; its first mark opens the objection whose body the tests below put a link in. */
async function openFirstMark(page: Page): Promise<void> {
	await page.locator('[data-pane] .fragment mark.annotation').first().click();
	await expect(page.locator('[data-testid="comment-expanded"] article.box').first()).toBeVisible();
}

function linkInComment(m: typeof manifest, href: string): void {
	m.annotations['a-2026-09-16-0001'].body_html = `<p>The hypothesis is used in <a href="${href}">Kresch, Theorem 2.1</a>.</p>`;
}

test.describe('the ledger', () => {
	test('the library list has one home, and the ledger lists the cited works', async ({ page }) => {
		await page.goto('/library');
		await expect(page.getByTestId('library-works')).toBeVisible();
		await expect(page.getByTestId('library-works')).toContainText('Kre99');
		// the route is a ledger, a table of what each work needs, and never a second list of works to navigate by
		await expect(page.locator('main ul a[href*="/library/"]')).toHaveCount(0);
		// the list is the panel's, and it stands beside the ledger rather than being displaced by it
		await expect(page.getByTestId('library-list')).toBeVisible();
		await expect(page.getByTestId('library-list').locator('a[href^="/library/"]').first()).toBeVisible();
	});

	test('the ledger says what needs work', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Kre99.results = { 'Kre99-x': { state: 'proposed' } };
			m.references.Man12.reading = { total: 2, open: 1 };
		});
		await page.goto('/library');
		const filters = page.getByRole('group', { name: 'which works' }).getByRole('button');
		await expect(filters).toHaveText([/^all/, /^needs work/, /^proposed/]);
		await page.getByTestId('show-needs-work').click();
		await expect(page).toHaveURL(/show=needs-work/);
		const rows = page.getByTestId('library-works').locator('tbody tr');
		await expect(rows).toHaveCount(2);
		await expect(page.getByTestId('ledger-Kre99')).toBeVisible();
		await expect(page.getByTestId('open-Man12')).toHaveText('1');
		await page.getByTestId('show-proposed').click();
		await expect(rows).toHaveCount(1);
	});

	test('the backlog is the same view filtered, not another page', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Kre99.results = { 'Kre99-thm-9.9': { state: 'proposed', level: 1, class: 'anchored', page: 1, artifact: 'x', origin: [] } };
		});
		await page.goto('/library');
		await page.getByTestId('show-proposed').click();
		await expect(page).toHaveURL(/show=proposed/);
		await expect(page.getByTestId('pending-Kre99')).toHaveText('1');
		await expect(page.getByTestId('library-works').locator('tbody tr')).toHaveCount(1);
	});

	test("a work's counts are stated once", async ({ page }) => {
		// the panel says whether a copy is filed, the one thing a click cannot be guessed to give; every count is the ledger's
		await page.goto('/master/main');
		const list = page.getByTestId('library-list');
		await expect(list.locator('.dot').first()).toBeAttached();
		const texts = await list.locator('li').allInnerTexts();
		for (const t of texts.filter((x) => !/ledger|more|nothing/.test(x))) expect(t, t).not.toMatch(/\b\d+p?\s*$/);
	});

	test("a work's page lists results with their citers, and the Library counts them", async ({ page }) => {
		await page.goto('/library/Kre99');
		await digestTab(page);
		const item = page.locator('li:has(> a:first-child[href="/node/Kre99-thm-2.1"])');
		await expect(item).toContainText('sy-000A'); // \cite[Theorem 2.1]{Kre99} resolved to this result by its locator
		await page.goto('/library');
		// the ledger counts what was read off it and how much of that the corpus leans on; who cites it is the work's own Digest view
		await expect(page.getByTestId('digest-Kre99')).toHaveText('2');
		await expect(page.getByTestId('used-Kre99')).not.toHaveText('—');
		await page.goto('/problems');
		await expect(page.getByText('names no result in the digest of Kre99').first()).toBeVisible();
	});

	test('the ledger links each work out by its identifier', async ({ page }) => {
		await page.goto('/library');
		const links = page.getByTestId('work-links-Man12').locator('a');
		await expect(links).toHaveCount(1);
		await expect(links.first()).toHaveAttribute('href', 'https://arxiv.org/abs/0805.2065v2');
		await expect(links.first()).toHaveAttribute('target', '_blank');
		// a work with only a synthetic identifier has nowhere to link
		await expect(page.getByTestId('work-links-Har77')).toHaveCount(0);
		await expect(page.locator('main table')).not.toContainText('{');
	});

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

test.describe('a work', () => {
	test('a filed paper opens on the paper, whether or not anything is anchored to it yet', async ({ page }) => {
		// a paper filed and not yet extracted from is the state every newly filed paper is in; it opens on the paper, and with no digest there is no Digest view to hide it behind
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			m.references.Kre99.results = {};
			m.references.Kre99.digest = null;
		});
		await servePapers(page);
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('pdf-doc')).toBeVisible();
		await expect(page.getByTestId('tab-digest')).toHaveCount(0);
	});

	test('a fetched PDF is offered only when the manifest says it is there', async ({ page }) => {
		await serve(page, (m) => (m.references.Man12.artifacts.pdf = true));
		await page.goto('/library/Man12');
		await page.getByTestId('tab-info').click();
		await expect(page.getByTestId('work-links-Man12').getByRole('link', { name: 'PDF' })).toHaveAttribute('href', `/${manifest.references.Man12.artifacts.dir}/paper.pdf`);
	});

	test("a work's tools stay, greyed, off the paper", async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('tool-select')).toBeEnabled();
		await page.getByTestId('tab-info').click();
		await expect(page.getByTestId('tool-select')).toBeDisabled();
		await expect(page.getByTestId('zoom-at')).toBeDisabled();
		await expect(page.getByTestId('page-at')).toBeDisabled();
		await page.getByTestId('tab-paper').click();
		await expect(page.getByTestId('zoom-at')).toBeEnabled();
	});
});

test.describe('the digest', () => {
	test('a digest result links its page into the version it was extracted from, and the viewer closes on an outside press', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await servePapers(page);
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

	test('a proposal is merged into the page it is about, with both texts beside each other', async ({ page }) => {
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
		// the heading and its count, and no paragraph explaining what a proposal is: that is the book's
		await expect(page.getByTestId('proposals').locator('> h2')).toContainText('Proposed');
		await expect(page.getByTestId('proposals')).not.toContainText('nobody has vouched');
		await expect(page.getByTestId('proposals')).not.toContainText('Read off the page');
	});

	test('a proposal shows the page itself, and names the words of the rendering the page does not have', async ({ page }) => {
		// the text layer keeps one "X" for a stack and its space, so a symbol is judged from the page or not at all (DR-179); the page is rendered here, since nothing is drawn at build time
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
		await servePapers(page);
		await page.goto('/library/Kre99');
		await digestTab(page);
		await expect(page.getByTestId('proposal-paper')).toBeVisible();
		await expect(page.getByTestId('proposal-paper').getByTestId('pdf-page-1')).toBeVisible();
		// the quotation is marked on the page, which is what the author's eye is led to
		await expect(page.getByTestId('mark-Kre99-thm-9.9').first()).toBeVisible();
		await expect(page.getByTestId('proposal-added')).toContainText('Deligne');
		await expect(page.getByTestId('proposal-noimage')).toHaveCount(0);
		// and the page's own text, which is what the anchor check runs against, is still reachable behind its disclosure
		await page.getByTestId('proposal-pagetext').locator('summary').click();
		await expect(page.getByTestId('proposal-pagetext').getByTestId('proposal-page')).toContainText('Every cycle group');
	});

	test('with no PDF on the building machine a proposal says there is no image, rather than showing nothing', async ({ page }) => {
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
});

test.describe('links into cited works', () => {
	test('a link in a comment opens the work beside at its page, and the node stays', async ({ page }) => {
		// a copy on this machine opens as the work itself, not in a modal; and a link is a connection between two texts, so it opens in the other pane and the node it was followed from is still there
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			linkInComment(m, 'cited:arxiv:math/9810166v2?page=4');
		});
		await servePapers(page);
		await page.goto('/node/sy-0003');
		await openFirstMark(page);
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect.poll(() => new URL(page.url()).searchParams.get('beside')).toBe('/library/Kre99?page=4');
		await expect(pane(page, 1).getByTestId('pdf-doc')).toBeVisible();
		await expect(page.getByTestId('pdf-viewer')).toHaveCount(0); // no modal for a copy that is here
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible(); // and the node it came from stands
		expect(new URL(page.url()).pathname).toBe('/node/sy-0003');
	});

	test('a paper not fetched on this machine says so and links to its source at the page', async ({ page }) => {
		await serve(page, (m) => linkInComment(m, 'cited:arxiv:math/9810166v2#page=4'));
		await page.goto('/node/sy-0003');
		await openFirstMark(page);
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
		await servePapers(page);
		await page.goto('/node/sy-0003');
		await openFirstMark(page);
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect(page.getByTestId('pdf-absent')).toContainText('a different version');
		await expect(page.getByTestId('pdf-frame')).toHaveCount(0);
		await page.getByTestId('pdf-open-anyway').click();
		await expect(page.getByTestId('pdf-frame')).toBeVisible();
	});

	test('a quote anchor travels in the URL, in the same keys the app uses', async ({ page }) => {
		// the place itself is lit by the publisher mapping the quote onto the page, which the reading suite covers under `loom serve`; here there is no publisher, so what is checked is that the link carried it whole
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			linkInComment(m, 'cited:arxiv:math/9810166v2#quote=Artin%20stacks');
		});
		await servePapers(page);
		await page.goto('/node/sy-0003');
		await openFirstMark(page);
		await page.getByRole('link', { name: 'Kresch, Theorem 2.1' }).click();
		await expect.poll(() => new URL(page.url()).searchParams.get('beside')).toBe('/library/Kre99?page=1&quote=Artin+stacks');
		await expect(pane(page, 1).getByTestId('pdf-doc')).toBeVisible();
	});
});

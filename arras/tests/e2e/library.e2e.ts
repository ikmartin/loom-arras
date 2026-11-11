// The Library: the ledger of cited works and the panel's one list of them, a work opened on its paper or its Info, a proposal read against its page, and the links into a cited work from what the corpus says about it. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { pane } from '../workspace';
import { manifest, serve, servePapers } from '../manifest';

/** A work opens on its paper; a test about what is known of it asks for Info. */
async function infoTab(page: Page): Promise<void> {
	await page.getByTestId('tab-info').click();
}

/** A node lists no annotations; its first mark opens the objection whose body the tests below put a link in. */
async function openFirstMark(page: Page): Promise<void> {
	await page.locator('[data-pane] .fragment mark.annotation').first().click();
	await expect(page.locator('[data-testid="comment-expanded"] article.box').first()).toBeVisible();
}

function linkInComment(m: typeof manifest, href: string): void {
	m.annotations['a-2026-09-16-ecnav2'].body_html = `<p>The hypothesis is used in <a href="${href}">Kresch, Theorem 2.1</a>.</p>`;
}

test.describe('the ledger', () => {
	test('the library list has one home, and the ledger lists the cited works', async ({ page }) => {
		await page.goto('/review/library');
		await expect(page.getByTestId('library-works')).toBeVisible();
		await expect(page.getByTestId('library-works')).toContainText('Kre99');
		// the route is a ledger, a table of what each work needs, and never a second list of works to navigate by
		await expect(page.locator('main ul a[href*="/library/"]')).toHaveCount(0);
		// the ledger is a section of Review; the list of works is on the shelf under Docs
		await expect(page.getByTestId('primary-review')).toHaveAttribute('aria-current', 'page');
		await page.goto('/master/drafting/main');
		// folded until opened: the documents are what the column is for
		await expect(page.getByTestId('library-toggle')).toHaveAttribute('aria-expanded', 'false');
		await expect(page.getByTestId('library-list')).toHaveCount(0);
		await page.getByTestId('library-toggle').click();
		await expect(page.getByTestId('library-list')).toBeVisible();
		await expect(page.getByTestId('library-list').locator('a[href^="/library/"]').first()).toBeVisible();
		await expect(page.getByTestId('manage-link')).toHaveAttribute('href', '/review/library');
		await expect(page.getByTestId('manage-link')).toHaveText('Manage the library');
		// and it says how many works want something, a way to just those
		await expect(page.getByTestId('manage-wanted')).toHaveText(/^\d+ needs? you$/);
		await expect(page.getByTestId('manage-wanted')).toHaveAttribute('href', '/review/library?show=needs-you');
	});

	test('the ledger says what needs you', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Kre99.results = { 'Kre99-x': { state: 'proposed' } };
			m.references.Man12.reading = { total: 2, open: 1 };
		});
		await page.goto('/review/library');
		const filters = page.getByRole('group', { name: 'which works' }).getByRole('button');
		await expect(filters).toHaveText([/^all/, /^needs you/, /^no paper/, /^no overview/, /^not cited/, /^proposed/, /^verified/]);
		await page.getByTestId('show-needs-you').click();
		await expect(page).toHaveURL(/show=needs-you/);
		// a proposal to judge (Kre99), a note awaiting an answer (Man12), and a problem with a fix (Har77, which names no identifier)
		const rows = page.getByTestId('library-works').locator('tbody tr');
		await expect(rows).toHaveCount(3);
		await expect(page.getByTestId('ledger-Kre99')).toBeVisible();
		await expect(page.getByTestId('open-Man12')).toHaveText('· 1 open');
		await page.getByTestId('show-proposed').click();
		await expect(rows).toHaveCount(1);
		await page.getByTestId('show-not-cited').click();
		await expect(rows).toHaveCount(1);
		await expect(page.getByTestId('ledger-Man12')).toBeVisible();
	});

	test('the backlog is the same view filtered, not another page', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Kre99.results = { 'Kre99-thm-9.9': { state: 'proposed', level: 1, class: 'anchored', page: 1, artifact: 'x', origin: [] } };
		});
		await page.goto('/review/library');
		await page.getByTestId('show-proposed').click();
		await expect(page).toHaveURL(/show=proposed/);
		await expect(page.getByTestId('pending-Kre99')).toHaveText('1 to verify');
		await expect(page.getByTestId('library-works').locator('tbody tr')).toHaveCount(1);
	});

	test('the ledger says what loom extracted, what a person verified and what an agent proposed', async ({ page }) => {
		await serve(page, (m) => {
			const base = { level: 3, class: 'mechanical', page: 4, artifact: 'x', origin: [] };
			m.references.Kre99.results = {
				'Kre99-thm-2.1': { ...base, state: 'verified', origin: [{ act: 'verified', by: 'A. Author', when: '2026-10-04T00:00:00Z' }] },
				'Kre99-x': { ...base, state: 'extracted' }
			};
			m.references.Man12.results = { 'Man12-y': { ...base, state: 'extracted' } };
		});
		await page.goto('/review/library');
		const head = page.getByTestId('library-works').locator('thead th');
		await expect(head).toContainText(['work', 'paper', 'digest', 'verified', 'overview', 'cited']);
		await expect(head.filter({ hasText: 'unvouched' })).toHaveCount(0);
		// each column says what it counts
		await expect(head.filter({ hasText: 'digest' })).toHaveAttribute('title', /its LaTeX source, or its pages/);
		await expect(page.getByTestId('verified-Kre99')).toHaveText('1');
		await expect(page.getByTestId('verified-Man12')).toHaveText('—');
		const rows = page.getByTestId('library-works').locator('tbody tr');
		await page.getByTestId('show-verified').click();
		await expect(page).toHaveURL(/show=verified/);
		await expect(rows).toHaveCount(1);
		// nothing extracted or verified waits on the author
		await page.getByTestId('show-proposed').click();
		await expect(rows).toHaveCount(0);
	});

	test("a work's versions are one row, and its Info links each to its own page", async ({ page }) => {
		await serve(page, (m) => {
			const base = { level: 3, class: 'mechanical', page: 4, artifact: 'x', origin: [] };
			m.references.Kre99A = {
				...structuredClone(m.references.Kre99),
				citekey: 'Kre99A',
				version_of: 'Kre99',
				results: { 'Kre99A-x': { ...base, state: 'extracted' } }
			};
			m.references.Kre99.versions = [{ citekey: 'Kre99A', work: 'arXiv:math/9810166v1', artifacts: { dir: 'x', pdf: false, source: false } }];
		});
		await page.goto('/review/library');
		await expect(page.getByTestId('library-works').locator('tbody tr')).toHaveCount(Object.keys(manifest.references).length);
		await expect(page.getByTestId('ledger-Kre99A')).toHaveCount(0);
		await expect(page.getByTestId('versions-Kre99')).toContainText('Kre99A');
		await page.goto('/library/Kre99');
		await page.getByTestId('tab-info').click();
		await page.getByTestId('work-details').locator('summary').click();
		const versions = page.getByTestId('work-versions');
		await expect(versions).toContainText('Kre99A (arXiv:math/9810166v1)');
		const link = versions.getByRole('link', { name: 'Kre99A' });
		await expect(link).toHaveAttribute('href', '/library/Kre99A');
		// a link inside a work opens beside it, as every link in a pane does
		await link.click();
		await expect(page).toHaveURL(/beside=%2Flibrary%2FKre99A/);
		await page.goto('/library/Kre99A');
		await page.getByTestId('tab-info').click();
		await page.getByTestId('work-details').locator('summary').click();
		await expect(page.getByTestId('work-version-of')).toContainText('Kre99');
	});

	test('the panel lists every work, however many', async ({ page }) => {
		// a cap left "46 more; narrow it" at the foot of a real library, which said neither what was hidden nor how to reach it
		await serve(page, (m) => {
			const one = m.references.Kre99;
			for (let i = 0; i < 40; i++) m.references[`Extra${i}`] = { ...structuredClone(one), citekey: `Extra${i}` };
		});
		await page.goto('/master/drafting/main');
		await page.getByTestId('library-toggle').click();
		const list = page.getByTestId('library-list');
		await expect(list.locator('a[href^="/library/"]')).toHaveCount(Object.keys(manifest.references).length + 40);
		await expect(list).not.toContainText('more');
	});

	test('the column lists works by author and title alone, sorted by author', async ({ page }) => {
		// what each holds and needs is said on its Info and in Review, not beside every row: no dot, no count
		await serve(page, (m) => {
			const one = m.references.Kre99;
			m.references = {
				Zeb: { ...structuredClone(one), citekey: 'Zeb', version_of: undefined, bib: { title: 'Zebras', author: 'Casella, George and Berger, Roger' } },
				Sta: { ...structuredClone(one), citekey: 'Sta', version_of: undefined, bib: { title: 'Statistics for quants' } },
				Abs: { ...structuredClone(one), citekey: 'Abs', version_of: undefined, bib: { title: 'Abstract nonsense', author: 'Mac Lane, Saunders' } }
			};
		});
		await page.goto('/master/drafting/main');
		await page.getByTestId('library-toggle').click();
		const list = page.getByTestId('library-list');
		await expect(list.locator('a[href^="/library/"]')).toHaveText(['Casella and Berger, Zebras', 'Mac Lane, Abstract nonsense', 'Statistics for quants']);
		await expect(list.locator('.dot')).toHaveCount(0);
		const texts = await list.locator('li').allInnerTexts();
		for (const t of texts.filter((x) => !/Manage|more|nothing/.test(x))) expect(t, t).not.toMatch(/\b\d+p?\s*$/);
	});

	test("a work's page lists results with their citers, and the Library counts them", async ({ page }) => {
		await page.goto('/library/Kre99');
		await infoTab(page);
		const card = page.locator('[data-testid="result-card"][data-result="Kre99-thm-2.1"]');
		await expect(card.getByTestId('result-used').locator('a[href="/node/sy-000A"]')).toHaveCount(1); // \cite[Theorem 2.1]{Kre99} resolved to this result by its locator
		await page.goto('/review/library');
		// the ledger counts what was read off it and the places that cite it; which results they lean on is the work's own Info
		await expect(page.getByTestId('digest-Kre99')).toHaveText('2');
		await expect(page.getByTestId('cited-Kre99')).toHaveText(/^\d+$/);
		await expect(page.getByTestId('cited-Man12')).toHaveText('not cited');
		await page.goto('/review/problems');
		await expect(page.getByTestId('problems-yours').getByText('names no result in the digest of Kre99').first()).toBeVisible();
	});

	test('the ledger links each work out by its identifier', async ({ page }) => {
		await page.goto('/review/library');
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
		await page.goto('/review/library');
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
		// a paper filed and not yet extracted from is the state every newly filed paper is in; it opens on the paper
		await serve(page, (m) => {
			m.references.Kre99.artifacts.pdf = true;
			m.references.Kre99.results = {};
			m.references.Kre99.digest = null;
		});
		await servePapers(page);
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('pdf-doc')).toBeVisible();
	});

	test("a work's Info says who stands behind its results, and when they were read off another version", async ({ page }) => {
		await serve(page, (m) => {
			const base = { level: 3, class: 'mechanical', page: 4, artifact: 'x', origin: [] };
			const version = { extracted_from: 'arXiv:math/9810166v2', cited: 'doi:10.1007/s002220050351' };
			m.references.Kre99.results = {
				'Kre99-a': { ...base, state: 'extracted', version },
				'Kre99-b': { ...base, state: 'extracted', version },
				'Kre99-c': { ...base, state: 'verified', version },
				'Kre99-d': { ...base, class: 'anchored', state: 'proposed' }
			};
		});
		await page.goto('/library/Kre99');
		await page.getByTestId('tab-info').click();
		await expect(page.getByTestId('result-counts')).toHaveText('Results: 2 extracted by loom, 1 verified by you, 1 proposed.');
		await expect(page.getByTestId('read-from')).toHaveText('Read from arXiv:math/9810166v2; the bibliography cites the published version.');
		// a work read off the version it cites says nothing about versions
		await page.goto('/library/Man12');
		await page.getByTestId('tab-info').click();
		await expect(page.getByTestId('work-info')).toBeVisible();
		await expect(page.getByTestId('read-from')).toHaveCount(0);
	});

	test("a work's overview tops its Info, a reading that says who wrote it", async ({ page }) => {
		// plan 0.21.3: an agent's reading of the paper, never the paper; written with `loom write`
		await serve(page, (m) => {
			m.references.Kre99.overview = {
				path: 'digests/storage/arxiv/math_9810166v2/overview.md',
				hash: 'sha256:0',
				body_html: '<section data-block="overview"><h2>overview</h2><p>Kresch builds cycle groups for Artin stacks; <span class="math inline">\\(A_*\\)</span> is the hard part.</p></section>',
				by: { kind: 'agent', id: 'Survey Agent' },
				when: '2026-10-28T10:00:00Z',
				edited_since: false,
				links: { broken: [], moved: [] }
			};
		});
		await page.goto('/library/Kre99');
		await page.getByTestId('tab-info').click();
		const overview = page.getByTestId('work-overview');
		await expect(overview).toContainText('Kresch builds cycle groups for Artin stacks');
		await expect(overview.getByTestId('page-meta')).toContainText('written by Survey Agent');
		await expect(overview.locator('mjx-container')).toHaveCount(1);
		// its lines stop at the line width, wherever the page around it runs to
		await page.setViewportSize({ width: 2000, height: 900 });
		const rem = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
		await expect.poll(async () => (await overview.locator('.body').boundingBox())!.width).toBeCloseTo(48 * rem, 0);
		// a work with none shows no overview
		await page.goto('/library/Man12');
		await page.getByTestId('tab-info').click();
		await expect(page.getByTestId('work-info')).toBeVisible();
		await expect(page.getByTestId('work-overview')).toHaveCount(0);
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

	test('a selection draws nothing at the line breaks of the page text', async ({ page }) => {
		// three lines of real text, so the text layer ends each with a <br>; selected, those drew a column of bars down the page's left edge
		const stream = 'BT /F1 24 Tf 72 700 Td (First line) Tj 0 -30 Td (Second line) Tj 0 -30 Td (Third line) Tj ET';
		const pdf = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length ${stream.length}>>stream
${stream}
endstream endobj
trailer<</Root 1 0 R>>
%%EOF`;
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.route('**/paper.pdf', (route) => route.fulfill({ body: pdf, contentType: 'application/pdf' }));
		await page.goto('/library/Kre99');
		const layer = page.locator('.page .text').first();
		await expect(layer.locator('br').first()).toBeAttached();
		await layer.evaluate((el) => {
			const range = document.createRange();
			range.selectNodeContents(el);
			getSelection()!.removeAllRanges();
			getSelection()!.addRange(range);
		});
		// the strip down the layer's left edge holds no text, only where the breaks stand: count its selection-blue pixels
		const box = (await layer.boundingBox())!;
		const shot = await page.screenshot({ clip: { x: box.x, y: box.y, width: 12, height: box.height } });
		const blue = await page.evaluate(async (data) => {
			const img = new Image();
			img.src = `data:image/png;base64,${data}`;
			await img.decode();
			const c = document.createElement('canvas');
			[c.width, c.height] = [img.width, img.height];
			const ctx = c.getContext('2d')!;
			ctx.drawImage(img, 0, 0);
			const px = ctx.getImageData(0, 0, c.width, c.height).data;
			let n = 0;
			for (let i = 0; i < px.length; i += 4) if (px[i + 2] - px[i] > 30) n++;
			return n;
		}, shot.toString('base64'));
		expect(blue).toBe(0);
	});
});

test('a paper that failed to load is tried again when it is next opened', async ({ page }) => {
	const pdf = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]>>endobj
trailer<</Root 1 0 R>>
%%EOF`;
	let down = true;
	await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
	await page.route('**/paper.pdf', (route) => (down ? route.abort() : route.fulfill({ body: pdf, contentType: 'application/pdf' })));
	await page.goto('/library/Kre99');
	await expect(page.getByTestId('pdf-problem')).toBeVisible();
	down = false;
	// no reload: another work in front of it, then back by its tab
	await page.locator('button, summary').filter({ hasText: /^\W*Library/ }).first().click();
	await page.locator('a[href="/library/Man12"]').first().click();
	await page.getByRole('tab', { name: 'Kre99' }).click();
	await expect(page.getByTestId('pdf-page-1').locator('canvas').first()).toBeVisible();
	await expect(page.getByTestId('pdf-problem')).toHaveCount(0);
});

test('a scanned paper draws, its JPEG 2000 and JBIG2 images decoded from what the bundle ships', async ({ page }) => {
	// one page, a black square in each half: the left in JPEG 2000, the right in JBIG2
	const jpx = Buffer.from('AAAADGpQICANCocKAAAAFGZ0eXBqcDIgAAAAAGpwMiAAAAAtanAyaAAAABZpaGRyAAAAEAAAABAAAQcHAAAAAAAPY29scgEAAAAAABEAAACUanAyY/9P/1EAKQAAAAAAEAAAABAAAAAAAAAAAAAAABAAAAAQAAAAAAAAAAAAAQcBAf9SAAwAAAABAAQEBAAB/1wAEEBASEhQSEhQSEhQSEhQ/2QAJQABQ3JlYXRlZCBieSBPcGVuSlBFRyB2ZXJzaW9uIDIuNS40/5AACgAAAAAAFgAB/5PfgAgHgICAgP/Z', 'base64');
	const jbig2 = Buffer.from('AAAAADAAAQAAABMAAAAQAAAAEAAAAAAAAAAAAAAAAAAAASYAAQAAABwAAAAQAAAAEAAAAAAAAAAAAAEmoL/////gAgAg', 'base64');
	const image = (n: number, dict: string, data: Buffer) => [Buffer.from(`${n} 0 obj<</Type/XObject/Subtype/Image/Width 16/Height 16/ColorSpace/DeviceGray${dict}/Length ${data.length}>>stream\n`), data, Buffer.from('\nendstream endobj\n')];
	const contents = 'q 100 0 0 100 0 0 cm /L Do Q q 100 0 0 100 100 0 cm /R Do Q';
	const pdf = Buffer.concat([
		Buffer.from(`%PDF-1.5
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]/Resources<</XObject<</L 5 0 R/R 6 0 R>>>>/Contents 4 0 R>>endobj
4 0 obj<</Length ${contents.length}>>stream
${contents}
endstream endobj
`),
		...image(5, '/BitsPerComponent 8/Filter/JPXDecode', jpx),
		...image(6, '/BitsPerComponent 1/Filter/JBIG2Decode', jbig2),
		Buffer.from('trailer<</Root 1 0 R>>\n%%EOF')
	]);
	await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
	await page.route('**/paper.pdf', (route) => route.fulfill({ body: pdf, contentType: 'application/pdf' }));
	await page.goto('/library/Kre99');
	const canvas = page.getByTestId('pdf-page-1').locator('canvas').first();
	await expect
		.poll(() =>
			canvas.evaluate((c: HTMLCanvasElement) => {
				const red = (x: number) => c.getContext('2d')!.getImageData(Math.round(c.width * x), Math.round(c.height / 2), 1, 1).data[0];
				return [red(0.25), red(0.75)];
			})
		)
		.toEqual([0, 0]);
});

test.describe('the digest', () => {
	test("a digest result's page links to the result on its paper, in the pane", async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await servePapers(page);
		await page.goto('/library/Kre99');
		await infoTab(page);
		const link = page.getByTestId('page-link').first();
		await expect(link).toHaveText('p. 4');
		await expect(link).toHaveAttribute('href', '/library/Kre99?page=4&result=Kre99-thm-2.1');
		await link.click();
		await expect(page.getByTestId('tab-paper')).toHaveAttribute('aria-pressed', 'true');
		await expect(page.getByTestId('pdf-viewer')).toHaveCount(0);
	});

	test('with no copy on file a digest page is plain text', async ({ page }) => {
		await page.goto('/library/Kre99');
		await infoTab(page);
		await expect(page.locator('main')).toContainText('Theorem 2.1, p. 4');
		await expect(page.getByTestId('page-link')).toHaveCount(0);
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

	test('a link to another version of the work warns before opening the copy on file, and the viewer closes on an outside press', async ({ page }) => {
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
		await page.mouse.click(5, 5);
		await expect(page.getByTestId('pdf-viewer')).toHaveCount(0);
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
		// a quote with no page names no page: the publisher looks for it across the work
		await expect.poll(() => new URL(page.url()).searchParams.get('beside')).toBe('/library/Kre99?quote=Artin+stacks');
		await expect(pane(page, 1).getByTestId('pdf-doc')).toBeVisible();
	});
});

test.describe('Review › Library acts', () => {
	test("says each work's problems in its row, finds works by search, and acts on nothing without a publisher", async ({ page }) => {
		await page.goto('/review/library');
		// the fixture holds no copy of Kre99, and Har77's entry names no identifier
		await expect(page.getByTestId('ledger-Kre99').getByTestId('problem-Kre99')).toHaveAttribute('data-code', 'no-copy');
		await expect(page.getByTestId('problem-Kre99')).toContainText('No copy of the paper can be read here.');
		await expect(page.getByTestId('problem-Har77')).toHaveAttribute('data-code', 'unidentified');
		await expect(page.getByTestId('problem-Man12')).toHaveCount(0);
		// a static viewer offers no fix, no checkbox, and a menu that only opens a work and copies its entry
		await expect(page.getByTestId('library-works').locator('[data-testid^="fix-"]')).toHaveCount(0);
		await expect(page.getByTestId('select-all')).toHaveCount(0);
		await page.getByTestId('menu-Kre99').click();
		const items = page.getByTestId('menu-items-Kre99').getByRole('menuitem');
		await expect(items).toHaveText(['Open its info', 'Copy BibTeX']);
		await page.keyboard.press('Escape');
		// the search narrows by key, title or author, and the address keeps it
		await page.getByTestId('ledger-search').fill('kresch artin');
		await expect(page).toHaveURL(/q=kresch\+artin|q=kresch%20artin/);
		await expect(page.getByTestId('library-works').locator('tbody tr')).toHaveCount(1);
		await expect(page.getByTestId('show-all')).toContainText('1');
		await page.goto('/review/library?q=manolache');
		await expect(page.getByTestId('ledger-Man12')).toBeVisible();
		await expect(page.getByTestId('library-works').locator('tbody tr')).toHaveCount(1);
	});
});

test.describe("a work's Info", () => {
	/** Kre99 with a third section of fourteen theorems, one of them verified: more than the dozen Info shows before it folds. */
	async function longDigest(page: Page): Promise<void> {
		await serve(page, (m) => {
			const ref = m.references.Kre99;
			const base = m.nodes['Kre99-thm-2.1'];
			const more = Array.from({ length: 14 }, (_, i) => `Kre99-thm-3.${i + 1}`);
			more.forEach((id, i) => (m.nodes[id] = { ...base, id, locator: `Theorem 3.${i + 1}, p.~${6 + i}` }));
			m.nodes['Kre99-sec-3'] = { ...base, id: 'Kre99-sec-3', kind: 'section', title: 'Towers', locator: undefined, children: more };
			ref.digest!.nodes = [...ref.digest!.nodes, ...more];
			ref.results = { 'Kre99-thm-3.1': { state: 'verified' } as never };
		});
	}

	test('reads in order: what it holds, its overview or who writes one, its results, where it is cited, then its entry and details folded', async ({ page }) => {
		await longDigest(page);
		await page.goto('/library/Kre99');
		const parts = ['work-status', 'overview-empty', 'work-results', 'cited-in', 'work-entry', 'work-details'];
		await expect(page.getByTestId('work-details')).toBeAttached();
		const order = await page.getByTestId('work-info').locator('[data-testid]').evaluateAll((els, want) => els.map((e) => e.getAttribute('data-testid')!).filter((id) => want.includes(id)), parts);
		expect(order).toEqual(parts);
		await expect(page.getByTestId('overview-empty')).toContainText('No overview yet. An agent writes one the next time it reads this paper through');
		// the entry and where the digest came from are folded until asked for
		await expect(page.getByTestId('work-entry')).toHaveJSProperty('open', false);
		await expect(page.getByTestId('bib-list')).toBeHidden();
		await page.getByTestId('work-entry').locator('summary').click();
		await expect(page.getByTestId('bib-list')).toBeVisible();
		await expect(page.getByTestId('bibtex-copy')).toHaveText('copy BibTeX');
		await expect(page.getByTestId('result-counts')).toBeHidden();
		await page.getByTestId('work-details').locator('summary').click();
		await expect(page.getByTestId('result-counts')).toBeVisible();
	});

	test('lists its results as cards by section, a dozen before the rest fold, narrowed by a filter', async ({ page }) => {
		await longDigest(page);
		await page.goto('/library/Kre99');
		const cards = page.getByTestId('result-card');
		await expect(cards).toHaveCount(12);
		await expect(page.getByTestId('results-section').filter({ hasText: 'Towers' })).toHaveText('3 · Towers');
		const card = page.locator('[data-testid="result-card"][data-result="Kre99-thm-3.1"]');
		await expect(card.getByTestId('result-name')).toHaveText('Theorem 3.1');
		await expect(card.getByTestId('result-state')).toHaveText('verified');
		await expect(page.getByTestId('results-more')).toHaveText('4 further results · show all 16');
		await page.getByTestId('results-more').click();
		await expect(cards).toHaveCount(16);
		// a filter offers only what narrows, with its count
		await expect(page.getByTestId('results-all')).toHaveText('all 16');
		await expect(page.getByTestId('results-proposed')).toHaveCount(0);
		await page.getByTestId('results-verified').click();
		await expect(cards).toHaveCount(1);
		await expect(cards.first()).toHaveAttribute('data-result', 'Kre99-thm-3.1');
		// what the person's text reaches: the theorem it cites, and the standing assumptions every result rests on
		await page.getByTestId('results-used').click();
		await expect(page.locator('[data-testid="result-card"][data-result="Kre99-thm-2.1"]')).toHaveCount(1);
		await expect(page.locator('[data-testid="result-card"][data-result="Kre99-thm-3.1"]')).toHaveCount(0);
		await expect(page.getByTestId('results-more')).toHaveCount(0);
	});

	test("says where the person's documents cite it, never an agent's, and what to write where nothing does", async ({ page }) => {
		await page.goto('/library/Kre99?view=info');
		const cited = page.getByTestId('cited-in');
		await expect(cited.locator('a[href="/node/sy-000A"]')).toHaveCount(1);
		await expect(cited.locator('a[href="/node/sy-000A-ai"]')).toHaveCount(0);
		await expect(cited).not.toContainText('aidoc');
		await page.goto('/library/Man12');
		await expect(page.getByTestId('not-cited')).toHaveText('Not cited yet. Cite it as \\cite{Man12}.');
		// a static viewer writes nothing, so nobody is asked for an overview
		await expect(page.getByTestId('ask-agent')).toHaveCount(0);
		await expect(page.getByTestId('status-ask')).toHaveCount(0);
	});
});

test.describe('the status line on Info', () => {
	test("says what a work holds, and offers no run where no publisher runs them", async ({ page }) => {
		await page.goto('/library/Kre99');
		const status = page.getByTestId('work-status');
		await expect(status).toBeVisible();
		await expect(page.getByTestId('status-paper')).not.toContainText('filed');
		await expect(page.getByTestId('status-digest')).toContainText('2 results · 0 verified');
		await expect(page.getByTestId('status-overview')).toContainText('Overview');
		// a static viewer starts nothing
		await expect(status.getByRole('button')).toHaveCount(0);
		await page.goto('/library/Man12');
		await expect(page.getByTestId('status-digest')).not.toContainText('results');
	});
});

test('no work is added where no publisher writes the library', async ({ page }) => {
	await page.goto('/review/library');
	await expect(page.getByTestId('review-add')).toHaveCount(0);
	await expect(page.getByTestId('library-add')).toHaveCount(0);
});

// Every kind of link to a cited result, and where it lands (V7): the paper at the result's page wherever a copy is filed and the page is known, the digest node's own page where not. One test per kind of link; a click is read off the pane it opens, a hover off its card, and the two must name one place.
import { expect, test, type Locator, type Page } from '@playwright/test';
import { beside, pane } from '../workspace';
import { PDF5, REFEREE, saying, serve, servePapers } from '../manifest';

const RESULT = 'Kre99-thm-2.1';
/** Where every link to Theorem 2.1 goes: its locator says `p.~4`. */
const AT = `/library/Kre99?page=4&result=${RESULT}`;

/** Kre99 filed as a five-page paper whose sidecar carries Theorem 2.1's lines; `edit` changes the copy of the manifest further. */
async function filed(page: Page, edit: (m: any) => void = () => {}): Promise<void> {
	await serve(page, (m) => {
		m.references.Kre99.artifacts.pdf = true;
		m.references.Kre99.spans = { path: 'spans/arxiv/math_9810166v2.json', sha256: 'abc' };
		edit(m);
	});
	await servePapers(page, PDF5);
	await page.route('**/spans/**.json', (route) => route.fulfill({ json: { artifact: 'x', pages: {}, quads: { [RESULT]: [[72, 300, 540, 316]] } } }));
}

/** The page of the paper in view in `scope`: the one whose holder spans the middle of its column; 0 before one does. */
function shown(scope: Locator): Promise<number> {
	return scope
		.getByTestId('pdf-doc')
		.locator('.column')
		.first()
		.evaluate((c) => {
			const mid = c.getBoundingClientRect().top + c.clientHeight / 2;
			for (const h of c.querySelectorAll<HTMLElement>('[data-holder]')) {
				const r = h.getBoundingClientRect();
				if (r.top <= mid && r.bottom > mid) return Number(h.dataset.holder);
			}
			return 0;
		});
}

/** A pane shows the work on its paper, at page `n`. */
async function onPage(page: Page, index: number, n: number): Promise<void> {
	await expect(pane(page, index).getByTestId('tab-paper')).toHaveAttribute('aria-pressed', 'true');
	await expect.poll(() => shown(pane(page, index))).toBe(n);
}

/** Hover a link and read the page its card shows, then let the card go. */
async function hovered(page: Page, link: Locator): Promise<number> {
	await link.hover();
	const card = page.getByTestId('link-preview');
	await expect(card.getByTestId('pdf-doc')).toBeVisible();
	let at = 0;
	await expect.poll(async () => (at = await shown(card))).toBeGreaterThan(0);
	await page.mouse.move(0, 0);
	await expect(card).toHaveCount(0);
	return at;
}

test.describe('a citation', () => {
	test('of a result opens its paper beside, at the page, as its hover shows it', async ({ page }) => {
		await filed(page);
		await page.goto('/node/sy-000A');
		const cite = pane(page, 0).locator(`span.cite[data-target="${RESULT}"] a`).first();
		await expect(cite).toHaveAttribute('href', AT);
		expect(await hovered(page, cite)).toBe(4);
		await cite.click();
		await onPage(page, 1, 4);
	});

	test('lands on the page its anchor was read from, where the result is marked', async ({ page }) => {
		// a result read off the copy filed knows its page there; the locator's is the extraction's, and the two need not agree
		await filed(page, (m) => {
			m.references.Kre99.results = { [RESULT]: { state: 'verified', level: 3, class: 'anchored', page: 3, artifact: 'x', origin: [] } };
		});
		await page.goto('/node/sy-000A');
		const cite = pane(page, 0).locator(`span.cite[data-target="${RESULT}"] a`).first();
		await expect(cite).toHaveAttribute('href', `/library/Kre99?page=3&result=${RESULT}`);
		await cite.click();
		await onPage(page, 1, 3);
		await expect(pane(page, 1).getByTestId(`mark-${RESULT}`)).toBeInViewport();
	});

	test('with no result behind it opens the page its postnote names, or the front where it names none', async ({ page }) => {
		await filed(page);
		// a digest result's own heading cites its work at the page, `[Kre99, Theorem 2.1, p. 4]`, and names no result
		await page.goto('/node/' + RESULT);
		const heading = pane(page, 0).locator('span.cite[data-postnote="Theorem 2.1, p.~4"] a').first();
		await expect(heading).toHaveAttribute('href', '/library/Kre99?page=4');
		expect(await hovered(page, heading)).toBe(4);
		await heading.click();
		await onPage(page, 1, 4);
		// `\cite[Lemma 9]{Kre99}` names no page and no result the digest holds: the work, at its front, as a bare citation opens it
		await page.goto('/node/sy-0100');
		const lemma = pane(page, 0).locator('span.cite[data-postnote="Lemma 9"] a').first();
		await expect(lemma).toHaveAttribute('href', '/library/Kre99');
		await lemma.click();
		await onPage(page, 1, 1);
	});
});

test.describe('a link to a result', () => {
	test('in a `\\ref` goes where its citation goes', async ({ page }) => {
		await filed(page);
		await page.route('**/fragments/nodes/sy-0003.html', async (route) => {
			const res = await route.fetch();
			await route.fulfill({ response: res, body: (await res.text()) + `<p>As in <a class="ref" data-target="${RESULT}" data-tex="\\ref{${RESULT}}">Theorem 2.1</a>.</p>` });
		});
		await page.goto('/node/sy-0003');
		const ref = pane(page, 0).locator(`a.ref[data-target="${RESULT}"]`);
		await expect(ref).toHaveAttribute('href', AT);
		await ref.click();
		await onPage(page, 1, 4);
	});

	test("in a node's context and its local graph opens the paper at the page", async ({ page }) => {
		await filed(page);
		await page.goto('/context/sy-000A');
		const context = pane(page, 0).getByTestId('context');
		await expect(context.locator(`a[title="${RESULT}"]`).first()).toHaveAttribute('href', AT);
		await expect(context.getByTestId('local-graph').locator(`a[data-preview-key="${RESULT}"]`)).toHaveAttribute('href', AT);
		await context.locator(`a[title="${RESULT}"]`).first().click();
		await onPage(page, 1, 4);
	});

	test('in a message, by `quilt:` or `cited:`, opens the paper at the place it names', async ({ page }) => {
		await filed(page);
		await saying(page, `<p><a href="quilt:${RESULT}">a</a> <a href="cited:arxiv:math/9810166v2?page=2">b</a> <a href="cited:arxiv:math/9810166v2?result=${RESULT}">c</a></p>`);
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		const links = pane(page, 1).getByTestId('message-1').locator('a');
		await links.nth(0).click();
		await onPage(page, 0, 4);
		// the work already open: a new place moves it there, and a result alone names its page
		await links.nth(1).click();
		await onPage(page, 0, 2);
		await links.nth(2).click();
		await onPage(page, 0, 4);
	});

	test('to a work open on Info switches it to its paper at the place', async ({ page }) => {
		await filed(page);
		await page.goto('/node/sy-000A' + beside('/library/Kre99?view=info'));
		await expect(pane(page, 1).getByTestId('work-info')).toBeVisible();
		await pane(page, 0).locator(`span.cite[data-target="${RESULT}"] a`).first().click();
		await onPage(page, 1, 4);
	});

	test('followed again after the reader scrolled away lands again', async ({ page }) => {
		await filed(page);
		await page.goto('/node/sy-000A');
		const cite = pane(page, 0).locator(`span.cite[data-target="${RESULT}"] a`).first();
		await cite.click();
		await onPage(page, 1, 4);
		await pane(page, 1).getByTestId('pdf-doc').locator('.column').first().evaluate((c) => c.scrollTo(0, 0));
		await expect.poll(() => shown(pane(page, 1))).toBe(1);
		await cite.click();
		await expect.poll(() => shown(pane(page, 1))).toBe(4);
	});

	test("with no paper to open at a page goes to the digest node's page", async ({ page }) => {
		// the digest read off another version than the bibliography cites: its pages are that version's
		await filed(page, (m) => (m.references.Kre99.version_mismatch = true));
		await page.goto('/context/sy-000A');
		await expect(pane(page, 0).getByTestId('context').locator(`a[title="${RESULT}"]`).first()).toHaveAttribute('href', `/node/${RESULT}`);
		await page.goto('/node/sy-000A');
		await expect(pane(page, 0).locator(`span.cite[data-target="${RESULT}"] a`).first()).toHaveAttribute('href', `/node/${RESULT}`);
	});
});

test.describe("a work's Info", () => {
	test('lists the results the corpus uses, each linking to its paper at its page', async ({ page }) => {
		await filed(page);
		await page.goto('/library/Kre99?view=info');
		// the result's own row, which leads with it; the setup's row names it too, as what cites the setup
		const row = pane(page, 0).getByTestId('results-used').locator(`li:has(> a:first-child[href="${AT}"])`);
		await expect(row).toHaveCount(1);
		await expect(row.locator('a').first()).toHaveAttribute('href', AT);
		await expect(row.getByTestId('page-link')).toHaveAttribute('href', AT);
		// a result whose locator names no page has no paper to open at one, so it goes to its digest node
		await expect(pane(page, 0).getByTestId('results-used').locator('a[href="/node/Kre99-setup"]')).toHaveCount(1);
		// the work is open here, so its own link moves it to its paper at the page
		await row.getByTestId('page-link').click();
		await onPage(page, 0, 4);
	});
});

test.describe('the Library in the column', () => {
	test('lists a work once, however many documents it has, and opens the one filed in the focused pane', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Kre99A = { ...structuredClone(m.references.Kre99), citekey: 'Kre99A', version_of: 'Kre99', digest: null, results: {}, artifacts: { dir: 'refs/arxiv/math_9810166v1', pdf: true, source: false } };
			m.references.Kre99.versions = [{ citekey: 'Kre99A', work: 'arXiv:math/9810166v1', artifacts: m.references.Kre99A.artifacts }];
		});
		await servePapers(page);
		await page.goto('/master/main' + beside('/node/sy-0003'));
		await page.getByTestId('library-toggle').click();
		const list = page.getByTestId('library-list');
		await expect(list.getByTestId('library-work-Kre99')).toHaveAttribute('href', '/library/Kre99A');
		await expect(list.getByTestId('library-work-Kre99A')).toHaveCount(0);
		// the filter stands however short the list, and finds a work by its version's key
		await page.getByTestId('library-filter').fill('kre99a');
		await expect(list.locator('a[data-testid^="library-work-"]')).toHaveCount(1);
		await pane(page, 0).locator('.fragment').first().click();
		await list.getByTestId('library-work-Kre99').click();
		await expect(pane(page, 0).getByRole('group', { name: 'views of Kre99A' })).toBeVisible();
		await expect(pane(page, 1).getByTestId('item-tab')).toHaveCount(1);
	});
});

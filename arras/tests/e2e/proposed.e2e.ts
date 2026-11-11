// Review › Proposed Changes, read from the fixture: one card for each thing to decide, in order and counted; a copy, a pull or a work's results opens in the page at its own address, reviewed in one pass (plan 0.25.2); an annotation carrying text to put in is decided in its card. The acts are stubbed: e2e-write drives them against a running publisher.
import { expect, test, type Page } from '@playwright/test';
import { manifest, serve } from '../manifest';

const COPY = '.loom/copies/aidoc.tex';
const TEXT = 'a-2026-09-17-rvgxnv';
const PROSE = 'a-2026-09-16-6sn46y';
const MINE = 'a-2026-09-16-xgtcve';

const ACTS = ['suggestion-apply', 'resolve'];

/** A publisher serving the acts; what it was sent, by endpoint. */
async function serving(page: Page): Promise<Record<string, Record<string, unknown>>> {
	const sent: Record<string, Record<string, unknown>> = {};
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ACTS, token: 't' } }));
	for (const e of ACTS)
		await page.route(`**/_api/${e}`, async (route) => {
			sent[e] = route.request().postDataJSON();
			await route.fulfill({ json: { ok: true, result: e === 'suggestion-apply' ? 'applied the suggestion in main.tex; a version of main.tex is kept' : `done ${sent[e].annotation}` } });
		});
	return sent;
}

const card = (page: Page, id: string) => page.locator(`[data-testid="proposed-card"][data-id="${id}"]`);
const suggestion = (page: Page, id: string) => page.locator(`[data-testid="suggestion"][data-id="${id}"]`);

test('everything to decide is a card, in order, and counted; an annotation in prose alone is not proposed here', async ({ page }) => {
	await page.goto('/review/proposed');
	await expect(page.getByTestId('section-count-proposed')).toHaveText('2');
	await expect(page.getByTestId('proposed-summary')).toHaveText('2 to decide');
	const kinds = await page.getByTestId('proposed-card').evaluateAll((els) => els.map((e) => e.getAttribute('data-kind')));
	expect(kinds).toEqual(['copy', 'suggestion']);
	await expect(card(page, TEXT)).toHaveCount(1);
	await expect(suggestion(page, PROSE)).toHaveCount(0);
	// the lead says what taking one does, and promises no patch
	await expect(page.getByTestId('proposed')).toContainText('a version of the document kept first');
	await expect(page.getByTestId('proposed')).not.toContainText('reference note');
	await expect(page.getByTestId('proposed')).not.toContainText('the patch that takes it');
});

test('each names its document and who wrote it, its quote typeset rather than its LaTeX', async ({ page }) => {
	// the person's own suggestion is in prose; given text to put in, it is proposed
	await serve(page, (m) => (m.annotations[MINE].payload = 'Every orbit has one or two points.'));
	await page.goto('/review/proposed');
	const text = suggestion(page, TEXT);
	await expect(text.getByTestId('suggestion-document')).toHaveText('in main.tex');
	await expect(text.getByTestId('suggestion-quote')).not.toContainText('\\ref');
	await expect(text.getByTestId('suggestion-writer')).toContainText('agent');
	await expect(text.getByTestId('diff')).toHaveCount(1);
	// the person's own reads "you", and one read in the talk names the talk and opens there
	const mine = suggestion(page, MINE);
	await expect(mine.getByTestId('suggestion-writer')).toContainText('you');
	await expect(mine.getByTestId('suggestion-document')).toHaveText('in talk.tex');
	await expect(mine.getByTestId('suggestion-open')).toHaveAttribute('href', /^\/master\/drafting\/talk\?note=/);
});

test('a static host offers no acts', async ({ page }) => {
	await page.goto('/review/proposed');
	for (const id of ['proposed-take', 'proposed-leave']) await expect(page.getByTestId(id)).toHaveCount(0);
	// reviewing a copy or a pull only reads, so it can still be opened
	await expect(card(page, COPY).getByTestId('proposed-open')).toBeVisible();
});

test('Take it sends the suggestion, naming no session, and says what it did in the card', async ({ page }) => {
	const sent = await serving(page);
	await page.goto('/review/proposed');
	const c = card(page, TEXT);
	await c.getByTestId('proposed-take').click();
	await expect(c.getByTestId('suggestion-said')).toHaveText('Applied the suggestion in main.tex; a version of main.tex is kept.');
	expect(sent['suggestion-apply']).toMatchObject({ annotation: TEXT });
	expect(sent['suggestion-apply']).not.toHaveProperty('session');
});

test('Leave it resolves a suggestion without applying it, and the bar offers it back', async ({ page }) => {
	const sent = await serving(page);
	await page.goto('/review/proposed');
	const c = card(page, TEXT);
	await c.getByTestId('proposed-leave').click();
	await expect(c.getByTestId('suggestion-said')).toContainText('Left the suggestion on');
	expect(sent.resolve).toMatchObject({ annotation: TEXT });
	expect(sent.resolve.applied).toBeUndefined();
	await page.getByTestId('proposed-undo').click();
	await expect(page.getByTestId('proposed-bar-said')).toContainText('Put the suggestion on');
	expect(sent.resolve).toMatchObject({ annotation: TEXT, undo: true });
});

test('a decision needs no session selected', async ({ page }) => {
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ACTS, token: 't' } }));
	await page.goto('/review/proposed');
	await expect(page.getByTestId('proposed-no-session')).toHaveCount(0);
	await expect(card(page, TEXT).getByTestId('proposed-take')).toBeEnabled();
	await expect(card(page, TEXT).getByTestId('proposed-leave')).toBeEnabled();
});

test("a copy's card says where it stands and opens its review at its own address, and comes back", async ({ page }) => {
	await page.goto('/review/proposed');
	const c = card(page, COPY);
	await expect(c.getByTestId('proposed-tally')).toContainText("that can't be taken");
	await expect(c.getByTestId('proposed-chips')).toContainText('Orbits');
	await c.getByTestId('proposed-open').click();
	await expect(page).toHaveURL(/\/review\/proposed\?copy=/);
	await expect(page.getByTestId('contribution-bar')).toContainText('From aidoc into main');
	await expect(page.getByTestId('proposed-summary')).toHaveCount(0);
	await page.getByTestId('proposed-back').click();
	await expect(page.getByTestId('proposed-summary')).toBeVisible();
	// a copy no longer waiting leaves the list
	await page.goto('/review/proposed?copy=.loom%2Fcopies%2Fgone.tex');
	await expect(page.getByTestId('proposed-summary')).toBeVisible();
});

test("suggestions on a copy are folded on its card and not counted, since they come in with it", async ({ page }) => {
	await serve(page, (m) => {
		m.annotations[TEXT].in = COPY;
		m.nodes['sy-0002'].reached_by.push(COPY);
	});
	await page.goto('/review/proposed');
	await expect(card(page, TEXT)).toHaveCount(0);
	await expect(page.getByTestId('section-count-proposed')).toHaveText('1');
	const fold = card(page, COPY).getByTestId('proposed-on-copy');
	await expect(fold).toContainText('1 suggestion on it');
	await fold.locator('summary').click();
	await expect(fold.getByTestId('suggestion-on-copy')).toBeVisible();
});

test('a pull is a card first, said to be taken whole, and its review has an address', async ({ page }) => {
	await serve(page, (m) => {
		m.contributions = [];
		m.incoming = { workspace: 'https://git.overleaf.com/0123', branch: 'master', base: 'a'.repeat(40), commit: 'b'.repeat(40), observed: '2026-09-28', files: [], changes: [{ key: 'prose:intro', name: 'Introduction', category: 'prose', kind: 'edited', local_changed: false, conflict: false, already_local: false, local: null, incoming: null, incoming_macros: '', affected: [], current: 'Old prose', proposed: 'New prose' }] };
	});
	await page.goto('/review/proposed');
	const c = card(page, 'pull');
	await expect(c).toHaveAttribute('data-kind', 'pull');
	await expect(c).toContainText('1 change, taken whole.');
	await expect(c.getByTestId('proposed-chips')).toHaveText('Introduction');
	await c.getByTestId('proposed-open').click();
	await expect(page).toHaveURL(/\/review\/proposed\?pull/);
	await expect(page.getByTestId('contribution-bar')).toContainText('A pull is taken whole.');
});

test('a work with results proposed has a card that opens the queue at it', async ({ page }) => {
	await serve(page, (m) => {
		m.references.Kre99.results = { ...(m.references.Kre99.results ?? {}), 'Kre99-thm-9.9': { state: 'proposed', level: 1, class: 'anchored', page: 1, artifact: 'df039aa2ab80', origin: [{ act: 'proposed', by: 'run:2026-09-18T20-00', when: '2026-09-18T20:00:00Z' }], source_text: 'Every cycle group is generated by integral cycles.', statement: 'Every cycle group is generated by integral cycles.', page_text: 'Theorem 9.9. Every cycle group is generated by integral cycles.' } };
	});
	await page.goto('/review/proposed');
	await expect(page.getByTestId('section-count-proposed')).toHaveText('3');
	const c = card(page, 'Kre99');
	await expect(c).toHaveAttribute('data-kind', 'results');
	await expect(c).toContainText('1 result an agent proposes');
	await c.getByTestId('proposed-open').click();
	await expect(page).toHaveURL(/\/review\/proposed\?work=Kre99#queue$/);
	await expect(page.getByTestId('proposal-queue')).toBeVisible();
});

test('an agent copy is reviewed under a pinned bar, each change named, a clash said, and nothing to press without a publisher', async ({ page }) => {
	await page.goto('/review/proposed?copy=' + encodeURIComponent(COPY));
	const bar = page.getByTestId('contribution-bar');
	await expect(bar).toHaveCSS('position', 'sticky');
	await expect(bar).toContainText('From aidoc into main');
	await expect(bar).toContainText("1 can't be taken");
	// no rail: the change takes the page's width, and the counter opens the list
	await expect(page.getByTestId('change-row')).toHaveCount(0);
	const at = page.getByTestId('change-at');
	await expect(at).toHaveText(/^1 of \d+$/);
	await at.click();
	const rows = page.getByTestId('change-row');
	// names, not keys
	await expect(rows.filter({ hasText: 'Orbits' })).toHaveCount(1);
	await expect(rows.filter({ hasText: /^sy-0002/ })).toHaveCount(0);
	const widget = page.locator('[data-testid="change-row"][data-key="sy-0001"]');
	await expect(widget).toHaveAttribute('data-state', 'clash');
	await expect(widget).toContainText("can't be taken");
	// the filter narrows the list
	await page.getByTestId('change-filter').fill('orbit');
	await expect(rows).toHaveCount(2);
	await page.getByTestId('change-filter').fill('');
	// picking one shows it and closes the list; stepping moves through the rest, the bar staying put
	await rows.filter({ hasText: 'Orbits' }).click();
	await expect(rows).toHaveCount(0);
	await expect(at).toHaveText(/^2 of /);
	await page.getByTestId('next-change').click();
	await expect(at).toHaveText(/^3 of /);
	// a static host serves no writes
	for (const id of ['take-it', 'leave-it', 'take-all', 'apply', 'accept-checked']) await expect(page.getByTestId(id)).toHaveCount(0);
});

test('a change both sides edited whose lines fall apart is offered merged, and says so', async ({ page }) => {
	await serve(page, (m) => {
		const c = m.contributions.find((x: { kind: string }) => x.kind === 'adopt');
		const orbits = c.changes.find((x: { key: string }) => x.key === 'sy-0002');
		orbits.class = 'merged';
		orbits.merged = orbits.proposed;
	});
	await page.goto('/review/proposed?copy=' + encodeURIComponent(COPY));
	await page.getByTestId('change-at').click();
	const row = page.locator('[data-testid="change-row"][data-key="sy-0002"]');
	await expect(row).toContainText('merged');
	await row.click();
	await expect(page.getByTestId('merged-note')).toContainText('You both changed it');
});

test('what taking a copy in did is said even when the copy leaves the manifest before the answer arrives', async ({ page }) => {
	let gone = false;
	let answer = () => {};
	const held = new Promise<void>((resolve) => (answer = resolve));
	await page.route('**/build/manifest.json', async (route) => {
		const m = structuredClone(manifest);
		const c = m.contributions.find((x: { kind: string }) => x.kind === 'adopt');
		c.choices = { ...c.choices, keys: ['sy-0002'] };
		if (gone) m.contributions = m.contributions.filter((x: { kind: string }) => x.kind !== 'adopt');
		await route.fulfill({ json: m });
	});
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['adopt-decision', 'adopt-preview', 'adopt-finish'], token: 't' } }));
	await page.route('**/_api/adopt-preview', (route) => route.fulfill({ json: { ok: true, result: { token: 'p', review: { token: 'r', items: [] } } } }));
	await page.route('**/_api/adopt-finish', async (route) => {
		// the publisher has written the file and republished; its answer is still on its way
		gone = true;
		await held;
		await route.fulfill({ json: { ok: true, result: { accepted: [], pending: ['sy-0002'] } } });
	});
	await page.goto('/review/proposed?copy=' + encodeURIComponent(COPY));
	await page.getByTestId('apply').click();
	await expect(page.getByTestId('proposed-summary')).toBeVisible();
	answer();
	await expect(page.getByTestId('proposed-answer')).toContainText('Took 1 change into main: 0 accepted, 1 wait in Your Changes.');
});

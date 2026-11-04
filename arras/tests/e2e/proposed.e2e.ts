// Review › Proposed Changes, read from the fixture: one card for each thing to decide, in order and counted, prose suggestions beneath; a copy, a pull or a work's results opens in the page at its own address, reviewed in one pass (plan 0.25.2); a suggestion and a citation are decided in their cards. The acts are stubbed: e2e-write drives them against a running publisher.
import { expect, test, type Page } from '@playwright/test';
import { manifest, REFEREE, serve } from '../manifest';

const COPY = '.loom/copies/aidoc.tex';
const TEXT = 'a-2026-09-17-0001';
const PROSE = 'a-2026-09-16-0003';
const MINE = 'a-2026-09-16-0007';
const CITATION = 'a-2026-09-16-0005';

const ACTS = ['suggestion-apply', 'resolve', 'discard', 'library-cite'];

/** A publisher serving the acts, writing in the referee session; what it was sent, by endpoint. */
async function serving(page: Page): Promise<Record<string, Record<string, unknown>>> {
	const sent: Record<string, Record<string, unknown>> = {};
	await page.addInitScript((id) => localStorage.setItem('arras.session-view', JSON.stringify({ selected: id, view: 'all', showClosed: false })), REFEREE);
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

test('everything to decide is a card, in order, and counted; prose suggestions are to consider, and are not', async ({ page }) => {
	await page.goto('/review/proposed');
	await expect(page.getByTestId('section-count-proposed')).toHaveText('3');
	await expect(page.getByTestId('proposed-summary')).toHaveText('3 to decide · 2 to consider');
	const kinds = await page.getByTestId('proposed-card').evaluateAll((els) => els.map((e) => e.getAttribute('data-kind')));
	expect(kinds).toEqual(['copy', 'suggestion', 'citation']);
	await expect(card(page, TEXT)).toHaveCount(1);
	await expect(card(page, CITATION)).toHaveCount(1);
	await expect(page.getByTestId('proposed-consider').getByTestId('suggestion')).toHaveCount(2);
	// the lead says what taking each does, and promises no patch
	await expect(page.getByTestId('proposed')).toContainText('a version of the document kept first');
	await expect(page.getByTestId('proposed')).toContainText('nothing is written into the text');
	await expect(page.getByTestId('proposed')).not.toContainText('the patch that takes it');
});

test('each names its document and who wrote it, its quote typeset rather than its LaTeX', async ({ page }) => {
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

test('a citation says what it claims and the work it proposes', async ({ page }) => {
	await page.goto('/review/proposed');
	const c = card(page, CITATION);
	await expect(c).toContainText('a textbook reference would do');
	await expect(c.getByTestId('citation-work')).toHaveText('Proposes citing: any standard text on group actions');
});

test('a static host offers no acts', async ({ page }) => {
	await page.goto('/review/proposed');
	for (const id of ['proposed-take', 'proposed-leave', 'suggestion-resolve', 'suggestion-dismiss']) await expect(page.getByTestId(id)).toHaveCount(0);
	// reviewing a copy or a pull only reads, so it can still be opened
	await expect(card(page, COPY).getByTestId('proposed-open')).toBeVisible();
});

test('Take it sends the suggestion in the session written in, and says what it did in the card', async ({ page }) => {
	const sent = await serving(page);
	await page.goto('/review/proposed');
	const c = card(page, TEXT);
	await c.getByTestId('proposed-take').click();
	await expect(c.getByTestId('suggestion-said')).toHaveText('Applied the suggestion in main.tex; a version of main.tex is kept.');
	expect(sent['suggestion-apply']).toMatchObject({ annotation: TEXT, session: REFEREE });
	// a prose suggestion has nothing to take
	await expect(suggestion(page, PROSE).getByTestId('proposed-take')).toHaveCount(0);
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

test('a citation is taken and left through its own decision', async ({ page }) => {
	const sent = await serving(page);
	await page.goto('/review/proposed');
	const c = card(page, CITATION);
	await c.getByTestId('proposed-take').click();
	await expect(c.getByTestId('suggestion-said')).toContainText('as a reference note');
	expect(sent['library-cite']).toMatchObject({ annotation: CITATION, decision: 'accept', session: REFEREE });
	await c.getByTestId('proposed-leave').click();
	await expect(c.getByTestId('suggestion-said')).toContainText('Left the citation on');
	expect(sent['library-cite']).toMatchObject({ annotation: CITATION, decision: 'reject' });
});

test('Resolve and Dismiss answer in the row; Dismiss asks why first, optionally', async ({ page }) => {
	const sent = await serving(page);
	await page.goto('/review/proposed');
	const prose = suggestion(page, PROSE);
	await prose.getByTestId('suggestion-resolve').click();
	await expect(prose.getByTestId('suggestion-said')).toContainText('Resolved the suggestion on');
	expect(sent.resolve).toMatchObject({ annotation: PROSE });
	await prose.getByTestId('suggestion-dismiss').click();
	expect(sent.discard).toBeUndefined();
	await prose.getByTestId('suggestion-reason').fill('Already said in the introduction.');
	await prose.getByTestId('suggestion-dismiss-go').click();
	await expect(prose.getByTestId('suggestion-said')).toContainText('Dismissed the suggestion on');
	expect(sent.discard).toMatchObject({ annotation: PROSE, reason: 'Already said in the introduction.' });
});

test('without a session nothing can be decided, and the page says so before anything is pressed', async ({ page }) => {
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ACTS, token: 't' } }));
	await page.goto('/review/proposed');
	await expect(page.getByTestId('proposed-no-session')).toBeVisible();
	await expect(card(page, TEXT).getByTestId('proposed-take')).toBeDisabled();
	await expect(card(page, CITATION).getByTestId('proposed-leave')).toBeDisabled();
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
	await expect(page.getByTestId('section-count-proposed')).toHaveText('2');
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
	await expect(page.getByTestId('section-count-proposed')).toHaveText('4');
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
	await expect(page.getByTestId('proposed-summary')).toBeVisible({ timeout: 15000 });
	answer();
	await expect(page.getByTestId('proposed-answer')).toContainText('Took 1 change into main: 0 accepted, 1 wait in Your Changes.');
});

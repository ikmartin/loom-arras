// Review › Suggestions, read from the fixture: those with text to put in first, each with its change and Apply, and the only part counted; those in prose to consider beneath; each names its document and who wrote it, its quote typeset. The acts are stubbed: what is checked is what the viewer sends and says.
import { expect, test, type Page } from '@playwright/test';
import { REFEREE } from '../manifest';

const TEXT = 'a-2026-09-17-0001';
const PROSE = 'a-2026-09-16-0003';
const MINE = 'a-2026-09-16-0007';

/** A publisher serving the three acts, writing in the referee session; what it was sent, by endpoint. */
async function serving(page: Page): Promise<Record<string, Record<string, unknown>>> {
	const sent: Record<string, Record<string, unknown>> = {};
	await page.addInitScript((id) => localStorage.setItem('arras.session-view', JSON.stringify({ selected: id, view: 'all', showClosed: false })), REFEREE);
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['suggestion-apply', 'resolve', 'discard'], token: 't' } }));
	for (const e of ['suggestion-apply', 'resolve', 'discard'])
		await page.route(`**/_api/${e}`, async (route) => {
			sent[e] = route.request().postDataJSON();
			await route.fulfill({ json: { ok: true, result: e === 'suggestion-apply' ? 'applied the suggestion in main.tex; a version of main.tex is kept' : `done ${sent[e].annotation}` } });
		});
	return sent;
}

test('those with text come first and are counted; those in prose are to consider, and are not', async ({ page }) => {
	await page.goto('/review/suggestions');
	await expect(page.getByTestId('section-count-suggestions')).toHaveText('1');
	await expect(page.getByTestId('suggestions-summary')).toHaveText('1 to apply · 2 to consider');
	const apply = page.getByTestId('suggestions-apply').getByTestId('suggestion');
	await expect(apply).toHaveCount(1);
	await expect(apply).toHaveAttribute('data-id', TEXT);
	const consider = page.getByTestId('suggestions-consider').getByTestId('suggestion');
	await expect(consider).toHaveCount(2);
	// the lead promises no patch: a prose suggestion has none
	await expect(page.getByTestId('suggestions')).not.toContainText('the patch that takes it');
});

test('each names its document and who wrote it, its quote typeset rather than its LaTeX', async ({ page }) => {
	await page.goto('/review/suggestions');
	const text = page.locator(`[data-testid="suggestion"][data-id="${TEXT}"]`);
	await expect(text.getByTestId('suggestion-document')).toHaveText('in main.tex');
	await expect(text.getByTestId('suggestion-quote')).not.toContainText('\\ref');
	await expect(text.getByTestId('suggestion-writer')).toContainText('agent');
	// the person's own reads "you", and one read in the talk names the talk and opens there
	const mine = page.locator(`[data-testid="suggestion"][data-id="${MINE}"]`);
	await expect(mine.getByTestId('suggestion-writer')).toContainText('you');
	await expect(mine.getByTestId('suggestion-document')).toHaveText('in talk.tex');
	await expect(mine.getByTestId('suggestion-open')).toHaveAttribute('href', /^\/master\/drafting\/talk\?note=/);
});

test('a static host offers no acts', async ({ page }) => {
	await page.goto('/review/suggestions');
	await expect(page.getByTestId('suggestion-apply')).toHaveCount(0);
	await expect(page.getByTestId('suggestion-dismiss')).toHaveCount(0);
});

test('Apply sends the suggestion in the session written in, and says what it did in the row', async ({ page }) => {
	const sent = await serving(page);
	await page.goto('/review/suggestions');
	const row = page.locator(`[data-testid="suggestion"][data-id="${TEXT}"]`);
	await row.getByTestId('suggestion-apply').click();
	await expect(row.getByTestId('suggestion-said')).toHaveText('Applied the suggestion in main.tex; a version of main.tex is kept.');
	expect(sent['suggestion-apply']).toMatchObject({ annotation: TEXT, session: REFEREE });
	// a prose suggestion has nothing to apply
	await expect(page.locator(`[data-testid="suggestion"][data-id="${PROSE}"]`).getByTestId('suggestion-apply')).toHaveCount(0);
});

test('Resolve and Dismiss answer in the row; Dismiss asks why first, optionally', async ({ page }) => {
	const sent = await serving(page);
	await page.goto('/review/suggestions');
	const prose = page.locator(`[data-testid="suggestion"][data-id="${PROSE}"]`);
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

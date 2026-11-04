// Review › Your Changes: one document's blocks not freshly accepted, grouped by why they wait, each accepted in its row or several at once, what loom cannot accept saying why, and Read opening the block in its document beside the panel that says why it waits. Incoming's mathematics is accepted only where it is marked as checked. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { manifest, serve } from '../manifest';

const MAIN = 'drafting/main.tex';
type Row = { key: string; cause: string; refusal: string };
const rows = manifest.unresolved as Row[];
const inMain = rows.filter((r) => manifest.nodes[manifest.keys[r.key].node].reached_by.includes(MAIN));

/** Answer as a publisher that accepts: `answer` gives the reply to each request, and `posted` collects what was sent. */
async function accepting(page: Page, answer: (keys: string[]) => Record<string, unknown>): Promise<Record<string, unknown>[]> {
	const posted: Record<string, unknown>[] = [];
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['review-accept'], token: 't' } }));
	await page.route('**/_api/review-accept', async (route) => {
		const body = route.request().postDataJSON();
		posted.push(body);
		await route.fulfill({ json: { ok: true, ...answer(body.keys as string[]) } });
	});
	return posted;
}

test("one document's blocks are grouped by why they wait, and those accepted are folded beneath", async ({ page }) => {
	await page.goto('/review');
	const group = (id: string) => page.locator(`[data-testid="review-group"][data-group="${id}"]`);
	await expect(group('changed').getByTestId('review-group-count')).toHaveText(String(inMain.filter((r) => r.cause === 'earlier-change').length));
	await expect(group('never').getByTestId('review-group-count')).toHaveText(String(inMain.filter((r) => r.cause === 'never-accepted').length));
	await expect(group('taken')).toHaveCount(0);
	await expect(group('changed')).toHaveAttribute('open');
	await expect(group('accepted')).not.toHaveAttribute('open');
	await expect(group('accepted').getByTestId('review-row')).toHaveCount(1);
	await expect(page.getByTestId('review-summary')).toContainText('reviewing as The synthetic quilt');
	// a changed block says what changed, and opens on the change
	const widget = group('changed').locator('[data-testid="review-row"][data-key="sy-0001"]');
	await expect(widget.getByTestId('review-read')).toHaveText('See change');
	await expect(widget.getByTestId('review-read')).toHaveAttribute('href', '/master/drafting/main?review=sy-0001&cause=0#sy-0001');
	await expect(group('never').getByTestId('review-read').first()).toHaveText('Read');
	// nothing here is a choice that waits for a second press
	for (const name of ['Mark OK', 'Requires attention', /Finish review/]) await expect(page.getByRole('button', { name })).toHaveCount(0);
});

test('a block loom cannot accept says why in its row, and offers no Accept', async ({ page }) => {
	await accepting(page, () => ({}));
	await page.goto('/review');
	const unclassified = page.locator('[data-testid="review-row"][data-key="sy-000B"]');
	await expect(unclassified.getByTestId('review-refusal')).toHaveText("Can't be accepted yet: its basis is not said; a % !LOOM basis: line inside it says it.");
	await expect(unclassified.getByTestId('review-accept')).toHaveCount(0);
	await expect(unclassified.getByTestId('review-pick')).toBeDisabled();
	await expect(page.locator('[data-testid="review-row"][data-key="sy-0001"]').getByTestId('review-accept')).toBeVisible();
});

test('Accept in a row records at once and says so; a selection is accepted in one press, each refusal said by its block', async ({ page }) => {
	let gone: string[] = [];
	const posted = await accepting(page, (keys) => {
		const refused = keys.includes('sy-0002') && !keys.includes('sy-0001') ? [{ key: 'sy-0002', why: 'Accept Widget first, or with it.' }] : [];
		const accepted = keys.filter((k) => !refused.some((r) => r.key === k));
		gone = [...gone, ...accepted];
		return { result: `accepted ${accepted.length} of ${keys.length}`, accepted, refused };
	});
	await serve(page, (m) => {
		m.unresolved = m.unresolved.filter((r: Row) => !gone.includes(r.key));
	});
	await page.goto('/review');
	await page.locator('[data-testid="review-row"][data-key="sy-0004"]').getByTestId('review-accept').click();
	await expect(page.getByTestId('review-bar-said')).toHaveText(/^Accepted /);
	await expect(page.locator('[data-testid="review-row"][data-key="sy-0004"]')).toHaveCount(0);
	expect(posted[0]).toEqual({ reviewer: 'The synthetic quilt', keys: ['sy-0004'] });
	// two picked; the one resting on what was not picked stays, and says why
	await page.locator('[data-testid="review-row"][data-key="sy-0002"]').getByTestId('review-pick').check();
	await page.locator('[data-testid="review-row"][data-key="sy-0005"]').getByTestId('review-pick').check();
	await expect(page.getByTestId('review-picked')).toHaveText('2 selected');
	await page.getByTestId('review-accept-picked').click();
	await expect(page.getByTestId('review-bar-said')).toContainText('Accepted ');
	await expect(page.getByTestId('review-bar-said')).toContainText('Orbits: accept Widget first, or with it.');
	expect(posted[1].keys).toEqual(['sy-0002', 'sy-0005']);
	await expect(page.getByTestId('review-picked')).toHaveText('1 selected');
});

test('Read opens the block in its document, with why it waits and the way back beside it', async ({ page }) => {
	await page.goto('/review');
	await page.locator('[data-testid="review-row"][data-key="sy-0001"]').getByTestId('review-read').click();
	await expect(page).toHaveURL(/\/master\/drafting\/main\?review=sy-0001&cause=0#sy-0001$/);
	const panel = page.getByTestId('review-panel');
	await expect(panel.getByTestId('review-panel-status')).toHaveText('Changed since you accepted it.');
	await expect(panel.getByTestId('review-comparison')).toBeVisible();
	await expect(panel.getByTestId('review-panel-back')).toHaveAttribute('href', '/review?document=drafting%2Fmain.tex#review-sy-0001');
	await page.goto('/master/drafting/main?review=sy-000B#sy-000b');
	await expect(page.getByTestId('review-panel-status')).toHaveText('Never accepted.');
	await expect(page.getByTestId('review-panel-refusal')).toContainText('its basis is not said');
});

test('a block taken in is grouped by where it came from', async ({ page }) => {
	await serve(page, (m) => {
		const r = m.unresolved.find((x: Row) => x.key === 'sy-0004');
		Object.assign(r, { cause: 'adopted', contribution: '.loom/copies/aidoc.tex', source_label: 'Taken in from the copy “aidoc”' });
	});
	await page.goto('/review');
	const taken = page.locator('[data-testid="review-group"][data-group="taken"]');
	await expect(taken.locator('summary .title')).toHaveText('Taken in from the copy “aidoc”');
	await expect(taken.getByTestId('review-row')).toHaveCount(1);
});

test('the picker offers only documents with blocks, and a link to an accepted block opens its fold', async ({ page }) => {
	await serve(page, (m) => {
		m.masters.push({ ...m.masters[1], path: 'drafting/empty.tex', default: false });
	});
	await page.goto('/review?document=drafting%2Fmain.tex#review-sy-0003');
	await expect(page.getByTestId('review-document').locator('option')).toHaveText([/^main\.tex/, /^talk\.tex/]);
	await expect(page.locator('[data-testid="review-group"][data-group="accepted"]')).toHaveAttribute('open');
	await expect(page.locator('#review-sy-0003')).toBeInViewport();
});

test('with no reviewer name nothing can be accepted, and the page says where to choose one', async ({ page }) => {
	await accepting(page, () => ({}));
	await serve(page, (m) => {
		m.reviewer = { name: '', source: '' };
	});
	await page.goto('/review');
	await expect(page.getByTestId('review-no-reviewer')).toHaveText('Choose your reviewer name in Settings to accept.');
	await expect(page.getByTestId('review-accept')).toHaveCount(0);
});

test('a document whose every block is accepted says so', async ({ page }) => {
	await serve(page, (m) => {
		m.unresolved = [];
	});
	await page.goto('/review');
	await expect(page.getByTestId('review-empty')).toHaveText('Every block of main.tex is accepted.');
});

test('prose is inspected in a pull\'s review without mathematical acceptance controls, and a pull says it is taken whole', async ({ page }) => {
	await serve(page, (m) => {
		m.contributions = [];
		m.incoming = { workspace: 'https://git.overleaf.com/0123', branch: 'master', base: 'a'.repeat(40), commit: 'b'.repeat(40), observed: '2026-09-28', files: [{ status: 'M', path: 'drafting/main.tex', diff: '-Old prose\n+New prose' }], changes: [{ key: 'prose:setup', name: 'Introduction', category: 'prose', kind: 'edited', local_changed: false, conflict: false, already_local: false, current: 'Old prose', proposed: 'New prose', affected: [] }, { key: 'sy-0001', kind: 'edited', current: 'Old definition', proposed: 'New definition', local_changed: false, conflict: false, already_local: false, affected: [] }] };
	});
	await page.goto('/review/proposed?pull');
	await expect(page.getByText('Old prose', { exact: true })).toBeVisible();
	await expect(page.getByText('New prose', { exact: true })).toBeVisible();
	await expect(page.getByTestId('contribution-bar')).toContainText('A pull is taken whole.');
	await expect(page.getByTestId('accept-checked')).toHaveCount(0);
	await page.getByRole('button', { name: 'Next change' }).click();
	await expect(page.getByText('New definition', { exact: true })).toBeVisible();
	await page.getByRole('button', { name: 'Previous change' }).click();
	await expect(page.getByText('New prose', { exact: true })).toBeVisible();
});

test('a pull\'s review accepts only explicitly chosen mathematics while incorporating the whole pull', async ({ page }) => {
	let submitted: Record<string, unknown> | null = null;
	await serve(page, (m) => {
		m.reviewer = { name: 'Luisa', source: 'local' };
		m.contributions = [];
		m.incoming = { workspace: 'https://git.overleaf.com/0123', branch: 'master', base: 'a'.repeat(40), commit: 'b'.repeat(40), observed: '2026-09-28', files: [], changes: [{ key: 'prose:intro', name: 'Introduction', category: 'prose', kind: 'edited', current: 'Old prose', proposed: 'New prose', affected: [] }, { key: 'sy-0001', name: 'Lemma', kind: 'edited', current: 'Old lemma', proposed: 'New lemma', affected: [] }] };
	});
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['sync-incorporate', 'sync-preview'], token: 'test' } }));
	const fragment = { path: 'incorporation-review/example.html', macros: [] };
	await page.route('**/build/incorporation-review/example.html', (route) => route.fulfill({ contentType: 'text/html', body: '<div class="env"><p>Inspected mathematics.</p></div>' }));
	await page.route('**/_api/sync-preview', (route) => route.fulfill({ json: { ok: true, result: { token: 'preview', reviewer: 'Luisa', items: [{ key: 'sy-0001', name: 'Lemma', reason: 'Statement changed', local: fragment, proposed: fragment, unavailable: '' }, { key: 'sy-0001:proof', name: 'Existing proof', reason: 'Existing proof · statement changed in this pull', local: fragment, proposed: fragment, unavailable: '' }] } } }));
	await page.route('**/_api/sync-incorporate', async (route) => {
		submitted = route.request().postDataJSON();
		await route.fulfill({ json: { ok: true, result: { accepted: ['sy-0001'], pending: ['sy-0001:proof'] } } });
	});
	await page.goto('/review/proposed?pull');
	await expect(page.getByRole('heading', { name: 'Introduction', exact: true })).toBeVisible();
	// prose asks for no acceptance; a block of mathematics is accepted only where it is marked as checked
	const checked = page.getByTestId('accept-checked');
	await expect(checked).toHaveCount(0);
	await page.getByRole('button', { name: 'Next change', exact: true }).click();
	await expect(checked).toBeEnabled();
	await expect(checked).not.toBeChecked();
	await checked.check();
	expect(submitted).toBeNull();
	await page.getByRole('button', { name: 'Next change', exact: true }).click();
	await expect(page.getByRole('heading', { name: 'Existing proof', exact: true })).toBeVisible();
	await expect(checked).not.toBeChecked();
	await expect(page.getByTestId('contribution-bar')).toContainText('1 marked as checked');
	await page.getByTestId('apply').click();
	await expect(page.getByTestId('contribution-bar-said')).toContainText('Took the pull: 1 accepted, 1 wait in Your Changes.');
	expect(submitted!.accept).toEqual(['sy-0001']);
	expect(submitted!.incoming).toBe('b'.repeat(40));
	expect(submitted!.review_token).toBe('preview');
});

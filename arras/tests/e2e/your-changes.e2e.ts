// Review › Your Changes: first, one document's blocks waiting to be accepted; then every pending change in the quilt, a card each grouped by the document that lists it, Keep and Discard acting as they do in the document, To do adding the open annotations from others. The change rows are hand-made and the acts stubbed: e2e-write drives them against a running publisher.
import { expect, test, type Page } from '@playwright/test';
import { manifest, serve } from '../manifest';

const MAIN = 'drafting/main.tex';
const EDIT = 'c-1a2b3c4d';
const SUGGESTED = 'e-2026-09-18-each00';
const LONE = 'c-9e8d7c6b';
const STUCK = 'c-00ff00ff';

const rows = [
	{ id: EDIT, kind: 'edit', path: 'drafting/nodes/sy-0001.tex', key: 'sy-0001', documents: [MAIN], old: 'fixed', new: 'held', author: null, created: null, state: 'ready', block: null },
	{ id: SUGGESTED, kind: 'suggested', path: 'drafting/nodes/sy-0002.tex', key: 'sy-0002', documents: [MAIN], old: 'Every orbit', new: 'Each orbit', author: { kind: 'agent', id: 'agent', label: 'agent' }, created: '2026-09-18T09:00:00Z', comment_html: '<p>One at a time.</p>', answers: 'a-2026-09-16-6sn46y', state: 'ready', block: null },
	{ id: STUCK, kind: 'suggested', path: 'drafting/nodes/sy-0002.tex', key: 'sy-0002', documents: [MAIN], old: 'orbit', new: 'cycle', author: { kind: 'agent', id: 'agent', label: 'agent' }, created: '2026-09-18T10:00:00Z', state: 'unplaced', why: 'An earlier suggestion takes these words.', block: null },
	{ id: LONE, kind: 'edit', path: 'notes/intro.md', key: null, documents: [], old: 'and by nothing else.', new: 'and by its orbit.', author: null, state: 'ready', block: null }
];

/** The fixture with the hand-made changes. */
const withChanges = (page: Page) => serve(page, (m) => (m.changes = rows));

/** A publisher serving the acts; what it was sent, by endpoint, the last body each. */
async function serving(page: Page, caps = ['change-keep', 'change-discard', 'review-accept']): Promise<Record<string, Record<string, unknown>>> {
	const sent: Record<string, Record<string, unknown>> = {};
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: caps, token: 't' } }));
	await page.route('**/_api/*', async (route) => {
		const endpoint = new URL(route.request().url()).pathname.split('/').pop() ?? '';
		const body = route.request().postDataJSON();
		sent[endpoint] = body;
		const done = Array.isArray(body?.changes) ? body.changes : [EDIT, SUGGESTED];
		await route.fulfill({ json: { ok: true, result: 'done', done, refused: [] } });
	});
	return sent;
}

const group = (page: Page, path: string) => page.locator(`[data-testid="change-group"][data-path="${path}"]`);
const card = (page: Page, id: string) => page.locator(`[data-testid="change-card"][data-change="${id}"]`);
const waits = manifest.unresolved.filter((r: { cause: string }) => r.cause !== 'never-accepted').length;

test('every pending change is a card, grouped by the document that lists it, and counted with the blocks waiting', async ({ page }) => {
	await withChanges(page);
	await page.goto('/review');
	await expect(page.getByTestId('change-group')).toHaveCount(2);
	await expect(group(page, MAIN).getByTestId('change-card')).toHaveCount(3);
	await expect(group(page, MAIN).getByTestId('change-group-count')).toHaveText('3');
	await expect(group(page, 'notes/intro.md')).toContainText("in no document's text");
	// each says what it is, who made it, where it is, and its words out and in
	const s = card(page, SUGGESTED);
	await expect(s).toContainText('Suggestion');
	await expect(s).toContainText('agent');
	await expect(s.getByTestId('change-where')).toContainText('drafting/nodes/sy-0002.tex');
	await expect(s.getByTestId('change-words').locator('.del')).toHaveText('Every orbit');
	await expect(s.getByTestId('change-words').locator('.ins')).toHaveText('Each orbit');
	await expect(s).toContainText('One at a time.');
	await expect(s.getByTestId('change-card-answers')).toContainText('It answers');
	await expect(card(page, EDIT)).toContainText('Edit in the file');
	await expect(card(page, EDIT)).toContainText('since your look');
	// one that is not ready says why, and offers neither act
	await expect(card(page, STUCK).getByTestId('change-card-why')).toHaveText('An earlier suggestion takes these words.');
	await expect(page.getByTestId('section-count-changes')).toHaveText(String(waits + rows.length));
	await expect(page.getByTestId('review-summary')).toContainText('4 changes waiting');
});

test('Keep and Discard act on one change at once, as in the document, and the bar undoes a discarded suggestion', async ({ page }) => {
	await withChanges(page);
	const sent = await serving(page);
	await page.goto('/review');
	await card(page, EDIT).getByTestId('card-keep').click();
	await expect(card(page, EDIT)).toHaveCount(0);
	expect(sent['change-keep']).toEqual({ changes: [EDIT] });
	await card(page, SUGGESTED).getByTestId('card-discard').click();
	await expect(card(page, SUGGESTED)).toHaveCount(0);
	expect(sent['change-discard']).toEqual({ changes: [SUGGESTED] });
	await page.getByTestId('review-undo').click();
	await expect.poll(() => sent['change-discard']).toEqual({ changes: [SUGGESTED], undo: true });
	await expect(card(page, SUGGESTED)).toHaveCount(1);
	await expect(page.getByTestId('review-undo')).toHaveCount(0);
	// an edit in the file discarded has its words written back, and no undo here
	await card(page, LONE).getByTestId('card-discard').click();
	await expect(group(page, 'notes/intro.md')).toHaveCount(0);
	expect(sent['change-discard']).toEqual({ changes: [LONE] });
	await expect(page.getByTestId('review-undo')).toHaveCount(0);
	await expect(card(page, STUCK).getByTestId('card-keep')).toBeDisabled();
});

test("Keep all and Discard all act on a document's ready changes, saying what each does", async ({ page }) => {
	await withChanges(page);
	const sent = await serving(page);
	await page.goto('/review');
	const keepAll = group(page, MAIN).getByTestId('group-keep-all');
	await expect(keepAll).toHaveText('Keep all 2');
	await expect(keepAll).toHaveAttribute('title', 'Writes the 1 suggestion into the file and keeps the 1 edit already in it.');
	await keepAll.click();
	expect(sent['change-keep']).toEqual({ all: true, document: MAIN });
	await expect(page.getByTestId('review-bar-said')).toContainText('Kept 2 changes in main.tex');
	await expect(card(page, EDIT)).toHaveCount(0);
	await expect(card(page, SUGGESTED)).toHaveCount(0);
	await expect(card(page, STUCK)).toHaveCount(1);
	// a file in no document names its changes
	await group(page, 'notes/intro.md').getByTestId('group-discard-all').click();
	expect(sent['change-discard']).toEqual({ changes: [LONE] });
});

test('To do adds the open annotations from others beside the changes, each linking to its place', async ({ page }) => {
	await withChanges(page);
	await page.goto('/review');
	await expect(page.getByTestId('todo-row')).toHaveCount(0);
	await page.getByTestId('your-todo').click();
	const todo = group(page, MAIN).getByTestId('todo-row');
	await expect(todo.first()).toBeVisible();
	// the agent's open revision on sy-0003, and not the reader's own question
	await expect(page.locator('[data-testid="todo-row"][data-annotation="a-2026-09-16-ecnav2"]')).toHaveCount(1);
	await expect(page.locator('[data-testid="todo-row"][data-annotation="a-2026-09-16-bns3an"]')).toHaveCount(0);
	await expect(page.locator('[data-testid="todo-row"][data-annotation="a-2026-09-16-ecnav2"] a')).toHaveAttribute('href', 'quilt:a-2026-09-16-ecnav2');
});

test('the blocks waiting to be accepted are listed one document at a time', async ({ page }) => {
	await withChanges(page);
	await page.goto('/review');
	const picker = page.getByTestId('review-document');
	await expect(picker).toHaveValue(MAIN);
	await expect(picker.locator('option').first()).toHaveText(/^main\.tex · \d+$/);
	const widget = page.locator('[data-testid="review-row"][data-key="sy-0001"]');
	await expect(widget).toHaveCount(1);
	await expect(widget.getByTestId('tag-changed')).toBeVisible();
	await expect(page.locator('[data-testid="review-group"][data-group="never"]')).not.toHaveAttribute('open');
});

test('with no change waiting it says so, and a static host offers no acts', async ({ page }) => {
	await serve(page, (m) => (m.changes = []));
	await page.goto('/review');
	await expect(page.getByTestId('changes-empty')).toContainText('No changes wait in your text.');
	await page.unrouteAll();
	await withChanges(page);
	await page.goto('/review');
	await expect(card(page, EDIT).getByTestId('card-keep')).toBeDisabled();
	await expect(group(page, MAIN).getByTestId('group-keep-all')).toBeDisabled();
	await expect(page.getByTestId('review-undo')).toHaveCount(0);
});

test('the mathematics leads: the blocks waiting to be accepted stand above the changes to keep', async ({ page }) => {
	await withChanges(page);
	await page.goto('/review');
	const accept = (await page.getByRole('heading', { name: 'Waiting to be accepted' }).boundingBox())!;
	const keep = (await page.getByRole('heading', { name: 'Changes to keep' }).boundingBox())!;
	const list = (await page.getByTestId('your-change-list').boundingBox())!;
	expect(accept.y).toBeLessThan(keep.y);
	expect(keep.y).toBeLessThan(list.y);
});

test('a card reads an escaped dollar as a dollar, and however long its words it stays inside the page', async ({ page }) => {
	const words = 'You spend \\(100\\times 0.62 = 62\\) USD. If Yes, you win \\$100 for a profit of $100 - 62 = 38$ USD; if No, you lose all \\$62. ' + 'And so on. '.repeat(300) + '\\begin{align*} ' + 'x_1 + '.repeat(120) + 'y \\end{align*}';
	const long = { ...rows[3], id: 'c-0a0b0c0d', old: '', new: words };
	await serve(page, (m) => (m.changes = [long]));
	await page.goto('/review');
	const c = card(page, long.id);
	await expect(c.getByTestId('change-words')).toContainText('win $100 for a profit');
	await expect(c.getByTestId('change-words')).toContainText('lose all $62');
	const main = page.getByTestId('your-changes');
	expect(await main.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
	const box = (await c.boundingBox())!;
	expect(box.height).toBeLessThan(400);
});

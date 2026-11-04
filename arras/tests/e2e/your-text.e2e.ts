// Review › Your text, a block's edit and its acceptance joined: each block listed once with every reason it waits, its own changes drawn under it, text outside any block and files in no document apart, each with its own verbs. The acts are stubbed: e2e-write drives them against a running publisher.
import { expect, test, type Page } from '@playwright/test';
import { manifest, serve } from '../manifest';

type Mutate = Parameters<Parameters<typeof serve>[1]>[0];

const FILE = 'drafting/nodes/sy-0001.tex';
const DIFF = `--- a/${FILE}\n+++ b/${FILE}\n@@ -1,4 +1,4 @@\n one\n-the first old line\n+the first new line\n three\n four\n@@ -20,4 +20,4 @@\n twenty\n-the second old line\n+the second new line\n twenty-two\n`;

/** The fixture with `sy-0001`'s file edited, two changes, by `blocks`. */
async function edited(page: Page, blocks: string[][], over?: (m: Mutate) => void): Promise<void> {
	await page.route(`**/changes/${FILE}.diff`, (r) => r.fulfill({ contentType: 'text/plain', body: DIFF }));
	await serve(page, (m) => {
		m.changes = [...m.changes, { path: FILE, kind: 'changed', hash: 'sha256:now', hunks: blocks.length, diff: `changes/${FILE}.diff`, blocks, documents: ['drafting/main.tex'] }];
		over?.(m);
	});
}

/** A publisher serving the verbs; what it was sent, by endpoint. */
async function serving(page: Page): Promise<Record<string, Record<string, unknown>>> {
	const sent: Record<string, Record<string, unknown>> = {};
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['changes-keep', 'changes-undo', 'review-accept'], token: 't' } }));
	for (const e of ['changes-keep', 'changes-undo'])
		await page.route(`**/_api/${e}`, async (route) => {
			sent[e] = route.request().postDataJSON();
			await route.fulfill({ json: { ok: true, result: e === 'changes-keep' ? 'kept it' : 'put it back' } });
		});
	return sent;
}

const row = (page: Page, key: string) => page.locator(`[data-testid="review-row"][data-key="${key}"]`);

test('a block edited and changed is listed once, with both reasons and its own edit alone', async ({ page }) => {
	await edited(page, [['sy-0001'], []]);
	await page.goto('/review');
	const widget = row(page, 'sy-0001');
	await expect(widget).toHaveCount(1);
	await expect(widget.getByTestId('tag-edited')).toHaveText('edited since your look');
	await expect(widget.getByTestId('tag-changed')).toBeVisible();
	await expect(widget.getByTestId('diff')).toContainText('the first new line');
	await expect(widget.getByTestId('diff')).not.toContainText('the second new line');
	// the file's other change touches no block, and stands apart
	const outside = page.getByTestId('outside-row');
	await expect(outside).toHaveAttribute('data-path', FILE);
	await expect(outside.getByTestId('diff')).toContainText('the second new line');
	await expect(outside.getByTestId('diff')).not.toContainText('the first new line');
	// a file in no document stands apart too, with nothing to accept
	const notes = page.locator('[data-testid="review-group"][data-group="others"]');
	await expect(notes).toContainText('nothing to accept');
	await expect(notes.getByTestId('change')).toHaveAttribute('data-path', 'notes/intro.md');
	await expect(notes.getByTestId('review-accept')).toHaveCount(0);
});

test('the column counts a block once however it waits, and each other row', async ({ page }) => {
	const waits = manifest.unresolved.filter((r: { cause: string }) => r.cause !== 'never-accepted').length;
	await edited(page, [['sy-0001'], []]);
	await page.goto('/review');
	// the waiting blocks, sy-0001 among them; its file's text outside any block; the file in no document
	await expect(page.getByTestId('section-count-text')).toHaveText(String(waits + 2));
});

test('an edit across two blocks is drawn under the first, and the second says so', async ({ page }) => {
	await edited(page, [['sy-0001', 'sy-0002']]);
	await page.goto('/review');
	await expect(row(page, 'sy-0001').getByTestId('diff')).toContainText('the first new line');
	const second = row(page, 'sy-0002');
	await expect(second.getByTestId('diff')).toHaveCount(0);
	await expect(second.getByTestId('tag-edited-with')).toContainText('edited with Widget');
	await expect(second.getByTestId('edit-keep')).toHaveCount(0);
});

test('a block never accepted comes up out of its fold once it is edited, and the rest stay folded and uncounted', async ({ page }) => {
	await edited(page, [['sy-000B']]);
	await page.goto('/review');
	const group = (id: string) => page.locator(`[data-testid="review-group"][data-group="${id}"]`);
	await expect(group('never')).not.toHaveAttribute('open');
	await expect(group('never').locator('[data-key="sy-000B"]')).toHaveCount(0);
	const b = group('changed').locator('[data-key="sy-000B"]');
	await expect(b.getByTestId('tag-never')).toHaveText('never accepted');
	await expect(b.getByTestId('tag-edited')).toBeVisible();
});

test('a block taken in keeps its group, its edit folded until asked for', async ({ page }) => {
	await edited(page, [['sy-0004']], (m) => {
		Object.assign(m.unresolved.find((x: { key: string }) => x.key === 'sy-0004'), { cause: 'adopted', contribution: '.loom/copies/aidoc.tex', source_label: 'Taken in from the copy “aidoc”' });
	});
	await page.goto('/review');
	const b = page.locator('[data-testid="review-group"][data-group="taken"] [data-key="sy-0004"]');
	await expect(b.getByTestId('tag-edited')).toBeVisible();
	await expect(b.getByTestId('diff')).toHaveCount(0);
	await b.getByTestId('edit-fold').locator('summary').click();
	await expect(b.getByTestId('diff')).toContainText('the first new line');
});

test('Keep and Undo act on a block\'s own changes, against the file as drawn; Undo asks first', async ({ page }) => {
	const sent = await serving(page);
	await edited(page, [['sy-0001'], []]);
	await page.goto('/review');
	const widget = row(page, 'sy-0001');
	await widget.getByTestId('edit-keep').click();
	await expect(widget.getByTestId('review-said')).toHaveText('Kept it.');
	expect(sent['changes-keep']).toEqual({ path: FILE, seen: 'sha256:now', hunks: [0] });
	await widget.getByTestId('edit-undo').click();
	expect(sent['changes-undo']).toBeUndefined();
	await expect(widget.getByTestId('undo-ask')).toContainText('back as it was at your look');
	await widget.getByTestId('undo-go').click();
	await expect(widget.getByTestId('review-said')).toHaveText('Put it back.');
	expect(sent['changes-undo']).toEqual({ path: FILE, seen: 'sha256:now', hunks: [0] });
});

test('a block with several changes has its own verbs on each, and on all of them', async ({ page }) => {
	const sent = await serving(page);
	await edited(page, [['sy-0001'], ['sy-0001']]);
	await page.goto('/review');
	const widget = row(page, 'sy-0001');
	await expect(widget.getByTestId('hunk-acts')).toHaveCount(2);
	await widget.getByTestId('hunk-acts').nth(1).getByTestId('hunk-keep').click();
	expect(sent['changes-keep']).toEqual({ path: FILE, seen: 'sha256:now', hunks: [1] });
	// all of a file's changes is the file: no numbers to go stale
	await widget.getByTestId('edit-keep').click();
	await expect(widget.getByTestId('review-said')).toBeVisible();
	expect(sent['changes-keep']).toEqual({ path: FILE, seen: 'sha256:now' });
});

test('the picker opens on the first document with something waiting, and says how much waits in each', async ({ page }) => {
	await page.goto('/review');
	const picker = page.getByTestId('review-document');
	await expect(picker).toHaveValue('drafting/main.tex');
	await expect(picker.locator('option').first()).toHaveText(/^main\.tex · \d+$/);
});

test('a static host offers no verbs', async ({ page }) => {
	await edited(page, [['sy-0001']]);
	await page.goto('/review');
	for (const id of ['edit-keep', 'edit-undo', 'change-keep', 'changes-keep-all']) await expect(page.getByTestId(id)).toHaveCount(0);
});

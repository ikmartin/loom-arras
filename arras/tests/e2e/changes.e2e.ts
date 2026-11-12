// Pending changes in the document (plan 0.30.3): every change drawn in Markup, its words out struck and its words in underlined in teal, or with every change made in Final, or the text as kept while the list shows annotations alone; its popup, Keep and Discard taking effect at once; the Changes menu; and changes in the stepper and the Comments list. The manifest's change rows and the merged block are hand-made, and the writes are stubbed: e2e-write drives them against a running publisher.
import { expect, test, type Page } from '@playwright/test';
import { pane } from '../workspace';
import { serve } from '../manifest';

const BLOCK = 'drafting/nodes/sy-0003.tex:123:200';
const MERGED = 'fragments/changes/sy-0003-test.html';
const EDIT = 'c-0e1d2c3b';
const SUGGESTED = 'e-2026-09-18-hence0';
const STUCK = 'c-5a6b7c8d';
// the reader's own annotation on "finite widget", and the agent's reply to it, drawn again on the new word
const ON = 'a-2026-09-16-ecnav2';

const merged = `<p class="noindent" data-src="${BLOCK}">Let <span class="math inline">\\((X,\\sigma)\\)</span> be a <mark class="annotation" data-annotation="${ON} a-2026-09-16-hwnav1">finite <span class="change" data-change="${EDIT}" data-side="old">widget</span></mark><span class="change" data-change="${EDIT}" data-side="new"><mark class="annotation moved" data-annotation="${ON} a-2026-09-16-hwnav1">gadget</mark></span>. <span class="change" data-change="${SUGGESTED}" data-side="old">Then</span><span class="change" data-change="${SUGGESTED}" data-side="new">Hence</span> <span class="math inline">\\(|X| \\equiv |\\Fix(\\sigma)| \\pmod 2\\)</span>.</p>`;

const rows = [
	{ id: EDIT, kind: 'edit', path: 'drafting/nodes/sy-0003.tex', key: 'sy-0003', documents: ['drafting/main.tex'], old: 'widget', new: 'gadget', new_html: null, author: null, created: null, comment_html: null, answers: null, state: 'ready', why: null, block: { src: BLOCK, fragment: MERGED }, diff: null },
	{ id: SUGGESTED, kind: 'suggested', path: 'drafting/nodes/sy-0003.tex', key: 'sy-0003', documents: ['drafting/main.tex'], old: 'Then', new: 'Hence', new_html: null, author: { kind: 'agent', id: 'agent', label: 'agent' }, created: '2026-09-18T09:00:00Z', comment_html: '<p>A consequence, not a sequel.</p>', answers: null, state: 'ready', why: null, block: { src: BLOCK, fragment: MERGED }, diff: null },
	{ id: STUCK, kind: 'edit', path: 'drafting/main.tex', key: null, documents: ['drafting/main.tex'], old: 'an old line', new: 'a new line', new_html: null, author: null, created: null, comment_html: null, answers: null, state: 'unplaced', why: 'Its words are not in the file as it stands.', block: null, diff: null }
];

/** The fixture with the three changes, the merged block served, and a publisher that takes every write, keeping each body by endpoint. */
async function withChanges(page: Page): Promise<Record<string, Record<string, unknown>>> {
	await serve(page, (m) => {
		m.changes = rows;
	});
	await page.route(`**/${MERGED}`, (r) => r.fulfill({ contentType: 'text/html', body: merged }));
	const sent: Record<string, Record<string, unknown>> = {};
	await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['annotate', 'edit', 'delete', 'restore', 'change-keep', 'change-discard'], token: 't' } }));
	await page.route('**/_api/*', (r) => {
		const endpoint = new URL(r.request().url()).pathname.split('/').pop() ?? '';
		const body = r.request().postDataJSON();
		sent[endpoint] = body;
		const done = Array.isArray(body?.changes) ? body.changes : [EDIT, SUGGESTED];
		return r.fulfill({ json: { ok: true, result: 'done', done, refused: [] } });
	});
	await page.goto('/master/drafting/main');
	await expect(words(page, EDIT, 'old')).toBeAttached();
	return sent;
}

const words = (page: Page, id: string, side: 'old' | 'new') => pane(page, 0).locator(`.fragment span.change[data-change="${id}"][data-side="${side}"]`);
const css = (at: import('@playwright/test').Locator, prop: string) => at.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
const TEAL = 'rgb(0, 118, 118)';

test('every pending change is drawn in Markup: its words out struck and its words in underlined, in teal', async ({ page }) => {
	await withChanges(page);
	const out = words(page, SUGGESTED, 'old');
	const into = words(page, SUGGESTED, 'new');
	await expect(out).toBeVisible();
	await expect(into).toBeVisible();
	expect(await css(out, 'text-decoration-line')).toBe('line-through');
	expect(await css(into, 'text-decoration-line')).toBe('underline');
	expect(await css(into, 'color')).toBe(TEAL);
	// a change's words are its own: an annotation round them does not tint them, one in them is not drawn, and one drawn again on the new words waits for Final
	expect(await css(words(page, EDIT, 'new').locator('mark.annotation.moved'), 'background-image')).toBe('none');
	// the toolbar counts them, and the stepper goes through them with the annotations
	await expect(pane(page, 0).getByTestId('changes-count')).toHaveText('3');
	await expect(pane(page, 0).getByTestId('step-count')).toContainText('items');
});

test('Final shows the text with every change made, and Annotations alone shows it as kept', async ({ page }) => {
	await withChanges(page);
	await pane(page, 0).getByTestId('changes-toggle').click();
	await page.getByTestId('changes-view-final').click();
	await expect(words(page, SUGGESTED, 'old')).toBeHidden();
	await expect(words(page, SUGGESTED, 'new')).toBeVisible();
	expect(await css(words(page, SUGGESTED, 'new'), 'text-decoration-line')).toBe('none');
	// the annotation is drawn on the new word, dashed, and opens its own popup there
	const moved = words(page, EDIT, 'new').locator('mark.annotation.moved');
	expect(await css(moved, 'background-image')).toContain('repeating-linear-gradient');
	await moved.click();
	await expect(page.getByTestId('ann-popup')).toHaveAttribute('data-annotation-id', ON);
	await page.keyboard.press('Escape');
	// the list showing annotations alone: the text is as kept, and the views wait
	await pane(page, 0).getByTestId('open-comments').click();
	await page.getByTestId('layer-annotations').click();
	await expect(words(page, SUGGESTED, 'new')).toBeHidden();
	await expect(words(page, SUGGESTED, 'old')).toBeVisible();
	expect(await css(words(page, SUGGESTED, 'old'), 'text-decoration-line')).toBe('none');
	await expect(page.getByTestId('change-card')).toHaveCount(0);
	await pane(page, 0).getByTestId('changes-toggle').click();
	await expect(page.getByTestId('changes-view-markup')).toBeDisabled();
});

test("a change's popup says what it is and what is on its words, and Keep takes effect at once", async ({ page }) => {
	const sent = await withChanges(page);
	await words(page, SUGGESTED, 'new').click();
	const p = page.getByTestId('change-popup');
	await expect(p).toHaveAttribute('data-change-id', SUGGESTED);
	await expect(p.getByTestId('change-kind')).toHaveText('Suggestion');
	await expect(p).toContainText('agent');
	await expect(p.getByTestId('change-comment')).toHaveText('A consequence, not a sequel.');
	await expect(p.getByTestId('change-why')).toHaveText('Not in the file yet. Keep writes it in.');
	await p.getByTestId('change-keep').click();
	await expect(p).toHaveCount(0);
	// shown kept at once: its new word alone, unmarked
	await expect(words(page, SUGGESTED, 'old')).toBeHidden();
	expect(await css(words(page, SUGGESTED, 'new'), 'color')).not.toBe(TEAL);
	expect(sent['change-keep']).toEqual({ changes: [SUGGESTED] });
	await expect(pane(page, 0).getByTestId('changes-count')).toHaveText('2');
});

test("the annotations on a change's words are named in its popup and open their own", async ({ page }) => {
	await withChanges(page);
	await words(page, EDIT, 'old').click();
	const p = page.getByTestId('change-popup');
	await expect(p.getByTestId('change-kind')).toHaveText('Edit in the file');
	await expect(p.getByTestId('change-why')).toHaveText('Already in the file. Discard writes your words back.');
	// the reply is shown inside its parent, so one annotation is here
	await expect(p.getByTestId('change-here')).toContainText('1 annotation here');
	await p.getByTestId('change-here-open').click();
	await expect(page.getByTestId('ann-popup')).toHaveAttribute('data-annotation-id', ON);
	await expect(page.getByTestId('change-popup')).toHaveCount(0);
});

test('the box in its popup writes an annotation on the words it takes out', async ({ page }) => {
	const sent = await withChanges(page);
	await words(page, EDIT, 'old').click();
	const p = page.getByTestId('change-popup');
	await p.getByTestId('change-comment-field').fill('Why a gadget?');
	await p.getByTestId('change-comment-save').click();
	await expect(p.getByTestId('change-said')).toContainText('Written as an annotation on these words');
	expect(sent.annotate).toEqual({ target: 'sy-0003', quote: 'widget', message: 'Why a gadget?' });
});

test('Discard takes effect at once; the toolbar undoes a discarded suggestion, and an edit in the file comes back from its version', async ({ page }) => {
	const sent = await withChanges(page);
	await words(page, SUGGESTED, 'new').click();
	await page.getByTestId('change-popup').getByTestId('change-discard').click();
	await expect(words(page, SUGGESTED, 'new')).toBeHidden();
	expect(await css(words(page, SUGGESTED, 'old'), 'text-decoration-line')).toBe('none');
	expect(sent['change-discard']).toEqual({ changes: [SUGGESTED] });
	await expect(pane(page, 0).getByTestId('annotate-undo')).toHaveAttribute('title', 'Undo discard (⌘Z)');
	await pane(page, 0).getByTestId('annotate-undo').click();
	await expect.poll(() => sent['change-discard']).toEqual({ changes: [SUGGESTED], undo: true });
	await expect(words(page, SUGGESTED, 'new')).toBeVisible();
	// an edit in the file: its words are written back, a version kept first, and nothing is put on the toolbar's history
	await words(page, EDIT, 'new').click();
	await page.getByTestId('change-popup').getByTestId('change-discard').click();
	await expect(words(page, EDIT, 'new')).toBeHidden();
	expect(sent['change-discard']).toEqual({ changes: [EDIT] });
	await expect(pane(page, 0).getByTestId('annotate-undo')).toHaveAttribute('title', 'Undo');
});

test('the Changes menu keeps or discards every change of the document that is ready, saying what each does', async ({ page }) => {
	const sent = await withChanges(page);
	await pane(page, 0).getByTestId('changes-toggle').click();
	const menu = page.getByTestId('changes-menu');
	await expect(menu.getByTestId('changes-keep-all')).toContainText('Keep all 2');
	await expect(menu.getByTestId('changes-keep-all')).toContainText('Writes the 1 suggestion into the file and keeps the 1 edit already in it.');
	await expect(menu).toContainText('1 more cannot be kept or discarded now');
	await menu.getByTestId('changes-keep-all').click();
	expect(sent['change-keep']).toEqual({ all: true, document: 'drafting/main.tex' });
	await expect(words(page, EDIT, 'old')).toBeHidden();
	await expect(words(page, SUGGESTED, 'old')).toBeHidden();
});

test('the stepper and the Comments list go through changes with the annotations; one with no place says why it waits', async ({ page }) => {
	await withChanges(page);
	await pane(page, 0).getByTestId('open-comments').click();
	const list = page.getByTestId('side-list');
	await expect(list.locator('.stitle')).toHaveText('Comments and changes');
	await expect(list.getByTestId('change-card')).toHaveCount(3);
	const stuck = list.locator(`[data-testid="change-card"][data-change="${STUCK}"]`);
	await expect(stuck.getByTestId('change-card-why')).toHaveText('Its words are not in the file as it stands.');
	await expect(stuck.getByTestId('card-keep')).toBeDisabled();
	// a card opens its change at its words
	await list.locator(`[data-testid="change-card"][data-change="${SUGGESTED}"]`).click();
	await expect(page.getByTestId('change-popup')).toHaveAttribute('data-change-id', SUGGESTED);
	// Changes alone, and To do holds every change
	await list.getByTestId('layer-changes').click();
	await expect(list.getByTestId('comment-card')).toHaveCount(0);
	await list.getByTestId('layer-all').click();
	await list.getByTestId('comments-todo').click();
	await expect(list.getByTestId('change-card')).toHaveCount(3);
	// the margin draws a teal pen for each change drawn in Markup
	await expect(pane(page, 0).getByTestId('margin').locator(`[data-change="${EDIT}"], .mg`).first()).toBeAttached();
});

/** Whether a computed colour is the teal of a change, and not an annotation's: more green and blue than red, read off a canvas so any notation reads alike. */
const teal = (at: import('@playwright/test').Locator, prop: 'color' | 'background-color') =>
	at.evaluate((el, p) => {
		const c = document.createElement('canvas').getContext('2d', { willReadFrequently: true })!;
		c.fillStyle = getComputedStyle(el).getPropertyValue(p);
		c.fillRect(0, 0, 1, 1);
		const [r, g, b, a] = c.getImageData(0, 0, 1, 1).data;
		return a > 0 && g > r && b > r;
	}, prop);

test('every side of a change is teal in either theme, though a Revision round it is red', async ({ page }) => {
	for (const scheme of ['light', 'dark'] as const) {
		await page.emulateMedia({ colorScheme: scheme });
		await withChanges(page);
		// the reader's annotation round "finite widget" is a Revision, red
		for (const side of ['old', 'new'] as const) {
			const at = words(page, EDIT, side);
			expect(await teal(at, 'color'), `${scheme}: the ${side} words' colour`).toBe(true);
			expect(await teal(at, 'background-color'), `${scheme}: the ${side} words' wash`).toBe(true);
		}
		await page.unrouteAll();
	}
});

test.describe('a change not merged into the text', () => {
	const STRUCT = 'c-57ac7a11';
	const WIDE = 'c-31de0b1c';
	const ENV = 'c-e0f5a2c9';
	const DIFF = `--- a/drafting/nodes/sy-0003.tex\n+++ b/drafting/nodes/sy-0003.tex\n@@ -3,3 +3,3 @@\n-Then the parity holds.\n+The parity holds.\n`;
	const row = (over: Record<string, unknown>) => ({ kind: 'edit', path: 'drafting/nodes/sy-0003.tex', key: 'sy-0003', documents: ['drafting/main.tex'], old: 'Then', new: '', new_html: null, author: null, created: null, comment_html: null, answers: null, state: 'ready', why: null, block: null, diff: null, ...over });
	const marked = [
		// a change to the text's structure: its own words' place, and its patch
		row({ id: STRUCT, place: { src: 'drafting/nodes/sy-0003.tex:150:160' }, diff: 'changes/c-57ac7a11.diff' }),
		// a block that runs over several paragraphs, and one over a statement whose merged text drops its display: never swapped in
		row({ id: WIDE, old: 'a whole stretch', new: 'another', block: { src: 'drafting/nodes/sy-0003.tex:100:300', fragment: 'fragments/changes/wide-test.html' } }),
		row({ id: ENV, path: 'drafting/main.tex', key: 'sy-0001', old: 'locus', new: 'set', block: { src: 'drafting/main.tex:1046:1334', fragment: 'fragments/changes/env-test.html' } })
	];

	async function withMarked(page: Page): Promise<void> {
		await serve(page, (m) => (m.changes = marked));
		await page.route('**/changes/c-57ac7a11.diff', (r) => r.fulfill({ contentType: 'text/plain', body: DIFF }));
		await page.route('**/fragments/changes/wide-test.html', (r) => r.fulfill({ contentType: 'text/html', body: `<pre class="source" data-src="drafting/nodes/sy-0003.tex:100:300">WIDE SOURCE <span class="change" data-change="${WIDE}" data-side="old">a whole stretch</span></pre>` }));
		await page.route('**/fragments/changes/env-test.html', (r) => r.fulfill({ contentType: 'text/html', body: `<pre class="source" data-src="drafting/main.tex:1046:1334">ENV SOURCE <span class="change" data-change="${ENV}" data-side="old">locus</span></pre>` }));
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['annotate', 'change-keep', 'change-discard'], token: 't' } }));
		await page.goto('/master/drafting/main');
		await expect(pane(page, 0).locator(`.fragment [data-change-at~="${STRUCT}"]`)).toBeAttached();
	}

	test('a change to the structure is a teal marker on the element holding its words, opens its popup with its words and its patch, and is listed as any change', async ({ page }) => {
		await withMarked(page);
		const at = pane(page, 0).locator(`.fragment [data-change-at~="${STRUCT}"]`);
		// the innermost element holding its words: the statement's paragraph, not the statement
		await expect(at).toHaveAttribute('data-src', BLOCK);
		await expect(at).toHaveClass(/change-at/);
		expect(await css(at, 'box-shadow')).toContain(TEAL);
		await expect(pane(page, 0).locator('.fragment span.change')).toHaveCount(0);
		// its pen in the margin, on the line it starts, which it shares with the annotation on "finite widget": the line's count lists it
		const top = (await at.boundingBox())!.y;
		const counts = pane(page, 0).getByTestId('margin-count');
		let line = -1;
		for (let i = 0; i < (await counts.count()); i++) if (Math.abs((await counts.nth(i).boundingBox())!.y - top) < 24) line = i;
		expect(line, 'a count beside the marked line').toBeGreaterThanOrEqual(0);
		const icon = counts.nth(line);
		await icon.click();
		await page.getByTestId('line-chooser').locator(`[data-change="${STRUCT}"]`).click();
		const p = page.getByTestId('change-popup');
		await expect(p).toHaveAttribute('data-change-id', STRUCT);
		await expect(p.getByTestId('change-words').locator('.del')).toHaveText('Then');
		await expect(p.getByTestId('diff')).toContainText('The parity holds.');
		await page.keyboard.press('Escape');
		// in Final it shows only by its marker: the text is as it was
		await pane(page, 0).getByTestId('changes-toggle').click();
		await page.getByTestId('changes-view-final').click();
		await expect(at).toHaveClass(/change-at/);
		await expect(at).toContainText('Then');
		await expect(icon).toBeVisible();
		// listed, stepped to and to do as any change
		await pane(page, 0).getByTestId('open-comments').click();
		const list = page.getByTestId('side-list');
		await expect(list.locator(`[data-testid="change-card"][data-change="${STRUCT}"]`)).toBeVisible();
		await list.getByTestId('comments-todo').click();
		await expect(list.locator(`[data-testid="change-card"][data-change="${STRUCT}"]`)).toBeVisible();
		await pane(page, 0).getByTestId('step-next').click();
		await expect(page.getByTestId('change-popup')).toBeVisible();
		await page.goto('/review');
		await expect(page.locator(`[data-testid="change-card"][data-change="${STRUCT}"]`)).toBeVisible();
	});

	test('a merged block over several paragraphs, or one that drops a part of its statement, is never swapped in, and its change is marked instead', async ({ page }) => {
		await withMarked(page);
		const doc = pane(page, 0).locator('.fragment');
		await expect(doc).not.toContainText('WIDE SOURCE');
		await expect(doc).not.toContainText('ENV SOURCE');
		await expect(doc.locator(`span.change[data-change~="${WIDE}"], span.change[data-change~="${ENV}"]`)).toHaveCount(0);
		// each is marked on the innermost element holding its block
		await expect(doc.locator(`[data-change-at~="${WIDE}"]`)).toHaveCount(1);
		const env = doc.locator(`[data-change-at~="${ENV}"]`);
		await expect(env).toHaveAttribute('data-src', 'drafting/main.tex:1046:1334');
		// and the statement keeps its display, typeset
		await expect(env.locator('.math.display[data-label="eq:fix"] mjx-container')).toHaveCount(1);
	});
});

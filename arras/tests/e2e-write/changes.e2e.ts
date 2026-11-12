// Pending changes under a running `loom serve` (plan 0.30.3): an edit made in a file since the reviewer's look and a suggested edit, both drawn in the document in Markup and in Final and listed in Review › Your Changes; Keep and Discard doing the same from either place; an annotation on the words a kept edit replaces carried onto its new words; Keep resolving the annotation a suggestion answers; and Keep all and Discard all.
import { expect, test, type Served } from '../served';
import type { Page } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pane } from '../workspace';

const MAIN = 'drafting/main.tex';
const NODE = 'drafting/nodes/sy-0002.tex';
// the agent's suggestion on sy-0002: "the fixed points are those of" in place of "compare"
const SUGGESTED = 'e-2026-09-17-zwvx4m';
// the reader's own question on "one or two points" in sy-0002
const QUESTION = 'a-2026-09-16-bns3an';

type Row = { id: string; kind: string; path: string; documents: string[]; state: string; old: string; new: string; answers?: string | null };

/** The manifest as the publisher last built it. */
const built = (served: Served) => JSON.parse(readFileSync(join(served.root, '.loom/build/manifest.json'), 'utf8'));
const pending = (served: Served): Row[] => built(served).changes ?? [];
const text = (served: Served, path = NODE) => readFileSync(join(served.root, path), 'utf8');

/** Edit sy-0002 in its file, "one or two points" becoming "at most two points", and wait for the change loom cuts from it; its id. */
async function editInPlace(served: Served): Promise<string> {
	writeFileSync(join(served.root, NODE), text(served).replace('one or two points', 'at most two points'));
	let id = '';
	await expect
		.poll(() => (id = pending(served).find((c) => c.kind === 'edit' && c.path === NODE)?.id ?? ''), { timeout: 60_000 })
		.not.toBe('');
	return id;
}

const words = (page: Page, id: string, side: 'old' | 'new') => pane(page, 0).locator(`.fragment span.change[data-change~="${id}"][data-side="${side}"]`);
const card = (page: Page, id: string) => page.locator(`[data-testid="change-card"][data-change="${id}"]`);

/** Keep or discard change `id` from the document, by its popup, or from Review, by its card; done once loom no longer lists it. */
async function act(page: Page, served: Served, where: 'document' | 'review', id: string, how: 'keep' | 'discard'): Promise<void> {
	if (where === 'document') {
		await page.goto('/master/drafting/main');
		await words(page, id, 'new').first().click();
		const p = page.getByTestId('change-popup');
		await expect(p).toHaveAttribute('data-change-id', id);
		await p.getByTestId(how === 'keep' ? 'change-keep' : 'change-discard').click();
		// shown done at once, before the publisher has answered
		await expect(words(page, id, how === 'keep' ? 'old' : 'new').first()).toBeHidden();
	} else {
		await page.goto('/review');
		await card(page, id).getByTestId(how === 'keep' ? 'card-keep' : 'card-discard').click();
		await expect(card(page, id)).toHaveCount(0);
	}
	await expect.poll(() => pending(served).some((c) => c.id === id), { timeout: 60_000 }).toBe(false);
}

test('an edit in the file and a suggested edit are drawn in Markup and in Final, and listed in Review', async ({ page, served }) => {
	const edit = await editInPlace(served);
	await page.goto('/master/drafting/main');
	for (const id of [edit, SUGGESTED]) {
		await expect(words(page, id, 'old').first()).toBeVisible();
		await expect(words(page, id, 'new').first()).toBeVisible();
	}
	expect(await words(page, edit, 'old').first().evaluate((el) => getComputedStyle(el).textDecorationLine)).toBe('line-through');
	expect(await words(page, edit, 'new').first().evaluate((el) => getComputedStyle(el).textDecorationLine)).toBe('underline');
	await expect(words(page, edit, 'new').first()).toContainText('at most');
	await pane(page, 0).getByTestId('changes-toggle').click();
	await page.getByTestId('changes-view-final').click();
	for (const id of [edit, SUGGESTED]) {
		await expect(words(page, id, 'old').first()).toBeHidden();
		await expect(words(page, id, 'new').first()).toBeVisible();
	}
	// nothing of the suggestion's old words is left in Final, the references among them neither
	const shown = await words(page, SUGGESTED, 'new')
		.first()
		.evaluate((s) => {
			const block = s.closest('p, pre') as HTMLElement;
			const seen = (el: Element) => (el as HTMLElement).offsetParent !== null;
			return { text: block.innerText, refs: [...block.querySelectorAll('a.ref')].filter(seen).map((a) => a.getAttribute('data-target')), old: [...block.querySelectorAll('span.change[data-side="old"]')].filter(seen).length };
		});
	expect(shown.text).not.toContain('compare');
	expect(shown.old).toBe(0);
	expect(shown.refs.filter((t) => t === 'sy-0001#eq:fix').length).toBeLessThanOrEqual(1);
	expect(shown.refs.filter((t) => t === 'sy-0001').length).toBeLessThanOrEqual(1);
	await page.goto('/review');
	await expect(card(page, edit)).toContainText('Edit in the file');
	await expect(card(page, edit).getByTestId('change-words')).toContainText('at most');
	await expect(card(page, SUGGESTED)).toContainText('Suggestion');
	await expect(card(page, SUGGESTED)).toContainText('Say what the comparison shows.');
});

for (const where of ['document', 'review'] as const) {
	test(`from ${where === 'document' ? 'the document' : 'Review'}, Keep takes an edit into the look and Discard drops a suggestion, the file as it was`, async ({ page, served }) => {
		const edit = await editInPlace(served);
		await act(page, served, where, edit, 'keep');
		await act(page, served, where, SUGGESTED, 'discard');
		const now = text(served);
		expect(now).toContain('at most two points');
		expect(now).toContain('compare');
		expect(now).not.toContain('the fixed points are those of');
		expect(built(served).suggested_edits[SUGGESTED].status).toBe('discarded');
	});

	test(`from ${where === 'document' ? 'the document' : 'Review'}, Discard writes the old words back over an edit and Keep writes a suggestion in`, async ({ page, served }) => {
		const edit = await editInPlace(served);
		await act(page, served, where, edit, 'discard');
		await act(page, served, where, SUGGESTED, 'keep');
		const now = text(served);
		expect(now).toContain('one or two points');
		expect(now).not.toContain('at most two points');
		expect(now).toContain('the fixed points are those of');
		expect(built(served).suggested_edits[SUGGESTED].status).toBe('kept');
	});
}

test('an annotation on the words a kept edit replaces is drawn again on its new words, and moves to them', async ({ page, served }) => {
	const edit = await editInPlace(served);
	// before Keep it stands on the words kept, and is drawn again on the new ones
	await page.goto('/master/drafting/main');
	await expect(words(page, edit, 'old').first()).toBeVisible();
	await expect(pane(page, 0).locator(`.fragment mark.annotation.moved[data-annotation~="${QUESTION}"]`)).not.toHaveCount(0);
	await act(page, served, 'document', edit, 'keep');
	await expect.poll(() => built(served).annotations[QUESTION]?.earlier?.quote ?? '', { timeout: 60_000 }).toContain('one or');
	await page.goto('/master/drafting/main');
	const mark = pane(page, 0).locator(`.fragment mark.annotation[data-annotation~="${QUESTION}"]`).first();
	await expect(mark).toContainText('at most');
	await mark.click();
	await expect(page.getByTestId('ann-popup').getByTestId('popup-earlier')).toContainText('one or');
});

test('Keep resolves the annotation a suggestion answers', async ({ page, served }) => {
	served.loom(['suggest', 'sy-0002', '--quote', 'Every orbit', '--with', 'Each orbit', '--answers', QUESTION, '--comment', 'One orbit at a time.', '--as', 'Referee Agent']);
	let id = '';
	await expect.poll(() => (id = pending(served).find((c) => c.answers === QUESTION)?.id ?? ''), { timeout: 60_000 }).not.toBe('');
	expect(built(served).annotations[QUESTION].status).toBe('open');
	await page.goto('/master/drafting/main');
	await words(page, id, 'new').first().click();
	await expect(page.getByTestId('change-popup').getByTestId('change-answers')).toContainText('Keep resolves it');
	await act(page, served, 'review', id, 'keep');
	await expect.poll(() => built(served).annotations[QUESTION].status, { timeout: 60_000 }).toBe('resolved');
	expect(text(served)).toContain('Each orbit');
});

test("Keep all keeps every ready change of a document from its Changes menu, and Discard all a file's from Review", async ({ page, served }) => {
	await editInPlace(served);
	await page.goto('/master/drafting/main');
	await pane(page, 0).getByTestId('changes-toggle').click();
	await page.getByTestId('changes-keep-all').click();
	await expect.poll(() => pending(served).filter((c) => c.documents.includes(MAIN) && c.state === 'ready').length, { timeout: 60_000 }).toBe(0);
	const now = text(served);
	expect(now).toContain('at most two points');
	expect(now).toContain('the fixed points are those of');
	// a file in no document: its changes discarded from Review, its words written back
	const intro = 'notes/intro.md';
	expect(pending(served).some((c) => c.path === intro)).toBe(true);
	const before = text(served, intro);
	await page.goto('/review');
	await page.locator(`[data-testid="change-group"][data-path="${intro}"]`).getByTestId('group-discard-all').click();
	await expect.poll(() => pending(served).some((c) => c.path === intro), { timeout: 60_000 }).toBe(false);
	expect(text(served, intro)).not.toBe(before);
});

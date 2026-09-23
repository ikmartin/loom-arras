// Writing from the viewer, against a publisher that is actually serving the write API.
import { expect, test } from '@playwright/test';
import { openPicker } from '../picker';
import { readFileSync } from 'node:fs';

const QUILT = '.tmp-write-quilt';

/**
 * Select a session, because a write names one (plan 0.13.1) and nothing is selected at rest.
 *
 * This is the setup the interface asks of a reader too: the composer is greyed until an open session is chosen, and
 * nothing is opened behind their back. Every write test therefore starts by choosing where its work will be filed.
 */
async function intoASession(page: import('@playwright/test').Page) {
	await openPicker(page);
	const first = page.getByTestId('session-list').locator('[data-testid^="session-s-"]').first();
	if (await first.count()) {
		await first.click();
	} else {
		await page.getByTestId('session-new').click();
		await page.getByTestId('session-new-title').fill('a sitting for the tests');
		await page.getByTestId('session-new-title').press('Enter');
	}
	await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations are written into/);
}

function log(): Record<string, unknown>[] {
	return readFileSync(`${QUILT}/annotations/log.jsonl`, 'utf8')
		.split('\n')
		.filter((l) => l.trim())
		.map((l) => JSON.parse(l));
}

/** Select an element's words as a reader would, and let go: the page offers to annotate them. */
async function select(at: import('@playwright/test').Locator): Promise<void> {
	await at.evaluate((node) => {
		const range = document.createRange();
		range.selectNodeContents(node);
		const sel = window.getSelection();
		sel?.removeAllRanges();
		sel?.addRange(range);
		node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
}

test('a comment written from a selection lands in the log as a person, anchored across the formula it crosses', async ({ page }) => {
	// The gate of plan 0.11 Part H, with the tools a work's pages have (phase 4): not "the button appeared" -- the file changed.
	await page.goto('/node/sy-0003');
	await intoASession(page);
	const statement = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0003"] > p[data-src]').first();
	await statement.locator('mjx-container').first().waitFor();
	await select(statement);
	await page.getByTestId('annotate-offer').click();
	// the place is named as the tab names it (this corpus is not compiled, so by its id), and the quote carries the formula as TeX
	await expect(page.getByTestId('note-where')).toContainText('sy-0003');
	// the selection stays lit while the comment is written, and the composer does not repeat it
	await expect(page.getByTestId('note-quote')).toHaveCount(0);
	await expect.poll(() => page.evaluate(() => (CSS as unknown as { highlights: Map<string, unknown> }).highlights.has('note-pending'))).toBe(true);
	await page.getByTestId('note-body').fill('Does finiteness do any work in the closedness half?');
	// an objection, because severity grades a fault and only `objection` and `suggestion` claim one (DR-204)
	await page.getByTestId('note-kind').selectOption('objection');
	await page.getByTestId('note-severity').selectOption('minor');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);

	const mine = log().filter((e) => String(e.body ?? '').startsWith('Does finiteness'));
	expect(mine).toHaveLength(1);
	expect(mine[0].kind).toBe('human'); // written by a person, not by the run whose page it was
	expect(mine[0].target).toBe('sy-0003');
	expect(mine[0].annotation_kind).toBe('objection');
	expect(mine[0].severity).toBe('minor');
	// anchored to the sentence, not to the node, and recorded as the source has it: the formula's own TeX
	const exact = (mine[0].anchor as { exact: string }).exact;
	expect(exact).toContain('finite widget');
	expect(exact).toMatch(/\$|\\\(/);
});

test("the publisher's refusal is shown rather than swallowed, and the whole result is offered instead", async ({ page }) => {
	// "quote not found" means something different from "no such key", and a reader told only "failed" has to guess.
	await page.goto('/node/sy-0003');
	await intoASession(page);
	const statement = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0003"] > p[data-src]').first();
	await statement.locator('mjx-container').first().waitFor();
	// words that are nowhere in the source: what a reader would get from a selection loom cannot map back
	await statement.evaluate((p) => p.insertAdjacentText('afterbegin', 'a phrase that appears nowhere in this statement at all '));
	await select(statement);
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('This should be refused.');
	await page.getByTestId('note-submit').click();
	const said = page.getByTestId('note-said');
	await expect(said).toContainText('quote');
	expect(log().filter((e) => e.body === 'This should be refused.')).toHaveLength(0);
	// nothing is filed as anchored that is not: the one way on is a note on the whole result, said as such
	await page.getByTestId('note-whole').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	const whole = log().filter((e) => e.body === 'This should be refused.');
	expect(whole).toHaveLength(1);
	expect(whole[0].target).toBe('sy-0003');
	expect(whole[0].anchor ?? null).toBeNull();
});

test('a box drawn round an equation notes the equation itself', async ({ page }) => {
	await page.goto('/node/sy-0001');
	await intoASession(page);
	const display = page.locator('[data-pane="0"] .fragment .math.display[data-label="eq:fix"]');
	await display.locator('mjx-container').waitFor();
	await page.getByTestId('tool-box').click();
	const b = (await display.boundingBox())!;
	await page.mouse.move(b.x + 4, b.y + 2);
	await page.mouse.down();
	await page.mouse.move(b.x + b.width - 4, b.y + b.height - 2, { steps: 6 });
	await page.mouse.up();
	await expect(page.getByTestId('note-where')).toContainText('equation');
	await page.getByTestId('note-body').fill('Name the fixed locus here.');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	const mine = log().filter((e) => e.body === 'Name the fixed locus here.');
	expect(mine).toHaveLength(1);
	expect(mine[0].target).toBe('sy-0001#eq:fix');
	// and once the publisher has rebuilt, the display is marked, underlined rather than barred
	await expect(display).toHaveClass(/annotation-block/, { timeout: 10000 });
	expect(await display.evaluate((d) => getComputedStyle(d).borderLeftWidth)).toBe('0px');
});

test('a document is written on the same way', async ({ page }) => {
	await page.goto('/master/main');
	await intoASession(page);
	await expect(page.getByTestId('tool-select')).toBeVisible();
	const words = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0008"] > p[data-src]').first();
	await words.scrollIntoViewIfNeeded();
	await select(words);
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('A gadget wants an example.');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	const mine = log().filter((e) => e.body === 'A gadget wants an example.');
	expect(mine).toHaveLength(1);
	expect(mine[0].target).toBe('sy-0008');
});

test('a citation suggestion can be accepted from the context, and leaves a breadcrumb', async ({ page }) => {
	await page.goto('/node/sy-0002');
	await intoASession(page);
	await page.getByTestId('open-context').click();
	const notes = page.getByTestId('context').getByTestId('reference-notes');
	await expect(notes).toContainText('Suggested citations');
	await page.getByTestId('refnote-accept').first().click();
	await expect(notes.getByRole('status')).toHaveText('accepted');
	const written = readFileSync(`${QUILT}/reference-notes.jsonl`, 'utf8');
	expect(written).toContain('a textbook reference would do');
	expect(written).toContain('"verified": false'); // never a second source of identity truth
});

/** Comments shown in place (`inline` beneath the block, `hover` floating at the mark), with the reply written inside the box that is showing them. */
function inPlace(where: 'inline' | 'floating') {
	return async ({ page }: { page: import('@playwright/test').Page }) => {
		await page.addInitScript(
			(c) => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: c })),
			where
		);
		await page.goto('/node/sy-0003');
	await intoASession(page);
		const mark = page.locator('.fragment mark.annotation').first();
		await mark.waitFor();
		const box = page.locator('[data-testid="comment-expanded"]'); // one host, however many comments the mark carries by now
		await mark.click();
		await expect(box).toHaveCount(1);

		const body = `a reply written in the ${where} box`;
		await page.locator('[data-testid="comment-expanded"] [data-testid="verb-reply"]').first().click();
		await page.locator('[data-testid="comment-expanded"] [data-testid="verb-text"]').first().fill(body);
		await page.locator('[data-testid="comment-expanded"] [data-testid="verb-send"]').first().click();

		// The write changes the manifest, and the re-wire that follows it must leave the box where the reply was written open, now showing the reply.
		await expect(page.locator('[data-testid="comment-expanded"] .reply').filter({ hasText: body })).toHaveCount(1);
		await page.waitForTimeout(2500); // several polls: a publisher rebuilding once a second closed it again within the second
		await expect(box).toHaveCount(1);
		expect(log().filter((e) => e.body === body)).toHaveLength(1);

		// And the mark still toggles: one click closes it, the next opens it, and it stays open.
		await mark.click();
		await expect(box).toHaveCount(0);
		await mark.click();
		await expect(box).toHaveCount(1);
		await page.waitForTimeout(600); // in `hover` the pointer's own beat falls inside the click, and must not shut what the click opened
		await expect(box).toHaveCount(1);
	};
}

test('a reply written in an inline comment box leaves the box open', inPlace('inline'));
test('a reply written in a floating comment box leaves the box open', inPlace('floating'));

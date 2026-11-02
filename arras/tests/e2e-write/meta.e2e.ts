// Quoting and changes under a running `loom serve` (plan 0.22.8): one press of quote on a passage of a document, of a Markdown file or on a message writes a note an agent reads with `loom since`; and in Review's Changes the author keeps a change, or undoes one and the file's text is back.
import { expect, test, type Served } from '../served';
import { pickSession } from '../picker';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

async function intoASession(page: import('@playwright/test').Page, served: Served): Promise<string> {
	const id = served.openSessions().at(-1)!;
	await pickSession(page, id);
	await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations are written into/);
	return id;
}

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

/** What a person quoted since an agent last looked, as `loom since` reports it. */
function quotes(served: Served): string[] {
	return (JSON.parse(served.loom(['since', '--as', 'Watching Agent', '--json'])).noted ?? []).map((n: { quote?: string }) => n.quote ?? '');
}

test('one press of quote on a passage, a Markdown passage or a message writes a note an agent reads', async ({ page, served }) => {
	served.loom(['since', '--as', 'Watching Agent']);
	await page.goto('/node/sy-0003');
	const sid = await intoASession(page, served);
	const statement = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0003"] > p[data-src]').first();
	await statement.locator('mjx-container').first().waitFor();
	await select(statement);
	await page.getByTestId('quote-offer').click();
	await expect(page.getByTestId('quote-said')).toHaveText('quoted');
	await expect.poll(() => quotes(served).join(' | ')).toContain('finite widget');

	await page.goto('/file/notes/intro.md');
	const para = page.locator('[data-pane="0"] [data-testid="file-item"] p').first();
	await select(para);
	await page.getByTestId('quote-offer').click();
	await expect(page.getByTestId('quote-said')).toHaveText('quoted');
	await expect.poll(() => quotes(served).join(' | ')).toContain('These notes sit beside');

	await page.goto(`/session/${sid}`);
	const first = page.getByTestId('transcript').locator('li.message').first();
	await first.hover();
	await first.getByTestId('quote-message').click();
	await expect.poll(() => (JSON.parse(served.loom(['since', '--as', 'Watching Agent', '--json'])).noted ?? []).length).toBeGreaterThan(0);
	await expect(page.getByTestId('transcript').locator('[data-testid^="noted-"]').first()).toBeVisible();
});

test('in Changes the author keeps a change, or undoes one and the file is back as it was', async ({ page, served }) => {
	await page.goto('/review/changes');
	const change = page.getByTestId('change').filter({ has: page.locator('code', { hasText: 'notes/intro.md' }) });
	await expect(change).toContainText('and by nothing else.');
	await change.getByTestId('change-undo').click();
	await expect(page.getByTestId('changes-none')).toBeVisible();
	const undone = readFileSync(join(served.root, 'notes/intro.md'), 'utf8');
	expect(undone).toContain('A widget is fixed by its locus. The');
	expect(undone).not.toContain('nothing else');
	// a change made now, as an agent writes a file, is kept
	const intro = join(served.root, 'notes/intro.md');
	const text = readFileSync(intro, 'utf8');
	(await import('node:fs')).writeFileSync(intro, text + '\nAn agent added this line.\n');
	await expect(page.getByTestId('change')).toHaveCount(1, { timeout: 10000 });
	await page.getByTestId('change-keep').click();
	await expect(page.getByTestId('changes-none')).toBeVisible();
});

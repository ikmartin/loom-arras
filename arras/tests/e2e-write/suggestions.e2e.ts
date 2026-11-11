// Suggestions and sessions under a running `loom serve`: Take it writes a suggestion's text into its file, a version of the document kept first, and resolves it as applied; and reading another session's transcript leaves the person's writes where they were. None of this compiles anything.
import { expect, test } from '../served';
import { pickSession } from '../picker';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const TEXT = 'a-2026-09-17-rvgxnv';

test('Take it writes the suggestion into its file, keeps a version first, and resolves it as applied', async ({ page, served }) => {
	const [referee] = served.openSessions();
	await page.goto('/review/proposed');
	await pickSession(page, referee);
	const row = page.locator(`[data-testid="suggestion"][data-id="${TEXT}"]`);
	await row.getByTestId('proposed-take').click();
	await expect(page.getByTestId('proposed-bar-said')).toContainText('Applied the suggestion in main.tex');
	expect(readFileSync(join(served.root, 'drafting/nodes/sy-0002.tex'), 'utf8')).toContain('the fixed points are those of');
	const resolved = served.log().find((e) => e.event === 'resolved' && e.id === TEXT);
	expect(resolved?.applied).toBeTruthy();
	// the version kept first is in the document's history, named for the act
	await page.goto('/review/record?document=drafting%2Fmain.tex');
	await expect(page.getByTestId('history-tick').last()).toContainText('Before applying a suggestion');
});

test("an annotation written while another session's transcript is read names no session, and the footer keeps where notes go", async ({ page, served }) => {
	const [referee] = served.openSessions();
	await served.api('session-new', { title: 'a side sitting' });
	const side = served.openSessions().at(-1)!;
	await page.goto('/node/sy-0003');
	await pickSession(page, referee);
	await page.goto(`/node/sy-0003?beside=${encodeURIComponent('/session/' + side)}`);
	await expect(page.getByTestId('chat-writing')).toContainText('You are writing in “referee”.');
	await expect(page.getByTestId('session-footer-name')).toHaveText('referee');
	const at = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0003"] > p[data-src]').first();
	await at.locator('mjx-container').first().waitFor();
	await at.evaluate((el) => {
		const range = document.createRange();
		range.selectNodeContents(el);
		const sel = window.getSelection()!;
		sel.removeAllRanges();
		sel.addRange(range);
		el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('Written while reading the side sitting.');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	expect(served.written('Written while reading the side sitting.')).not.toHaveProperty('session');
});

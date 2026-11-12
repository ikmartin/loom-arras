// Screenshots of the editing surfaces, which exist only where a publisher is actually serving the write API. ARRAS_SHOTS_OUT puts them elsewhere than the committed pictures, for checking the run itself.
import { expect, test } from '../served';
import { pickSession } from '../picker';

const OUT = process.env.ARRAS_SHOTS_OUT ?? '../docs/reports/images';

test('the editing surfaces', async ({ page, served }) => {
	// a write names its session, and nothing is selected at rest (plan 0.13.1), so the pictures are of a reader who has chosen where their work goes -- which is the state the composer is usable in
	const session = served.openSessions().at(-1)!;
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.addInitScript(() => localStorage.setItem('arras.prefs', JSON.stringify({ face: 'serif', size: 'm', width: 'mid', theme: 'light' })));
	await page.addInitScript(() => localStorage.setItem('arras.annotate.hand', JSON.stringify({ type: 'question', over: {} })));

	await page.goto('/node/sy-0002');
	const words = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0002"] > p[data-src]').first();
	await words.locator('mark.annotation').waitFor();
	await pickSession(page, session);
	await settled(page);
	// Annotate, holding a type that asks something: the popup opens where the selection is, for what it asks
	await page.getByTestId('tool-annotate').click();
	await words.evaluate((node) => {
		const range = document.createRange();
		range.selectNodeContents(node);
		window.getSelection()?.removeAllRanges();
		window.getSelection()?.addRange(range);
		node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
	await page.getByTestId('popup-comment-field').fill('Is the singleton orbit counted once or twice here?');
	await expect(page.getByTestId('popup-type')).toContainText('Question');
	await page.screenshot({ path: `${OUT}/composer.png`, animations: 'disabled' });

	await page.goto('/master/drafting/main');
	// choosing where to write opens its Chat, beside the document
	await pickSession(page, session);
	await settled(page);
	await page.screenshot({ path: `${OUT}/document-annotations.png`, animations: 'disabled' });
});

/** The Chat beside has drawn its messages, and every formula on the page is typeset. */
async function settled(page: import('@playwright/test').Page): Promise<void> {
	await expect(page.locator('[data-pane="1"] [data-testid="chat"] [data-testid^="message-"]').first()).toBeVisible();
	await expect.poll(() => page.locator('.math:not(:has(mjx-container))').count()).toBe(0);
	await page.evaluate(() => document.fonts.ready.then(() => undefined));
}

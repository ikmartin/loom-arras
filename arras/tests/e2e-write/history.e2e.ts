// Versions under a running `loom serve` (plan 0.25.5): keeping an edit to a document keeps a version of it, a version is recorded by name from Review › The Record, and Restore puts one back, the text it replaced kept as a version first. None of this compiles anything.
import { expect, test } from '../served';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

test('keeping an edit keeps a version of the document, which Restore puts back after another edit', async ({ page, served }) => {
	const node = join(served.root, 'drafting/nodes/sy-0002.tex');
	writeFileSync(node, readFileSync(node, 'utf8').replace('Every orbit', 'Each orbit'));
	await page.goto('/review');
	const card = page.getByTestId('change-card').filter({ has: page.locator('.ins', { hasText: 'Each' }) });
	await card.getByTestId('card-keep').click();
	await expect(card).toHaveCount(0);
	// a kept block still waits to be accepted
	await expect(page.locator('[data-testid="review-row"][data-key="sy-0002"]').getByTestId('review-accept')).toBeVisible();
	await page.goto('/review/record?document=drafting%2Fmain.tex');
	await expect(page.getByTestId('history-tick').last()).toContainText('Kept an edit');
	// another edit, then the kept version put back
	writeFileSync(node, readFileSync(node, 'utf8').replace('Each orbit', 'Any orbit'));
	await page.getByTestId('history-restore').click();
	await expect(page.getByTestId('history-ask')).toContainText('Put main.tex back as it was');
	await page.getByTestId('history-restore-go').click();
	await expect(page.getByTestId('history-bar-said')).toContainText('Put main.tex back as “Kept an edit” holds it');
	expect(readFileSync(node, 'utf8')).toContain('Each orbit');
	await expect(page.getByTestId('history-tick').last()).toContainText('Before restoring');
});

test('a version is recorded by name, and a name in use is refused', async ({ page }) => {
	await page.goto('/review/record?document=drafting%2Fmain.tex');
	await page.getByTestId('history-record').click();
	await page.getByTestId('history-record-name').fill('Before referee');
	await page.getByTestId('history-record-go').click();
	await expect(page.getByTestId('history-bar-said')).toHaveText('Kept this version of main.tex as “Before referee”.');
	await expect(page.getByTestId('history-tick').last()).toContainText('Before referee');
	await page.getByTestId('history-record').click();
	await page.getByTestId('history-record-name').fill('Before referee');
	await page.getByTestId('history-record-go').click();
	await expect(page.getByTestId('history-bar-said')).toContainText('kept already');
});

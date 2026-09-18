// Writing from the viewer, against a publisher that is actually serving the write API.
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const QUILT = '.tmp-write-quilt';

function log(): Record<string, unknown>[] {
	return readFileSync(`${QUILT}/annotations/log.jsonl`, 'utf8')
		.split('\n')
		.filter((l) => l.trim())
		.map((l) => JSON.parse(l));
}

test('a comment written in the browser lands in the log as a person', async ({ page }) => {
	// The gate of plan 0.11 Part H. Not "the button appeared" -- the file changed.
	await page.goto('/node/sy-0003');
	await expect(page.getByTestId('composer')).toBeVisible();
	await page.getByTestId('composer-open').click();
	await page.getByTestId('composer-quote').fill('finite widget');
	await page.getByTestId('composer-message').fill('Does finiteness do any work in the closedness half?');
	await page.getByTestId('composer-kind').selectOption('question');
	await page.getByTestId('composer-severity').selectOption('minor');
	await page.getByTestId('composer-submit').click();
	await expect(page.getByTestId('composer-said')).toHaveText('written');

	const mine = log().filter((e) => String(e.body ?? '').startsWith('Does finiteness'));
	expect(mine).toHaveLength(1);
	expect(mine[0].kind).toBe('human'); // written by a person, not by the run whose page it was
	expect(mine[0].severity).toBe('minor');
	expect(JSON.stringify(mine[0])).toContain('finite widget'); // anchored to the sentence, not to the node
});

test("the publisher's refusal is shown rather than swallowed", async ({ page }) => {
	// "quote not found" means something different from "no such key", and a reader told only "failed" has to guess.
	await page.goto('/node/sy-0003');
	await page.getByTestId('composer-open').click();
	await page.getByTestId('composer-quote').fill('a phrase that appears nowhere in this statement at all');
	await page.getByTestId('composer-message').fill('This should be refused.');
	await page.getByTestId('composer-submit').click();
	const said = page.getByTestId('composer-said');
	await expect(said).toBeVisible();
	await expect(said).not.toHaveText('written');
	expect(log().filter((e) => e.body === 'This should be refused.')).toHaveLength(0);
});

test('a citation suggestion can be accepted, and leaves a breadcrumb', async ({ page }) => {
	await page.goto('/node/sy-0002');
	const notes = page.getByTestId('reference-notes');
	await expect(notes).toContainText('Suggested citations');
	await page.getByTestId('refnote-accept').first().click();
	await expect(notes.getByRole('status')).toHaveText('accepted');
	const written = readFileSync(`${QUILT}/reference-notes.jsonl`, 'utf8');
	expect(written).toContain('a textbook reference would do');
	expect(written).toContain('"verified": false'); // never a second source of identity truth
});

// Changes and acceptance under a running `loom serve`: in Review › Your Changes an edit is kept or discarded as a change of words, and a block it is in still waits to be accepted, which Accept records and which keeps its edit too.
import { expect, test } from '../served';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

test('an edit made in a file is a change of words: Keep leaves its block waiting to be accepted, Discard puts the kept words back, and Accept keeps its edit too', async ({ page, served }) => {
	const node = join(served.root, 'drafting/nodes/sy-0002.tex');
	const row = page.locator('[data-testid="review-row"][data-key="sy-0002"]');
	const edit = (from: string, to: string) => writeFileSync(node, readFileSync(node, 'utf8').replace(from, to));
	// a change is cut by words: the card names the words it puts in
	const card = (word: string) => page.getByTestId('change-card').filter({ has: page.locator('.ins', { hasText: word }) });
	// a card goes at once; the publisher has acted once its manifest no longer lists the change
	const listed = (word: string) => (JSON.parse(readFileSync(join(served.root, '.loom/build/manifest.json'), 'utf8')).changes ?? []).some((c: { new: string }) => c.new === word);
	edit('Every orbit', 'Each orbit');
	await page.goto('/review');
	await expect(card('Each')).toHaveCount(1);
	await expect(card('Each').getByTestId('change-words').locator('.del')).toHaveText('Every');
	await expect(row).toHaveCount(1);
	// Keep says nothing about the mathematics, so the block still waits
	await card('Each').getByTestId('card-keep').click();
	await expect(card('Each')).toHaveCount(0);
	await expect.poll(() => listed('Each')).toBe(false);
	await expect(row.getByTestId('review-accept')).toBeVisible();
	// edited again, and Discard puts back what was kept
	edit('Each orbit', 'Any orbit');
	await expect(card('Any')).toHaveCount(1);
	await card('Any').getByTestId('card-discard').click();
	await expect(card('Any')).toHaveCount(0);
	await expect.poll(() => listed('Any')).toBe(false);
	await expect.poll(() => readFileSync(node, 'utf8')).toContain('Each orbit');
	// edited once more and accepted: the edit goes with the wait
	edit('Each orbit', 'Any orbit');
	await expect(card('Any')).toHaveCount(1);
	// a PDF newer than every source is loom's sign the document compiles, so no TeX run happens here
	mkdirSync(join(served.root, '.loom/build/drafting/main'), { recursive: true });
	writeFileSync(join(served.root, '.loom/build/drafting/main/main.pdf'), '%PDF-1.4\n');
	await page.locator('[data-testid="review-row"][data-key="sy-0001"]').getByTestId('review-pick').check();
	await row.getByTestId('review-pick').check();
	await page.getByTestId('review-accept-picked').click();
	await expect(page.getByTestId('review-bar-said')).toContainText('Accepted 2 blocks');
	await expect(page.locator('[data-testid="review-group"][data-group="changed"] [data-key="sy-0002"]')).toHaveCount(0);
	await expect(card('Any')).toHaveCount(0);
	// the agent's suggestion on the block still waits; the edit made in the file does not
	const edits = () => (JSON.parse(readFileSync(join(served.root, '.loom/build/manifest.json'), 'utf8')).changes ?? []).filter((c: { kind: string; path: string }) => c.kind === 'edit' && c.path === 'drafting/nodes/sy-0002.tex');
	await expect.poll(() => edits().length).toBe(0);
});

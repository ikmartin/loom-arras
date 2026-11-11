// Changes under a running `loom serve` (plan 0.22.8): in Review's Changes the author keeps a change, or undoes one and the file's text is back.
import { expect, test } from '../served';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

test('in Your Changes the author keeps a change, or undoes one after saying so, and the file is back as it was', async ({ page, served }) => {
	const fs = await import('node:fs');
	await page.goto('/review');
	const change = page.getByTestId('change').filter({ hasText: 'notes/intro.md' });
	await expect(change).toContainText('and by nothing else.');
	// undo asks first, and Cancel leaves the file alone
	await change.getByTestId('change-undo').click();
	await expect(change.getByTestId('undo-ask')).toContainText('Put notes/intro.md back as it was at your look? Its text now is kept.');
	await change.getByTestId('undo-cancel').click();
	await expect(change.getByTestId('undo-ask')).toHaveCount(0);
	await change.getByTestId('change-undo').click();
	await change.getByTestId('undo-go').click();
	await expect(page.getByTestId('change')).toHaveCount(0);
	await expect(page.getByTestId('review-bar-said')).toContainText('Put back notes/intro.md');
	const intro = join(served.root, 'notes/intro.md');
	const undone = readFileSync(intro, 'utf8');
	expect(undone).toContain('A widget is fixed by its locus. The');
	expect(undone).not.toContain('nothing else');
	// a change made now, as an agent writes a file, is kept, the button busy until the page is drawn again
	fs.writeFileSync(intro, undone + '\nAn agent added this line.\n');
	await expect(page.getByTestId('change')).toHaveCount(1);
	await page.getByTestId('change-keep').click();
	await expect(page.getByTestId('change')).toHaveCount(0);
	await expect(page.getByTestId('review-bar-said')).toHaveText('Kept notes/intro.md.');
});

test('one of two changes in a file is kept or undone alone, and a new file is removed by undoing it', async ({ page, served }) => {
	const fs = await import('node:fs');
	await page.goto('/review');
	await page.getByTestId('changes-keep-all').click();
	await expect(page.getByTestId('change')).toHaveCount(0);
	const path = join(served.root, 'notes/intro.md');
	const lines = Array.from({ length: 20 }, (_, i) => `line ${i + 1}`);
	fs.writeFileSync(path, lines.join('\n') + '\n');
	await expect(page.getByTestId('change')).toHaveCount(1);
	await page.getByTestId('change-keep').click();
	await expect(page.getByTestId('change')).toHaveCount(0);
	fs.writeFileSync(path, lines.map((l) => (l === 'line 2' ? 'line two' : l === 'line 18' ? 'line eighteen' : l)).join('\n') + '\n');
	const change = page.getByTestId('change');
	await expect(change).toContainText('2 changes');
	const hunks = change.getByTestId('hunk-acts');
	await expect(hunks).toHaveCount(2);
	// keep the first: the second is still a change
	await hunks.first().getByTestId('hunk-keep').click();
	await expect(change).not.toContainText('2 changes');
	await expect(change).toContainText('line eighteen');
	await expect(page.getByTestId('change-said')).toContainText('Kept a change to notes/intro.md');
	// undo what is left, after saying so: line 18 is back, line 2 stays as kept
	await change.getByTestId('change-undo').click();
	await change.getByTestId('undo-go').click();
	await expect(page.getByTestId('change')).toHaveCount(0);
	const now = readFileSync(path, 'utf8');
	expect(now).toContain('line two');
	expect(now).toContain('line 18\n');
	// a file new since the look is removed by undoing it, its text kept
	const fresh = join(served.root, 'notes/fresh.md');
	fs.writeFileSync(fresh, '# Fresh\n');
	const added = page.getByTestId('change').filter({ hasText: 'notes/fresh.md' });
	await expect(added).toContainText('new since your look');
	await added.getByTestId('change-undo').click();
	await expect(added.getByTestId('undo-ask')).toContainText('Remove notes/fresh.md? Its text is kept.');
	await added.getByTestId('undo-go').click();
	await expect(page.getByTestId('review-bar-said')).toContainText('Removed notes/fresh.md');
	expect(fs.existsSync(fresh)).toBe(false);
});

test('an act on a file that moved since the page was drawn is refused, and the page is drawn again', async ({ page, served }) => {
	const fs = await import('node:fs');
	const path = join(served.root, 'notes/intro.md');
	await page.goto('/review');
	await expect(page.getByTestId('change')).toHaveCount(1);
	// the file moves on behind the page's back, before the watcher redraws it
	await page.route('**/_api/changes-keep', async (route) => {
		fs.writeFileSync(path, readFileSync(path, 'utf8') + '\nMoved on.\n');
		await route.continue();
	});
	await page.getByTestId('change-keep').click();
	await expect(page.getByTestId('change-said')).toContainText('This file changed since the page was drawn');
	await expect(page.getByTestId('change')).toContainText('Moved on.');
});

test("Your Changes lists an edited block once: Keep leaves it waiting to be accepted, and Accept keeps its edit too", async ({ page, served }) => {
	const fs = await import('node:fs');
	const node = join(served.root, 'drafting/nodes/sy-0002.tex');
	const row = page.locator('[data-testid="review-row"][data-key="sy-0002"]');
	const edit = (from: string, to: string) => fs.writeFileSync(node, readFileSync(node, 'utf8').replace(from, to));
	edit('Every orbit', 'Each orbit');
	await page.goto('/review');
	await expect(row.getByTestId('tag-edited')).toBeVisible();
	await expect(row).toHaveCount(1);
	await expect(row.getByTestId('diff')).toContainText('Each orbit');
	// Keep says nothing about the mathematics, so the block still waits
	await row.getByTestId('edit-keep').click();
	await expect(row.getByTestId('tag-edited')).toHaveCount(0);
	await expect(row.getByTestId('review-accept')).toBeVisible();
	await expect(row.getByTestId('diff')).toHaveCount(0);
	// edited again, and Undo puts back only what changed since it was kept
	edit('Each orbit', 'Any orbit');
	await expect(row.getByTestId('tag-edited')).toBeVisible();
	await row.getByTestId('edit-undo').click();
	await row.getByTestId('undo-go').click();
	await expect(row.getByTestId('tag-edited')).toHaveCount(0);
	expect(readFileSync(node, 'utf8')).toContain('Each orbit');
	// edited once more and accepted: the edit goes with the wait
	edit('Each orbit', 'Any orbit');
	await expect(row.getByTestId('tag-edited')).toBeVisible();
	// a PDF newer than every source is loom's sign the document compiles, so no TeX run happens here
	fs.mkdirSync(join(served.root, '.loom/build/drafting/main'), { recursive: true });
	fs.writeFileSync(join(served.root, '.loom/build/drafting/main/main.pdf'), '%PDF-1.4\n');
	await page.locator('[data-testid="review-row"][data-key="sy-0001"]').getByTestId('review-pick').check();
	await row.getByTestId('review-pick').check();
	await page.getByTestId('review-accept-picked').click();
	await expect(page.getByTestId('review-bar-said')).toContainText('Accepted 2 blocks');
	await expect(page.locator('[data-testid="review-group"][data-group="changed"] [data-key="sy-0002"]')).toHaveCount(0);
	expect(served.loom(['changes', '--json'])).not.toContain('sy-0002.tex');
});

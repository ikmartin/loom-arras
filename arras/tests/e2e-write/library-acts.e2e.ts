// Acting from Review › Library under a running `loom serve` (plan 0.24.4): a row's menu runs on its work and follows the run, stops asking for a paper and asks again, copies the entry, uploads a PDF for the work, and removes a work added by hand; selected rows run as one; a citation suggestion is decided in its line.
import { expect, test } from '../served';
import { pickSession } from '../picker';

const ENTRY = '@article{Ost18,\n  author = {Ostrander, D.},\n  title = {Widget categories and their duals},\n  year = {2018},\n  journal = {J. Widget Theory}\n}';

test("a row's menu runs on its work, asking for the network the quilt has off, and the page follows the run", async ({ page }) => {
	await page.goto('/review/library');
	await page.getByTestId('menu-Man12').click();
	await page.getByTestId('menu-items-Man12').getByTestId('act-run').click();
	await page.getByTestId('network-offline').click();
	const run = page.getByTestId('job-progress');
	await expect(run).toHaveCount(1);
	await expect(run).toHaveAttribute('data-state', 'done', { timeout: 60000 });
});

test('"Stop asking for its paper…" asks why and declares it unreadable, and asking again undoes it', async ({ page }) => {
	await page.goto('/review/library');
	await page.getByTestId('menu-Man12').click();
	await page.getByTestId('act-ignore').click();
	await page.getByTestId('ignore-why').fill('a living document');
	await page.getByTestId('ignore-go').click();
	await expect(page.getByTestId('unreadable-Man12')).toBeVisible();
	await expect(page.getByTestId('row-said-Man12')).toContainText('declared unreadable: a living document');
	await page.getByTestId('menu-Man12').click();
	await page.getByTestId('act-unignore').click();
	await page.getByTestId('ignore-why').fill('a version can be had');
	await page.getByTestId('ignore-go').click();
	await expect(page.getByTestId('unreadable-Man12')).toHaveCount(0);
});

test('"Copy BibTeX" copies the entry as a .bib holds it', async ({ page, context }) => {
	await context.grantPermissions(['clipboard-read', 'clipboard-write']);
	await page.goto('/review/library');
	await page.getByTestId('menu-Kre99').click();
	await page.getByTestId('act-copy').click();
	await expect(page.getByTestId('row-said-Kre99')).toHaveText('BibTeX copied');
	const copied = await page.evaluate(() => navigator.clipboard.readText());
	expect(copied).toMatch(/^@article\{Kre99,\n {2}author = \{Kresch, Andrew\},/);
	expect(copied).not.toContain('loom-');
});

test('two rows selected run as one, followed on the page', async ({ page }) => {
	await page.goto('/review/library');
	await page.getByTestId('select-Kre99').check();
	await page.getByTestId('select-Man12').check();
	await expect(page.getByTestId('bulk')).toContainText('2 selected');
	await page.getByTestId('bulk-run').click();
	await page.getByTestId('network-offline').click();
	const run = page.getByTestId('job-progress');
	await expect(run).toHaveCount(1);
	await expect(run).toHaveAttribute('data-state', 'done', { timeout: 60000 });
	await expect(page.getByTestId('bulk-run')).toHaveCount(0);
});

test('a citation suggestion is accepted in its line, which then leaves the list', async ({ page, served }) => {
	await page.goto('/review/library');
	const list = page.getByTestId('citation-suggestions');
	const accept = list.locator('[data-testid^="cite-accept-"]').first();
	// a decision is recorded in a session, so there is none to take without one
	await expect(accept).toBeDisabled();
	await pickSession(page, served.openSessions().at(-1)!);
	const before = await list.locator('li').count();
	await accept.click();
	await expect(list.locator('li')).toHaveCount(before - 1);
});

test('a work added by hand that nothing cites is removed from its row, after asking', async ({ page, served }) => {
	await served.api('library-add', { text: ENTRY });
	await page.goto('/review/library');
	await expect(page.getByTestId('added-Ost18')).toBeVisible();
	await page.getByTestId('menu-Ost18').click();
	await page.getByTestId('act-remove').click();
	await expect(page.getByTestId('ledger-Ost18')).toContainText('A paper stored for it is set aside, not deleted.');
	await page.getByTestId('remove-go').click();
	await expect(page.getByTestId('ledger-Ost18')).toHaveCount(0);
	// a cited work offers no removal
	await page.getByTestId('menu-Kre99').click();
	await expect(page.getByTestId('menu-items-Kre99').getByTestId('act-remove')).toHaveCount(0);
});

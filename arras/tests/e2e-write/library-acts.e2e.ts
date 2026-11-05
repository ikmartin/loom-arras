// Acting from the library's page under a running `loom serve` (plan 0.24.4): a row's menu runs on its work and follows the run, stops asking for a paper and asks again, copies the entry, uploads a PDF for the work, and removes a work added by hand; selected rows run as one; a citation suggestion is decided in its line.
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
	await expect(run).toHaveAttribute('data-state', 'done');
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
	await expect(run).toHaveAttribute('data-state', 'done');
	await expect(page.getByTestId('bulk-run')).toHaveCount(0);
});

test('a citation suggestion is taken in its card, which then leaves the list', async ({ page, served }) => {
	await page.goto('/review/proposed');
	const cards = page.locator('[data-testid="proposed-card"][data-kind="citation"]');
	const take = cards.first().getByTestId('proposed-take');
	// a decision is recorded in a session, so there is none to take without one
	await expect(take).toBeDisabled();
	await expect(page.getByTestId('proposed-no-session')).toBeVisible();
	await pickSession(page, served.openSessions().at(-1)!);
	const before = await cards.count();
	await take.click();
	await expect(cards).toHaveCount(before - 1);
	await expect(page.getByTestId('proposed-bar-said')).toContainText('as a reference note');
});

test('a work nothing cites is deleted from its row, after saying what goes with it', async ({ page, served }) => {
	await served.api('library-add', { text: ENTRY });
	await page.goto('/review/library');
	await expect(page.getByTestId('added-Ost18')).toBeVisible();
	await page.getByTestId('menu-Ost18').click();
	await page.getByTestId('act-delete').click();
	await expect(page.getByTestId('delete-ask')).toContainText('Delete Ost18 from the library? This cannot be undone.');
	await page.getByTestId('delete-go').click();
	await expect(page.getByTestId('ledger-Ost18')).toHaveCount(0);
	await expect(page.getByTestId('bulk-said')).toHaveText('Deleted Ost18 from the library');
	// a cited work says why it stays, and acts on nothing
	await page.getByTestId('menu-Kre99').click();
	const line = page.getByTestId('menu-items-Kre99').getByTestId('act-delete');
	await expect(line).toHaveAttribute('aria-disabled', 'true');
	await expect(line).toHaveAttribute('title', /Your documents cite Kre99/);
	await line.click({ force: true });
	await expect(page.getByTestId('delete-ask')).toHaveCount(0);
});

test('what a document carries is refused where it was asked, and says where to remove it', async ({ page }) => {
	await page.goto('/review/library?show=not-cited');
	const row = page.locator('tr[data-testid^="ledger-"]').first();
	const key = (await row.getAttribute('data-testid'))!.replace('ledger-', '');
	await page.getByTestId(`menu-${key}`).click();
	await page.getByTestId(`menu-items-${key}`).getByTestId('act-delete').click();
	await page.getByTestId('delete-go').click();
	await expect(page.getByTestId(`row-said-${key}`)).toContainText('gathering brings it back');
	await expect(page.getByTestId(`ledger-${key}`)).toBeVisible();
	await expect(page.getByTestId('delete-ask')).toHaveCount(0);
});

test('selected works are deleted together, and one that must stay says why and stays selected', async ({ page, served }) => {
	await served.api('library-add', { text: ENTRY });
	await served.api('library-add', { text: ENTRY.replaceAll('Ost18', 'Ost19').replace('Widget categories', 'Gadget categories').replace('2018', '2019') });
	await page.goto('/review/library');
	for (const key of ['Ost18', 'Ost19', 'Kre99']) await page.getByTestId(`select-${key}`).check();
	await page.getByTestId('bulk-delete').click();
	await expect(page.getByTestId('bulk-delete-ask')).toContainText('these 3 works');
	await page.getByTestId('bulk-delete-go').click();
	await expect(page.getByTestId('ledger-Ost18')).toHaveCount(0);
	await expect(page.getByTestId('ledger-Ost19')).toHaveCount(0);
	await expect(page.getByTestId('bulk-said')).toContainText('Deleted 2 works.');
	await expect(page.getByTestId('bulk-said')).toContainText('Kre99');
	await expect(page.getByTestId('ledger-Kre99')).toBeVisible();
	await expect(page.getByTestId('select-Kre99')).toBeChecked();
});

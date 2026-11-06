// Library runs from the viewer under a running `loom serve` (plan 0.24.1): a run on one work from its Info, and on every work from the library's page, each asking first for the network the synthetic quilt has off, each followed step by step to its verdict.
import { expect, test } from '../served';

test("a work's run starts from its Info, asks for the network the quilt has off, and runs offline to its verdict", async ({ page }) => {
	await page.goto('/library/Kre99');
	await page.getByTestId('run-get').click();
	await expect(page.getByTestId('network-ask')).toBeVisible();
	await page.getByTestId('network-offline').click();
	const run = page.getByTestId('job-progress');
	await expect(run).toHaveAttribute('data-state', 'done');
	// offline, looking up and fetching act on nothing, and say so; the run still reaches its verdict
	await expect(run.locator('[data-step="resolve"]')).toHaveAttribute('data-state', 'skipped');
	await expect(run.locator('[data-step="fetch"]')).toHaveAttribute('data-state', 'skipped');
	await expect(run.locator('.head strong')).not.toHaveText('Done');
	await run.getByRole('button', { name: 'Dismiss' }).click();
	await expect(run).toHaveCount(0);
});

test("a run over every work starts from the library's page and gathers the bibliography first", async ({ page }) => {
	await page.goto('/review/library');
	await page.getByTestId('run-everything').click();
	await page.getByTestId('network-offline').click();
	const run = page.getByTestId('job-progress');
	await expect(run.locator('[data-step="gather"]')).toBeVisible();
	await expect(run).toHaveAttribute('data-state', 'done');
	await expect(run.locator('[data-step="gather"]')).toHaveAttribute('data-state', 'done');
});

test("a cited work's problem offers digesting the work again, which starts a run and answers with its verdict", async ({ page, served }) => {
	const fs = await import('node:fs');
	const { join } = await import('node:path');
	const digest = join(served.root, '.loom/digests/Kre99.tex');
	// a reference to nothing inside one of Kre99's results, as a fault in the digest writer leaves one
	fs.writeFileSync(digest, fs.readFileSync(digest, 'utf8').replace('\\end{theorem}', 'See \\ref{nowhere-at-all}.\n\\end{theorem}'));
	await page.goto('/review/problems');
	const works = page.getByTestId('problems-works');
	await expect(works).toBeVisible();
	await expect(page.getByTestId('problems-yours')).not.toContainText('nowhere-at-all');
	await works.locator('summary').first().click();
	const work = page.locator('[data-testid="problem-work"][data-work="Kre99"]');
	await expect(work).toContainText('A reference points nowhere');
	await work.getByTestId('digest-again').click();
	const said = work.getByTestId('digest-said');
	await expect(said).toContainText('Digesting Kre99 again');
	// the fixture's digest of Kre99 was made by hand and has no paper to read again, so the run ends with nothing new, and says so
	await expect(said).toContainText('Done.');
	await expect(said).toContainText('digested');
});

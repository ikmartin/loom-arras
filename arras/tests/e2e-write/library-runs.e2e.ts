// Library runs from the viewer under a running `loom serve` (plan 0.24.1): a run on one work from its Info, and on every work from Review › Library, each asking first for the network the synthetic quilt has off, each followed step by step to its verdict.
import { expect, test } from '../served';

test("a work's run starts from its Info, asks for the network the quilt has off, and runs offline to its verdict", async ({ page }) => {
	await page.goto('/library/Kre99');
	await page.getByTestId('run-get').click();
	await expect(page.getByTestId('network-ask')).toBeVisible();
	await page.getByTestId('network-offline').click();
	const run = page.getByTestId('job-progress');
	await expect(run).toHaveAttribute('data-state', 'done', { timeout: 60000 });
	// offline, looking up and fetching act on nothing, and say so; the run still reaches its verdict
	await expect(run.locator('[data-step="resolve"]')).toHaveAttribute('data-state', 'skipped');
	await expect(run.locator('[data-step="fetch"]')).toHaveAttribute('data-state', 'skipped');
	await expect(run.locator('.head strong')).not.toHaveText('Done');
	await run.getByRole('button', { name: 'Dismiss' }).click();
	await expect(run).toHaveCount(0);
});

test('a run over every work starts from Review › Library and gathers the bibliography first', async ({ page }) => {
	await page.goto('/review/library');
	await page.getByTestId('run-everything').click();
	await page.getByTestId('network-offline').click();
	const run = page.getByTestId('job-progress');
	await expect(run.locator('[data-step="gather"]')).toBeVisible();
	await expect(run).toHaveAttribute('data-state', 'done', { timeout: 120000 });
	await expect(run.locator('[data-step="gather"]')).toHaveAttribute('data-state', 'done');
});

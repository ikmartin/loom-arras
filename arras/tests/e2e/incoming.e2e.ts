// Incoming in one pass (plan 0.25.2), read from the fixture's agent copy: every change is listed by the name its result has, under its section, in the list the counter in a bar that stays at the top opens, so the two texts take the page's width; a change whose edits clash with the person's can't be taken and says why; one merged with the person's edit says so; and with no publisher to ask, nothing offers to take or apply.
import { expect, test } from '@playwright/test';
import { serve } from '../manifest';

test('an agent copy is reviewed under a pinned bar, each change named, a clash said, and nothing to press without a publisher', async ({ page }) => {
	await page.goto('/review/incoming');
	const bar = page.getByTestId('contribution-bar');
	await expect(bar).toHaveCSS('position', 'sticky');
	await expect(bar).toContainText('From aidoc into main');
	await expect(bar).toContainText("1 can't be taken");
	// no rail: the change takes the page's width, and the counter opens the list
	await expect(page.getByTestId('change-row')).toHaveCount(0);
	const at = page.getByTestId('change-at');
	await expect(at).toHaveText(/^1 of \d+$/);
	await at.click();
	const rows = page.getByTestId('change-row');
	// names, not keys
	await expect(rows.filter({ hasText: 'Orbits' })).toHaveCount(1);
	await expect(rows.filter({ hasText: /^sy-0002/ })).toHaveCount(0);
	const widget = page.locator('[data-testid="change-row"][data-key="sy-0001"]');
	await expect(widget).toHaveAttribute('data-state', 'clash');
	await expect(widget).toContainText("can't be taken");
	// the filter narrows the list
	await page.getByTestId('change-filter').fill('orbit');
	await expect(rows).toHaveCount(2);
	await page.getByTestId('change-filter').fill('');
	// picking one shows it and closes the list; stepping moves through the rest, the bar staying put
	await rows.filter({ hasText: 'Orbits' }).click();
	await expect(rows).toHaveCount(0);
	await expect(at).toHaveText(/^2 of /);
	await page.getByTestId('next-change').click();
	await expect(at).toHaveText(/^3 of /);
	// a static host serves no writes
	for (const id of ['take-it', 'leave-it', 'take-all', 'apply', 'accept-checked']) await expect(page.getByTestId(id)).toHaveCount(0);
});

test('a change both sides edited whose lines fall apart is offered merged, and says so', async ({ page }) => {
	await serve(page, (m) => {
		const c = m.contributions.find((x: { kind: string }) => x.kind === 'adopt');
		const orbits = c.changes.find((x: { key: string }) => x.key === 'sy-0002');
		orbits.class = 'merged';
		orbits.merged = orbits.proposed;
	});
	await page.goto('/review/incoming');
	await page.getByTestId('change-at').click();
	const row = page.locator('[data-testid="change-row"][data-key="sy-0002"]');
	await expect(row).toContainText('merged');
	await row.click();
	await expect(page.getByTestId('merged-note')).toContainText('You both changed it');
});

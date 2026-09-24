// What it did (plan 0.14 phase 6): a session's `run.log`, in order, opening on the newest action; a row that made or changed an annotation links it, names what it is on by the key it was filed under, and says where it stands. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { beside, pane } from '../workspace';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));
const REFEREE = 's-2026-09-16-0001';

/** The referee's log, padded with `extra` plain commands before it, so the view has something to scroll. */
async function longLog(page: Page, extra: number) {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		const pad = Array.from({ length: extra }, (_, i) => ({ time: '2026-09-15T09:00:00Z', command: `loom source sy-000${i % 9} --closure` }));
		m.threads[REFEREE].log = [...pad, ...m.threads[REFEREE].log];
		await route.fulfill({ json: m });
	});
}

test('the rows are the log, in order, and the view opens on the newest', async ({ page }) => {
	await longLog(page, 60);
	await page.goto(`/session/${REFEREE}?view=did`);
	const rows = page.getByTestId('did-row');
	await expect(rows).toHaveCount(60 + manifest.threads[REFEREE].log.length);
	await expect(rows.last()).toBeInViewport();
	await expect(rows.first()).not.toBeInViewport();
	await expect(rows.first()).toContainText('loom source sy-0000 --closure');
});

test('a row names what its annotation is on by its key, never as a reader numbers it, and says where it stands', async ({ page }) => {
	await page.goto(`/session/${REFEREE}?view=did`);
	const made = page.locator('[id="ann-a-2026-09-16-0001"]');
	await expect(made.getByTestId('did-annotation')).toHaveText('objection');
	await expect(made).toContainText('sy-0003');
	await expect(made).not.toContainText('Theorem');
	await expect(made.getByTestId('did-state')).toHaveText('open');
	// a later row about the same annotation links it too, but only the first carries its anchor
	const resolved = page.getByTestId('did-row').filter({ hasText: '--resolve a-2026-09-16-0002' });
	await expect(resolved.getByTestId('did-state')).toHaveText('resolved');
	await expect(resolved).not.toHaveAttribute('id', /.+/);
});

test("a row's annotation opens beside, with its box open", async ({ page }) => {
	await page.goto('/master/main' + beside(`/session/${REFEREE}?view=did`));
	await pane(page, 1).locator('[id="ann-a-2026-09-16-0001"]').getByTestId('did-annotation').click();
	await expect(pane(page, 0).getByTestId('comment-expanded').locator('[data-annotation-id="a-2026-09-16-0001"]')).toBeVisible();
	await expect(pane(page, 1).getByTestId('session-did')).toBeVisible();
});

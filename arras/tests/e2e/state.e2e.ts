// The research state (plan 0.21.3): a page about the whole quilt that an agent keeps and the person edits, read from one row at the top of the Docs column. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { pane } from '../workspace';
import { REFEREE, saying, serve } from '../manifest';

test.describe('the research state', () => {
	test('a row above the documents opens it in the focused pane, saying who wrote it, and a reload keeps it', async ({ page }) => {
		await page.goto('/master/main');
		await page.getByTestId('docs-state').getByRole('link', { name: 'Research state' }).click();
		await expect(page).toHaveURL(/\/page\/state$/);
		const state = pane(page, 0).getByTestId('research-state');
		await expect(state).toContainText('Widgets are finite throughout');
		await expect(state.getByTestId('page-meta')).toContainText('written by Referee Agent');
		await expect(state.locator('mjx-container, a').first()).toBeVisible();
		await expect(page.getByRole('tab', { name: 'Research state' })).toBeVisible();
		await expect(page.getByTestId('docs-state').getByRole('link')).toHaveAttribute('aria-current', 'page');
		await page.reload();
		await expect(pane(page, 0).getByTestId('research-state')).toContainText('Widgets are finite throughout');
	});

	test('a quilt with no research state has no row', async ({ page }) => {
		await serve(page, (m) => delete m.research_state);
		await page.goto('/master/main');
		await expect(page.getByTestId('docs-drafts')).toBeVisible();
		await expect(page.getByTestId('docs-state')).toHaveCount(0);
	});

	test('the meta line says when the person has edited it since, and what its links no longer name', async ({ page }) => {
		await serve(page, (m) => {
			m.research_state!.edited_since = true;
			m.research_state!.links = { broken: [{ href: 'quilt:sy-9999', why: 'no key' }], moved: [{ href: 'quilt:sy-0003', key: 'sy-0003' }] };
		});
		await page.goto('/page/state');
		await expect(page.getByTestId('page-meta')).toHaveText(/edited since · 1 linked result has changed since · 1 link names nothing now/);
	});

	test('a quilt:state link in a message opens it beside the transcript', async ({ page }) => {
		await saying(page, '<p>See <a href="quilt:state"></a>.</p>');
		await page.goto('/session/' + REFEREE);
		await page.getByTestId('message-1').getByRole('link', { name: 'the research state' }).click();
		await expect(pane(page, 1).getByTestId('research-state')).toContainText('Widgets are finite throughout');
	});
});

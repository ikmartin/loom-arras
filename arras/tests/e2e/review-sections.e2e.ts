// Review, the quilt's management: its column lists the sections, each with what waits for the author there, and each section is a page of its own. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { manifest, serve } from '../manifest';

test('Review\'s column lists its sections, each counting what waits there, the current one marked', async ({ page }) => {
	await page.goto('/review');
	const list = page.getByTestId('review-sections');
	await expect(list.getByRole('link')).toHaveText([/^Needs review/, /^Incoming/, /^Library/, /^Sessions/, /^History/, /^Problems/]);
	await expect(page.getByTestId('section-needs-review')).toHaveAttribute('aria-current', 'page');
	const unresolved = (manifest.unresolved ?? []).filter((r: { status: string }) => r.status === 'needs-review').length;
	await expect(page.getByTestId('section-count-needs-review')).toHaveText(String(unresolved));
	await expect(page.getByTestId('section-count-incoming')).toHaveText(String((manifest.contributions ?? []).length));
	await expect(page.getByTestId('section-count-sessions')).toHaveText('1');
	const problems = manifest.diagnostics.filter((d: { severity: string }) => d.severity === 'error' || d.severity === 'warning').length;
	await expect(page.getByTestId('section-count-problems')).toHaveText(String(problems));
	// every landmark leads to a live draft, so History waits for nothing
	await expect(page.getByTestId('section-count-history')).toHaveCount(0);
	await expect(page.getByTestId('section-library')).toHaveAttribute('title', /citation suggestion/);
	// each section is its own page, and the column marks it
	for (const id of ['incoming', 'library', 'sessions', 'history', 'problems']) {
		await page.getByTestId(`section-${id}`).click();
		await expect(page).toHaveURL(new RegExp(`/review/${id}$`));
		await expect(page.getByTestId(`section-${id}`)).toHaveAttribute('aria-current', 'page');
	}
});

test('Sessions lists every session with what it holds, each opening its transcript', async ({ page }) => {
	await page.goto('/review/sessions');
	const table = page.getByTestId('sessions-table');
	for (const s of manifest.sessions) await expect(table.getByTestId(`session-row-${s.id}`)).toContainText(s.state);
	await table.getByRole('link').first().click();
	await expect(page).toHaveURL(/\/session\//);
	// a static host serves no writes, so no verb is offered
	await page.goto('/review/sessions');
	await expect(page.locator('[data-testid^="sessions-close-"]')).toHaveCount(0);
});

test('History lists every step newest first, and flags a landmark no live draft leads to', async ({ page }) => {
	await serve(page, (m) => {
		const oldest = m.canon[0];
		delete oldest.in;
		const step = m.history.steps.find((s: { landmark?: string }) => s.landmark === oldest.path);
		delete step.in;
	});
	await page.goto('/review/history');
	const rows = page.getByTestId('history-table').locator('tbody tr');
	const steps = manifest.history.steps;
	await expect(rows).toHaveCount(steps.length);
	await expect(rows.first()).toHaveAttribute('data-testid', `history-step-${steps[steps.length - 1].step}`);
	const oldest = steps.find((s: { landmark?: string }) => s.landmark === manifest.canon[0].path);
	await expect(page.getByTestId(`history-orphan-${oldest.step}`)).toHaveText('no draft leads here');
	await expect(page.getByTestId(`history-step-${oldest.step}`).getByRole('link', { name: oldest.name })).toHaveAttribute('href', /\/canon\//);
	// and the column counts it
	await expect(page.getByTestId('section-count-history')).toHaveText('1');
});

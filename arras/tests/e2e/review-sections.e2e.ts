// Review, the quilt's management: its column lists the sections, each with what waits for the author there, and each section is a page of its own. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { manifest, serve } from '../manifest';

test('Review\'s column lists its sections, each counting what waits there, the current one marked', async ({ page }) => {
	await page.goto('/review');
	const list = page.getByTestId('review-sections');
	await expect(list.getByRole('link')).toHaveText([/^Changes/, /^Needs review/, /^Incoming/, /^Suggestions/, /^Library/, /^Sessions/, /^History/, /^Problems/]);
	await expect(page.getByTestId('section-needs-review')).toHaveAttribute('aria-current', 'page');
	// what changed since it was accepted, or was taken in; a block never accepted is listed there, not counted
	const unresolved = (manifest.unresolved ?? []).filter((r: { cause: string }) => r.cause !== 'never-accepted').length;
	await expect(page.getByTestId('section-count-needs-review')).toHaveText(String(unresolved));
	await expect(page.getByTestId('section-count-incoming')).toHaveText(String((manifest.contributions ?? []).length));
	// an open session waits for no one: it is said on hover, never counted
	await expect(page.getByTestId('section-count-sessions')).toHaveCount(0);
	await expect(page.getByTestId('section-sessions')).toHaveAttribute('title', /1 open session/);
	const problems = manifest.diagnostics.filter((d: { severity: string; owner?: string }) => (d.owner ?? 'person') === 'person' && (d.severity === 'error' || d.severity === 'warning')).length;
	await expect(page.getByTestId('section-count-problems')).toHaveText(String(problems));
	// every landmark leads to a live draft, so History waits for nothing
	await expect(page.getByTestId('section-count-history')).toHaveCount(0);
	await expect(page.getByTestId('section-library')).toHaveAttribute('title', /citation suggestion/);
	// each section is its own page, and the column marks it
	for (const id of ['changes', 'incoming', 'suggestions', 'library', 'sessions', 'history', 'problems']) {
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

test('History shows a document’s versions oldest first and Now, every act recorded, and flags a version no live draft leads to', async ({ page }) => {
	await serve(page, (m) => {
		const oldest = m.canon[0];
		delete oldest.in;
		const step = m.history.steps.find((s: { landmark?: string }) => s.landmark === oldest.path);
		delete step.in;
	});
	await page.goto('/review/history');
	await expect(page.getByTestId('history-tick')).toHaveText([/widgets-v2/, /widgets-v3/]);
	await expect(page.getByTestId('history-now')).toHaveText('Now');
	// the newest is chosen, and opens as a document of its own or beside the live text
	await expect(page.getByTestId('history-selected').locator('h2')).toHaveText('widgets-v3');
	await expect(page.getByTestId('history-open')).toHaveAttribute('href', '/canon/widgets-v3');
	await expect(page.getByTestId('history-compare')).toHaveAttribute('href', /\/canon\/widgets-v3\?beside=.*master.*&compare=1/);
	await page.getByTestId('history-tick').first().click();
	await expect(page.getByTestId('history-selected').locator('h2')).toHaveText('widgets-v2');
	const oldest = manifest.history.steps.find((s: { landmark?: string }) => s.landmark === manifest.canon[0].path);
	await expect(page.getByTestId(`history-orphan-${oldest.step}`)).toHaveText('no draft leads here');
	// every act, in words, newest first
	await page.getByTestId('history-acts').locator('summary').click();
	const acts = page.getByTestId('history-act');
	await expect(acts).toHaveCount(manifest.history.acts.length);
	await expect(acts.first()).toHaveAttribute('data-action', manifest.history.acts.at(-1).action);
	// and the column counts it
	await expect(page.getByTestId('section-count-history')).toHaveText('1');
});

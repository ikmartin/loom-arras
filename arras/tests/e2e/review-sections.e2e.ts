// Review, the quilt's management: its column lists the sections, each with what waits for the author there, and each section is a page of its own. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { manifest, QUICK, REFEREE, serve } from '../manifest';

test('Review\'s column lists its sections, each counting what waits there, the current one marked', async ({ page }) => {
	await page.goto('/review');
	const list = page.getByTestId('review-sections');
	await expect(list.getByRole('link')).toHaveText([/^Your Changes/, /^Proposed Changes/, /^Problems/, /^The Record/]);
	await expect(page.getByTestId('section-changes')).toHaveAttribute('aria-current', 'page');
	// what changed since it was accepted, or was taken in, and the one file edited since the look; a block never accepted is listed there, not counted
	const unresolved = (manifest.unresolved ?? []).filter((r: { cause: string }) => r.cause !== 'never-accepted').length;
	await expect(page.getByTestId('section-count-changes')).toHaveText(String(unresolved + 1));
	// an agent's copy, a suggestion with text and a citation
	await expect(page.getByTestId('section-count-proposed')).toHaveText('3');
	// an open session waits for no one: it is said on hover, never counted
	await expect(page.getByTestId('section-record')).toHaveAttribute('title', /1 open session/);
	const problems = manifest.diagnostics.filter((d: { severity: string; owner?: string }) => (d.owner ?? 'person') === 'person' && (d.severity === 'error' || d.severity === 'warning')).length;
	await expect(page.getByTestId('section-count-problems')).toHaveText(String(problems));
	// every landmark leads to a live draft, so The Record waits for nothing
	await expect(page.getByTestId('section-count-record')).toHaveCount(0);
	// each says what it is for
	await expect(page.getByTestId('section-changes')).toContainText('edits to keep, mathematics to accept');
	await expect(page.getByTestId('section-record')).toContainText('versions, sessions, everything done');
	await expect(page.getByTestId('section-proposed')).toHaveAttribute('title', /3 proposals to decide/);
	// each section is its own page, and the column marks it
	for (const id of ['proposed', 'problems', 'record']) {
		await page.getByTestId(`section-${id}`).click();
		await expect(page).toHaveURL(new RegExp(`/review/${id}$`));
		await expect(page.getByTestId(`section-${id}`)).toHaveAttribute('aria-current', 'page');
	}
});

test('The Record\'s Sessions lists every session with what awaits an answer and when it was last active, each opening its transcript', async ({ page }) => {
	await page.goto('/review/record/sessions');
	const table = page.getByTestId('sessions-table');
	await expect(table.locator('thead')).toContainText('Awaiting an answer');
	await expect(table.locator('thead')).toContainText('Last active');
	for (const s of manifest.sessions) await expect(table.getByTestId(`session-row-${s.id}`)).toContainText(s.state);
	// last active is the newest thing done in it, which opening it never moves
	const referee = manifest.sessions.find((s: { id: string }) => s.id === REFEREE)!;
	await expect(table.getByTestId(`session-last-${REFEREE}`)).toHaveAttribute('title', referee.last);
	await table.getByRole('link').first().click();
	await expect(page).toHaveURL(/\/session\//);
	// a static host serves no writes, so no verb is offered but Write here, which is the viewer's own
	await page.goto('/review/record/sessions');
	await expect(page.locator('[data-testid^="sessions-close-"]')).toHaveCount(0);
	await expect(page.getByTestId('sessions-new')).toHaveCount(0);
	await expect(page.getByTestId('sessions-writing')).toHaveText('Not writing in a session');
	await page.getByTestId(`sessions-write-here-${REFEREE}`).click();
	await expect(page.getByTestId('sessions-writing-here')).toBeVisible();
	await expect(page.getByTestId('session-footer-name')).toHaveText('referee');
	// a closed session is not offered as a place to write
	await expect(page.locator(`[data-testid="sessions-write-here-${QUICK}"]`)).toHaveCount(0);
});

test('The Record shows a document’s versions oldest first and Now, every act recorded on its own tab, and flags a version no live draft leads to', async ({ page }) => {
	await serve(page, (m) => {
		const oldest = m.canon[0];
		delete oldest.in;
		const step = m.history.steps.find((s: { landmark?: string }) => s.landmark === oldest.path);
		delete step.in;
	});
	await page.goto('/review/record');
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
	// and the column counts it
	await expect(page.getByTestId('section-count-record')).toHaveText('1');
	// every act, in words, newest first, on a tab of its own
	await page.getByTestId('record-tab-acts').click();
	await expect(page).toHaveURL(/\/review\/record\/acts$/);
	await expect(page.getByTestId('section-record')).toHaveAttribute('aria-current', 'page');
	const acts = page.getByTestId('history-act');
	await expect(acts).toHaveCount(manifest.history.acts.length);
	await expect(acts.first()).toHaveAttribute('data-action', manifest.history.acts.at(-1).action);
});

test('Your Changes keeps its help dot small, beside its heading', async ({ page }) => {
	await page.goto('/review');
	const dot = page.getByTestId('help-review');
	await expect(dot).toBeVisible();
	const box = (await dot.boundingBox())!;
	expect(box.width).toBeLessThanOrEqual(16);
	expect(box.height).toBeLessThanOrEqual(16);
});

test("a section's count stands beside its name, on the name's line, not under its description", async ({ page }) => {
	await page.goto('/review');
	const name = (await page.getByTestId('section-changes').locator('.section-name').boundingBox())!;
	const count = (await page.getByTestId('section-count-changes').boundingBox())!;
	expect(count.x).toBeGreaterThanOrEqual(name.x + name.width);
	expect(count.y).toBeLessThan(name.y + 16);
});

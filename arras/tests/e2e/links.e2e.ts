// Links (plan 0.14 phase 3): one form for what the quilt owns, `quilt:`, beside `cited:`, and one rule for where every link opens — revealed where it is already open, otherwise a new tab in the pane the reader is not in. An empty link is named by the viewer. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane } from '../workspace';

const REFEREE = 's-2026-09-16-0001';

/** The referee session's Chat, holding one message whose body is `html`. */
async function saying(page: Page, html: string) {
	await page.route(`**/build/transcripts/${REFEREE}/1.json`, (route) =>
		route.fulfill({ json: { session: REFEREE, page: 1, events: [{ seq: 1, kind: 'message', who: 'Referee Agent', when: '2026-09-16T10:00:00Z', body: '…', body_html: html }] } })
	);
}

test.describe('naming', () => {
	test('an empty link reads as the viewer names the thing; a titled one as written', async ({ page }) => {
		await saying(page, '<p><a href="quilt:sy-0003"></a>, <a href="quilt:sy-0003">the parity theorem</a>, <a href="quilt:a-2026-09-16-0001"></a> and <a href="quilt:drafting/main.tex"></a>.</p>');
		await page.goto('/session/' + REFEREE);
		const links = page.getByTestId('message-1').locator('a');
		await expect(links.nth(0)).toHaveText('Theorem 2.1');
		await expect(links.nth(1)).toHaveText('the parity theorem');
		await expect(links.nth(2)).toHaveText('objection on Theorem 2.1');
		await expect(links.nth(3)).toHaveText('main.tex');
	});
});

test.describe('the one rule', () => {
	test('what is open is revealed where it is, its place marked, and no tab is added', async ({ page }) => {
		await saying(page, '<p>See <a href="quilt:drafting/main.tex#sy-0003"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(1);
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toHaveClass(/travelled/);
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toBeInViewport();
	});

	test('what is not open opens as a new tab in the other pane, and the Chat stays', async ({ page }) => {
		// sy-999A is in the talk only, so the open main.tex does not hold it
		await saying(page, '<p>See <a href="quilt:sy-999A"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(2);
		await expect(pane(page, 0).getByRole('tab', { selected: true })).toContainText('sy-999A');
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
	});

	test('a node an open document holds is revealed in the document, not opened beside it (DR-280-ikmartin)', async ({ page }) => {
		await saying(page, '<p>See <a href="quilt:sy-0003"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(1);
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toHaveClass(/travelled/);
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toBeInViewport();
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
	});

	test('behind another tab, the document is brought forward to the node', async ({ page }) => {
		await saying(page, '<p>See <a href="quilt:sy-0003"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		// put main.tex behind the talk, opened from the side panel into the reader's pane
		await pane(page, 0).getByRole('tab').first().click();
		await page.locator('a', { hasText: /^talk\.tex$/ }).first().click();
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(2);
		await expect(pane(page, 0).getByRole('tab', { selected: true })).toContainText('talk.tex');
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		await expect(pane(page, 0).getByRole('tab', { selected: true })).toContainText('main.tex');
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toBeInViewport();
	});

	test("a document's link to its own content takes the same path: it scrolls there and marks it", async ({ page }) => {
		await page.goto('/master/main');
		const ref = pane(page, 0).locator('.fragment a.ref[href^="#"]').first();
		await expect(ref).toBeVisible();
		const id = decodeURIComponent((await ref.getAttribute('href'))!.slice(1));
		await ref.click();
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(1);
		await expect(pane(page, 0).locator(`[id="${id}"]`)).toHaveClass(/travelled/);
		await expect(pane(page, 0).locator(`[id="${id}"]`)).toBeInViewport();
	});

	test('a link to an annotation opens what it is on, with its box open', async ({ page }) => {
		await saying(page, '<p>My <a href="quilt:a-2026-09-16-0001"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		const box = pane(page, 0).getByTestId('comment-expanded');
		await expect(box).toBeVisible();
		await expect(box.locator('[data-annotation-id="a-2026-09-16-0001"]')).toHaveCount(1);
		await expect.poll(() => new URL(page.url()).searchParams.get('note')).toBe('a-2026-09-16-0001');
	});
});

test.describe('previews', () => {
	test('a quilt: link previews what it names, and a link to an annotation previews what it is on', async ({ page }) => {
		await saying(page, '<p><a href="quilt:sy-0003"></a> and <a href="quilt:a-2026-09-16-0001"></a>.</p>');
		await page.goto('/session/' + REFEREE);
		const links = page.getByTestId('message-1').locator('a');
		await links.nth(0).hover();
		await expect(page.getByTestId('link-preview')).toBeVisible();
		await expect(page.getByTestId('link-preview')).toContainText('widget');
		await page.mouse.move(0, 0);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);
		await links.nth(1).hover();
		await expect(page.getByTestId('link-preview')).toBeVisible();
		await expect(page.getByTestId('link-preview').locator('.env[data-id="sy-0003"]').first()).toBeVisible();
	});
});
